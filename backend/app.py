from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DATA_DIR = Path(os.getenv("STUDYSPACE_DATA_DIR", Path.home() / ".local/share/studyspace")).expanduser()
FILES_DIR = DATA_DIR / "files"
DB_PATH = DATA_DIR / "studyspace.sqlite3"
DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
FILES_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
try:
    os.chmod(DATA_DIR, 0o700)
    os.chmod(FILES_DIR, 0o700)
except OSError:
    pass

app = FastAPI(title="Studyspace API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS subjects (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', color TEXT NOT NULL DEFAULT 'violet', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notes (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS resources (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, kind TEXT NOT NULL, url TEXT NOT NULL DEFAULT '', file_name TEXT NOT NULL DEFAULT '', stored_name TEXT NOT NULL DEFAULT '', extracted_text TEXT NOT NULL DEFAULT '', transcript TEXT NOT NULL DEFAULT '', subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        if count == 0:
            conn.executemany("INSERT INTO subjects(name,description,color,created_at) VALUES(?,?,?,?)", [
                ("Signals & Systems", "Signals, transforms, systems, and intuition.", "violet", now()),
                ("Robotics & Control", "Kinematics, control, estimation, and experiments.", "mint", now()),
                ("Computer Architecture", "RISC-V, digital design, and low-level systems.", "amber", now()),
            ])


@app.on_event("startup")
def startup() -> None:
    init_db()
    try:
        os.chmod(DB_PATH, 0o600)
    except OSError:
        pass


def rows(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    with db() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def one(query: str, params: tuple = ()) -> dict[str, Any] | None:
    result = rows(query, params)
    return result[0] if result else None


class SubjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    color: str = Field(default="violet", max_length=24)


class NoteInput(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(default="", max_length=500_000)
    subject_id: int | None = None


class ResourceInput(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    kind: str = Field(default="link", pattern="^(link|video|course|transcript)$")
    url: str = Field(default="", max_length=2048)
    subject_id: int | None = None
    transcript: str = Field(default="", max_length=500_000)


class SettingsInput(BaseModel):
    provider: str = Field(default="ollama", pattern="^(ollama|openai-compatible)$")
    base_url: str = Field(default="", max_length=2048)
    model: str = Field(default="", max_length=200)
    api_key: str = Field(default="", max_length=500)


class ChatRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(min_length=1)
    model: str = Field(default="", max_length=200)
    temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    context: str = Field(default="", max_length=30_000)


@app.get("/api/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
        return {"ok": True, "provider": "ollama", "base_url": OLLAMA_BASE_URL, "version": "0.2.0"}
    except httpx.HTTPError:
        return {"ok": False, "provider": "ollama", "base_url": OLLAMA_BASE_URL, "version": "0.2.0"}


@app.get("/api/models")
async def models():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
        return {"models": [{"name": m.get("name", ""), "size": m.get("size", 0)} for m in response.json().get("models", []) if m.get("name")]}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Cannot reach Ollama. Check that it is running at " + OLLAMA_BASE_URL) from exc


@app.get("/api/overview")
def overview():
    return {
        "subjects": rows("SELECT * FROM subjects ORDER BY id"),
        "notes": rows("SELECT * FROM notes ORDER BY updated_at DESC LIMIT 100"),
        "resources": rows("SELECT id,title,kind,url,file_name,subject_id,created_at, length(extracted_text) AS text_length, length(transcript) AS transcript_length FROM resources ORDER BY created_at DESC LIMIT 200"),
        "counts": {
            "subjects": one("SELECT COUNT(*) AS n FROM subjects")["n"],
            "notes": one("SELECT COUNT(*) AS n FROM notes")["n"],
            "resources": one("SELECT COUNT(*) AS n FROM resources")["n"],
        },
    }


@app.post("/api/subjects")
def create_subject(body: SubjectInput):
    with db() as conn:
        cur = conn.execute("INSERT INTO subjects(name,description,color,created_at) VALUES(?,?,?,?)", (body.name.strip(), body.description.strip(), body.color, now()))
        subject_id = cur.lastrowid
    return one("SELECT * FROM subjects WHERE id=?", (subject_id,))


@app.put("/api/subjects/{subject_id}")
def update_subject(subject_id: int, body: SubjectInput):
    with db() as conn:
        cur = conn.execute("UPDATE subjects SET name=?,description=?,color=? WHERE id=?", (body.name.strip(), body.description.strip(), body.color, subject_id))
        if not cur.rowcount:
            raise HTTPException(404, "Subject not found")
    return one("SELECT * FROM subjects WHERE id=?", (subject_id,))


@app.delete("/api/subjects/{subject_id}")
def delete_subject(subject_id: int):
    with db() as conn:
        cur = conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Subject not found")
    return {"ok": True}


@app.post("/api/notes")
def create_note(body: NoteInput):
    with db() as conn:
        cur = conn.execute("INSERT INTO notes(title,body,subject_id,updated_at) VALUES(?,?,?,?)", (body.title.strip(), body.body, body.subject_id, now()))
        note_id = cur.lastrowid
    return one("SELECT * FROM notes WHERE id=?", (note_id,))


@app.put("/api/notes/{note_id}")
def update_note(note_id: int, body: NoteInput):
    with db() as conn:
        cur = conn.execute("UPDATE notes SET title=?,body=?,subject_id=?,updated_at=? WHERE id=?", (body.title.strip(), body.body, body.subject_id, now(), note_id))
        if not cur.rowcount:
            raise HTTPException(404, "Note not found")
    return one("SELECT * FROM notes WHERE id=?", (note_id,))


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int):
    with db() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Note not found")
    return {"ok": True}


@app.post("/api/resources")
def create_resource(body: ResourceInput):
    if body.url and not body.url.startswith(("https://", "http://")):
        raise HTTPException(400, "Resource URLs must begin with http:// or https://")
    with db() as conn:
        cur = conn.execute("INSERT INTO resources(title,kind,url,subject_id,transcript,created_at) VALUES(?,?,?,?,?,?)", (body.title.strip(), body.kind, body.url.strip(), body.subject_id, body.transcript, now()))
        resource_id = cur.lastrowid
    return one("SELECT * FROM resources WHERE id=?", (resource_id,))


@app.get("/api/resources/{resource_id}/transcript")
def get_saved_transcript(resource_id: int):
    resource = one("SELECT id,title,url,transcript FROM resources WHERE id=? AND kind='transcript'", (resource_id,))
    if not resource:
        raise HTTPException(404, "Saved transcript not found")
    return resource


@app.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int):
    resource = one("SELECT stored_name FROM resources WHERE id=?", (resource_id,))
    if not resource:
        raise HTTPException(404, "Resource not found")
    with db() as conn:
        conn.execute("DELETE FROM resources WHERE id=?", (resource_id,))
    if resource["stored_name"]:
        (FILES_DIR / resource["stored_name"]).unlink(missing_ok=True)
    return {"ok": True}


@app.post("/api/library/pdf")
async def upload_pdf(file: UploadFile = File(...), subject_id: int | None = None):
    filename = Path(file.filename or "document.pdf").name
    if not filename.lower().endswith(".pdf") or file.content_type not in ("application/pdf", "application/octet-stream", None):
        raise HTTPException(415, "Please upload a PDF file")
    content = await file.read()
    if len(content) > 80 * 1024 * 1024:
        raise HTTPException(413, "PDF exceeds the 80 MB limit")
    if not content.startswith(b"%PDF"):
        raise HTTPException(415, "The uploaded file does not look like a PDF")
    stored_name = secrets.token_hex(16) + ".pdf"
    path = FILES_DIR / stored_name
    path.write_bytes(content)
    extracted = ""
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        extracted = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(422, "Could not extract text from this PDF. It may be damaged or scanned; OCR is not included yet.") from exc
    with db() as conn:
        cur = conn.execute("INSERT INTO resources(title,kind,file_name,stored_name,extracted_text,subject_id,created_at) VALUES(?,?,?,?,?,?,?)", (filename, "pdf", filename, stored_name, extracted, subject_id, now()))
        resource_id = cur.lastrowid
    return {**one("SELECT id,title,kind,file_name,subject_id,created_at,length(extracted_text) AS text_length FROM resources WHERE id=?", (resource_id,)), "pages_text": len(extracted), "has_text": bool(extracted.strip())}


@app.get("/api/library/{resource_id}/file")
def pdf_file(resource_id: int):
    resource = one("SELECT stored_name,file_name FROM resources WHERE id=? AND kind='pdf'", (resource_id,))
    if not resource:
        raise HTTPException(404, "PDF not found")
    path = FILES_DIR / resource["stored_name"]
    if not path.is_file():
        raise HTTPException(404, "PDF file is missing from local storage")
    return FileResponse(path, media_type="application/pdf", filename=resource["file_name"], content_disposition_type="inline")


@app.get("/api/library/{resource_id}/text")
def pdf_text(resource_id: int):
    resource = one("SELECT id,title,extracted_text FROM resources WHERE id=? AND kind='pdf'", (resource_id,))
    if not resource:
        raise HTTPException(404, "PDF not found")
    return resource


def youtube_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtube-nocookie.com"}:
        return None
    if host == "youtu.be":
        return parsed.path.strip("/").split("/")[0] or None
    if parsed.path == "/watch":
        from urllib.parse import parse_qs
        return parse_qs(parsed.query).get("v", [None])[0]
    match = re.match(r"/(?:embed|shorts)/([^/?]+)", parsed.path)
    return match.group(1) if match else None


@app.post("/api/transcripts/youtube")
def fetch_youtube_transcript(body: dict[str, str]):
    url = body.get("url", "")
    video_id = youtube_id(url)
    if not video_id:
        raise HTTPException(400, "Provide a valid YouTube video URL")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        try:
            transcript = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
            segments = list(transcript)
            text = "\n".join(str(segment.text if hasattr(segment, "text") else segment.get("text", "")) for segment in segments)
        except (AttributeError, TypeError):
            segments = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
            text = "\n".join(segment.get("text", "") for segment in segments)
        if not text.strip():
            raise ValueError("Transcript was empty")
        return {"video_id": video_id, "transcript": text}
    except Exception as exc:
        raise HTTPException(422, "Transcript could not be fetched. The video may have captions disabled, be restricted, or the transcript service may have changed. You can paste a transcript manually.") from exc


@app.get("/api/settings")
def get_settings():
    stored = {row["key"]: row["value"] for row in rows("SELECT key,value FROM settings")}
    return {"provider": stored.get("provider", "ollama"), "base_url": stored.get("base_url", ""), "model": stored.get("model", ""), "has_api_key": bool(stored.get("api_key", "")), "api_key_hint": "Stored locally in Studyspace's private data directory" if stored.get("api_key") else "Not configured"}


@app.put("/api/settings")
def put_settings(body: SettingsInput):
    base_url = body.base_url.strip().rstrip("/")
    if body.provider == "openai-compatible":
        if not base_url.startswith("https://") and not base_url.startswith("http://127.0.0.1") and not base_url.startswith("http://localhost"):
            raise HTTPException(400, "Use HTTPS for remote providers; HTTP is allowed only for localhost endpoints")
        if not body.model.strip():
            raise HTTPException(400, "Enter the model name used by this provider")
    values = {"provider": body.provider, "base_url": base_url, "model": body.model.strip()}
    if body.api_key:
        values["api_key"] = body.api_key
    elif body.provider == "ollama":
        values["api_key"] = ""
    with db() as conn:
        for key, value in values.items():
            conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    try:
        os.chmod(DB_PATH, 0o600)
    except OSError:
        pass
    return get_settings()


@app.post("/api/chat")
async def chat(body: ChatRequest):
    settings = {row["key"]: row["value"] for row in rows("SELECT key,value FROM settings")}
    provider = settings.get("provider", "ollama")
    messages = list(body.messages)
    if body.context.strip():
        system_message = {"role": "system", "content": "Use the following user-provided study material as context. Be clear about what the source supports and what you infer.\n\n" + body.context[:30_000]}
        messages.insert(0, system_message)
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            if provider == "ollama":
                model = body.model or settings.get("model") or "qwen2.5:3b-instruct-q4_1"
                response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json={"model": model, "messages": messages, "stream": False, "options": {"temperature": body.temperature}})
                response.raise_for_status()
                payload = response.json()
                return {"content": payload.get("message", {}).get("content", ""), "model": payload.get("model", model), "provider": "ollama", "done": payload.get("done", True)}
            base_url = settings.get("base_url", "").rstrip("/")
            model = body.model or settings.get("model", "")
            if not base_url or not model:
                raise HTTPException(400, "Configure a cloud or OpenAI-compatible provider in Settings first")
            headers = {"Content-Type": "application/json"}
            if settings.get("api_key"):
                headers["Authorization"] = "Bearer " + settings["api_key"]
            endpoint = base_url if base_url.endswith("/chat/completions") else base_url + "/chat/completions"
            response = await client.post(endpoint, headers=headers, json={"model": model, "messages": messages, "temperature": body.temperature, "stream": False})
            response.raise_for_status()
            payload = response.json()
            return {"content": payload["choices"][0]["message"]["content"], "model": payload.get("model", model), "provider": "openai-compatible", "done": True}
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        detail = "The AI provider returned an error."
        try:
            detail = exc.response.json().get("error", {}).get("message") or exc.response.json().get("error") or detail
        except (ValueError, AttributeError):
            pass
        raise HTTPException(502, str(detail)) from exc
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(503, "Could not complete the AI request. Check the provider settings and connection.") from exc

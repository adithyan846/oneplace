import os
import sys
from pathlib import Path

# Add project root to path so imports work from both backend/ and project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from typing import Any, Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.storage import DocumentStore


class PageBody(BaseModel):
    page: int = Field(default=1, ge=1)
from backend.pdf_utils import (
    validate_pdf,
    get_pdf_info,
    extract_text_for_page,
    extract_text_for_document,
    is_scanned_pdf,
    check_ocr_availability,
)

DATA_DIR_DEFAULT = "./data"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")

app = FastAPI(title="Studyspace API", version="0.1.0")

# Local development only. Backend binds to 127.0.0.1 by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

store = DocumentStore(data_dir=os.environ.get("STUDYSPACE_DATA_DIR"))


class ChatRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    messages: list[dict[str, Any]] = Field(min_length=1)
    temperature: float = Field(default=0.4, ge=0.0, le=2.0)


# ---- PDF API routes ----

@app.get("/api/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
        return {"ok": True, "provider": "ollama", "base_url": OLLAMA_BASE_URL}
    except (httpx.HTTPError, ValueError):
        return {"ok": False, "provider": "ollama", "base_url": OLLAMA_BASE_URL}


@app.get("/api/models")
async def models():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            payload = response.json()
        return {
            "models": [
                {"name": model.get("name", ""), "size": model.get("size", 0)}
                for model in payload.get("models", [])
                if model.get("name")
            ]
        }
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Ollama. Check that it is running at " + OLLAMA_BASE_URL,
        ) from exc


@app.post("/api/chat")
async def chat(body: ChatRequest):
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": body.model,
                    "messages": body.messages,
                    "stream": False,
                    "options": {"temperature": body.temperature},
                },
            )
            response.raise_for_status()
            payload = response.json()
        message = payload.get("message", {})
        return {
            "content": message.get("content", ""),
            "model": payload.get("model", body.model),
            "done": payload.get("done", True),
        }
    except httpx.HTTPStatusError as exc:
        detail = "Ollama returned an error."
        try:
            detail = exc.response.json().get("error", detail)
        except ValueError:
            pass
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not connect to Ollama.") from exc


# ---- PDF import ----

ALLOWED_EXTENSION_CHECK = True  # always check via PDF header


@app.post("/api/pdfs")
async def upload_pdf(file: UploadFile = File(...)):
    """Import a PDF upload. Generates server-side UUID ID and filename.

    Accepts multipart/form-data with a file field named 'file'.
    Validates PDF header, saves to library directory, extracts metadata into SQLite.
    """
    import uuid
    import io

    # Read the uploaded file bytes
    contents = await file.read()

    # Generate server-side ID and filename
    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}.pdf"
    library_dir = Path(os.environ.get("STUDYSPACE_DATA_DIR", "./data")) / "library"
    library_dir.mkdir(parents=True, exist_ok=True)

    file_path = library_dir / safe_filename

    # Validate PDF header from bytes before saving
    if len(contents) < 5 or contents[:5] != b"%PDF-":
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF (missing %PDF- header)")

    # Save the file
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Extract PDF info using pypdf
    info = get_pdf_info(str(file_path))

    # Insert into SQLite
    store.insert_document(
        doc_id=doc_id,
        title=info.get("title", file.filename or safe_filename),
        filename=file.filename or safe_filename,
        file_path=str(file_path),
        page_count=info.get("page_count", 0),
        is_scanned=info.get("is_scanned", False),
        encrypted=info.get("encrypted", False),
    )

    return {
        "id": doc_id,
        "title": info.get("title", file.filename or safe_filename),
        "filename": safe_filename,
        "page_count": info.get("page_count", 0),
        "is_scanned": info.get("is_scanned", False),
        "encrypted": info.get("encrypted", False),
    }


@app.get("/api/pdfs")
def list_pdfs(include_deleted: bool = False):
    """List all imported documents with metadata."""
    docs = store.list_documents(include_deleted=include_deleted)
    return {"documents": docs, "count": len(docs), "include_deleted": include_deleted}


@app.get("/api/pdfs/{doc_id}")
def get_pdf_details(doc_id: str):
    """Get document details from SQLite."""
    doc = store.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.get("/api/pdfs/{doc_id}/info")
def get_pdf_info_endpoint(doc_id: str):
    """Get page count, is_scanned flag."""
    doc = store.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Re-extract info from the actual file
    file_path = doc["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    info = get_pdf_info(file_path)
    return {
        "page_count": info.get("page_count", doc.get("page_count", 0)),
        "is_scanned": info.get("is_scanned", doc.get("is_scanned", False)),
    }


@app.get("/api/pdfs/{doc_id}/text")
def get_pdf_text(doc_id: str, page: int = 1):
    """Get extracted text for a specific page, include page reference."""
    doc = store.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    text, is_scanned = extract_text_for_page(file_path, page)
    return {
        "page": page,
        "total_pages": doc.get("page_count", 0),
        "text": text,
        "is_scanned": is_scanned,
        "id": doc_id,
    }


@app.get("/api/pdfs/{doc_id}/progress")
def get_reading_progress(doc_id: str):
    """Get last read page + reading preferences."""
    doc = store.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    progress = store.get_progress(doc_id)
    return {
        "last_read_page": progress,
        "preferences": doc.get("preferences", "{}"),
    }


@app.put("/api/pdfs/{doc_id}/progress")
def set_reading_progress(doc_id: str, body: PageBody):
    """Save last read page + preferences."""
    store.set_progress(doc_id, body.page)
    return {"last_read_page": body.page, "doc_id": doc_id}


@app.put("/api/pdfs/{doc_id}/restore")
def restore_document(doc_id: str):
    """Restore a soft-deleted document."""
    store.restore(doc_id)
    return {"status": "restored", "doc_id": doc_id}


# Soft delete and permanent delete
# Same path; ?permanent=true triggers hard delete
@app.delete("/api/pdfs/{doc_id}")
def delete_pdf(doc_id: str, permanent: bool = Query(default=False)):
    """Delete a document from the library.

    - Without ?permanent=true: soft delete (keeps original file on disk)
    - With ?permanent=true: permanent delete (removes file from disk too)
    """
    if permanent:
        store.permanent_delete(doc_id)
        return {"status": "permanently_deleted", "doc_id": doc_id}
    else:
        store.soft_delete(doc_id)
        return {"status": "soft_deleted", "doc_id": doc_id}


@app.get("/api/ocr-status")
def ocr_status():
    """Check if OCR tooling is available."""
    available, message = check_ocr_availability()
    return {"available": available, "message": message}
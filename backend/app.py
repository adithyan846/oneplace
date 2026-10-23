import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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


class ChatRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    messages: list[dict[str, Any]] = Field(min_length=1)
    temperature: float = Field(default=0.4, ge=0.0, le=2.0)


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

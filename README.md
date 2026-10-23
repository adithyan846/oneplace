# Studyspace

A local-first engineering learning environment. This starter contains a Svelte + TypeScript frontend and a small FastAPI backend that connects to your existing Ollama instance.

## Requirements

- Arch Linux (or another Linux distribution)
- Node.js and npm
- Python 3.14+
- Ollama already installed and running at `http://127.0.0.1:11434`

## Start

Open a terminal in this directory.

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8765
```

Keep this terminal open.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open the local URL Vite prints (normally `http://127.0.0.1:5173`).

## What works in this first milestone

- Responsive dark study workspace UI
- Ollama connectivity status
- Model list from your existing Ollama server
- Chat against a selected local model
- No model downloads and no cloud calls
- No Docker, no global Python package installation

## Current limitations

This is a starter, not the finished learning environment. Subject persistence, PDF reading, course/video library, transcript extraction, hosted AI providers, and handwritten-note workflow are subsequent milestones. Do not store API keys in frontend code. When cloud providers are added, credentials must stay in the backend.

## Configuration

Optional environment variables for the backend:

```bash
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

The backend binds to loopback only. Do not change that unless you deliberately want network access.

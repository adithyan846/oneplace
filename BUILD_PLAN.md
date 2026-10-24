# Studyspace build plan

## Product rule

Studyspace is a personal learning cockpit, not a second operating system and not a pile of integrations that each need babysitting. Keep the core small, local-first, and useful without AI. Add complexity only when it makes a real learning task easier.

## Architecture now

```text
Svelte 5 + TypeScript (127.0.0.1:5173)
          |
          | HTTP JSON / file upload
          v
FastAPI (127.0.0.1:8765)
   |          |             |
   v          v             v
SQLite     Local files    AI provider adapter
subjects   imported PDFs  Ollama / OpenAI-compatible
notes      extracted text
resources
settings
```

- The browser owns presentation and user interaction, not secrets or persistent business logic.
- FastAPI validates requests, talks to AI providers, extracts PDF text, and persists data.
- SQLite stores subjects, notes, resources, and provider settings.
- Imported PDFs are separate files under the same private local data directory.
- The UI uses the backend only through `http://127.0.0.1:8765/api`.
- No model is downloaded by the application. Ollama uses the existing model store.

## Current user workflows

1. **Organise:** create a subject, then assign notes and resources to it.
2. **Read:** import a PDF, view the original in the browser, switch to extracted text, search matching lines, and send a bounded text excerpt to the tutor.
3. **Study from video:** save a video/course URL, open it externally, try caption retrieval, review the transcript, and save it locally.
4. **Think:** use a local Ollama model or configure an OpenAI-compatible API. Cloud keys remain on the backend and are not returned to the UI.
5. **Build:** use links to existing coding tools without embedding a fragile, partial IDE inside the app.

## Milestone order and rationale

### 0.2: make the basic library real (this release)

- [x] Persistent subjects, notes, and resources
- [x] PDF original + extracted text
- [x] Saved course/video URLs
- [x] Best-effort transcript retrieval and transcript storage
- [x] Local/cloud-compatible AI provider settings
- [x] Local-only data storage and loopback binding

### 0.3: reading and retrieval quality

1. Add OCR for image-only PDFs and notebook photos. Prefer a local engine so private notes do not need to leave the laptop. Check binary/model footprint before selecting it because disk space is constrained.
2. Preserve page numbers during extraction. Make the reader navigate between PDF pages and text pages rather than treating the document as one giant string.
3. Add reading position, bookmarks, highlights, and note links. This requires schema migrations, not ad hoc columns silently added at runtime.
4. Chunk long documents and retrieve only relevant sections. Tutor answers should identify document/page context. This is the point to consider embeddings; don't add a vector database before lexical search and chunking are measured.
5. Add export/backup before making the local database more complex.

### 0.4: courses and study sessions

1. Add adapters for specific course providers only after verifying their stable public interfaces and usage terms.
2. Model playlists, videos, transcripts, and course units explicitly; do not scrape arbitrary websites with one brittle generic scraper.
3. Keep transcript timestamps and links to the relevant video time.
4. Add progress tracking and study-session history.

### 0.5: handwritten notes and engineering workflow

1. Import notebook photos or scans.
2. Run local OCR and show the extracted text beside the image for correction. Handwriting recognition should never silently replace the source image.
3. Link notebook pages to subjects, PDFs, and code projects.
4. Add optional Jupyter integration with explicit session boundaries. Never expose arbitrary host shell execution to a web page.
5. If launching Neovim/local files from the UI is important, build a separate loopback desktop bridge with authentication/allowlisted actions; a browser cannot safely launch arbitrary local apps by itself.

### Later, only after evidence

- Hybrid lexical + semantic retrieval and embeddings
- Streaming chat and saved conversations
- Provider-specific adapters when OpenAI-compatible APIs are insufficient
- Automated site/playlist ingestion for supported providers
- Spaced repetition and generated quizzes based on cited material

## Explicit non-goals for the current release

- No OCR for scans yet.
- No video downloading or offline video playback.
- No full course-site crawler.
- No arbitrary code execution in the browser.
- No vector database or embedding model download.
- No claim that a transcript can always be extracted. Captions may be unavailable or a provider may block retrieval.

## Constraints and quality gates

- Disk space is scarce: avoid Docker, bundled models, and new AI runtimes.
- The UI should remain usable when AI is unavailable.
- Every new persisted entity needs a create/read/update/delete story and an export story before the schema grows much further.
- Keep the backend bound to loopback unless authentication and threat boundaries are reviewed.
- Keep cloud keys out of frontend state beyond the one-time form input; never expose the key through API responses or commit the local database.
- Before calling a milestone complete: run backend smoke tests, `npm run check`, `npm run build`, verify the important workflows manually, and test a clean install from the README.

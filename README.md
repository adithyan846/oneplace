# Studyspace 0.2

A local-first learning workspace for engineering study. This version extends the initial Svelte + TypeScript / FastAPI starter with persistent subjects and notes, PDF import and reading, course/video links, best-effort YouTube transcript retrieval, and a provider switch for Ollama or an OpenAI-compatible chat endpoint.

See [BUILD_PLAN.md](BUILD_PLAN.md) for architecture, workflow rationale, and the sequenced roadmap.

## What is implemented

- **Persistent subjects:** create and delete subjects; notes/resources become unsorted if their subject is deleted.
- **Persistent notes:** create, edit, and delete notes in SQLite.
- **PDF library:** upload PDFs (up to 80 MB), store the original locally, view it in the browser, and switch to extracted text. Text extraction uses `pypdf`.
- **Search/filter:** filter library entries by title/link and optionally by subject; find matching lines in extracted PDF text.
- **Course/video links:** save course pages, video links, and ordinary URLs.
- **YouTube transcript attempt:** fetch available captions where the current YouTube transcript endpoint permits it; review/edit and save the transcript. It is best-effort, not guaranteed. Manual transcript pasting remains possible.
- **AI tutor:** use the existing local Ollama models or configure an OpenAI-compatible `/chat/completions` endpoint. PDF extracted text can be attached as context (first 30,000 characters).
- **Local persistence:** SQLite and imported PDFs live under `~/.local/share/studyspace/` by default.
- **No Docker and no model downloads.**

## Not implemented yet / explicit limits

- OCR for scanned PDFs. The PDF can open, but image-only pages will not produce extracted text.
- True offline video playback/downloads. Course links open in the browser; no video is downloaded.
- Automatic scraping of entire course sites/playlists. Save individual URLs for now; scraping sites robustly requires per-site adapters and respectful rate limits.
- Handwriting/photo notebook ingestion and OCR. Next milestone should be image upload, local OCR, and linking the result to a subject/note.
- Streaming AI output, embeddings/semantic search, document chunking/RAG, and source citations. Current PDF context is a simple bounded text prefix, not a full retrieval system.
- In-browser code execution or a full IDE. Coding Lab provides practical links/commands, not a fake IDE; the browser cannot launch Neovim or arbitrary local applications without a separate desktop bridge.
- A secure OS keyring integration for cloud API credentials. Credentials are stored in the local SQLite database with restrictive directory/database permissions. Use this only on a trusted personal Linux account; do not commit the database.

## Requirements

- Linux, Node.js/npm, Python 3.11+ recommended (the user's system is Python 3.14; dependency compatibility should be checked at install time).
- Existing Ollama installation for local AI. Ollama is optional if using an OpenAI-compatible provider.
- Internet is only needed for npm/pip installs, external course links, transcript retrieval, and cloud AI.

## Run on Arch Linux

From the project root, start the backend in terminal 1:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8765
```

Start the frontend in terminal 2:

```bash
cd frontend
npm install
npm run check
npm run build
npm run dev
```

Open `http://127.0.0.1:5173`. The backend binds to loopback and the frontend binds to loopback. Do not expose either to a network without adding authentication and reviewing security.

### Environment variables

```bash
OLLAMA_BASE_URL=http://127.0.0.1:11434
STUDYSPACE_DATA_DIR="$HOME/.local/share/studyspace"
```

If you set `STUDYSPACE_DATA_DIR`, do so consistently before starting the backend; it controls where the SQLite database and imported PDFs live.

## API smoke checks

```bash
curl http://127.0.0.1:8765/api/health
curl http://127.0.0.1:8765/api/overview
curl http://127.0.0.1:8765/api/models
```

The first response reports whether the backend can reach Ollama. The app itself can still use the cloud-compatible provider if Ollama is unavailable.

## Roadmap

### Milestone 0.2 (this release)

- [x] SQLite-backed subjects, notes, and resources
- [x] PDF upload, original-file viewing, text extraction
- [x] Saved course/video URLs and transcript workflow
- [x] Ollama/cloud-compatible provider configuration
- [x] Local-first storage and loopback binding

### Milestone 0.3: make the reading workflow serious

- [ ] OCR for scanned PDFs and notebook photos (prefer a local OCR engine)
- [ ] Page-aware PDF text extraction and page navigation
- [ ] Persist reading position, bookmarks, highlights, and notes linked to a PDF/page
- [ ] Chunked retrieval for long documents, with source/page citations in tutor answers
- [ ] Import/export and backup/restore for the workspace

### Milestone 0.4: courses and study sessions

- [ ] Playlist/course import adapters for supported providers
- [ ] Transcript timestamps and jump-to-time links
- [ ] Playlist progress and watch/read status
- [ ] Session history and lightweight spaced-repetition prompts

### Milestone 0.5: notebooks and coding workflow

- [ ] Image capture/import and OCR for handwritten notes, with a human correction step
- [ ] Link code projects and notebooks to subjects
- [ ] Optional local desktop bridge for opening Neovim/filesystem paths (separate security review)
- [ ] Optional Jupyter kernel/session integration, not arbitrary code execution from the web UI

### Later, only if it earns its complexity

- [ ] Embeddings and hybrid lexical/semantic retrieval
- [ ] Streaming model responses and chat history
- [ ] Provider-specific integrations where OpenAI-compatible APIs are insufficient
- [ ] Automated course-site extraction only for sources with stable, permitted interfaces

## Git branch workflow: upgrade your existing repo without losing your work

**Do not copy this new folder over the existing repository.** Keep the downloaded release in a separate directory, then bring it into a branch with Git. This lets Git show exactly what changed and makes rollback possible.

### Option A: safest workflow, create a feature branch and copy the release into it

Extract this ZIP somewhere separate, for example `~/Downloads/studyspace-v0.2/`. Then in the existing repository:

```bash
cd /path/to/your/existing-studyspace-repo
git status --short
git switch -c feature/studyspace-v0.2
```

If `git status --short` shows important uncommitted work, commit it or stash it before proceeding. Then copy the release contents into the repository root. **Use this non-destructive command first**; it replaces files with matching paths and leaves unrelated repository files alone:

```bash
rsync -av \
  --exclude='.git/' --exclude='node_modules/' --exclude='dist/' --exclude='.venv/' \
  --exclude='*.sqlite3' --exclude='__pycache__/' --exclude='changes.patch' \
  ~/Downloads/studyspace-v0.2/ /path/to/your/existing-studyspace-repo/
```

Avoid `rsync --delete` unless you deliberately want to remove files in the repository that are absent from this release. That flag is a small chainsaw disguised as a sync option.

Review, test, and commit:

```bash
git status --short
git diff --stat
git diff
# run the backend/frontend checks described above
git add -A
git commit -m "Build Studyspace learning workflows"
```

When you're happy with the branch, merge it into your main branch:

```bash
git switch main
git merge --no-ff feature/studyspace-v0.2
```

Replace `main` with your actual default branch name if it differs.

### Option B: use a patch for review

This release also includes `changes.patch`, a Git patch against the original starter files. A patch is useful when your local repository matches that starter exactly:

```bash
git switch -c feature/studyspace-v0.2
git apply --check ~/Downloads/studyspace-v0.2/changes.patch
git apply ~/Downloads/studyspace-v0.2/changes.patch
git diff --check
```

If `git apply --check` fails, do not force it. Your repository has diverged; use Option A and review the diff instead.

## Data safety

- User data is not stored in the repository by default.
- Do not commit `~/.local/share/studyspace/` or API credentials.
- Back up the local data directory before changing versions.
- This is a personal local app, not a multi-user internet-facing service.

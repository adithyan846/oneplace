<script lang="ts">
  import { Activity, BookOpen, BookMarked, BrainCircuit, Check, ChevronRight, CircleHelp, Code2, FileText, FolderOpen, GraduationCap, LibraryBig, LoaderCircle, MessageCircle, Play, Plus, RefreshCw, Search, Send, Settings2, Sparkles, Trash2, Upload, Video, Wifi, WifiOff, X } from 'lucide-svelte';

  const API = 'http://127.0.0.1:8765/api';
  type Subject = { id: number; name: string; description: string; color: string; created_at: string };
  type Note = { id: number; title: string; body: string; subject_id: number | null; updated_at: string };
  type Resource = { id: number; title: string; kind: string; url: string; file_name: string; subject_id: number | null; created_at: string; text_length?: number; transcript_length?: number };
  type Model = { name: string; size: number };
  type Message = { role: 'user' | 'assistant'; content: string };

  let activeNav = $state('Home');
  let subjects = $state<Subject[]>([]);
  let notes = $state<Note[]>([]);
  let resources = $state<Resource[]>([]);
  let counts = $state({ subjects: 0, notes: 0, resources: 0 });
  let models = $state<Model[]>([]);
  let selectedModel = $state('');
  let provider = $state('ollama');
  let baseUrl = $state('');
  let cloudModel = $state('');
  let apiKey = $state('');
  let hasApiKey = $state(false);
  let apiKeyHint = $state('Not configured');
  let backendOnline = $state(false);
  let busy = $state(false);
  let chatBusy = $state(false);
  let toast = $state('');
  let query = $state('');
  let sidebarOpen = $state(true);
  let chatOpen = $state(false);
  let chatContext = $state('');
  let prompt = $state('');
  let messages = $state<Message[]>([{ role: 'assistant', content: 'I’m ready. Ask a question, or open a PDF and attach its extracted text as context.' }]);
  let selectedSubject = $state<number | null>(null);
  let showSubjectForm = $state(false);
  let subjectName = $state('');
  let subjectDescription = $state('');
  let subjectColor = $state('violet');
  let showNoteForm = $state(false);
  let editingNoteId = $state<number | null>(null);
  let noteTitle = $state('');
  let noteBody = $state('');
  let noteSubject = $state<number | null>(null);
  let resourceTitle = $state('');
  let resourceUrl = $state('');
  let resourceKind = $state('video');
  let resourceSubject = $state<number | null>(null);
  let uploadFile = $state<File | null>(null);
  let readerResource = $state<Resource | null>(null);
  let readerText = $state('');
  let readerMode = $state<'pdf' | 'text'>('pdf');
  let readerSearch = $state('');
  let readerProgress = $state<{last_page: number; font_size: number; line_spacing: number; content_width: string; theme: string }>({ last_page: 1, font_size: 14, line_spacing: 1.5, content_width: 'full', theme: 'dark' });
  let transcriptText = $state('');
  let transcriptTarget = $state<Resource | null>(null);
  let loadingTranscript = $state(false);
  let savedTranscriptTitle = $state('');
  let savedTranscriptText = $state('');

  const navItems = [
    { label: 'Home', icon: Activity }, { label: 'My subjects', icon: GraduationCap }, { label: 'Library', icon: LibraryBig },
    { label: 'Courses', icon: Play }, { label: 'Notes', icon: BookMarked }, { label: 'Coding lab', icon: Code2 }, { label: 'Settings', icon: Settings2 }
  ];

async function api(path: string, init: RequestInit = {}) {
    const response = await fetch(`${API}${path}`, init);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    return data;
}
function apiPut(path: string, data: object) {
    return fetch(`${API}${path}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json().catch(() => ({})));
}
  function flash(message: string) { toast = message; window.setTimeout(() => { if (toast === message) toast = ''; }, 4500); }
  function subjectNameFor(id: number | null) { return subjects.find((s) => s.id === id)?.name ?? 'Unsorted'; }
  function formatDate(value: string) { try { return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }); } catch { return ''; } }
  function formatSize(bytes: number) { return bytes > 1_000_000_000 ? `${(bytes / 1_000_000_000).toFixed(1)} GB` : `${Math.round(bytes / 1_000_000)} MB`; }
  function filteredResources(kind?: string) { return resources.filter((r) => (!kind || r.kind === kind || (kind === 'course' && ['video', 'course', 'transcript', 'link'].includes(r.kind))) && `${r.title} ${r.url} ${r.kind}`.toLowerCase().includes(query.toLowerCase())); }
  function selectNav(label: string) { activeNav = label; if (label === 'AI tutor') chatOpen = true; }

  async function refreshAll() {
    busy = true;
    try {
      const [overview, health, settings] = await Promise.all([
        api('/overview'), api('/health').catch(() => ({ ok: false })), api('/settings').catch(() => ({ provider: 'ollama', base_url: '', model: '', has_api_key: false, api_key_hint: 'Not configured' }))
      ]);
      subjects = overview.subjects ?? []; notes = overview.notes ?? []; resources = overview.resources ?? []; counts = overview.counts ?? counts;
      backendOnline = !!health.ok;
      provider = settings.provider ?? 'ollama'; baseUrl = settings.base_url ?? ''; cloudModel = settings.model ?? ''; hasApiKey = !!settings.has_api_key; apiKeyHint = settings.api_key_hint ?? 'Not configured';
      try {
        const modelData = await api('/models'); models = modelData.models ?? [];
        if (!selectedModel || !models.some((m) => m.name === selectedModel)) selectedModel = models.find((m) => m.name.includes('qwen2.5:3b'))?.name ?? models[0]?.name ?? '';
      } catch { models = []; }
    } catch (e) { flash(e instanceof Error ? e.message : 'Could not load Studyspace data. Is the backend running?'); }
    finally { busy = false; }
  }

  async function createSubject(event: SubmitEvent) {
    event.preventDefault(); if (!subjectName.trim()) return;
    try { await api('/subjects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: subjectName, description: subjectDescription, color: subjectColor }) }); subjectName = ''; subjectDescription = ''; showSubjectForm = false; await refreshAll(); flash('Subject created. A tiny administrative miracle.'); }
    catch (e) { flash(e instanceof Error ? e.message : 'Could not create subject'); }
  }
  async function deleteSubject(subject: Subject) {
    if (!confirm(`Delete “${subject.name}”? Notes and resources will become unsorted, not be deleted.`)) return;
    try { await api(`/subjects/${subject.id}`, { method: 'DELETE' }); await refreshAll(); flash('Subject deleted.'); } catch (e) { flash(e instanceof Error ? e.message : 'Could not delete subject'); }
  }
  function startNewNote() { editingNoteId = null; noteTitle = ''; noteBody = ''; noteSubject = selectedSubject; showNoteForm = true; }
  function editNote(note: Note) { editingNoteId = note.id; noteTitle = note.title; noteBody = note.body; noteSubject = note.subject_id; showNoteForm = true; }
  async function saveNote(event: SubmitEvent) {
    event.preventDefault(); if (!noteTitle.trim()) return;
    const payload = { title: noteTitle, body: noteBody, subject_id: noteSubject };
    try { await api(editingNoteId ? `/notes/${editingNoteId}` : '/notes', { method: editingNoteId ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); showNoteForm = false; await refreshAll(); flash('Note saved locally.'); }
    catch (e) { flash(e instanceof Error ? e.message : 'Could not save note'); }
  }
  async function deleteNote(note: Note) {
    if (!confirm(`Delete “${note.title}”?`)) return;
    try { await api(`/notes/${note.id}`, { method: 'DELETE' }); await refreshAll(); flash('Note deleted.'); } catch (e) { flash(e instanceof Error ? e.message : 'Could not delete note'); }
  }
  async function addResource(event: SubmitEvent) {
    event.preventDefault(); if (!resourceTitle.trim() || !resourceUrl.trim()) return;
    try { await api('/resources', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: resourceTitle, url: resourceUrl, kind: resourceKind, subject_id: resourceSubject }) }); resourceTitle = ''; resourceUrl = ''; await refreshAll(); flash('Resource saved.'); }
    catch (e) { flash(e instanceof Error ? e.message : 'Could not save resource'); }
  }
  async function uploadPdf(event: SubmitEvent) {
    event.preventDefault(); if (!uploadFile) { flash('Choose a PDF first.'); return; }
    const form = new FormData(); form.append('file', uploadFile);
    const subject = selectedSubject ?? resourceSubject;
    const url = `${API}/library/pdf${subject ? `?subject_id=${subject}` : ''}`;
    busy = true;
    try { const response = await fetch(url, { method: 'POST', body: form }); const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Upload failed'); uploadFile = null; await refreshAll(); const resource = resources.find((r) => r.id === data.id) ?? data; openReader(resource); flash(data.has_text ? `PDF imported. Extracted ${data.pages_text.toLocaleString()} characters.` : 'PDF imported, but it has no extractable text. Scanned-page OCR is not included yet.'); }
    catch (e) { flash(e instanceof Error ? e.message : 'PDF upload failed'); }
    finally { busy = false; }
  }
  async function openReader(resource: Resource) {
    readerResource = resource; readerMode = 'pdf'; readerText = ''; readerSearch = '';
    try { const data = await api(`/library/${resource.id}/text`); readerText = data.extracted_text ?? ''; }
    catch (e) { flash(e instanceof Error ? e.message : 'Could not read PDF text'); }
  }
  async function deleteResource(resource: Resource) {
    if (!confirm(`Remove “${resource.title}” from your library?`)) return;
    try { await api(`/resources/${resource.id}`, { method: 'DELETE' }); if (readerResource?.id === resource.id) readerResource = null; await refreshAll(); flash('Resource removed.'); }
    catch (e) { flash(e instanceof Error ? e.message : 'Could not remove resource'); }
  }
  async function openSavedTranscript(resource: Resource) {
    try { const data = await api(`/resources/${resource.id}/transcript`); savedTranscriptTitle = data.title; savedTranscriptText = data.transcript ?? ''; }
    catch (e) { flash(e instanceof Error ? e.message : 'Could not open transcript'); }
  }
  async function fetchTranscript(resource: Resource) {
    loadingTranscript = true; transcriptTarget = resource;
    try { const data = await api('/transcripts/youtube', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: resource.url }) }); transcriptText = data.transcript; }
    catch (e) { flash(e instanceof Error ? e.message : 'Could not retrieve transcript'); }
    finally { loadingTranscript = false; }
  }
  async function saveTranscript() {
    if (!transcriptTarget || !transcriptText.trim()) return;
    try {
      await api('/resources', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: `${transcriptTarget.title} · transcript`, kind: 'transcript', url: transcriptTarget.url, subject_id: transcriptTarget.subject_id, transcript: transcriptText }) });
      await refreshAll(); transcriptTarget = null; transcriptText = ''; flash('Transcript saved to your library.');
    } catch (e) { flash(e instanceof Error ? e.message : 'Could not save transcript'); }
  }
  async function saveSettings(event: SubmitEvent) {
    event.preventDefault();
    try { const data = await api('/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider, base_url: baseUrl, model: cloudModel, api_key: apiKey }) }); hasApiKey = data.has_api_key; apiKeyHint = data.api_key_hint; apiKey = ''; flash('Provider settings saved locally.'); }
    catch (e) { flash(e instanceof Error ? e.message : 'Could not save settings'); }
  }
  async function sendMessage(event?: SubmitEvent) {
    event?.preventDefault(); const content = prompt.trim(); if (!content || chatBusy) return;
    messages = [...messages, { role: 'user', content }]; prompt = ''; chatBusy = true;
    try {
      const data = await api('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: provider === 'ollama' ? selectedModel : cloudModel, messages: messages.map((m) => ({ role: m.role, content: m.content })), context: chatContext }) });
      messages = [...messages, { role: 'assistant', content: data.content }];
    } catch (e) { messages = [...messages, { role: 'assistant', content: `Request failed: ${e instanceof Error ? e.message : 'unknown error'}` }]; }
    finally { chatBusy = false; }
  }
  function askAboutPdf() { if (!readerResource) return; chatContext = readerText.slice(0, 30000); chatOpen = true; flash('PDF text attached as tutor context (up to 30,000 characters).'); }

  $effect(() => { refreshAll(); });
</script>

<svelte:head><title>{activeNav} · Studyspace</title><meta name="theme-color" content="#11131a" /></svelte:head>

<div class="app-shell">
  {#if sidebarOpen}
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark"><GraduationCap size={21}/></div><div class="brand-copy"><span class="brand-name">studyspace<span class="brand-dot">.</span></span><span class="brand-caption">YOUR PERSONAL UNIVERSITY</span></div><button class="icon-button sidebar-collapse" aria-label="Collapse sidebar" onclick={() => sidebarOpen = false}>‹</button></div>
      <button class="search-button" onclick={() => document.getElementById('global-search')?.focus()}><Search size={15}/><span>Search workspace</span><kbd>/</kbd></button>
      <div class="nav-label">WORKSPACE</div>
      <nav class="nav-list">{#each navItems as item}<button class:active={activeNav === item.label} class="nav-item" onclick={() => selectNav(item.label)}><item.icon size={17}/><span>{item.label}</span>{#if item.label === 'Library'}<span class="nav-count">{counts.resources}</span>{/if}</button>{/each}</nav>
      <div class="nav-label subjects-label">YOUR SUBJECTS <button class="tiny-icon" aria-label="Add subject" onclick={() => { activeNav = 'My subjects'; showSubjectForm = true; }}><Plus size={14}/></button></div>
      <div class="mini-subjects">{#each subjects.slice(0, 5) as subject}<button onclick={() => { selectedSubject = subject.id; activeNav = 'My subjects'; }}><span class={`subject-dot dot-${subject.color}`}></span>{subject.name}</button>{/each}</div>
      <div class="sidebar-spacer"></div>
      <div class="local-card"><div class="local-card-top"><span class:online={backendOnline} class="status-dot"></span><span>{backendOnline ? 'LOCAL API CONNECTED' : 'API NOT REACHABLE'}</span></div><p>{backendOnline ? `${models.length} local models detected.` : 'Start the Studyspace backend and Ollama.'}</p><button class="text-action" onclick={refreshAll}>Refresh connection <ChevronRight size={13}/></button></div>
      <div class="sidebar-footer"><span class="avatar">S</span><div><strong>Personal workspace</strong><small>Stored on this device</small></div></div>
    </aside>
  {:else}<button class="restore-sidebar" aria-label="Open sidebar" onclick={() => sidebarOpen = true}>☰</button>{/if}

  <main class="main-area">
    <header class="topbar"><div class="breadcrumbs"><span>Workspace</span><span class="crumb-sep">/</span><strong>{activeNav}</strong></div><div class="topbar-actions"><div class="offline-pill"><span class:online={backendOnline} class="status-dot"></span> LOCAL FIRST</div><button class="icon-button" aria-label="Help" onclick={() => flash('Your notes, subjects, PDFs, and saved resources live in ~/.local/share/studyspace.')}><CircleHelp size={18}/></button></div></header>
    <div class="page-content">
      {#if activeNav === 'Home'}
        <section class="welcome-row"><div><div class="eyebrow"><span class="eyebrow-line"></span> YOUR SPACE TO FIGURE THINGS OUT</div><h1>Good morning<span class="heading-period">.</span></h1><p class="welcome-subtitle">Pick up where your curiosity left off.</p></div><div class="date-chip"><Activity size={14}/> LOCAL · PERSISTENT · YOURS</div></section>
        <section class="continue-card"><div class="continue-art"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="art-core"><Activity size={39}/></div><span class="formula formula-one">x(t)</span><span class="formula formula-two">H(jω)</span><span class="formula formula-three">∫ f(t)dt</span></div><div class="continue-content"><div class="continue-meta"><span class="overline">YOUR LEARNING WORKSPACE</span><span class="pill pill-violet">LOCAL FIRST</span></div><h2>Keep the thread.</h2><p>Books, lecture links, notes, and your local AI tutor in one place. Less tab archaeology, more understanding.</p><div class="continue-bottom"><span class="progress-label"><span class="progress-dot"></span>{counts.resources} resources · {counts.notes} notes · {counts.subjects} subjects</span><button class="primary-button" onclick={() => activeNav = 'Library'}>Open library <ChevronRight size={15}/></button></div></div></section>
        <section class="section-block"><div class="section-heading"><div><h3>Your learning worlds</h3><p>Persistent subjects, ready to organise.</p></div><button class="quiet-button" onclick={() => activeNav = 'My subjects'}>All subjects <ChevronRight size={14}/></button></div><div class="subject-grid">{#each subjects.slice(0, 3) as subject}<button class="subject-card" onclick={() => { selectedSubject = subject.id; activeNav = 'My subjects'; }}><div class="subject-card-top"><div class={`subject-icon ${subject.color}`}><GraduationCap size={19}/></div><span class="muted-icon">↗</span></div><span class="card-tag">SUBJECT</span><h4>{subject.name}</h4><p>{subject.description || 'A place to collect materials and ideas.'}</p><div class="card-bottom"><span class="tiny-indicator"></span><span>Open workspace</span><ChevronRight size={15}/></div></button>{/each}<button class="add-subject-card" onclick={() => { activeNav = 'My subjects'; showSubjectForm = true; }}><div class="add-icon"><Plus size={19}/></div><strong>Make room for a new obsession</strong><span>Create a subject workspace</span></button></div></section>
        <section class="section-block"><div class="section-heading"><div><h3>Recent materials</h3><p>Last things you added to the system.</p></div><button class="quiet-button" onclick={() => activeNav = 'Library'}>Browse library <ChevronRight size={14}/></button></div>{#if resources.length}<div class="resource-list">{#each resources.slice(0, 4) as resource}<button class="resource-row" onclick={() => resource.kind === 'pdf' ? openReader(resource) : window.open(resource.url, '_blank', 'noopener,noreferrer')}><div class="resource-icon">{#if resource.kind === 'pdf'}<FileText size={18}/>{:else if resource.kind === 'video'}<Video size={18}/>{:else}<BookOpen size={18}/>{/if}</div><div class="resource-main"><strong>{resource.title}</strong><span>{resource.kind.toUpperCase()} · {subjectNameFor(resource.subject_id)}</span></div><ChevronRight size={16}/></button>{/each}</div>{:else}<div class="quiet-empty">Your library is empty. Start by importing a PDF or saving a lecture link.</div>{/if}</section>
      {:else if activeNav === 'Courses'}
        <div class="page-heading"><div class="eyebrow"><span class="eyebrow-line"></span> LECTURES AND LEARNING PATHS</div><h1>Courses<span class="heading-period">.</span></h1><p class="welcome-subtitle">Save course pages, video links, and available transcripts.</p></div>
        <section class="panel"><div class="panel-title"><div><h3>Save a course or video</h3><p>External videos open in your browser. Transcripts depend on captions being available.</p></div><Video size={18}/></div><form class="stack-form" onsubmit={addResource}><label>Title<input bind:value={resourceTitle} required placeholder="e.g. MIT OCW · Signals and Systems"/></label><label>URL<input bind:value={resourceUrl} type="url" required placeholder="https://…"/></label><div class="form-row"><label>Type<select bind:value={resourceKind}><option value="video">Video</option><option value="course">Course</option><option value="link">Resource link</option></select></label><label>Subject<select bind:value={resourceSubject}><option value={null}>Unsorted</option>{#each subjects as subject}<option value={subject.id}>{subject.name}</option>{/each}</select></label></div><button class="primary-button" type="submit"><Plus size={15}/> Save resource</button></form></section>
        <div class="section-heading list-heading"><div><h3>Your course links</h3><p>{filteredResources('course').length} saved links and videos.</p></div><input class="search-input compact-search" bind:value={query} placeholder="Filter courses…"/></div><div class="resource-list">{#each filteredResources('course') as resource}<article class="resource-row"><div class="resource-icon"><Video size={18}/></div><div class="resource-main"><strong>{resource.title}</strong><span>{subjectNameFor(resource.subject_id)} · {resource.url}</span></div><div class="resource-actions"><button class="quiet-button small" onclick={() => window.open(resource.url, '_blank', 'noopener,noreferrer')}>Open</button>{#if resource.url.includes('youtube.com') || resource.url.includes('youtu.be')}<button class="quiet-button small" onclick={() => fetchTranscript(resource)}>Get transcript</button>{/if}<button class="icon-button danger" aria-label="Delete course link" onclick={() => deleteResource(resource)}><Trash2 size={14}/></button></div></article>{/each}</div>
        {#if transcriptTarget}<section class="panel transcript-panel"><div class="panel-title"><div><h3>Transcript · {transcriptTarget.title}</h3><p>Check it before saving. Caption extraction is best-effort, because platforms enjoy changing their interfaces.</p></div><button class="icon-button" onclick={() => { transcriptTarget = null; transcriptText = ''; }}><X size={16}/></button></div>{#if loadingTranscript}<div class="quiet-empty"><LoaderCircle class="spin" size={17}/> Fetching transcript…</div>{:else}<textarea class="transcript-editor" bind:value={transcriptText} rows="12" placeholder="Paste a transcript here if automatic retrieval is unavailable."/><div class="form-actions"><button class="quiet-button" onclick={() => { transcriptTarget = null; transcriptText = ''; }}>Cancel</button><button class="primary-button" onclick={saveTranscript} disabled={!transcriptText.trim()}><Check size={15}/> Save transcript</button></div>{/if}</section>{/if}
      {:else if activeNav === 'Notes'}
        <div class="page-heading"><div class="eyebrow"><span class="eyebrow-line"></span> YOUR THINKING, KEPT</div><div class="heading-row"><div><h1>Notes<span class="heading-period">.</span></h1><p class="welcome-subtitle">Write down the reasoning, not just the answer.</p></div><button class="primary-button" onclick={startNewNote}><Plus size={15}/> New note</button></div></div>
        {#if showNoteForm}<form class="panel form-panel" onsubmit={saveNote}><label>Title<input bind:value={noteTitle} required placeholder="A useful thing I figured out"/></label><label>Subject<select bind:value={noteSubject}><option value={null}>Unsorted</option>{#each subjects as subject}<option value={subject.id}>{subject.name}</option>{/each}</select></label><label>Note<textarea bind:value={noteBody} rows="12" placeholder="Derivations, questions, observations…"/></label><div class="form-actions"><button type="button" class="quiet-button" onclick={() => showNoteForm = false}>Cancel</button><button type="submit" class="primary-button"><Check size={15}/> Save note</button></div></form>{/if}
        <div class="notes-grid">{#each notes.filter((n) => selectedSubject === null || n.subject_id === selectedSubject) as note}<article class="note-card"><div class="note-card-top"><span class="card-tag">{subjectNameFor(note.subject_id)}</span><div class="resource-actions"><button class="icon-button" aria-label="Edit note" onclick={() => editNote(note)}><FileText size={15}/></button><button class="icon-button danger" aria-label="Delete note" onclick={() => deleteNote(note)}><Trash2 size={14}/></button></div></div><button class="note-open" onclick={() => editNote(note)}><h3>{note.title}</h3><p>{note.body || 'An empty note, patiently awaiting human thought.'}</p></button><span class="note-date">UPDATED {formatDate(note.updated_at)}</span></article>{/each}{#if !notes.length}<div class="quiet-empty">No notes yet. Create one and it will persist across restarts.</div>{/if}</div>
      {:else if activeNav === 'Coding lab'}
        <div class="page-heading"><div class="eyebrow"><span class="eyebrow-line"></span> BUILD AND EXPERIMENT</div><h1>Coding lab<span class="heading-period">.</span></h1><p class="welcome-subtitle">Keep the real tools you already use. Studyspace organises the workflow; it does not impersonate a full IDE.</p></div>
        <div class="tool-grid large-tools"><a class="tool-card" href="http://127.0.0.1:8888" target="_blank" rel="noreferrer"><div class="tool-icon tool-purple"><Code2 size={18}/></div><div><strong>JupyterLab</strong><span>Open if running locally at port 8888</span></div><ChevronRight size={15}/></a><a class="tool-card" href="https://www.kaggle.com/code" target="_blank" rel="noreferrer"><div class="tool-icon tool-blue"><Activity size={18}/></div><div><strong>Kaggle Notebooks</strong><span>Hosted notebooks; internet required</span></div><ChevronRight size={15}/></a><a class="tool-card" href="https://github.com" target="_blank" rel="noreferrer"><div class="tool-icon tool-gold"><FolderOpen size={18}/></div><div><strong>GitHub</strong><span>Repos, issues, and project history</span></div><ChevronRight size={15}/></a><a class="tool-card" href="https://docs.python.org/3/" target="_blank" rel="noreferrer"><div class="tool-icon tool-blue"><BookOpen size={18}/></div><div><strong>Python documentation</strong><span>Reference, not a random tutorial rabbit hole</span></div><ChevronRight size={15}/></a></div>
        <section class="panel"><h3>Local project shortcuts</h3><p class="muted-note">Browser security prevents this page from launching Neovim or opening arbitrary filesystem paths directly. Keep project paths in notes, and launch tools from your terminal or a future desktop bridge.</p><div class="code-line"><code>nvim ~/your-project</code><button class="quiet-button small" onclick={() => navigator.clipboard.writeText('nvim ~/your-project')}>Copy command</button></div><div class="code-line"><code>jupyter lab</code><button class="quiet-button small" onclick={() => navigator.clipboard.writeText('jupyter lab')}>Copy command</button></div></section>
      {:else if activeNav === 'Settings'}
        <div class="page-heading"><div class="eyebrow"><span class="eyebrow-line"></span> YOUR ENVIRONMENT</div><h1>Settings<span class="heading-period">.</span></h1><p class="welcome-subtitle">Choose a local model or configure an OpenAI-compatible endpoint.</p></div>
        <form class="panel form-panel settings-form" onsubmit={saveSettings}><label>AI provider<select bind:value={provider}><option value="ollama">Local Ollama</option><option value="openai-compatible">OpenAI-compatible API</option></select></label>{#if provider === 'ollama'}<div class="settings-status"><span class:online={backendOnline} class="status-dot"></span><div><strong>{backendOnline ? 'Ollama reachable' : 'Ollama unavailable'}</strong><p>Uses your existing model store at 127.0.0.1:11434. No new models are downloaded.</p></div><button type="button" class="quiet-button small" onclick={refreshAll}><RefreshCw size={13}/> Check</button></div><label>Local model<select bind:value={selectedModel}>{#each models as model}<option value={model.name}>{model.name} · {formatSize(model.size)}</option>{/each}</select></label>{:else}<label>API base URL<input bind:value={baseUrl} required placeholder="https://api.example.com/v1"/><small>Use HTTPS for remote providers. The endpoint must support /chat/completions.</small></label><label>Model name<input bind:value={cloudModel} required placeholder="e.g. gpt-4o-mini or provider/model"/></label><label>API key<input bind:value={apiKey} type="password" autocomplete="new-password" placeholder={hasApiKey ? 'Saved key exists; enter a new key to replace it' : 'Paste API key'} /><small>{apiKeyHint}. Keys stay in the local backend database and are never sent to the frontend except as a yes/no status.</small></label>{/if}<div class="form-actions"><button class="primary-button" type="submit"><Check size={15}/> Save provider settings</button></div></form>
        <section class="panel"><h3>Local storage</h3><p class="muted-note">Studyspace stores subjects, notes, settings, imported PDFs, and extracted text under <code>~/.local/share/studyspace/</code>. Back up that directory to back up your workspace. API keys are stored locally in the SQLite database; keep your Linux user account protected.</p></section>
      {/if}
    </div>
  </main>

  <button class="tutor-fab" onclick={() => chatOpen = !chatOpen} aria-label="Toggle AI tutor">{#if chatOpen}<X size={19}/>{:else}<BrainCircuit size={20}/>{/if}<span>{chatOpen ? 'Close tutor' : 'Ask your tutor'}</span></button>
  {#if chatOpen}<aside class="chat-drawer"><div class="chat-header"><div class="chat-heading-icon"><Sparkles size={17}/></div><div class="chat-heading"><strong>Your AI tutor</strong><span><span class:online={backendOnline} class="status-dot"></span>{provider === 'ollama' ? 'Local · Ollama' : 'OpenAI-compatible provider'}</span></div><button class="icon-button" aria-label="Close tutor" onclick={() => chatOpen = false}><X size={17}/></button></div><div class="model-row"><span>MODEL</span>{#if provider === 'ollama'}<select bind:value={selectedModel} aria-label="Choose model">{#each models as model}<option value={model.name}>{model.name}</option>{/each}</select>{:else}<span class="cloud-model-label">{cloudModel || 'Configure in Settings'}</span>{/if}<button class="tiny-icon" aria-label="Refresh models" onclick={refreshAll}><RefreshCw size={14}/></button></div><div class="context-row"><label><input type="checkbox" checked={!!chatContext} onchange={(e) => { if (!(e.currentTarget as HTMLInputElement).checked) chatContext = ''; }}/> {chatContext ? 'PDF context attached' : 'No document context'}</label>{#if chatContext}<button class="tiny-icon" onclick={() => chatContext = ''} aria-label="Remove context"><X size={13}/></button>{/if}</div><div class="chat-messages">{#each messages as message}<div class:from-user={message.role === 'user'} class="message">{#if message.role === 'assistant'}<div class="message-avatar"><Sparkles size={13}/></div>{/if}<div class="message-body">{message.content}</div></div>{/each}{#if chatBusy}<div class="message"><div class="message-avatar"><LoaderCircle size={13} class="spin"/></div><div class="message-body thinking">Thinking through it…</div></div>{/if}</div><form class="chat-composer" onsubmit={sendMessage}><textarea bind:value={prompt} placeholder="Ask about something you're learning…" rows="3" onkeydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendMessage(); } }}></textarea><div class="composer-bottom"><span><Wifi size={12}/> {provider === 'ollama' ? 'Local model' : 'Configured provider'}</span><button class="send-button" disabled={!prompt.trim() || chatBusy} aria-label="Send message"><Send size={15}/></button></div></form></aside>{/if}
  {#if toast}<div class="toast" role="status"><span>{toast}</span><button aria-label="Dismiss" onclick={() => toast = ''}><X size={15}/></button></div>{/if}
</div>

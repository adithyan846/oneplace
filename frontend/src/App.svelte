<script lang="ts">
  import {
    Activity, ArrowDownLeft, ArrowRight, BookOpen, BookMarked, BrainCircuit,
    Check, ChevronDown, CircleHelp, Clock3, Code2, Command, FileText,
    FolderOpen, GraduationCap, Headphones, LibraryBig, ListTodo, LoaderCircle,
    MessageCircle, MoreHorizontal, PanelLeftClose, Play, Plus, Search, Send,
    Settings2, Sparkles, Video, Wifi, WifiOff, X
  } from 'lucide-svelte';

  type Model = { name: string; size: number };
  type ChatMessage = { role: 'user' | 'assistant'; content: string };

  let activeNav = $state('Home');
  let models = $state<Model[]>([]);
  let selectedModel = $state('');
  let ollamaOnline = $state(false);
  let modelLoading = $state(true);
  let prompt = $state('');
  let chatBusy = $state(false);
  let chatOpen = $state(false);
  let messages = $state<ChatMessage[]>([
    { role: 'assistant', content: 'Your study space is ready. Ask me about a concept, or connect a course and its materials as we build out the library.' }
  ]);
  let error = $state('');
  let sidebarOpen = $state(true);

  const navItems = [
    { label: 'Home', icon: Activity },
    { label: 'My subjects', icon: GraduationCap },
    { label: 'Library', icon: LibraryBig },
    { label: 'Courses', icon: Play },
    { label: 'Notes', icon: BookMarked },
    { label: 'Coding lab', icon: Code2 }
  ];

  const subjects = [
    { title: 'Signals & Systems', detail: 'Textbook · Lectures · Simulations', tag: 'IN PROGRESS', color: 'violet', icon: Activity },
    { title: 'Robotics & Control', detail: 'Notes · Papers · Experiments', tag: 'YOUR SUBJECT', color: 'mint', icon: Command },
    { title: 'Computer Architecture', detail: 'RISC-V · Digital design · Labs', tag: 'YOUR SUBJECT', color: 'amber', icon: Code2 }
  ];

  function formatSize(bytes: number) {
    if (!bytes) return '';
    return bytes >= 1_000_000_000
      ? `${(bytes / 1_000_000_000).toFixed(1)} GB`
      : `${(bytes / 1_000_000).toFixed(0)} MB`;
  }

  async function refreshModels() {
    modelLoading = true;
    error = '';
    try {
      const health = await fetch('http://127.0.0.1:8765/api/health');
      const healthData = await health.json();
      ollamaOnline = !!healthData.ok;
      if (!ollamaOnline) throw new Error('Ollama is not reachable.');
      const response = await fetch('http://127.0.0.1:8765/api/models');
      if (!response.ok) throw new Error('Could not load models from Ollama.');
      const data = await response.json();
      models = data.models ?? [];
      if (!selectedModel || !models.some((m) => m.name === selectedModel)) {
        selectedModel = models.find((m) => m.name.includes('qwen2.5:3b'))?.name
          ?? models[0]?.name ?? '';
      }
    } catch (e) {
      ollamaOnline = false;
      error = e instanceof Error ? e.message : 'Could not connect to the local AI service.';
    } finally {
      modelLoading = false;
    }
  }

  async function sendMessage() {
    const content = prompt.trim();
    if (!content || chatBusy || !selectedModel) return;
    messages = [...messages, { role: 'user', content }];
    prompt = '';
    chatBusy = true;
    error = '';
    try {
      const response = await fetch('http://127.0.0.1:8765/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel,
          messages: messages.map((m) => ({ role: m.role, content: m.content }))
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? 'The model request failed.');
      messages = [...messages, { role: 'assistant', content: data.content }];
    } catch (e) {
      error = e instanceof Error ? e.message : 'The model request failed.';
    } finally {
      chatBusy = false;
    }
  }

  function selectNav(label: string) {
    activeNav = label;
    if (label === 'AI tutor') chatOpen = true;
  }

  $effect(() => { refreshModels(); });
</script>

<svelte:head>
  <title>{activeNav} · Studyspace</title>
</svelte:head>

<div class="app-shell">
  {#if sidebarOpen}
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark"><GraduationCap size={21} strokeWidth={1.8} /></div>
        <div class="brand-copy">
          <span class="brand-name">studyspace<span class="brand-dot">.</span></span>
          <span class="brand-caption">YOUR PERSONAL UNIVERSITY</span>
        </div>
        <button class="icon-button sidebar-collapse" aria-label="Collapse sidebar" onclick={() => sidebarOpen = false}><PanelLeftClose size={17}/></button>
      </div>

      <button class="search-button" onclick={() => error = 'Search across your library will arrive with the library milestone.'}>
        <Search size={16}/><span>Search everything</span><kbd>⌘ K</kbd>
      </button>

      <div class="nav-label">WORKSPACE</div>
      <nav class="nav-list">
        {#each navItems as item}
          <button class:active={activeNav === item.label} class="nav-item" onclick={() => selectNav(item.label)}>
            <item.icon size={17} strokeWidth={1.8}/><span>{item.label}</span>
            {#if item.label === 'Library'}<span class="nav-count">0</span>{/if}
          </button>
        {/each}
      </nav>

      <div class="nav-label subjects-label">YOUR SUBJECTS <button class="tiny-icon" aria-label="Add subject" onclick={() => error = 'Subject creation is part of the next implementation step.'}><Plus size={14}/></button></div>
      <div class="mini-subjects">
        <button onclick={() => { activeNav = 'My subjects'; }}><span class="subject-dot dot-violet"></span>Signals & Systems</button>
        <button onclick={() => { activeNav = 'My subjects'; }}><span class="subject-dot dot-mint"></span>Robotics & Control</button>
        <button onclick={() => { activeNav = 'My subjects'; }}><span class="subject-dot dot-amber"></span>Computer Architecture</button>
      </div>

      <div class="sidebar-spacer"></div>
      <div class="local-card">
        <div class="local-card-top">
          <span class:online={ollamaOnline} class="status-dot"></span>
          <span>{ollamaOnline ? 'LOCAL AI CONNECTED' : 'LOCAL AI OFFLINE'}</span>
        </div>
        <p>{ollamaOnline ? 'Your models are ready when you are.' : 'Start Ollama and the Studyspace API to chat locally.'}</p>
        <button class="text-action" onclick={refreshModels}>Check connection <ArrowRight size={13}/></button>
      </div>
      <button class:active={activeNav === 'Settings'} class="nav-item settings-link" onclick={() => selectNav('Settings')}><Settings2 size={17}/><span>Settings</span></button>
      <div class="sidebar-footer"><span class="avatar">K</span><div><strong>Personal workspace</strong><small>Stored on this device</small></div><MoreHorizontal size={17}/></div>
    </aside>
  {:else}
    <button class="restore-sidebar" aria-label="Open sidebar" onclick={() => sidebarOpen = true}><PanelLeftClose size={18}/></button>
  {/if}

  <main class="main-area">
    <header class="topbar">
      <div class="breadcrumbs"><span>Workspace</span><span class="crumb-sep">/</span><strong>{activeNav}</strong></div>
      <div class="topbar-actions">
        <div class="offline-pill"><span class="status-dot online"></span> LOCAL FIRST</div>
        <button class="icon-button" aria-label="Help" onclick={() => error = 'Tip: this first build runs entirely on your machine and uses your existing Ollama models.'}><CircleHelp size={18}/></button>
      </div>
    </header>

    {#if activeNav === 'Home'}
      <div class="page-content">
        <section class="welcome-row">
          <div>
            <div class="eyebrow"><span class="eyebrow-line"></span> YOUR SPACE TO FIGURE THINGS OUT</div>
            <h1>Good morning<span class="heading-period">.</span></h1>
            <p class="welcome-subtitle">Pick up where your curiosity left off.</p>
          </div>
          <div class="date-chip"><Clock3 size={14}/> YOUR PACE, YOUR PLACE</div>
        </section>

        <section class="continue-card">
          <div class="continue-art">
            <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div>
            <div class="art-core"><Activity size={39} strokeWidth={1.2}/></div>
            <span class="formula formula-one">x(t)</span><span class="formula formula-two">H(jω)</span><span class="formula formula-three">∫ f(t)dt</span>
          </div>
          <div class="continue-content">
            <div class="continue-meta"><span class="overline">PICK UP WHERE YOU LEFT OFF</span><span class="pill pill-violet">ENGINEERING</span></div>
            <h2>Signals & Systems</h2>
            <p>Build intuition for how signals behave, transform, and tell stories about the world.</p>
            <div class="continue-bottom"><span class="progress-label"><span class="progress-dot"></span> Ready for your next session</span><button class="primary-button" onclick={() => { activeNav = 'My subjects'; }}>Open subject <ArrowRight size={15}/></button></div>
          </div>
        </section>

        <section class="section-block">
          <div class="section-heading"><div><h3>Your learning worlds</h3><p>Different threads, one connected workspace.</p></div><button class="quiet-button" onclick={() => activeNav = 'My subjects'}>All subjects <ArrowRight size={14}/></button></div>
          <div class="subject-grid">
            {#each subjects as subject}
              <button class="subject-card" onclick={() => activeNav = 'My subjects'}>
                <div class="subject-card-top"><div class={`subject-icon ${subject.color}`}><subject.icon size={19} strokeWidth={1.7}/></div><MoreHorizontal size={18} class="muted-icon"/></div>
                <span class="card-tag">{subject.tag}</span>
                <h4>{subject.title}</h4>
                <p>{subject.detail}</p>
                <div class="card-bottom"><span class="tiny-indicator"></span><span>Workspace ready to shape</span><ArrowRight size={15}/></div>
              </button>
            {/each}
            <button class="add-subject-card" onclick={() => { activeNav = 'My subjects'; error = 'We will implement persistent subject creation next.'; }}>
              <div class="add-icon"><Plus size={19}/></div><strong>Make room for a new obsession</strong><span>Create a subject workspace</span>
            </button>
          </div>
        </section>

        <section class="section-block bottom-grid">
          <div class="section-heading"><div><h3>Settle in</h3><p>Your tools, without the tab archaeology.</p></div></div>
          <div class="tool-grid">
            <button class="tool-card" onclick={() => activeNav = 'Library'}><div class="tool-icon tool-purple"><BookOpen size={18}/></div><div><strong>Open the library</strong><span>Books, papers & manuals</span></div><ArrowRight size={15}/></button>
            <button class="tool-card" onclick={() => activeNav = 'Courses'}><div class="tool-icon tool-blue"><Video size={18}/></div><div><strong>Continue a lecture</strong><span>Videos, playlists & transcripts</span></div><ArrowRight size={15}/></button>
            <button class="tool-card" onclick={() => activeNav = 'Notes'}><div class="tool-icon tool-gold"><FileText size={18}/></div><div><strong>Get something down</strong><span>Notes, ideas & derivations</span></div><ArrowRight size={15}/></button>
          </div>
        </section>
        <footer class="page-footer"><span>STUDYSPACE <span class="footer-dot">/</span> LOCAL BY DESIGN</span><span>Made for the long way around.</span></footer>
      </div>
    {:else if activeNav === 'AI tutor'}
      <div class="simple-page">
        <div class="eyebrow"><span class="eyebrow-line"></span> THINK IT THROUGH</div>
        <h1>AI tutor<span class="heading-period">.</span></h1>
        <p class="welcome-subtitle">A local conversation, using models you already have.</p>
        {@render chatPanel()}
      </div>
    {:else}
      <div class="simple-page">
        <div class="eyebrow"><span class="eyebrow-line"></span> YOUR WORKSPACE</div>
        <h1>{activeNav}<span class="heading-period">.</span></h1>
        <p class="welcome-subtitle">{activeNav === 'My subjects' ? 'Build connected spaces for the things you want to understand.' : activeNav === 'Library' ? 'Your books, papers, manuals, and saved resources will live here.' : activeNav === 'Courses' ? 'Offline lectures, online playlists, transcripts, and course notes.' : activeNav === 'Notes' ? 'Your thinking, in your own words and formats.' : activeNav === 'Coding lab' ? 'Neovim, notebooks, experiments, and projects, connected to what you study.' : 'Make the environment feel like yours.'}</p>
        <div class="empty-state">
          <div class="empty-illustration">{#if activeNav === 'Library'}<LibraryBig size={28}/>{:else if activeNav === 'Courses'}<Headphones size={28}/>{:else if activeNav === 'Notes'}<FileText size={28}/>{:else if activeNav === 'Coding lab'}<Code2 size={28}/>{:else if activeNav === 'My subjects'}<GraduationCap size={28}/>{:else}<Settings2 size={28}/>{/if}</div>
          <h3>{activeNav === 'My subjects' ? 'A place for each thread of curiosity' : activeNav === 'Library' ? 'Your library starts with one good source' : activeNav === 'Courses' ? 'Bring a lecture into your space' : activeNav === 'Notes' ? 'Leave a trail for your future self' : activeNav === 'Coding lab' ? 'Your tools, connected to your learning' : 'Tune your environment'}</h3>
          <p>This section is part of the build plan. We will implement real file-backed workflows here, not decorative buttons that pretend to work.</p>
          <button class="primary-button" onclick={() => { activeNav = 'Home'; }}>Back to your space <ArrowRight size={15}/></button>
        </div>
      </div>
    {/if}

    {#if error}
      <div class="toast" role="status"><span>{error}</span><button aria-label="Dismiss" onclick={() => error = ''}><X size={15}/></button></div>
    {/if}
  </main>

  <button class="tutor-fab" onclick={() => { chatOpen = !chatOpen; if (chatOpen) activeNav = 'Home'; }} aria-label="Toggle AI tutor">
    {#if chatOpen}<X size={19}/>{:else}<BrainCircuit size={20}/>{/if}<span>{chatOpen ? 'Close tutor' : 'Ask your tutor'}</span>
  </button>

  {#if chatOpen}
    <aside class="chat-drawer">
      <div class="chat-header">
        <div class="chat-heading-icon"><Sparkles size={17}/></div>
        <div class="chat-heading"><strong>Your AI tutor</strong><span><span class:online={ollamaOnline} class="status-dot"></span> {ollamaOnline ? 'Local · Ollama' : 'Waiting for local AI'}</span></div>
        <button class="icon-button" aria-label="Close tutor" onclick={() => chatOpen = false}><X size={17}/></button>
      </div>
      <div class="model-row">
        <span>MODEL</span>
        <div class="model-select-wrap">
          <select bind:value={selectedModel} disabled={modelLoading || models.length === 0} aria-label="Choose model">
            {#each models as model}<option value={model.name}>{model.name}</option>{/each}
          </select><ChevronDown size={13}/>
        </div>
        <button class="tiny-icon" aria-label="Refresh models" onclick={refreshModels}><Activity size={14}/></button>
      </div>
      <div class="chat-messages">
        {#each messages as message, i}
          <div class:from-user={message.role === 'user'} class="message">
            {#if message.role === 'assistant'}<div class="message-avatar"><Sparkles size={13}/></div>{/if}
            <div class="message-body">{message.content}</div>
          </div>
        {/each}
        {#if chatBusy}<div class="message"><div class="message-avatar"><LoaderCircle size={13} class="spin"/></div><div class="message-body thinking">Thinking through it…</div></div>{/if}
        {#if error}<div class="chat-error">{error}</div>{/if}
      </div>
      <form class="chat-composer" onsubmit={(e) => { e.preventDefault(); sendMessage(); }}>
        <textarea bind:value={prompt} placeholder="Ask about something you're learning…" rows="3" onkeydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}></textarea>
        <div class="composer-bottom"><span><Wifi size={12}/> Local model · stays on device</span><button class="send-button" disabled={!prompt.trim() || chatBusy || !selectedModel} aria-label="Send message"><Send size={15}/></button></div>
      </form>
    </aside>
  {/if}
</div>

{#snippet chatPanel()}
  <div class="inline-chat">
    <div class="model-row">
      <span>MODEL</span>
      <div class="model-select-wrap"><select bind:value={selectedModel} disabled={modelLoading || models.length === 0} aria-label="Choose model">{#each models as model}<option value={model.name}>{model.name}</option>{/each}</select><ChevronDown size={13}/></div>
      <span class="connection-label"><span class:online={ollamaOnline} class="status-dot"></span>{ollamaOnline ? 'Connected' : 'Not connected'}</span>
    </div>
    <div class="inline-messages">
      {#each messages as message}
        <div class:from-user={message.role === 'user'} class="message">
          {#if message.role === 'assistant'}<div class="message-avatar"><Sparkles size={13}/></div>{/if}
          <div class="message-body">{message.content}</div>
        </div>
      {/each}
      {#if chatBusy}<div class="message"><div class="message-avatar"><LoaderCircle size={13}/></div><div class="message-body thinking">Thinking…</div></div>{/if}
      {#if error}<div class="chat-error">{error}</div>{/if}
    </div>
    <form class="chat-composer inline-composer" onsubmit={(e) => { e.preventDefault(); sendMessage(); }}>
      <textarea bind:value={prompt} placeholder="Ask a question…" rows="3" onkeydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}></textarea>
      <div class="composer-bottom"><span><Wifi size={12}/> Local model</span><button class="send-button" disabled={!prompt.trim() || chatBusy || !selectedModel} aria-label="Send message"><Send size={15}/></button></div>
    </form>
  </div>
{/snippet}

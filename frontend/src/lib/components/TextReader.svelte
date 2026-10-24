<script lang="ts">
  import { onMount } from 'svelte';
  import { defaultPreferences, type ReadingPreferences } from '../stores/reading-store';

  let preferences: ReadingPreferences = $state({ ...defaultPreferences });
  let textContent = $state('');
  let currentPage = $state(1);
  let totalPages = $state(1);
  let isLoading = $state(true);
  let error = $state('');

  // Update preferences when changed
  const updatePreference = (key: keyof ReadingPreferences, value: number | 'light' | 'dark') => {
    preferences = {
      ...preferences,
      [key]: value,
    };
    // Persist to localStorage
    localStorage.setItem('readingPreferences', JSON.stringify(preferences));
  };

  // Load text content from backend
  const loadText = async (docId: string, page: number = 1) => {
    try {
      const res = await fetch(`/api/pdfs/${docId}/text?page=${page}`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        textContent = data.text || '';
        totalPages = data.total_pages || 1;
        currentPage = data.page || 1;
        isLoading = false;
      } else {
        error = 'Failed to load text';
        isLoading = false;
      }
    } catch (e) {
      error = 'Error loading text';
      isLoading = false;
      console.error(e);
    }
  };

  // Auto-save preferences on unload
  onMount(() => {
    // Restore preferences from localStorage
    const stored = localStorage.getItem('readingPreferences');
    if (stored) {
      const parsed = JSON.parse(stored);
      preferences = { ...defaultPreferences, ...parsed };
    }
  });
</script>

<div class="text-reader-panel">
  {#if error}
    <div class="error-message">{error}</div>
  {:else if isLoading}
    <div class="loading-state">Loading text...</div>
  {:else}
    <div class="reader-toolbar">
      <div class="toolbar-left">
        <button class="btn-nav" onclick={() => { if (currentPage > 1) currentPage--; }}>← Prev</button>
        <span class="page-indicator">Page {currentPage} of {totalPages}</span>
        <button class="btn-nav" onclick={() => { if (currentPage < totalPages) currentPage++; }}>Next →</button>
      </div>
      <div class="toolbar-right">
        <div class="preference-controls">
          <label>Font size: 
            <button class="btn-small" onclick={() => updatePreference('fontSize', preferences.fontSize - 2)}>-</button>
            <span>{preferences.fontSize}</span>
            <button class="btn-small" onclick={() => updatePreference('fontSize', preferences.fontSize + 2)}>+</button>
          </label>
          <label>Line spacing: 
            <button class="btn-small" onclick={() => updatePreference('lineSpacing', preferences.lineSpacing - 0.1)}>-</button>
            <span>{preferences.lineSpacing}</span>
            <button class="btn-small" onclick={() => updatePreference('lineSpacing', preferences.lineSpacing + 0.1)}>+</button>
          </label>
        </div>
      </div>
    </div>

    <div class="reader-content" style={{
      fontFamily: preferences.theme === 'dark' ? 'serif, system-ui, sans-serif' : 'serif, system-ui, sans-serif',
      fontSize: `${preferences.fontSize}px`,
      lineHeight: `${preferences.lineSpacing}em`,
      maxWidth: `${preferences.contentWidth}px`,
      margin: '0 auto',
    }}>
      {#if textContent}
        <div class="text-block">
          {#each textContent.split('\n') as line, i}
            <p>{line}</p>
          {/each}
        </div>
      {:else}
        <p>No text extracted for this PDF. <a href="#" onclick={(e: Event) => { e.preventDefault(); alert('No extractable text. Install Tesseract for OCR.'); }}>Install Tesseract for OCR</a></p>
      {/if}}
    </div>
  {/if}
</div>

<style>
.text-reader-panel {
  max-width: 100%;
  background: var(--background-primary, #ffffff);
  border-radius: 8px;
  overflow: hidden;
  font-family: var(--font-base, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial);
}

.reader-toolbar {
  padding: 8px 12px;
  background: var(--toolbar-background, #f8f9fa);
  border-bottom: 1px solid var(-- divider-color, #e0e0e0);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preference-controls {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.btn-small {
  padding: 2px 6px;
  background: none;
  border: 1px solid var(-- divider-color, #e0e0e0);
  border-radius: 3px;
  cursor: pointer;
  color: var(--text-primary, #333);
  font-size: 11px;
}

.btn-small:hover {
  background: var(-- hover-background, #e2e6ea);
}

.reader-content {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  text-align: justify;
}

.text-block {
  margin-bottom: 20px;
}

.text-block p {
  margin: 0 0 12px 0;
  line-height: 1.6;
}

.no-ocr-message {
  background: #fff3e0;
  border: 1px solid #ffcc80;
  color: #e65100;
  padding: 12px;
  border-radius: 4px;
  margin: 12px 0;
  font-size: 12px;
}

/* OCR notice */
.ocr-notice {
  background: #e3f2fd;
  border: 1px solid #90caf9;
  color: #1976d2;
  padding: 8px 12px;
  border-radius: 4px;
  margin: 8px 0;
  font-size: 12px;
}

/* Responsive */
@media (max-width: 600px) {
  .text-reader-panel {
    border-radius: 0;
    margin: 0;
    max-height: 100vh;
  }

  .reader-toolbar {
    padding: 6px 8px;
    font-size: 10px;
    flex-direction: column;
    gap: 4px;
  }

  .toolbar-left,
  .toolbar-right {
    width: 100%;
    justify-content: center;
  }

  .preference-controls {
    flex-direction: row;
    gap: 2px;
  }

  .reader-content {
    padding: 12px;
    max-width: 100%;
  }
}
</style>
<script lang="ts">
  import { onMount, onCleanup } from 'svelte';
  import { readFile } from 'fs/promises';
  import { defaultReadingState, type ReadingState, type ReadingPreferences } from '../stores/reading-store';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  // State
  let readingState = $type<ReadingState>({ ...defaultReadingState });
  let files: File[] = [];
  let libraries: any[] = [];
  let isLoading = false;

  // Load library from backend on mount
  onMount(async () => {
    try {
      const res = await fetch('/api/pdfs', {
        credentials: 'include'
      });
      if (res.ok) {
        libraries = await res.json();
        libraries.forEach((doc: any) => {
          readingState = {
            ...readingState,
            currentDocId: doc.id,
            mode: 'pdf',
            open: true
          };
        });
      }
    } catch (e) {
      console.error('Failed to load library', e);
    }
  });

  // File picker
  const pickFiles = async (event: Event) => {
    const input = event.target as HTMLInputElement;
    if (!input.files) return;
    files = Array.from(input.files);
    isLoading = true;

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/pdfs', {
          method: 'POST',
          body: formData,
          credentials: 'include'
        });
        if (res.ok) {
          const doc = await res.json();
          libraries.push(doc);
          readingState = {
            ...readingState,
            currentDocId: doc.id,
            mode: 'pdf',
            open: true
          };
        } else {
          console.error('Failed to upload', file.name);
        }
      } catch (e) {
        console.error('Upload error', e);
      }
    }

    isLoading = false;
    // Reset file input
    if (input.files) {
      input.value = '';
    }
  };

  // Soft delete document
  const softDelete = async (docId: string) => {
    if (!confirm('Remove from library? Original PDF file will remain on device.')) return;
    try {
      const res = await fetch(`/api/pdfs/${docId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (res.ok) {
        libraries = libraries.filter((d: any) => d.id !== docId);
        if (readingState.currentDocId === docId) {
          readingState = {
            ...defaultReadingState,
            mode: 'home',
            open: true
          };
        }
      }
    } catch (e) {
      console.error('Delete error', e);
    }
  };

  // Permanent delete document
  const permanentDelete = async (docId: string) => {
    if (!confirm('Permanently delete this PDF? This cannot be undone.')) return;
    try {
      const res = await fetch(`/api/pdfs/${docId}?permanent=true`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (res.ok) {
        libraries = libraries.filter((d: any) => d.id !== docId);
        const filePath = `/home/siesta/projects/studyspace-starter/data/library/${docId}.pdf`;
        // Note: file deletion handled by backend
        if (readingState.currentDocId === docId) {
          readingState = {
            ...defaultReadingState,
            mode: 'home',
            open: true
          };
        }
      }
    } catch (e) {
      console.error('Permanent delete error', e);
    }
  };

  // Restore document
  const restoreDocument = async (docId: string) => {
    try {
      const res = await fetch(`/api/pdfs/${docId}/restore`, {
        method: 'PUT',
        credentials: 'include'
      });
      if (res.ok) {
        const doc = await res.json();
        libraries.push(doc);
        readingState = {
          ...readingState,
          currentDocId: doc.id,
          mode: 'pdf',
          open: true
        };
      }
    } catch (e) {
      console.error('Restore error', e);
    }
  };
</script>

<div class="pdf-library-panel">
  <div class="panel-header">
    <h2>PDF Library</h2>
    <button class="close-button" onclick={() => { readingState = { ...defaultReadingState, open: true }; }}>Close</button>
  </div>

  <div class="panel-body">
    {#if libraries.length === 0}
      <div class="empty-state">
        <div class="empty-illustration"><BookOpen size={28}/></div>
        <h3>Your library is empty</h3>
        <p>Upload PDFs to build your personal library.</p>
      </div>
    {:else}
      <div class="library-grid">
        {#each libraries as doc (doc.id)}
          <div class="library-card">
            <div class="card-header">
              <h4>{doc.title || doc.filename}</h4>
              <div class="card-meta">
                <span>{doc.page_count} pages</span>
                <span>{doc.is_scanned ? 'Scanned' : 'Text'}</span>
              </div>
            </div>
            <div class="card-actions">
              {#if doc.is_deleted}
                <button class="btn-restore" onclick={() => restoreDocument(doc.id)}>Restore</button>
              {:else}
                <div class="action-group">
                  <button class="btn-soft" onclick={() => softDelete(doc.id)}>Remove from library</button>
                  <button class="btn-permanent" onclick={() => permanentDelete(doc.id)}>Permanently delete</button>
                </div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}}
  </div>

  {#if isLoading}
    <div class="loading-state">Importing PDFs...</div>
  {/if}

  <div class="file-picker">
    <label class="file-input-label">
      <input type="file" accept="application/pdf" on:change={pickFiles} multiple />
      <span>Select PDFs</span>
    </label>
  </div>
</div>

<style>
.pdf-library-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 380px;
  background: var(--background-primary, #ffffff);
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.15);
  z-index: 100;
  display: flex;
  flex-direction: column;
  height: 100vh;
  font-family: var(--font-base, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial);
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(-- divider-color, #e0e0e0);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.close-button {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--text-secondary, #666);
}

.panel-body {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.empty-illustration {
  width: 64px;
  height: 64px;
  margin: 0 auto 12px;
  opacity: 0.6;
}

.library-grid {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}

.library-card {
  background: var(--card-background, #f8f9fa);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 140px;
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
}

.card-header .card-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary, #666);
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  justify-content: flex-end;
}

.action-group {
  display: flex;
  gap: 4px;
}

.btn-soft,
.btn-permanent,
.btn-restore {
  padding: 6px 12px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: inherit;
}

.btn-soft {
  background: #e3f2fd;
  color: #1976d2;
}

.btn-permanent {
  background: #ffebee;
  color: #b71c1c;
}

.btn-restore {
  background: #e8f5e9;
  color: #2e7d32;
}

.file-picker {
  padding: 12px 16px;
  border-top: 1px solid var(-- divider-color, #e0e0e0);
  background: var(-- background-primary, #ffffff);
  display: flex;
  gap: 8px;
}

.file-input-label {
  flex: 1;
  cursor: pointer;
}

.file-input-label input {
  display: none;
}

.file-input-label span {
  padding: 8px 12px;
  background: #f1f8ff;
  border-radius: 4px;
  border: 1px solid #90caf9;
  cursor: pointer;
  font-size: 12px;
  color: #1976d2;
}

.loading-state {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary, #666);
  font-style: italic;
}

/* Responsive */
@media (max-width: 600px) {
  .pdf-library-panel {
    width: 100%;
    right: auto;
    left: 0;
  }
  
  .library-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
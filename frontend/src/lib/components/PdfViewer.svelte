<script lang="ts">
  import { onMount, onCleanup } from 'svelte';

  let pdfSrc = $state('');  // URL to PDF file
  let currentPage = $state(1);
  let totalPages = $state(0);
  let zoom = $state(1);
  let isRendering = $state(false);
  let error = $state('');

  // Dynamic import of pdfjs-dist
  onMount(async () => {
    // Will be set when viewer is initialized with a PDF source
  });

  // Set PDF source and render first page
  const loadPDF = async (src: string) => {
    pdfSrc = src;
    totalPages = 0;
    currentPage = 1;
    isRendering = true;
    error = '';

    try {
      // Dynamic import - pdfjs-dist is already installed
      const { pdfjsLib } = await import('pdfjs-dist');
      pdfjsLib.GlobalWorkerOptions.workerSrc = '/node_modules/pdfjs-dist/build/pdf.worker.mjs';

      const loadingTask = pdfjsLib.getDocument(src);
      const pdf = await loadingTask.promise;
      totalPages = pdf.numPages;

      // Render first page
      if (totalPages > 0) {
        const page = await pdf.getPage(currentPage);
        const viewport = page.getViewport({ scale: zoom });
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        if (!context) throw new Error('No 2d context');

        canvas.height = viewport.height;
        canvas.width = viewport.width;
        page.render({ canvasContext: context, viewport }).promise;

        // Replace viewer element with canvas
        const viewer = document.querySelector('.pdf-viewer');
        if (viewer && viewer.firstChild) {
          viewer.innerHTML = '';
          viewer.appendChild(canvas);
        }
      }
    } catch (e: any) {
      error = e.message || 'Failed to load PDF';
      console.error('PDF.js error:', e);
    } finally {
      isRendering = false;
    }
  };

  // Navigate to next page
  const nextPage = () => {
    if (currentPage < totalPages) {
      currentPage++;
      renderCurrentPage();
    }
  };

  // Navigate to previous page
  const prevPage = () => {
    if (currentPage > 1) {
      currentPage--;
      renderCurrentPage();
    }
  };

  // Render current page
  const renderCurrentPage = async () => {
    if (!pdfSrc || totalPages === 0) return;
    isRendering = true;
    error = '';

    try {
      const { pdfjsLib } = await import('pdfjs-dist');
      pdfjsLib.GlobalWorkerOptions.workerSrc = '/node_modules/pdfjs-dist/build/pdf.worker.mjs';

      const pdf = await pdfjsLib.getDocument(pdfSrc).promise;
      const page = await pdf.getPage(currentPage);
      const viewport = page.getViewport({ scale: zoom });

      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      if (!context) throw new Error('No 2d context');

      canvas.height = viewport.height;
      canvas.width = viewport.width;
      page.render({ canvasContext: context, viewport }).promise;

      // Replace canvas in viewer
      const viewer = document.querySelector('.pdf-viewer');
      if (viewer && viewer.firstChild) {
        viewer.innerHTML = '';
        viewer.appendChild(canvas);
      }
    } catch (e: any) {
      error = e.message || 'Failed to render page';
      console.error('Render error:', e);
    } finally {
      isRendering = false;
    }
  };

  // Zoom in
  const zoomIn = () => {
    zoom = Math.min(3, zoom + 0.25);
    if (!isRendering) renderCurrentPage();
  };

  // Zoom out
  const zoomOut = () => {
    zoom = Math.max(0.25, zoom - 0.25);
    if (!isRendering) renderCurrentPage();
  };

  // Fit to width
  const fitToWidth = () => {
    // Calculate zoom based on container width
    const container = document.querySelector('.pdf-container');
    if (!container || !pdfSrc) return;
    const containerWidth = container.clientWidth - 32; // padding
    // Simplified - set reasonable zoom
    zoom = 1;
    renderCurrentPage();
  };

  // Fit to page
  const fitToPage = () => {
    zoom = 1;
    renderCurrentPage();
  };
</script>

<div class="pdf-viewer-panel">
  <div class="pdf-toolbar">
    <div class="toolbar-left">
      <button class="btn-nav" onclick={prevPage} aria-label="Previous page">←</button>
      <span class="page-counter">Page {currentPage} of {totalPages}</span>
      <button class="btn-nav" onclick={nextPage} aria-label="Next page">→</button>
    </div>
    <div class="toolbar-right">
      <button class="btn-zoom" onclick={zoomIn} title="Zoom in">+</button>
      <button class="btn-zoom" onclick={zoomOut} title="Zoom out">−</button>
      <button class="btn-fit" onclick={fitToWidth} title="Fit to width">F</button>
      <button class="btn-fit" onclick={fitToPage} title="Fit to page">P</button>
    </div>
  </div>

  {#if error}
    <div class="error-message">{error}</div>
  {:else if isRendering && totalPages > 0}
    <div class="pdf-container">
      <canvas class="pdf-viewer" aria-live="polite"></canvas>
    </div>
  {:else}
    <div class="no-pdf">
      <p>Select a PDF to view</p>
    </div>
  {/if}
</div>

<style>
.pdf-viewer-panel {
  max-width: 100%;
  max-height: 800px;
  background: var(--background-primary, #ffffff);
  border-radius: 8px;
  overflow: hidden;
  font-family: var(--font-base, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial);
}

.pdf-toolbar {
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
  gap: 4px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-nav {
  padding: 4px 8px;
  background: none;
  border: 1px solid var(-- divider-color, #e0e0e0);
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-primary, #333);
  font-size: 14px;
}

.btn-nav:hover {
  background: var(-- hover-background, #e2e6ea);
}

.page-counter {
  margin: 0 8px;
  color: var(--text-primary, #333);
}

.btn-zoom {
  padding: 4px 8px;
  background: none;
  border: 1px solid var(-- divider-color, #e0e0e0);
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-primary, #333);
  font-size: 14px;
}

.btn-zoom:hover {
  background: var(-- hover-background, #e2e6ea);
}

.btn-fit {
  padding: 4px 8px;
  background: none;
  border: 1px solid var(-- divider-color, #e0e0e0);
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-primary, #333);
  font-size: 12px;
}

.error-message {
  padding: 12px;
  color: #b00020;
  background: #ffebee;
  border-radius: 4px;
  margin: 8px;
}

.no-pdf {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-secondary, #666);
  font-style: italic;
}

.pdf-container {
  padding: 0;
  margin: 0;
}

.pdf-viewer {
  display: block;
  width: 100%;
  height: auto;
}

/* Responsive */
@media (max-width: 600px) {
  .pdf-viewer-panel {
    border-radius: 0;
    margin: 0;
    max-height: 100vh;
  }

  .pdf-toolbar {
    padding: 6px 8px;
    font-size: 10px;
  }

  .page-counter {
    margin: 0 4px;
  }
}
</style>
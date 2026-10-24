import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import pypdf

DATA_DIR_DEFAULT = Path("./data")


def _is_within_base(file_path: str, base_dir: Path) -> bool:
    """Return True if file_path (resolved) is within base_dir (resolved)."""
    resolved = Path(file_path).resolve()
    base = base_dir.resolve()
    try:
        resolved.relative_to(base)
        return True
    except ValueError:
        return False


def validate_pdf(path: str, base_dir: str | None = None) -> Tuple[bool, Optional[str]]:
    """Validate that path is a readable PDF file within allowed boundaries.

    Returns (is_valid, reason). reason is None if valid.
    """
    if base_dir is None:
        base_dir = str(DATA_DIR_DEFAULT)
    p = Path(path)

    # Check file exists
    if not p.is_file():
        return False, "File not found"

    # Check path containment
    if not _is_within_base(p, Path(base_dir)):
        return False, "Path outside allowed directory"

    # Check PDF header
    try:
        with open(p, "rb") as f:
            header = f.read(5)
    except OSError:
        return False, "Cannot read file"

    if header != b"%PDF-":
        return False, "Not a PDF file (missing %PDF- header)"

    # Try pypdf parse
    try:
        reader = pypdf.PdfReader(str(p))
        # Read metadata lightly
        try:
            _ = reader.metadata
        except Exception:
            pass  # may have no metadata, that's fine
    except (pypdf.PdfReadError, pdf.PdfReadError, OSError, ValueError) as e:
        return False, f"Malformed PDF: {e}"

    return True, None


def get_pdf_info(path: str, base_dir: str | None = None) -> dict[str, Any]:
    """Extract PDF metadata using pypdf.

    Returns dict with title, page_count, file_size, is_scanned, encrypted.
    """
    if base_dir is None:
        base_dir = str(DATA_DIR_DEFAULT)
    p = Path(path)

    if not p.is_file():
        return {"title": "", "page_count": 0, "file_size": 0, "is_scanned": False, "encrypted": False}

    # File size
    try:
        file_size = p.stat().st_size
    except OSError:
        file_size = 0

    # pypdf read
    try:
        reader = pypdf.PdfReader(str(p))
        page_count = len(reader.pages)

        # Check encryption
        encrypted = reader.is_encrypted

        # Check if scanned: extract text from first page; if empty, assume scanned
        is_scanned = False
        try:
            first_page = reader.pages[0]
            try:
                text = first_page.extract_text()
                if not text or text.strip() == "":
                    is_scanned = True
            except Exception:
                is_scanned = True
        except Exception:
            is_scanned = True

        # Try title from metadata
        title = ""
        try:
            meta = reader.metadata
            if meta:
                title = (meta.get("/Title") or "").strip()
        except Exception:
            pass

        return {
            "title": title or path,
            "page_count": page_count,
            "file_size": file_size,
            "is_scanned": is_scanned,
            "encrypted": encrypted,
        }
    except Exception as e:
        return {"title": "", "page_count": 0, "file_size": file_size, "is_scanned": False, "encrypted": False}


def extract_text_for_page(path: str, page_num: int, base_dir: str | None = None) -> Tuple[str, bool]:
    """Extract text for a single page (1-indexed).

    Returns (text, is_scanned). If page number out of range, returns ("", False).
    """
    if base_dir is None:
        base_dir = str(DATA_DIR_DEFAULT)
    p = Path(path)

    if not p.is_file():
        return "", False

    try:
        reader = pypdf.PdfReader(str(p))
        page_count = len(reader.pages)

        if page_num < 1 or page_num > page_count:
            return "", False

        page = reader.pages[page_num - 1]
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        # Determine if scanned
        is_scanned = not bool(text.strip())

        return text, is_scanned
    except Exception:
        return "", True


def extract_text_for_document(path: str, base_dir: str | None = None) -> List[Tuple[int, str]]:
    """Extract text page-by-page (generator/iterator for large docs).

    Returns list of (page_num, text) tuples. Page numbers are 1-indexed.
    """
    if base_dir is None:
        base_dir = str(DATA_DIR_DEFAULT)
    p = Path(path)

    if not p.is_file():
        return []

    try:
        reader = pypdf.PdfReader(str(p))
        page_count = len(reader.pages)
        results: List[Tuple[int, str]] = []

        for i in range(page_count):
            page = reader.pages[i]
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            results.append((i + 1, text))

        return results
    except Exception:
        return []


def is_scanned_pdf(path: str, base_dir: str | None = None) -> bool:
    """Check if PDF appears to be scanned (no extractable text in first page)."""
    if base_dir is None:
        base_dir = str(DATA_DIR_DEFAULT)
    p = Path(path)

    if not p.is_file():
        return False

    try:
        reader = pypdf.PdfReader(str(p))
        if not reader.pages:
            return True
        first_page = reader.pages[0]
        try:
            text = first_page.extract_text()
            return not bool(text and text.strip())
        except Exception:
            return True
    except Exception:
        return True


def check_ocr_availability() -> Tuple[bool, str]:
    """Check if Tesseract OCR is installed on the system.

    Returns (available, message). message explains how to install if not.
    """
    import shutil

    available = shutil.which("tesseract") is not None
    if available:
        return True, "Tesseract is available for OCR."
    return False, (
        "Tesseract is not installed. To enable OCR for scanned PDFs, "
        "install Tesseract: 'sudo pacman -S tesseract' (Arch) or 'apt-get install tesseract-ocr' (Debian/Ubuntu)."
    )
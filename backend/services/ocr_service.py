"""OCR and text extraction services for PDF and Markdown files."""
import os as _os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── PDF text extraction ──────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF. Tries direct extraction first, falls back to OCR."""
    # Try direct PDF text extraction via pdfminer
    text = _extract_pdfminer(file_path)
    if text and len(text.strip()) > 50:
        return text

    # If too little text, try OCR (requires Tesseract installed)
    text = _extract_ocr(file_path)
    if text:
        return text

    raise ValueError(
        "Could not extract text from PDF. "
        "For scanned PDFs, Tesseract OCR must be installed on the server."
    )


def _extract_pdfminer(file_path: str) -> str:
    """Extract text from a digital PDF using pdfminer.six."""
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(file_path)
        return text.strip()
    except Exception as e:
        logger.warning(f"pdfminer extraction failed for {file_path}: {e}")
        return ""


def _extract_ocr(file_path: str) -> str:
    """Extract text from a scanned PDF using Tesseract OCR (if available)."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        # Check if Tesseract is actually installed
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            logger.warning("Tesseract not installed — OCR unavailable")
            return ""

        images = convert_from_path(file_path, dpi=300)
        texts = []
        for img in images:
            t = pytesseract.image_to_string(img, lang="deu+eng")
            texts.append(t)
        return "\n\n".join(texts).strip()
    except ImportError as e:
        logger.warning(f"OCR libraries not installed: {e}")
        return ""
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        return ""


# ── Markdown text extraction ─────────────────────────────────────────

def extract_text_from_markdown(file_path: str) -> str:
    """Read a Markdown file and return its raw text content."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

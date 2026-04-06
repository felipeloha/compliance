"""Shared utilities for compliance integrations."""

import io
import os
from pathlib import Path

from pypdf import PdfReader

from integrations.base import Control


def safe_filename(title: str) -> str:
    """Convert a title to a lowercase, filesystem-safe filename."""
    return "".join(c if c.isalnum() or c in " -_" else "-" for c in title).strip().lower().replace(" ", "-")


def extract_family(control: Control) -> str:
    """Derive the control family prefix from external_id or name (e.g. 'AM-01' -> 'AM')."""
    if "-" in control.external_id:
        return control.external_id.split("-")[0].strip()
    if "-" in control.name:
        return control.name.split("-")[0].strip()
    return "UNKNOWN"


def source_type_from_url(url: str) -> str:
    """Classify a URL as 'confluence' or 'external_url'."""
    confluence_base = os.environ.get("CONFLUENCE_BASE_URL", "")
    if confluence_base and url.startswith(confluence_base):
        return "confluence"
    if "atlassian.net" in url or "confluence" in url.lower():
        return "confluence"
    return "external_url"


def pdf_bytes_to_text(content: bytes) -> str | None:
    """Extract plain text from PDF bytes using pypdf. Returns None on failure or empty result."""
    try:
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        return text if text else None
    except Exception as exc:
        print(f"  PDF text extraction failed: {exc}")
        return None


def save_file_as_txt(content: bytes, file_name: str, dest_dir: Path, base_name: str) -> Path:
    """Save downloaded content as a .txt file, converting PDFs via pypdf.

    - PDF: text extracted with pypdf; raw bytes saved as fallback if extraction fails.
    - Word (.docx/.doc): placeholder text written (no conversion available).
    - Other: raw bytes written as-is.
    """
    txt_path = dest_dir / f"{base_name}.txt"
    suffix = Path(file_name).suffix.lower()

    if suffix == ".pdf":
        text = pdf_bytes_to_text(content)
        if text:
            txt_path.write_text(text, encoding="utf-8")
        else:
            print(f"  PDF conversion failed for {file_name}; saving raw content")
            txt_path.write_bytes(content)
    elif suffix in {".docx", ".doc"}:
        print(f"  Word document {file_name} cannot be auto-converted; saving placeholder")
        txt_path.write_text(
            f"[Word document: {file_name} - convert manually and replace this file]\n",
            encoding="utf-8",
        )
    else:
        txt_path.write_bytes(content)

    return txt_path

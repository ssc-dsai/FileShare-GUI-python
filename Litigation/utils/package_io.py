# Litigation/utils/package_io.py
"""Shared helpers for litigation packages."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".txt",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".webp",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".webp"}


def safe_package_name(name: str | None) -> str:
    if not name or not str(name).strip():
        return f"Litigation_Package_{datetime.now().strftime('%Y%m%d_%H%M')}"
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", str(name).strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:120] or f"Litigation_Package_{datetime.now().strftime('%Y%m%d_%H%M')}"


def list_supported_files(folder: Path) -> list[Path]:
    files = []
    for p in folder.rglob("*.*"):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(p)
    return sorted(files)


def document_separator(path: Path, index: int, total: int) -> str:
    return (
        f"\n\n{'=' * 80}\n"
        f"DOCUMENT {index}/{total}\n"
        f"File: {path.name}\n"
        f"Path: {path.resolve()}\n"
        f"{'=' * 80}\n\n"
    )
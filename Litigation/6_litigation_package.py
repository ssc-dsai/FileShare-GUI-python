# Litigation/6_litigation_package.py
# Build a COMPACT litigation package from a folder of court-case documents.
# Output is optimized for use as a semantic search query (not a full dump).
#
#   python Litigation/6_litigation_package.py --input_folder "D:\Matters\Smith_v_Jones"
#   python Litigation/6_litigation_package.py --input_folder "..." --output_name "Smith_v_Jones"

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import LITIGATION_PACKAGES_DIR

from Ingestion.extractors import extract_text_from_file
from Litigation.utils.extractive_summary import extractive_summary
from Litigation.utils.package_io import (
    IMAGE_EXTENSIONS,
    list_supported_files,
    safe_package_name,
)
from Litigation.utils.tombstone_extractor import extract_tombstone_data, merge_tombstones

logger = logging.getLogger("litigation_package")

# Per-document budget for the search package (keeps query embedding tractable)
PER_DOC_SUMMARY_CHARS = 1200


def _setup_logging(run_log: Path) -> None:
    run_log.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("litigation_package")
    root.setLevel(logging.INFO)
    root.handlers.clear()
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(run_log, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)


def build_package(input_folder: Path, output_name: str | None = None) -> Path | None:
    input_folder = Path(input_folder)
    if not input_folder.is_dir():
        print(f"ERROR: Folder not found: {input_folder}")
        return None

    # Guard: do not package the packages output root into itself
    try:
        if input_folder.resolve() == LITIGATION_PACKAGES_DIR.resolve():
            print(
                "ERROR: Input folder cannot be LITIGATION_PACKAGES_DIR.\n"
                "Choose the folder that contains the court-case source documents."
            )
            return None
    except Exception:
        pass

    LITIGATION_PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    package_stem = safe_package_name(output_name or input_folder.name)
    package_dir = LITIGATION_PACKAGES_DIR / package_stem
    package_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_txt = package_dir / f"{package_stem}.txt"
    output_manifest = package_dir / f"{package_stem}.manifest.txt"
    run_log = package_dir / f"package_builder_{stamp}.log"
    _setup_logging(run_log)

    logger.info("=== Litigation Package Builder Started (compact / search-oriented) ===")
    logger.info(f"Input folder : {input_folder.resolve()}")
    logger.info(f"Package dir  : {package_dir.resolve()}")

    files = list_supported_files(input_folder)
    logger.info(f"Files found  : {len(files)}")
    if not files:
        print("No supported files found.")
        return None

    tombstone_rows: list[dict] = []
    doc_blocks: list[str] = []
    manifest_lines = [
        f"Litigation package: {package_stem}",
        f"Created: {datetime.now().isoformat()}",
        f"Source folder: {input_folder.resolve()}",
        f"Mode: compact (tombstone + extractive summaries)",
        f"Document count: {len(files)}",
        "",
        "Documents:",
    ]

    ok = errors = vision_count = 0
    total_summary_chars = 0

    for i, path in enumerate(files, 1):
        logger.info(f"[{i}/{len(files)}] {path.name}")
        try:
            raw = extract_text_from_file(path) or ""
            if path.suffix.lower() in IMAGE_EXTENSIONS or "[VISION_FLAG: Yes]" in raw:
                vision_count += 1

            tomb = extract_tombstone_data(raw, path)
            tombstone_rows.append(tomb)

            summary = extractive_summary(raw, max_chars=PER_DOC_SUMMARY_CHARS)
            total_summary_chars += len(summary)

            block = (
                f"--- DOCUMENT {i}/{len(files)}: {path.name} ---\n"
                f"Path: {path.resolve()}\n"
                f"Plaintiff: {tomb.get('Plaintiff_Name')}\n"
                f"Defendant: {tomb.get('Defendant_Name')}\n"
                f"Case: {tomb.get('Case_Number')}\n"
                f"Summary:\n{summary}\n"
            )
            doc_blocks.append(block)
            manifest_lines.append(
                f"  {i:04d}. {path.name} | summary_chars={len(summary)} | {path}"
            )
            ok += 1
        except Exception as e:
            errors += 1
            logger.error(f"Failed {path.name}: {type(e).__name__}: {e}")
            manifest_lines.append(f"  {i:04d}. {path.name} | ERROR: {e}")

    merged = merge_tombstones(tombstone_rows)

    header = (
        f"LITIGATION PACKAGE (COMPACT – FOR SEARCH)\n"
        f"Name        : {package_stem}\n"
        f"Created     : {datetime.now().isoformat()}\n"
        f"Source      : {input_folder.resolve()}\n"
        f"Documents   : {ok} ok / {errors} errors / {vision_count} vision-flagged\n"
        f"Summary size: {total_summary_chars} characters (extractive, not full text)\n"
        f"{'=' * 80}\n\n"
        f"=== TOMBSTONE / KEY FACTS (AGGREGATED) ===\n"
        f"Plaintiff_Name    : {merged.get('Plaintiff_Name')}\n"
        f"Defendant_Name    : {merged.get('Defendant_Name')}\n"
        f"Case_Number       : {merged.get('Case_Number')}\n"
        f"Date_of_Incident  : {merged.get('Date_of_Incident')}\n"
        f"Claim_Amount      : {merged.get('Claim_Amount')}\n"
        f"Key_File_Reference: {merged.get('Key_File_Reference')}\n"
        f"Source_Files      : {merged.get('Source_Files')}\n\n"
        f"=== DOCUMENT SUMMARIES (SEARCH QUERY BODY) ===\n\n"
    )

    output_txt.write_text(header + "\n".join(doc_blocks), encoding="utf-8")
    output_manifest.write_text("\n".join(manifest_lines), encoding="utf-8")

    logger.info(f"Package written : {output_txt} ({output_txt.stat().st_size} bytes)")
    logger.info(f"Manifest written: {output_manifest}")

    print("\n" + "=" * 70)
    print(f"Compact package complete | {ok} documents")
    print(f"Folder  : {package_dir}")
    print(f"Package : {output_txt}")
    print(f"Manifest: {output_manifest}")
    print(f"Log     : {run_log}")
    print("=" * 70)
    return output_txt


def main():
    parser = argparse.ArgumentParser(
        description="Build a compact litigation package for semantic search"
    )
    parser.add_argument("--input_folder", required=True, help="Folder of court-case documents")
    parser.add_argument("--output_name", default=None, help="Optional package name")
    args = parser.parse_args()
    build_package(Path(args.input_folder), args.output_name)


if __name__ == "__main__":
    main()
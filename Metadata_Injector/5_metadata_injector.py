# Metadata_Injector/5_metadata_injector.py
#   python Metadata_Injector/5_metadata_injector.py --embedder minilm
#   python Metadata_Injector/5_metadata_injector.py --embedder qwen3

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_config import (
    INJECTED_METADATA_DIR,
    SOURCE_DOCS_DIR,
    metadata_dirs_for,
)

try:
    import win32com.client as win32
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False

LOG_DIR = INJECTED_METADATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"injector_{datetime.now().strftime('%Y%m%d_%H%M')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("injector")

NATIVE_CUSTOM_KEYS = [
    "language_detected",
    "Title | Titre",
    "Document Type / Type de document",
    "Sensitivity",
    "Sensibilité",
    "personal_information",
    "Function_EN",
    "Function_FR",
    "Function_Desc_Sum_EN",
    "Function_Desc_Sum_FR",
    "Sub-Function_EN",
    "Sub-Function_FR",
    "Sub-Function_Desc_Summ_EN",
    "Sub-Function_Desc_Summ_FR",
    "Business_Process_EN",
    "Business_Process_FR",
    "Full_File_Class_No",
    "Retention Period",
    "Retention Trigger",
    "Disposition Authorization / Autorisation de disposition",
    "Technical Environment | Environnement technique",
    "Litigation_hold",
    "Archival_value",
    "critical_business_content",
    "needs_review",
    "embedding_model",
]


def _resolve_original(metadata: dict, json_file: Path) -> Path | None:
    raw = str(metadata.get("original_path", "") or "").strip()
    if raw:
        p = Path(raw)
        if p.is_file():
            return p

    name = json_file.name
    if name.endswith(".metadata.json"):
        original_name = name[: -len(".metadata.json")]
    else:
        original_name = json_file.stem

    hits = list(SOURCE_DOCS_DIR.rglob(original_name))
    for h in hits:
        if h.is_file():
            return h
    return None


def _set_custom_property(doc, key: str, value: str) -> None:
    value = (value or "")[:255]
    if not value.strip():
        return
    safe_key = (
        key.replace("|", "-")
        .replace("/", "-")
        .replace("\\", "-")
        [:64]
    )
    try:
        doc.CustomDocumentProperties(safe_key).Value = value
    except Exception:
        try:
            doc.CustomDocumentProperties.Add(safe_key, False, 4, value)
        except Exception:
            pass


def _inject_word(target_path: Path, metadata: dict) -> bool:
    app = None
    doc = None
    try:
        app = win32.DispatchEx("Word.Application")
        app.Visible = False
        app.DisplayAlerts = 0
        doc = app.Documents.Open(str(target_path), ReadOnly=False)

        title = str(metadata.get("Title | Titre", "") or "")[:255]
        subject = str(metadata.get("Document Type / Type de document", "") or "")[:255]
        keywords = (
            f"Function:{metadata.get('Function_EN', '')}; "
            f"Class:{metadata.get('Full_File_Class_No', '')}; "
            f"Sensitivity:{metadata.get('Sensitivity', '')}"
        )[:255]

        try:
            doc.BuiltInDocumentProperties("Title").Value = title
        except Exception:
            pass
        try:
            doc.BuiltInDocumentProperties("Subject").Value = subject
        except Exception:
            pass
        try:
            doc.BuiltInDocumentProperties("Keywords").Value = keywords
        except Exception:
            pass

        for key in NATIVE_CUSTOM_KEYS:
            _set_custom_property(doc, key, str(metadata.get(key, "") or ""))

        doc.Save()
        return True
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
            try:
                del app
            except Exception:
                pass


def _inject_excel(target_path: Path, metadata: dict) -> bool:
    app = None
    wb = None
    try:
        app = win32.DispatchEx("Excel.Application")
        app.Visible = False
        app.DisplayAlerts = False
        wb = app.Workbooks.Open(str(target_path))

        try:
            wb.BuiltinDocumentProperties("Title").Value = str(
                metadata.get("Title | Titre", "") or ""
            )[:255]
        except Exception:
            pass
        try:
            wb.BuiltinDocumentProperties("Subject").Value = str(
                metadata.get("Document Type / Type de document", "") or ""
            )[:255]
        except Exception:
            pass

        wb.Save()
        return True
    finally:
        if wb is not None:
            try:
                wb.Close(False)
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
            try:
                del app
            except Exception:
                pass


def inject_metadata(original_path: Path, sidecar_path: Path, target_path: Path) -> bool:
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original_path, target_path)
        logger.info(f"Cloned: {target_path}")

        with open(sidecar_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        suffix = target_path.suffix.lower()
        native_ok = False

        if WIN32COM_AVAILABLE and suffix in {".docx", ".doc"}:
            try:
                native_ok = bool(_inject_word(target_path, metadata))
                if native_ok:
                    logger.info(f"Native Word metadata: {target_path.name}")
            except Exception as e:
                logger.warning(f"Word injection failed for {target_path.name}: {e}")

        elif WIN32COM_AVAILABLE and suffix in {".xlsx", ".xls"}:
            try:
                native_ok = bool(_inject_excel(target_path, metadata))
                if native_ok:
                    logger.info(f"Native Excel metadata: {target_path.name}")
            except Exception as e:
                logger.warning(f"Excel injection failed for {target_path.name}: {e}")

        sidecar_copy = target_path.with_name(target_path.name + ".metadata.json")
        shutil.copy2(sidecar_path, sidecar_copy)
        if not native_ok:
            logger.info(f"Side-car only (no native inject): {sidecar_copy.name}")

        return True

    except Exception as e:
        logger.error(f"Failed {original_path.name}: {type(e).__name__}: {e}")
        return False


def run_injector(embedder_key: str = "minilm") -> None:
    dirs = metadata_dirs_for(embedder_key)
    placeholders = dirs["placeholders"]
    injected = dirs["root"]

    logger.info("=" * 70)
    logger.info("METADATA INJECTOR STARTED")
    logger.info(f"Embedder     : {dirs['key']}")
    logger.info(f"Source docs  : {SOURCE_DOCS_DIR}")
    logger.info(f"Placeholders : {placeholders}")
    logger.info(f"Injected out : {injected}")
    logger.info(f"win32com     : {WIN32COM_AVAILABLE}")
    logger.info("=" * 70)

    injected.mkdir(parents=True, exist_ok=True)

    if not placeholders.exists():
        logger.error(f"Placeholders folder not found: {placeholders}")
        print(f"ERROR: Placeholders not found: {placeholders}")
        return

    json_files = sorted(placeholders.glob("*.metadata.json"))
    logger.info(f"Found {len(json_files)} placeholder JSON files")

    if not json_files:
        logger.warning("No placeholder JSON files found.")
        print("No placeholders to process.")
        return

    success = 0
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error(f"Cannot read {json_file.name}: {e}")
            continue

        original_path = _resolve_original(metadata, json_file)
        if original_path is None:
            logger.warning(f"Original not found for: {json_file.name}")
            continue

        try:
            relative = original_path.relative_to(SOURCE_DOCS_DIR)
            target_path = injected / relative
        except ValueError:
            target_path = injected / original_path.name

        if inject_metadata(original_path, json_file, target_path):
            success += 1

    logger.info(f"Injection finished | {success} / {len(json_files)} processed")
    print("\n" + "=" * 70)
    print(f"Injector complete | {success} documents | embedder={dirs['key']}")
    print(f"Output: {injected}")
    print(f"Log   : {LOG_FILE}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Clone documents and inject metadata")
    parser.add_argument(
        "--embedder",
        default="minilm",
        choices=["minilm", "qwen3"],
        help="Which model folder to read placeholders from and write clones into",
    )
    args = parser.parse_args()
    run_injector(args.embedder)


if __name__ == "__main__":
    main()
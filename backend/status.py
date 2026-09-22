# backend/status.py
"""Live folder / artifact status for the Gradio Dashboard."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from project_config import (
    CLASSIFICATION_RESULTS_DIR,
    DEDUPS_DIR,
    EXTRACTED_TEXTS_DIR,
    INJECTED_MINILM_DIR,
    INJECTED_QWEN_DIR,
    PLACEHOLDERS_MINILM_DIR,
    PLACEHOLDERS_QWEN_DIR,
    SOURCE_DOCS_DIR,
    PLACEHOLDERS_QWEN3_4B_DIR,
    INJECTED_QWEN3_4B_DIR,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_DIR = PROJECT_ROOT / "Resources-Sources"
FCP_CACHE_DIR = CLASSIFICATION_RESULTS_DIR / "embedding_cache"


def _iter_files(folder: Path, patterns: list[str] | None = None):
    if not folder.exists():
        return
    if not patterns:
        for p in folder.rglob("*.*"):
            if p.is_file():
                yield p
        return
    for pat in patterns:
        for p in folder.rglob(pat):
            if p.is_file():
                yield p


def _count(folder: Path, patterns: list[str] | None = None) -> int:
    return sum(1 for _ in _iter_files(folder, patterns))


def _latest_mtime(folder: Path, patterns: list[str] | None = None) -> str:
    latest = None
    for p in _iter_files(folder, patterns):
        try:
            m = p.stat().st_mtime
        except OSError:
            continue
        if latest is None or m > latest:
            latest = m
    if latest is None:
        return "—"
    return datetime.fromtimestamp(latest).strftime("%Y-%m-%d %H:%M")


def _mtime_file(path: Path) -> str:
    if not path.is_file():
        return "—"
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def collect_status() -> dict:
    minilm_xlsx = CLASSIFICATION_RESULTS_DIR / "classification_results_minilm.xlsx"
    qwen_xlsx = CLASSIFICATION_RESULTS_DIR / "classification_results_qwen3.xlsx"
    qwen4_xlsx = CLASSIFICATION_RESULTS_DIR / "classification_results_qwen3_4b.xlsx"

    injected_json_m = _count(INJECTED_MINILM_DIR, ["*.metadata.json", "*.json"])
    injected_all_m = _count(INJECTED_MINILM_DIR)
    injected_clones_m = max(0, injected_all_m - injected_json_m)

    injected_json_q = _count(INJECTED_QWEN_DIR, ["*.metadata.json", "*.json"])
    injected_all_q = _count(INJECTED_QWEN_DIR)
    injected_clones_q = max(0, injected_all_q - injected_json_q)

    resource_files = {
        "Doc_Type_Dictionary.txt": (RESOURCES_DIR / "Doc_Type_Dictionary.txt").is_file(),
        "fcp_CSV-UTF.csv": (RESOURCES_DIR / "fcp_CSV-UTF.csv").is_file(),
        "RegEx-db.csv": (RESOURCES_DIR / "RegEx-db.csv").is_file(),
        "trivial_subjects.txt": (RESOURCES_DIR / "trivial_subjects.txt").is_file(),
    }

    fcp_ready = any(FCP_CACHE_DIR.rglob("*.npy")) if FCP_CACHE_DIR.exists() else False

    return {
        "source_docs": _count(SOURCE_DOCS_DIR),
        "source_mtime": _latest_mtime(SOURCE_DOCS_DIR),
        "dedup_reports": _count(DEDUPS_DIR, ["*.xlsx"]),
        "dedup_mtime": _latest_mtime(DEDUPS_DIR, ["*.xlsx"]),
        "extracted_texts": _count(EXTRACTED_TEXTS_DIR, ["*.txt"]),
        "extracted_mtime": _latest_mtime(EXTRACTED_TEXTS_DIR, ["*.txt"]),
        "class_minilm": minilm_xlsx.is_file(),
        "class_minilm_mtime": _mtime_file(minilm_xlsx),
        "class_qwen": qwen_xlsx.is_file(),
        "class_qwen_mtime": _mtime_file(qwen_xlsx),
        "class_qwen4": qwen4_xlsx.is_file(),
        "class_qwen4_mtime": _mtime_file(qwen4_xlsx),
        "ph_minilm": _count(PLACEHOLDERS_MINILM_DIR, ["*.json"]),
        "ph_minilm_mtime": _latest_mtime(PLACEHOLDERS_MINILM_DIR, ["*.json"]),
        "ph_qwen": _count(PLACEHOLDERS_QWEN_DIR, ["*.json"]),
        "ph_qwen_mtime": _latest_mtime(PLACEHOLDERS_QWEN_DIR, ["*.json"]),
        "ph_qwen4": _count(PLACEHOLDERS_QWEN3_4B_DIR, ["*.json"]),
        "ph_qwen4_mtime": _latest_mtime(PLACEHOLDERS_QWEN3_4B_DIR, ["*.json"]),
        "inj_json_minilm": injected_json_m,
        "inj_clones_minilm": injected_clones_m,
        "inj_minilm_mtime": _latest_mtime(INJECTED_MINILM_DIR),
        "inj_json_qwen": injected_json_q,
        "inj_clones_qwen": injected_clones_q,
        "inj_qwen_mtime": _latest_mtime(INJECTED_QWEN_DIR),
        "fcp_index_ready": fcp_ready,
        "fcp_index_mtime": _latest_mtime(FCP_CACHE_DIR, ["*.npy"]),
        "res_doc_type_dict": resource_files["Doc_Type_Dictionary.txt"],
        "res_fcp_csv": resource_files["fcp_CSV-UTF.csv"],
        "res_regex_db": resource_files["RegEx-db.csv"],
        "res_trivial": resource_files["trivial_subjects.txt"],
        "resources_mtime": _latest_mtime(RESOURCES_DIR) if RESOURCES_DIR.exists() else "—",
        "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def status_markdown() -> str:
    s = collect_status()

    def yn_file(ok: bool) -> str:
        return "Yes" if ok else "No"

    def yn(ok: bool) -> str:
        return "**Ready**" if ok else "Missing"

    fcp = "**Ready**" if s["fcp_index_ready"] else "Missing — run Classification once"

    return f"""
### Pipeline snapshot
_Updated: **{s['now']}**_

| Area | Count / status | Last change |
|------|----------------|-------------|
| Source documents | {s['source_docs']} | {s['source_mtime']} |
| Dedup reports (.xlsx) | {s['dedup_reports']} | {s['dedup_mtime']} |
| Extracted texts (.txt) | {s['extracted_texts']} | {s['extracted_mtime']} |
| Classification MiniLM | {yn_file(s['class_minilm'])} | {s['class_minilm_mtime']} |
| Classification Qwen3 | {yn_file(s['class_qwen'])} | {s['class_qwen_mtime']} |
| Classification Qwen3-4B | {yn_file(s['class_qwen4'])} | {s['class_qwen4_mtime']} |
| Placeholders Qwen3-4B (JSON) | {s['ph_qwen4']} | {s['ph_qwen4_mtime']} |
| Placeholders MiniLM (JSON) | {s['ph_minilm']} | {s['ph_minilm_mtime']} |
| Placeholders Qwen3 (JSON) | {s['ph_qwen']} | {s['ph_qwen_mtime']} |
| Injected MiniLM side-cars | {s['inj_json_minilm']} | {s['inj_minilm_mtime']} |
| Injected MiniLM clones | {s['inj_clones_minilm']} | {s['inj_minilm_mtime']} |
| Injected Qwen3 side-cars | {s['inj_json_qwen']} | {s['inj_qwen_mtime']} |
| Injected Qwen3 clones | {s['inj_clones_qwen']} | {s['inj_qwen_mtime']} |
| FCP hierarchy index | {fcp} | {s['fcp_index_mtime']} |
| Resources · Doc_Type_Dictionary.txt | {yn(s['res_doc_type_dict'])} | {s['resources_mtime']} |
| Resources · fcp_CSV-UTF.csv | {yn(s['res_fcp_csv'])} | {s['resources_mtime']} |
| Resources · RegEx-db.csv | {yn(s['res_regex_db'])} | {s['resources_mtime']} |
| Resources · trivial_subjects.txt | {yn(s['res_trivial'])} | {s['resources_mtime']} |

*Click **Refresh status** after a phase finishes. Counts include nested folders.*
"""
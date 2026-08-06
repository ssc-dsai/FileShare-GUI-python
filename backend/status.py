# backend/status.py
"""Live folder / artifact status for the Gradio Dashboard."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from project_config import (
    CLASSIFICATION_RESULTS_DIR,
    DEDUPS_DIR,
    EXTRACTED_TEXTS_DIR,
    INJECTED_METADATA_DIR,
    LITIGATION_CASE_SOURCE_DIR,
    LITIGATION_INDEX_DIR,
    LITIGATION_PACKAGES_DIR,
    LITIGATION_REPORTS_DIR,
    LITIGATION_SEARCH_DIR,
    PLACEHOLDERS_DIR,
    SOURCE_DOCS_DIR,
)

# Project root (parent of backend/)
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
    class_xlsx = CLASSIFICATION_RESULTS_DIR / "classification_results.xlsx"
    class_csv = CLASSIFICATION_RESULTS_DIR / "classification_results.csv"
    emb = LITIGATION_INDEX_DIR / "chunks_embeddings.npy"
    bm25 = LITIGATION_INDEX_DIR / "bm25_corpus.pkl"

    # Injected: clones vs JSON side-cars
    injected_json = _count(INJECTED_METADATA_DIR, ["*.metadata.json", "*.json"])
    injected_all = _count(INJECTED_METADATA_DIR)
    injected_clones = max(0, injected_all - injected_json)

    # Package bodies (exclude manifests)
    package_main = 0
    if LITIGATION_PACKAGES_DIR.exists():
        for p in LITIGATION_PACKAGES_DIR.rglob("*.txt"):
            if p.is_file() and not p.name.endswith(".manifest.txt"):
                package_main += 1

    # Resources-Sources artifacts
    resource_files = {
        "Doc_Type_Dictionary.txt": (RESOURCES_DIR / "Doc_Type_Dictionary.txt").is_file(),
        "fcp_CSV-UTF.csv": (RESOURCES_DIR / "fcp_CSV-UTF.csv").is_file(),
        "RegEx-db.csv": (RESOURCES_DIR / "RegEx-db.csv").is_file(),
        "trivial_subjects.txt": (RESOURCES_DIR / "trivial_subjects.txt").is_file(),
    }

    # FCP hierarchy embedding cache (built during Classification)
    fcp_ready = False
    if FCP_CACHE_DIR.exists():
        fcp_ready = (
            (FCP_CACHE_DIR / "function_embeddings.npy").exists()
            or (FCP_CACHE_DIR / "embeddings.npy").exists()
            or any(FCP_CACHE_DIR.glob("*.npy"))
        )
    fcp_mtime = (
        _latest_mtime(FCP_CACHE_DIR, ["*.npy", "*.json", "*.txt"])
        if FCP_CACHE_DIR.exists()
        else "—"
    )

    return {
        "source_docs": _count(SOURCE_DOCS_DIR),
        "source_mtime": _latest_mtime(SOURCE_DOCS_DIR),
        "extracted_texts": _count(EXTRACTED_TEXTS_DIR, ["*.txt"]),
        "extracted_mtime": _latest_mtime(EXTRACTED_TEXTS_DIR, ["*.txt"]),
        "dedup_reports": _count(DEDUPS_DIR, ["*.xlsx"]),
        "dedup_mtime": _latest_mtime(DEDUPS_DIR, ["*.xlsx", "*.log"]),
        "classification_excel": class_xlsx.exists(),
        "classification_csv": class_csv.exists(),
        "classification_mtime": _mtime_file(class_xlsx),
        "placeholders": _count(PLACEHOLDERS_DIR, ["*.json", "*.metadata.json"]),
        "placeholders_mtime": _latest_mtime(PLACEHOLDERS_DIR, ["*.json", "*.metadata.json"]),
        "injected_clones": injected_clones,
        "injected_json": injected_json,
        "injected_mtime": _latest_mtime(INJECTED_METADATA_DIR),
        "case_source": _count(LITIGATION_CASE_SOURCE_DIR),
        "case_mtime": _latest_mtime(LITIGATION_CASE_SOURCE_DIR),
        "packages_txt": package_main,
        "packages_mtime": _latest_mtime(LITIGATION_PACKAGES_DIR, ["*.txt", "*.log"]),
        "search_corpus": _count(LITIGATION_SEARCH_DIR),
        "search_mtime": _latest_mtime(LITIGATION_SEARCH_DIR),
        "index_ready": emb.exists() and bm25.exists(),
        "index_mtime": _mtime_file(emb) if emb.exists() else "—",
        "fcp_index_ready": fcp_ready,
        "fcp_index_mtime": fcp_mtime,
        "res_doc_type_dict": resource_files["Doc_Type_Dictionary.txt"],
        "res_fcp_csv": resource_files["fcp_CSV-UTF.csv"],
        "res_regex_db": resource_files["RegEx-db.csv"],
        "res_trivial": resource_files["trivial_subjects.txt"],
        "resources_mtime": _latest_mtime(RESOURCES_DIR) if RESOURCES_DIR.exists() else "—",
        "reports_xlsx": _count(LITIGATION_REPORTS_DIR, ["*.xlsx"]),
        "reports_mtime": _latest_mtime(LITIGATION_REPORTS_DIR, ["*.xlsx", "*.csv"]),
        "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def status_markdown() -> str:
    s = collect_status()

    class_status = "Yes" if s["classification_excel"] else "No"
    if s["classification_csv"] and s["classification_excel"]:
        class_status = "Yes (xlsx + csv)"
    elif s["classification_csv"]:
        class_status = "CSV only"

    idx = "**Ready**" if s["index_ready"] else "Missing — run Build Index"
    fcp = "**Ready**" if s["fcp_index_ready"] else "Missing — run Classification once"

    def yn(ok: bool) -> str:
        return "**Ready**" if ok else "Missing"

    return f"""
### Pipeline snapshot
_Updated: **{s['now']}**_

| Area | Count / status | Last change |
|------|----------------|-------------|
| Source documents | {s['source_docs']} | {s['source_mtime']} |
| Dedup reports (.xlsx) | {s['dedup_reports']} | {s['dedup_mtime']} |
| Extracted texts (.txt) | {s['extracted_texts']} | {s['extracted_mtime']} |
| Classification Excel | {class_status} | {s['classification_mtime']} |
| Placeholders (JSON) | {s['placeholders']} | {s['placeholders_mtime']} |
| Injected side-car JSON | {s['injected_json']} | {s['injected_mtime']} |
| Injected clones | {s['injected_clones']} | {s['injected_mtime']} |
| Litigation case source | {s['case_source']} | {s['case_mtime']} |
| Litigation packages (.txt) | {s['packages_txt']} | {s['packages_mtime']} |
| Search corpus | {s['search_corpus']} | {s['search_mtime']} |
| Litigation index | {idx} | {s['index_mtime']} |
| FCP hierarchy index | {fcp} | {s['fcp_index_mtime']} |
| Resources · Doc_Type_Dictionary.txt | {yn(s['res_doc_type_dict'])} | {s['resources_mtime']} |
| Resources · fcp_CSV-UTF.csv | {yn(s['res_fcp_csv'])} | {s['resources_mtime']} |
| Resources · RegEx-db.csv | {yn(s['res_regex_db'])} | {s['resources_mtime']} |
| Resources · trivial_subjects.txt | {yn(s['res_trivial'])} | {s['resources_mtime']} |
| Search reports (.xlsx) | {s['reports_xlsx']} | {s['reports_mtime']} |

*Click **Refresh status** after a phase finishes. Counts include nested folders.*
"""
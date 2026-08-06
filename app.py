"""
FileShare-GUI – Gradio orchestrator
===================================
Launch:
    python app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr

from backend.runners import (
    run_classification,
    run_dedup_analysis,
    run_ingestion,
    run_litigation_index,
    run_litigation_package,
    run_litigation_search,
    run_metadata_injector,
    run_placeholder_creator,
    run_stop,
)
from project_config import (
    CLASSIFICATION_RESULTS_DIR,
    DEDUPS_DIR,
    EMBEDDING_MODEL_PATH,
    EXTRACTED_TEXTS_DIR,
    INJECTED_METADATA_DIR,
    LITIGATION_CASE_SOURCE_DIR,
    LITIGATION_INDEX_DIR,
    LITIGATION_PACKAGES_DIR,
    LITIGATION_REPORTS_DIR,
    LITIGATION_SEARCH_DIR,
    PLACEHOLDERS_DIR,
    SOURCE_DOCS_DIR,
    VISION_MODEL_PATH,
)

# Optional: status helper (falls back if missing)
try:
    from backend.status import status_markdown as _status_markdown
except Exception:
    def _status_markdown() -> str:
        return (
            "### Pipeline snapshot\n\n"
            "_`backend/status.py` not found — add it for live counts._\n"
        )


# ---------------------------------------------------------------------------
# CSS (Gradio 6: pass to launch(), not Blocks())
# ---------------------------------------------------------------------------
CSS = """
.log-box textarea {
    font-family: ui-monospace, Consolas, "Courier New", monospace !important;
    font-size: 12px !important;
    line-height: 1.35 !important;
}
"""


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def refresh_dashboard() -> str:
    return _status_markdown()


def ui_run_dedup() -> str:
    ok, log, _ = run_dedup_analysis()
    header = "✅ Deduplication analysis finished" if ok else "❌ Deduplication analysis failed"
    return f"{header}\n\n```\n{log}\n```"


def ui_run_ingestion() -> str:
    ok, log, _ = run_ingestion()
    header = "✅ Ingestion finished" if ok else "❌ Ingestion failed"
    return f"{header}\n\n```\n{log}\n```"


def ui_run_classification() -> str:
    ok, log, _ = run_classification()
    header = "✅ Classification finished" if ok else "❌ Classification failed"
    extra = f"\n\nExcel: `{CLASSIFICATION_RESULTS_DIR / 'classification_results.xlsx'}`"
    return f"{header}{extra if ok else ''}\n\n```\n{log}\n```"


def ui_run_placeholders(excel_name: str) -> str:
    ok, log, _ = run_placeholder_creator(excel_name.strip() or "classification_results.xlsx")
    header = "✅ Placeholders created" if ok else "❌ Placeholder creation failed"
    extra = f"\n\nFolder: `{PLACEHOLDERS_DIR}`"
    return f"{header}{extra if ok else ''}\n\n```\n{log}\n```"


def ui_run_injector() -> str:
    ok, log, _ = run_metadata_injector()
    header = "✅ Metadata injection finished" if ok else "❌ Metadata injection failed"
    extra = f"\n\nOutput: `{INJECTED_METADATA_DIR}`"
    return f"{header}{extra if ok else ''}\n\n```\n{log}\n```"


def ui_run_litigation_package(name: str) -> str:
    ok, log, _ = run_litigation_package(
        str(LITIGATION_CASE_SOURCE_DIR),
        (name or "").strip() or None,
    )
    header = "✅ Litigation package built" if ok else "❌ Litigation package failed"
    return f"{header}\n\n```\n{log}\n```"


def ui_run_litigation_index(rebuild: bool) -> str:
    ok, log, _ = run_litigation_index(rebuild=bool(rebuild))
    header = "✅ Index finished" if ok else "❌ Index failed"
    extra = f"\n\nIndex dir: `{LITIGATION_INDEX_DIR}`"
    return f"{header}{extra if ok else ''}\n\n```\n{log}\n```"


def ui_run_litigation_search(pkg: str, top_k: float, min_score: float) -> str:
    pkg = (pkg or "").strip()
    if not pkg:
        return "❌ Enter the full path to the package .txt file."
    ok, log, _ = run_litigation_search(
        pkg,
        top_k=int(top_k or 50),
        min_score=float(min_score or 0.22),
    )
    header = "✅ Search + report finished" if ok else "❌ Search failed"
    extra = f"\n\nReports: `{LITIGATION_REPORTS_DIR}`"
    return f"{header}{extra if ok else ''}\n\n```\n{log}\n```"

def ui_stop() -> str:
    ok, log, _ = run_stop()
    return log

# ---------------------------------------------------------------------------
# Build UI
# ---------------------------------------------------------------------------
def build_ui() -> gr.Blocks:
    with gr.Blocks(title="FileShare CleanUp") as demo:
        gr.Markdown(
            """
            # FileShare CleanUp
            Document classification, metadata, and litigation search orchestrator.

            Paths come from `project_config.py` / `ENV_*` env vars. **Restart** after path changes.
            """
        )

        # ===================== Dashboard =====================
        with gr.Tab("Dashboard"):
            gr.Markdown("### Operational snapshot")
            dash_md = gr.Markdown(value=refresh_dashboard())
            btn_refresh = gr.Button("🔄 Refresh status", variant="secondary")
            btn_refresh.click(fn=refresh_dashboard, inputs=None, outputs=dash_md)

        # ===================== Configuration =====================
        with gr.Tab("Configuration"):
            gr.Markdown(
                """
                ### Path groups
                Edit `project_config.py` or environment variables, then **restart** the app.
                Live path editing in the UI is not supported.
                """
            )
            gr.Markdown("#### Pipeline")
            gr.Textbox(label="SOURCE_DOCS_DIR", value=str(SOURCE_DOCS_DIR), interactive=False)
            gr.Textbox(label="EXTRACTED_TEXTS_DIR", value=str(EXTRACTED_TEXTS_DIR), interactive=False)
            gr.Textbox(label="CLASSIFICATION_RESULTS_DIR", value=str(CLASSIFICATION_RESULTS_DIR), interactive=False)
            gr.Textbox(label="DEDUPS_DIR", value=str(DEDUPS_DIR), interactive=False)
            gr.Textbox(label="INJECTED_METADATA_DIR", value=str(INJECTED_METADATA_DIR), interactive=False)
            gr.Textbox(label="PLACEHOLDERS_DIR", value=str(PLACEHOLDERS_DIR), interactive=False)

            gr.Markdown("#### Models")
            gr.Textbox(label="EMBEDDING_MODEL_PATH", value=str(EMBEDDING_MODEL_PATH), interactive=False)
            gr.Textbox(label="VISION_MODEL_PATH", value=str(VISION_MODEL_PATH), interactive=False)

            gr.Markdown("#### Litigation")
            gr.Textbox(label="LITIGATION_CASE_SOURCE_DIR", value=str(LITIGATION_CASE_SOURCE_DIR), interactive=False)
            gr.Textbox(label="LITIGATION_PACKAGES_DIR", value=str(LITIGATION_PACKAGES_DIR), interactive=False)
            gr.Textbox(label="LITIGATION_SEARCH_DIR", value=str(LITIGATION_SEARCH_DIR), interactive=False)
            gr.Textbox(label="LITIGATION_INDEX_DIR", value=str(LITIGATION_INDEX_DIR), interactive=False)
            gr.Textbox(label="LITIGATION_REPORTS_DIR", value=str(LITIGATION_REPORTS_DIR), interactive=False)

        # ===================== 0 Dedup =====================
        with gr.Tab("0 · Deduplication"):
            gr.Markdown(
                f"""
                ### Phase 0 – Deduplication
                **Prerequisite:** documents under `SOURCE_DOCS_DIR`  
                `{SOURCE_DOCS_DIR}`

                Produces a review Excel under `DEDUPS_DIR`. Adjust `User_Confirmed_Delete`, then use delete (dry-run available).
                """
            )
            btn_dedup = gr.Button("▶ Run Deduplication Analysis", variant="primary")
            dedup_log = gr.Textbox(label="Log output", lines=20, max_lines=40, elem_classes=["log-box"])
            btn_dedup.click(fn=ui_run_dedup, outputs=dedup_log)

        # ===================== 1 Ingestion =====================
        with gr.Tab("1 · Ingestion"):
            gr.Markdown(
                f"""
                ### Phase 1 – Ingestion
                **Prerequisite:** source documents present (Dedup optional).  
                Writes `.txt` files to `{EXTRACTED_TEXTS_DIR}`
                """
            )
            btn_ingest = gr.Button("▶ Run Ingestion", variant="primary")
            ingest_log = gr.Textbox(label="Log output", lines=20, max_lines=40, elem_classes=["log-box"])
            btn_ingest.click(fn=ui_run_ingestion, outputs=ingest_log)

        # ===================== 2 Classification =====================
        with gr.Tab("2 · Classification"):
            gr.Markdown(
                f"""
                ### Phase 2 – Classification
                **Prerequisite:** extracted `.txt` files in `{EXTRACTED_TEXTS_DIR}`

                MiniLM hierarchy match + optional Qwen2-VL for vision-flagged files.  
                Output: `{CLASSIFICATION_RESULTS_DIR / "classification_results.xlsx"}`
                """
            )
            btn_class = gr.Button("▶ Run Classification", variant="primary")
            class_log = gr.Textbox(label="Log output", lines=20, max_lines=40, elem_classes=["log-box"])
            btn_class.click(fn=ui_run_classification, outputs=class_log)

        # ===================== Metadata =====================
        with gr.Tab("3–4 · Metadata"):
            gr.Markdown(
                f"""
                ### Phase 3 – Placeholders
                **Prerequisite:** `classification_results.xlsx` exists.  
                Writes JSON under `{PLACEHOLDERS_DIR}`
                """
            )
            excel_name = gr.Textbox(
                label="Classification Excel filename",
                value="classification_results.xlsx",
            )
            btn_ph = gr.Button("▶ Create Placeholders", variant="primary")
            ph_log = gr.Textbox(label="Log (Placeholders)", lines=12, max_lines=25, elem_classes=["log-box"])
            btn_ph.click(fn=ui_run_placeholders, inputs=excel_name, outputs=ph_log)

            gr.Markdown("---")
            gr.Markdown(
                f"""
                ### Phase 4 – Metadata Injector
                **Prerequisite:** placeholder JSON files.  
                Clones + optional native Office properties → `{INJECTED_METADATA_DIR}`
                """
            )
            btn_inj = gr.Button("▶ Run Metadata Injector", variant="primary")
            inj_log = gr.Textbox(label="Log (Injector)", lines=12, max_lines=25, elem_classes=["log-box"])
            btn_inj.click(fn=ui_run_injector, outputs=inj_log)

        # ===================== Litigation =====================
        with gr.Tab("5 · Litigation"):
            gr.Markdown(
                f"""
                ### Paths (from Configuration)
                - **Case source (package input):** `{LITIGATION_CASE_SOURCE_DIR}`
                - **Packages output:** `{LITIGATION_PACKAGES_DIR}`
                - **Search corpus:** `{LITIGATION_SEARCH_DIR}`
                - **Index:** `{LITIGATION_INDEX_DIR}`
                - **Reports:** `{LITIGATION_REPORTS_DIR}`
                """
            )

            gr.Markdown("### 1 · Build compact package")
            lit_output_name = gr.Textbox(
                label="Package name (optional)",
                placeholder="Leave blank to use the case-source folder name",
            )
            btn_lit_package = gr.Button("▶ Build Litigation Package", variant="primary")
            lit_package_log = gr.Textbox(label="Package log", lines=12, max_lines=25, elem_classes=["log-box"])
            btn_lit_package.click(
                fn=ui_run_litigation_package,
                inputs=[lit_output_name],
                outputs=lit_package_log,
            )

            gr.Markdown("---")
            gr.Markdown(
                f"""
                ### 2 · Build / rebuild search index
                Indexes **`LITIGATION_SEARCH_DIR`** (`{LITIGATION_SEARCH_DIR}`).  
                Originals are never modified. Run once, or after the corpus changes.
                """
            )
            lit_rebuild = gr.Checkbox(
                label="Rebuild index from scratch (check to force rebuild)",
                value=True,
            )
            btn_lit_index = gr.Button("▶ Build / Rebuild Index", variant="primary")
            lit_index_log = gr.Textbox(label="Index log", lines=12, max_lines=25, elem_classes=["log-box"])
            btn_lit_index.click(
                fn=ui_run_litigation_index,
                inputs=[lit_rebuild],
                outputs=lit_index_log,
            )

            gr.Markdown("---")
            gr.Markdown(
                """
                ### 3 · Search with package → Excel report
                **Prerequisite:** index exists (`chunks_embeddings.npy` + `bm25_corpus.pkl`) and package `.txt`.
                Uses package as query (MiniLM + BM25 on tombstone when facts exist).
                """
            )
            default_pkg = str(
                LITIGATION_PACKAGES_DIR
                / LITIGATION_CASE_SOURCE_DIR.name
                / f"{LITIGATION_CASE_SOURCE_DIR.name}.txt"
            )
            lit_package_path = gr.Textbox(
                label="Package file (.txt) used as query",
                value=default_pkg,
            )
            lit_top_k = gr.Number(label="Top K results", value=50, precision=0)
            lit_min_score = gr.Number(label="Min vector similarity score", value=0.22)
            btn_lit_search = gr.Button("▶ Run Search + Report", variant="primary")
            lit_search_log = gr.Textbox(
                label="Search / report log",
                lines=14,
                max_lines=30,
                elem_classes=["log-box"],
            )
            btn_lit_search.click(
                fn=ui_run_litigation_search,
                inputs=[lit_package_path, lit_top_k, lit_min_score],
                outputs=lit_search_log,
            )

        gr.Markdown(
            """
            **Stop:** ends the current phase only. Files already written are **kept** (no undo).
            """
        )
        with gr.Row():
            btn_stop = gr.Button("⏹ Stop current job", variant="stop")
            stop_log = gr.Textbox(
                label="Stop status",
                lines=2,
                max_lines=4,
                elem_classes=["log-box"],
            )
        btn_stop.click(fn=ui_stop, inputs=None, outputs=stop_log)

        # ===================== Help =====================
        with gr.Tab("Help"):
            gr.Markdown(
                """
                ## Runbook

                ### Classification pipeline
                1. **0 · Deduplication** (optional) → review Excel → delete confirmed duplicates  
                2. **1 · Ingestion** → extracted texts  
                3. **2 · Classification** → Excel + vision descriptions  
                4. **3 · Placeholders** → JSON side-cars  
                5. **4 · Injector** → clones + native metadata where possible  

                ### Litigation (independent of classification)
                1. Put court-case files in **LITIGATION_CASE_SOURCE_DIR**  
                2. **Build package** (compact tombstone + summaries)  
                3. **Build index** on **LITIGATION_SEARCH_DIR** (once / when corpus changes)  
                4. **Search + report** using the package `.txt` as the query  

                ### Notes
                - Change paths only via `project_config.py` or `ENV_*` env vars, then **restart**.  
                - Closing the browser does **not** stop a long job already running on the server.  
                - BM25 uses tombstone facts; if all values are `Not Found`, only vector scores apply.  
                """
            )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.queue()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        css=CSS,
    )
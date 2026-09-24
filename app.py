"""
FileShare-GUI – Gradio orchestrator
===================================
Launch:
    python app.py
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr
import pandas as pd

from backend.runners import (
    run_classification,
    run_dedup_analysis,
    run_dedup_delete,
    run_ingestion,
    run_metadata_injector,
    run_placeholder_creator,
    run_stop,
)
from project_config import (
    CLASSIFICATION_RESULTS_DIR,
    DEDUPS_DIR,
    EMBEDDING_MODEL_MINILM_PATH,
    EMBEDDING_MODEL_QWEN_PATH,
    EXTRACTED_TEXTS_DIR,
    INJECTED_METADATA_DIR,
    INJECTED_MINILM_DIR,
    INJECTED_QWEN_DIR,
    PLACEHOLDERS_MINILM_DIR,
    PLACEHOLDERS_QWEN_DIR,
    SOURCE_DOCS_DIR,
    VISION_MODEL_PATH,
    HIERARCHY_CSV,
    EMBEDDING_MODEL_QWEN3_4B_PATH,
    INJECTED_QWEN3_4B_DIR,
    PLACEHOLDERS_QWEN3_4B_DIR,
)

from Classification.hitl_review import (
    apply_override,
    current_assignment,
    document_choices,
    function_choices,
    load_fcp,
    load_report,
    process_choices,
    subfunction_choices,
)

import re

_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _sanitize_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = (
                out[col]
                .astype(str)
                .map(lambda v: _ILLEGAL_XML.sub("", v) if v not in ("nan", "None") else v)
            )
    return out

try:
    from backend.status import status_markdown as _status_markdown
except Exception:
    def _status_markdown() -> str:
        return (
            "### Pipeline snapshot\n\n"
            "_`backend/status.py` not found — add it for live counts._\n"
        )


CSS = """
.log-box textarea {
    font-family: ui-monospace, Consolas, "Courier New", monospace !important;
    font-size: 12px !important;
    line-height: 1.35 !important;
}
"""


def refresh_dashboard() -> str:
    return _status_markdown()


RADIO_TO_KEY = {
    "MiniLM (fast baseline)": "minilm",
    "Qwen3-0.6B (stronger GPU)": "qwen3",
    "Qwen3-4B (strongest, heavy and slower)": "qwen3_4b",
}
RADIO_CHOICES = list(RADIO_TO_KEY.keys())


def _embedder_key(choice: str) -> str:
    if choice in RADIO_TO_KEY:
        return RADIO_TO_KEY[choice]
    c = (choice or "").lower()
    if "4b" in c:
        return "qwen3_4b"
    if "qwen" in c:
        return "qwen3"
    return "minilm"


def _excel_for_embedder(choice: str) -> str:
    return {
        "qwen3_4b": "classification_results_qwen3_4b.xlsx",
        "qwen3": "classification_results_qwen3.xlsx",
        "minilm": "classification_results_minilm.xlsx",
    }.get(_embedder_key(choice), "classification_results_minilm.xlsx")


def _hitl_key(choice: str) -> str:
    return _embedder_key(choice)


def ui_run_dedup() -> str:
    ok, log, _ = run_dedup_analysis()
    header = "✅ Deduplication analysis finished" if ok else "❌ Deduplication analysis failed"
    extra = f"\n\nFolder: `{DEDUPS_DIR}`"
    return f"{header}{extra}\n\n```\n{log}\n```"


def ui_run_dedup_delete(excel_name: str, dry_run: bool) -> str:
    name = (excel_name or "").strip()
    if not name:
        return "❌ Enter the Excel filename (it must sit in DEDUPS_DIR)."
    ok, log, _ = run_dedup_delete(name, dry_run=bool(dry_run))
    if dry_run:
        header = "✅ Dry-run finished (no files deleted)" if ok else "❌ Dry-run failed"
    else:
        header = "✅ Confirmed delete finished" if ok else "❌ Delete failed"
    extra = f"\n\nFolder: `{DEDUPS_DIR}`"
    return f"{header}{extra}\n\n```\n{log}\n```"


def ui_run_ingestion() -> str:
    ok, log, _ = run_ingestion()
    header = "✅ Ingestion finished" if ok else "❌ Ingestion failed"
    return f"{header}\n\n```\n{log}\n```"


def ui_run_classification(embedder_choice: str) -> str:
    key = _embedder_key(embedder_choice)
    stem = {
        "qwen3_4b": "classification_results_qwen3_4b",
        "qwen3": "classification_results_qwen3",
        "minilm": "classification_results_minilm",
    }.get(key, "classification_results_minilm")

    ok, log, _ = run_classification(key)
    header = "✅ Classification finished" if ok else "❌ Classification failed"
    extra = f"\n\nExcel: `{CLASSIFICATION_RESULTS_DIR / (stem + '.xlsx')}`"
    return f"{header}{extra if ok else ''}\n\n```\n{log}\n```"


def ui_run_placeholders(embedder_choice: str, excel_name: str) -> str:
    key = _embedder_key(embedder_choice)
    name = (excel_name or "").strip() or _excel_for_embedder(embedder_choice)
    ok, log, _ = run_placeholder_creator(name, embedder_key=key)
    if key == "qwen3_4b":
        out = PLACEHOLDERS_QWEN3_4B_DIR
    elif key == "qwen3":
        out = PLACEHOLDERS_QWEN_DIR
    else:
        out = PLACEHOLDERS_MINILM_DIR

    header = "✅ Placeholders created" if ok else "❌ Placeholder creation failed"
    extra = f"\n\nExcel: `{name}`\nFolder: `{out}`"
    return f"{header}{extra if ok else ''}\n\n```\n{log}\n```"


def ui_run_injector(embedder_choice: str) -> str:
    key = _embedder_key(embedder_choice)
    ok, log, _ = run_metadata_injector(embedder_key=key)
    if key == "qwen3_4b":
        out = INJECTED_QWEN3_4B_DIR
    elif key == "qwen3":
        out = INJECTED_QWEN_DIR
    else:
        out = INJECTED_MINILM_DIR

    header = "✅ Metadata injection finished" if ok else "❌ Metadata injection failed"
    extra = f"\n\nOutput: `{out}`"
    return f"{header}{extra if ok else ''}\n\n```\n{log}\n```"


def ui_stop() -> str:
    ok, log, _ = run_stop()
    return log

def _hitl_key(choice: str) -> str:
    return "qwen3" if "qwen" in (choice or "").lower() else "minilm"


def ui_hitl_load(embedder_choice: str):
    key = _hitl_key(embedder_choice)
    try:
        fcp = load_fcp()
        df = load_report(key)
    except Exception as e:
        empty = gr.update(choices=[], value=None)
        return empty, empty, empty, empty, f"❌ {e}"

    docs = document_choices(df)
    funcs = function_choices(fcp)
    first = docs[0] if docs else None
    cur = current_assignment(df, first) if first else {}
    fn = cur.get("Function_EN") or "Unknown"
    subs = subfunction_choices(fcp, fn)
    sub = cur.get("Sub-Function_EN") if cur.get("Sub-Function_EN") in subs else (subs[0] if subs else "Unknown")
    procs = process_choices(fcp, fn, sub)
    proc = cur.get("Business_Process_EN") if cur.get("Business_Process_EN") in procs else (procs[0] if procs else "Unknown")
    msg = f"Loaded {len(docs)} rows from classification_results_{key}.xlsx"
    return (
        gr.update(choices=docs, value=first),
        gr.update(choices=funcs, value=fn if fn in funcs else "Unknown"),
        gr.update(choices=subs, value=sub),
        gr.update(choices=procs, value=proc),
        msg,
    )


def ui_hitl_pick_doc(embedder_choice: str, filename: str):
    key = _hitl_key(embedder_choice)
    try:
        fcp = load_fcp()
        df = load_report(key)
        cur = current_assignment(df, filename)
    except Exception as e:
        return gr.update(), gr.update(), gr.update(), f"❌ {e}"
    fn = cur.get("Function_EN") or "Unknown"
    funcs = function_choices(fcp)
    subs = subfunction_choices(fcp, fn)
    sub = cur.get("Sub-Function_EN") if cur.get("Sub-Function_EN") in subs else (subs[0] if subs else "Unknown")
    procs = process_choices(fcp, fn, sub)
    proc = cur.get("Business_Process_EN") if cur.get("Business_Process_EN") in procs else (procs[0] if procs else "Unknown")
    return (
        gr.update(choices=funcs, value=fn if fn in funcs else "Unknown"),
        gr.update(choices=subs, value=sub),
        gr.update(choices=procs, value=proc),
        f"{filename} | class {cur.get('Full_File_Class_No', '')}",
    )


def ui_hitl_function(function_en: str):
    fcp = load_fcp()
    subs = subfunction_choices(fcp, function_en)
    sub = subs[1] if len(subs) > 1 else subs[0]
    procs = process_choices(fcp, function_en, sub)
    proc = procs[1] if len(procs) > 1 else procs[0]
    return gr.update(choices=subs, value=sub), gr.update(choices=procs, value=proc)


def ui_hitl_subfunction(function_en: str, sub_en: str):
    fcp = load_fcp()
    procs = process_choices(fcp, function_en, sub_en)
    proc = procs[1] if len(procs) > 1 else procs[0]
    return gr.update(choices=procs, value=proc)


def ui_hitl_apply(embedder_choice, filename, function_en, sub_en, process_en):
    if not filename:
        return "❌ Load a report and pick a document first."
    try:
        return apply_override(_hitl_key(embedder_choice), filename, function_en, sub_en, process_en)
    except Exception as e:
        return f"❌ {type(e).__name__}: {e}"

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="FileShare CleanUp") as demo:
        gr.Markdown(
            """
            # FileShare CleanUp
            Document classification and metadata orchestrator.

            Paths come from `project_config.py`. **Restart** after path changes.
            """
        )

        with gr.Tab("Dashboard"):
            gr.Markdown("### Operational snapshot")
            dash_md = gr.Markdown(value=refresh_dashboard())
            btn_refresh = gr.Button("🔄 Refresh status", variant="secondary")
            btn_refresh.click(fn=refresh_dashboard, inputs=None, outputs=dash_md)

        with gr.Tab("Configuration"):
            gr.Markdown(
                """
                ### Path groups
                Edit `project_config.py`, then **restart** the app.
                Live path editing in the UI is not supported.
                """
            )
            gr.Markdown("#### Pipeline")
            gr.Textbox(label="SOURCE_DOCS_DIR", value=str(SOURCE_DOCS_DIR), interactive=False)
            gr.Textbox(label="EXTRACTED_TEXTS_DIR", value=str(EXTRACTED_TEXTS_DIR), interactive=False)
            gr.Textbox(label="CLASSIFICATION_RESULTS_DIR", value=str(CLASSIFICATION_RESULTS_DIR), interactive=False)
            gr.Textbox(label="DEDUPS_DIR", value=str(DEDUPS_DIR), interactive=False)
            gr.Textbox(label="INJECTED_METADATA_DIR (parent)", value=str(INJECTED_METADATA_DIR), interactive=False)

            gr.Markdown("#### Placeholders (per model)")
            with gr.Row():
                gr.Textbox(label="PLACEHOLDERS_MINILM_DIR", value=str(PLACEHOLDERS_MINILM_DIR), interactive=False)
                gr.Textbox(label="PLACEHOLDERS_QWEN_DIR", value=str(PLACEHOLDERS_QWEN_DIR), interactive=False)
                gr.Textbox(label="PLACEHOLDERS_QWEN3_4B_DIR", value=str(PLACEHOLDERS_QWEN3_4B_DIR), interactive=False)

            gr.Markdown("#### Injected clones (per model)")
            with gr.Row():
                gr.Textbox(label="INJECTED_MINILM_DIR", value=str(INJECTED_MINILM_DIR), interactive=False)
                gr.Textbox(label="INJECTED_QWEN_DIR", value=str(INJECTED_QWEN_DIR), interactive=False)

            gr.Markdown("#### Embedding models — one loaded at a time")
            with gr.Row():
                gr.Textbox(
                    label="EMBEDDING_MODEL_MINILM_PATH",
                    value=str(EMBEDDING_MODEL_MINILM_PATH),
                    interactive=False,
                )
                gr.Textbox(
                    label="EMBEDDING_MODEL_QWEN_PATH",
                    value=str(EMBEDDING_MODEL_QWEN_PATH),
                    interactive=False,
                )
                gr.Textbox(
                    label="EMBEDDING_MODEL_QWEN3_4B_PATH",
                    value=str(EMBEDDING_MODEL_QWEN3_4B_PATH),
                    interactive=False,
                )
            gr.Textbox(label="VISION_MODEL_PATH", value=str(VISION_MODEL_PATH), interactive=False)

        with gr.Tab("0 · Deduplication"):
            gr.Markdown(
                f"""
                ### Phase 0 – Deduplication
                **Prerequisite:** documents under `{SOURCE_DOCS_DIR}`

                **Step A** — Run analysis. Review Excel is written under `{DEDUPS_DIR}`.

                **Step B** — Set **User_Confirmed_Delete** to `Yes`, then save.

                **Step C** — Type the Excel filename.
                - Dry-run **CHECKED** = preview only.
                - **Uncheck** only when ready to delete.
                """
            )
            btn_dedup = gr.Button("▶ Run Deduplication Analysis", variant="primary")
            dedup_log = gr.Textbox(label="Analysis log", lines=14, max_lines=30, elem_classes=["log-box"])
            btn_dedup.click(fn=ui_run_dedup, outputs=dedup_log)

            gr.Markdown("---")
            gr.Markdown("### Delete confirmed duplicates")
            dedup_excel = gr.Textbox(
                label="Reviewed Excel filename (in DEDUPS_DIR)",
                value="deduplication_review_data.xlsx",
            )
            dedup_dry_run = gr.Checkbox(
                label="Dry-run — CHECKED = preview only (no delete). UNCHECK = really delete rows marked Yes.",
                value=True,
            )
            btn_dedup_del = gr.Button("▶ Run delete / dry-run", variant="secondary")
            dedup_del_log = gr.Textbox(label="Delete / dry-run log", lines=12, max_lines=25, elem_classes=["log-box"])
            btn_dedup_del.click(
                fn=ui_run_dedup_delete,
                inputs=[dedup_excel, dedup_dry_run],
                outputs=dedup_del_log,
            )

        with gr.Tab("1 · Ingestion"):
            gr.Markdown(
                f"""
                ### Phase 1 – Ingestion
                Writes `.txt` files to `{EXTRACTED_TEXTS_DIR}`
                """
            )
            btn_ingest = gr.Button("▶ Run Ingestion", variant="primary")
            ingest_log = gr.Textbox(label="Log output", lines=20, max_lines=40, elem_classes=["log-box"])
            btn_ingest.click(fn=ui_run_ingestion, outputs=ingest_log)

        with gr.Tab("2 · Classification"):
            gr.Markdown(
                f"""
                ### Phase 2 – Classification
                Choose **one** embedding model (only one is loaded).
                - MiniLM (fast baseline) → `classification_results_minilm.xlsx`
                - Qwen3-0.6B (stronger GPU) → `classification_results_qwen3.xlsx`
                - Qwen3-4B (strongest, heavy and slower) → `classification_results_qwen3_4b.xlsx`
                - Folder: `{CLASSIFICATION_RESULTS_DIR}`
                """
            )
            embedder_radio = gr.Radio(
                choices=RADIO_CHOICES,
                value="MiniLM (fast baseline)",
            )
            btn_class = gr.Button("▶ Run Classification", variant="primary")
            class_log = gr.Textbox(label="Log output", lines=20, max_lines=40, elem_classes=["log-box"])
            btn_class.click(fn=ui_run_classification, inputs=embedder_radio, outputs=class_log)

        with gr.Tab("2b · Review / override"):
            gr.Markdown(
                """
                ### Human review
                Load the MiniLM or Qwen3 report. Pick a document.
                Choose **Function (EN)** → **Sub-Function (EN)** → **Business Process (EN)**.
                Apply writes official FCP fields (including French) into that same workbook
                and clears the six excerpt columns.
                """
            )
            hitl_model = gr.Radio(
                choices=RADIO_CHOICES,
                value="MiniLM (fast baseline)",
            )
            btn_hitl_load = gr.Button("▶ Load report", variant="secondary")
            hitl_doc = gr.Dropdown(label="Document (filename)", choices=[], interactive=True)
            hitl_fn = gr.Dropdown(label="Function_EN", choices=["Unknown"], value="Unknown")
            hitl_sub = gr.Dropdown(label="Sub-Function_EN", choices=["Unknown"], value="Unknown")
            hitl_proc = gr.Dropdown(label="Business_Process_EN", choices=["Unknown"], value="Unknown")
            btn_hitl_apply = gr.Button("▶ Apply FCP values to this row", variant="primary")
            hitl_log = gr.Textbox(label="Review log", lines=8, elem_classes=["log-box"])

            btn_hitl_load.click(
                fn=ui_hitl_load,
                inputs=hitl_model,
                outputs=[hitl_doc, hitl_fn, hitl_sub, hitl_proc, hitl_log],
            )
            hitl_doc.change(
                fn=ui_hitl_pick_doc,
                inputs=[hitl_model, hitl_doc],
                outputs=[hitl_fn, hitl_sub, hitl_proc, hitl_log],
            )
            hitl_fn.change(
                fn=ui_hitl_function,
                inputs=hitl_fn,
                outputs=[hitl_sub, hitl_proc],
            )
            hitl_sub.change(
                fn=ui_hitl_subfunction,
                inputs=[hitl_fn, hitl_sub],
                outputs=hitl_proc,
            )
            btn_hitl_apply.click(
                fn=ui_hitl_apply,
                inputs=[hitl_model, hitl_doc, hitl_fn, hitl_sub, hitl_proc],
                outputs=hitl_log,
            )


        with gr.Tab("3–4 · Metadata"):
            gr.Markdown(
                f"""
                ### Phase 3 – Placeholders
                Same model as classification. Filename updates with the radio.

                MiniLM → `{PLACEHOLDERS_MINILM_DIR}`  
                Qwen3 → `{PLACEHOLDERS_QWEN_DIR}`
                """
            )
            ph_embedder = gr.Radio(
                choices=RADIO_CHOICES,
                value="MiniLM (fast baseline)",
            )
            excel_name = gr.Textbox(
                label="Classification Excel filename (updates with the radio)",
                value="classification_results_minilm.xlsx",
            )
            ph_embedder.change(fn=_excel_for_embedder, inputs=ph_embedder, outputs=excel_name)
            btn_ph = gr.Button("▶ Create Placeholders", variant="primary")
            ph_log = gr.Textbox(label="Log (Placeholders)", lines=12, max_lines=25, elem_classes=["log-box"])
            btn_ph.click(fn=ui_run_placeholders, inputs=[ph_embedder, excel_name], outputs=ph_log)

            gr.Markdown("---")
            gr.Markdown(
                f"""
                ### Phase 4 – Metadata Injector
                Uses the **same radio** as Phase 3.

                MiniLM clones → `{INJECTED_MINILM_DIR}`  
                Qwen3 clones → `{INJECTED_QWEN_DIR}`
                """
            )
            btn_inj = gr.Button("▶ Run Metadata Injector", variant="primary")
            inj_log = gr.Textbox(label="Log (Injector)", lines=12, max_lines=25, elem_classes=["log-box"])
            btn_inj.click(fn=ui_run_injector, inputs=ph_embedder, outputs=inj_log)

        gr.Markdown("**Stop:** ends the current phase only. Files already written are kept.")
        with gr.Row():
            btn_stop = gr.Button("⏹ Stop current job", variant="stop")
            stop_log = gr.Textbox(label="Stop status", lines=2, max_lines=4, elem_classes=["log-box"])
        btn_stop.click(fn=ui_stop, inputs=None, outputs=stop_log)

        with gr.Tab("Help"):
            gr.Markdown(
                """
                ## Runbook
                1. Dedup → review Excel → dry-run → delete
                2. Ingestion
                3. Classification (MiniLM or Qwen3)
                4. Placeholders (same model)
                5. Injector (same model)

                Paths only change in `project_config.py`, then restart.
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
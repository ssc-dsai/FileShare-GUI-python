# backend/runners.py
"""
Thin runners that execute pipeline phases as subprocesses.
Designed for Gradio handlers and cooperative Stop via job_control.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.job_control import is_running, set_current, stop as job_stop

PROJECT_ROOT = Path(__file__).resolve().parent.parent

Result = Tuple[bool, str, Dict]


def _run_script_subprocess(
    script_relative: str,
    extra_args: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """
    Run a phase script as a child process so Stop can kill it.
    Returns (ok, combined_stdout_log).
    """
    if is_running():
        return (
            False,
            "Another job is still running. Press « Stop current job » first "
            "(or wait for it to finish).",
        )

    script = PROJECT_ROOT / script_relative
    if not script.is_file():
        return False, f"Script not found: {script}"

    cmd = [sys.executable, str(script)]
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TRANSFORMERS_OFFLINE", "1")

    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    set_current(proc, label=script_relative)

    chunks: List[str] = []
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            chunks.append(line)
        proc.wait()
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        set_current(None, "")
        log = "".join(chunks) + f"\n===== EXCEPTION =====\n{type(e).__name__}: {e}\n"
        return False, log

    set_current(None, "")
    log = "".join(chunks)
    code = proc.returncode if proc.returncode is not None else -1

    # Negative return codes often mean killed by signal (Stop on Unix);
    # on Windows, terminate typically yields a non-zero code.
    if code != 0:
        if "STOPPED" not in log.upper():
            # Heuristic: user stop mid-run
            if code in (-15, -9, 1, 15, 9) or code < 0:
                log += "\n===== STOPPED OR NON-ZERO EXIT =====\n"
            else:
                log += f"\n===== EXIT CODE {code} =====\n"
        return False, log

    return True, log


def _capture_sub(
    script_relative: str,
    extra_args: Optional[List[str]] = None,
) -> Result:
    ok, log = _run_script_subprocess(script_relative, extra_args)
    return ok, log, {}


# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------
def run_stop() -> Result:
    msg = job_stop()
    return True, msg, {}


# ---------------------------------------------------------------------------
# Pipeline phases
# ---------------------------------------------------------------------------
def run_dedup_analysis() -> Result:
    return _capture_sub("DeDuplication/0_dedup_analysis.py")


def run_dedup_delete(
    excel_name: str,
    dry_run: bool = True,
) -> Result:
    args: List[str] = ["--excel", excel_name]
    if dry_run:
        args.append("--dry-run")
    return _capture_sub("DeDuplication/dedup_delete.py", args)


def run_ingestion() -> Result:
    return _capture_sub("Ingestion/1_Ingestion.py")


def run_classification() -> Result:
    return _capture_sub("Classification/2_Classification.py")


def run_placeholder_creator(excel_name: str = "classification_results.xlsx") -> Result:
    return _capture_sub(
        "Metadata_Placeholder/4_placeholder_creator.py",
        ["--excel", excel_name],
    )


def run_metadata_injector() -> Result:
    return _capture_sub("Metadata_Injector/5_metadata_injector.py")


# ---------------------------------------------------------------------------
# Litigation
# ---------------------------------------------------------------------------
def run_litigation_package(
    input_folder: str,
    output_name: Optional[str] = None,
) -> Result:
    args: List[str] = ["--input", input_folder]
    if output_name:
        args.extend(["--name", output_name])
    return _capture_sub("Litigation/6_litigation_package.py", args)


def run_litigation_index(rebuild: bool = True) -> Result:
    args = ["--rebuild"] if rebuild else []
    return _capture_sub("Litigation/7_litigation_index.py", args)


def run_litigation_search(
    package_path: str,
    top_k: int = 50,
    min_score: float = 0.22,
) -> Result:
    return _capture_sub(
        "Litigation/8_litigation_search.py",
        [
            "--package",
            package_path,
            "--top_k",
            str(int(top_k)),
            "--min_score",
            str(float(min_score)),
        ],
    )


# Optional: ensure dirs if you still call it from Dashboard
def run_ensure_directories() -> Result:
    try:
        from project_config import ensure_directories

        ensure_directories()
        return True, "Directories ensured via project_config.ensure_directories()", {}
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", {}
#!/usr/bin/env python3
"""
coordination_watcher.py — Autonomous task dispatcher for Claude Code

Monitors task_box/ for new pending tasks and auto-launches:
    claude --dangerously-skip-permissions -p "..."

Sends Windows toast notification when a task completes.
On completion, renders result as HTML and opens it in the browser.

Usage:
    python coordination_watcher.py

Dependencies:
    pip install watchdog win11toast
"""

import glob
import json
import logging
import os
import subprocess
import sys
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from render_html import save_and_open, HTML_MIN_LENGTH

# ── Configuration ──────────────────────────────────────────────────────────────

TASK_BOX       = r"C:\Users\kazin\Desktop\_AI_Coordination\ai_coordination\task_box"
LOG_DIR        = r"C:\Users\kazin\Desktop\_AI_Coordination\ai_coordination\logs"
OUTPUT_REPORTS = r"C:\Users\kazin\Desktop\_AI_Coordination\ai_coordination\output_box\reports"

# Default working directory when task JSON has no 'workdir' field
DEFAULT_WORKDIR = r"C:\Users\kazin\Desktop\mobile_workspace\argus-1.0"

# Claude Code executable path (use full path to avoid PATH dependency)
CLAUDE_EXE = r"C:\Users\kazin\.local\bin\claude.exe"

# keyword (in description, lowercase) → working directory
WORKDIR_MAP = {
    "argus":               r"C:\Users\kazin\Desktop\mobile_workspace\argus-1.0",
    "ai-task-coordinator": r"C:\Users\kazin\Desktop\mobile_workspace\ai-task-coordinator",
}

# ── Logging ────────────────────────────────────────────────────────────────────

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "watcher.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ── HTML rendering (delegated to render_html.py) ───────────────────────────────

def save_and_open_result(task_id: str, result: str, task: dict) -> str | None:
    """Render result as HTML, save to output_box/reports/, open in browser."""
    os.makedirs(OUTPUT_REPORTS, exist_ok=True)
    html_path = os.path.join(OUTPUT_REPORTS, f"{task_id}.html")
    title = f"Task Result: {task_id}"
    return save_and_open(result, title=title, out_path=html_path)


# ── Toast notification ─────────────────────────────────────────────────────────

def toast(title: str, body: str) -> None:
    """Send Windows toast notification. Falls back to PowerShell balloon tip."""
    try:
        from win11toast import toast as _toast
        _toast(title, body, on_dismissed=lambda _: None)
        return
    except Exception:
        pass
    # PowerShell fallback (no extra package required)
    # Escape single quotes in title/body to prevent injection
    t = title.replace("'", "''")
    b = body.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = [System.Windows.Forms.NotifyIcon]::new(); "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(8000, '{t}', '{b}', "
        "[System.Windows.Forms.ToolTipIcon]::Info); "
        "Start-Sleep -Seconds 9; $n.Dispose()"
    )
    subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-Command", script],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

# ── Helpers ────────────────────────────────────────────────────────────────────

def resolve_workdir(task: dict) -> str:
    """Resolve working directory: task['workdir'] > keyword match > default."""
    if wd := task.get("workdir"):
        return wd
    desc = task.get("description", "").lower()
    for keyword, path in WORKDIR_MAP.items():
        if keyword in desc:
            return path
    return DEFAULT_WORKDIR


def dispatch_task(fpath: str, task: dict) -> None:
    """Launch claude -p for the given task file."""
    task_id  = task.get("id", os.path.basename(fpath))
    workdir  = resolve_workdir(task)
    log_path = os.path.join(LOG_DIR, f"{task_id}.log")

    prompt = (
        f"タスクファイル {fpath} を読んで、記述されたタスクを実行してください。"
        "完了後、そのJSONファイルの status を \"completed\"、"
        "completed_at に現在のISO timestamp、result に完了要約を記載して保存してください。"
    )

    log.info(f"DISPATCH  {task_id}  workdir={workdir}")

    # Remove CLAUDECODE to allow launching from inside an active Claude Code session
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    with open(log_path, "w", encoding="utf-8") as lf:
        subprocess.Popen(
            [CLAUDE_EXE, "--dangerously-skip-permissions", "-p", prompt],
            cwd=workdir,
            stdout=lf,
            stderr=lf,
            env=env,
            # New visible console so you can watch Claude work (remove flag to go silent)
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

# ── File system event handler ──────────────────────────────────────────────────

class TaskBoxHandler(FileSystemEventHandler):
    def __init__(self) -> None:
        self._dispatched: set[str] = set()   # tasks already handed to claude
        self._notified:   set[str] = set()   # completions already toasted

    def _process(self, fpath: str) -> None:
        if not fpath.endswith(".json"):
            return
        try:
            with open(fpath, encoding="utf-8") as f:
                task = json.load(f)
        except Exception:
            return

        task_id = task.get("id", os.path.basename(fpath))
        status  = str(task.get("status", "")).lower()

        if status == "pending" and task_id not in self._dispatched:
            self._dispatched.add(task_id)
            dispatch_task(fpath, task)

        elif status == "completed" and task_id not in self._notified:
            self._notified.add(task_id)
            result  = str(task.get("result", "(no result)"))
            summary = result[:120]
            log.info(f"COMPLETE  {task_id}")

            html_path = save_and_open_result(task_id, result, task)
            if html_path:
                log.info(f"HTML REPORT  {html_path}")
                toast(f"タスク完了 — ブラウザで結果表示済み", f"{task_id}\n{summary}")
            else:
                toast(f"タスク完了", f"{task_id}\n{summary}")

    def on_created(self, event):
        if not event.is_directory:
            self._process(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._process(event.src_path)

# ── Startup scan ───────────────────────────────────────────────────────────────

def startup_scan(handler: TaskBoxHandler) -> None:
    """
    On watcher start:
    - Mark all existing completed tasks as already-notified (no spam).
    - Dispatch any tasks that are already pending (resume after restart).
    """
    for fpath in sorted(glob.glob(os.path.join(TASK_BOX, "*.json"))):
        try:
            with open(fpath, encoding="utf-8") as f:
                task = json.load(f)
            task_id = task.get("id", os.path.basename(fpath))
            status  = str(task.get("status", "")).lower()

            if status == "completed":
                handler._notified.add(task_id)
            elif status == "pending":
                handler._dispatched.add(task_id)
                dispatch_task(fpath, task)
        except Exception:
            continue

# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info(f"Coordination Watcher started.")
    log.info(f"Monitoring: {TASK_BOX}")

    handler = TaskBoxHandler()
    startup_scan(handler)

    observer = PollingObserver(timeout=2)
    observer.schedule(handler, TASK_BOX, recursive=False)
    observer.start()
    log.info("Watching for new tasks... (Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Watcher stopped.")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()

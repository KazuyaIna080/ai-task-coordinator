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
import re
import subprocess
import sys
import time
import webbrowser

from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

# ── Configuration ──────────────────────────────────────────────────────────────

TASK_BOX       = r"C:\Users\kazin\Desktop\_AI_Coordination\ai_coordination\task_box"
LOG_DIR        = r"C:\Users\kazin\Desktop\_AI_Coordination\ai_coordination\logs"
OUTPUT_REPORTS = r"C:\Users\kazin\Desktop\_AI_Coordination\ai_coordination\output_box\reports"

# Minimum result length to trigger HTML rendering (shorter → toast only)
HTML_MIN_LENGTH = 100

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

# ── Markdown → HTML conversion (stdlib only) ───────────────────────────────────

def _md_to_html_body(md: str) -> str:
    """Convert a Markdown string to an HTML body fragment (no <html> wrapper)."""

    def escape(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    lines = md.split("\n")
    html_parts: list[str] = []
    i = 0

    def apply_inline(text: str) -> str:
        """Apply inline Markdown within a line (already HTML-escaped)."""
        # Inline code  `code`
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        # Bold **text** or __text__
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
        # Italic *text* or _text_
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"_([^_]+)_", r"<em>\1</em>", text)
        # Links [text](url)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        return text

    in_code_block = False
    code_lang = ""
    code_lines: list[str] = []
    in_list: list[str] = []   # stack of "ul" or "ol"
    in_table = False
    table_lines: list[str] = []

    def flush_list() -> None:
        while in_list:
            html_parts.append(f"</{in_list.pop()}>")

    def flush_table() -> None:
        nonlocal in_table, table_lines
        if not table_lines:
            return
        html_parts.append('<div class="table-wrap"><table>')
        header_done = False
        for tl in table_lines:
            cols = [c.strip() for c in tl.strip().strip("|").split("|")]
            if not header_done:
                html_parts.append("<thead><tr>" +
                    "".join(f"<th>{apply_inline(escape(c))}</th>" for c in cols) +
                    "</tr></thead><tbody>")
                header_done = True
            else:
                # skip separator rows (--- lines)
                if all(re.match(r"^[-: ]+$", c) for c in cols):
                    continue
                html_parts.append("<tr>" +
                    "".join(f"<td>{apply_inline(escape(c))}</td>" for c in cols) +
                    "</tr>")
        html_parts.append("</tbody></table></div>")
        table_lines = []
        in_table = False
        table_header_done = False

    while i < len(lines):
        line = lines[i]

        # ── Fenced code block ──
        if line.strip().startswith("```"):
            if in_code_block:
                html_parts.append(f'<pre><code class="language-{escape(code_lang)}">' +
                                   "\n".join(escape(cl) for cl in code_lines) +
                                   "</code></pre>")
                code_lines = []
                code_lang = ""
                in_code_block = False
            else:
                flush_list()
                flush_table()
                code_lang = line.strip()[3:].strip()
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # ── Table row ──
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            flush_list()
            if not in_table:
                in_table = True
            table_lines.append(line)
            i += 1
            continue
        elif in_table:
            flush_table()

        # ── Headings ──
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            flush_list()
            level = len(m.group(1))
            content = apply_inline(escape(m.group(2)))
            html_parts.append(f"<h{level}>{content}</h{level}>")
            i += 1
            continue

        # ── Horizontal rule ──
        if re.match(r"^[-*_]{3,}\s*$", line):
            flush_list()
            html_parts.append("<hr>")
            i += 1
            continue

        # ── Unordered list ──
        m = re.match(r"^(\s*)[*\-+]\s+(.*)", line)
        if m:
            if not in_list or in_list[-1] != "ul":
                in_list.append("ul")
                html_parts.append("<ul>")
            html_parts.append(f"<li>{apply_inline(escape(m.group(2)))}</li>")
            i += 1
            continue

        # ── Ordered list ──
        m = re.match(r"^(\s*)\d+\.\s+(.*)", line)
        if m:
            if not in_list or in_list[-1] != "ol":
                in_list.append("ol")
                html_parts.append("<ol>")
            html_parts.append(f"<li>{apply_inline(escape(m.group(2)))}</li>")
            i += 1
            continue

        # Non-list line: flush list
        if in_list and line.strip() == "":
            flush_list()

        # ── Blank line ──
        if line.strip() == "":
            if in_list:
                flush_list()
            html_parts.append("")
            i += 1
            continue

        # ── Plain paragraph ──
        flush_list()
        html_parts.append(f"<p>{apply_inline(escape(line))}</p>")
        i += 1

    flush_list()
    flush_table()
    if in_code_block and code_lines:
        html_parts.append(f'<pre><code class="language-{escape(code_lang)}">' +
                           "\n".join(escape(cl) for cl in code_lines) +
                           "</code></pre>")

    return "\n".join(html_parts)


def render_result_html(task_id: str, result: str, task: dict) -> str:
    """Build a full HTML page from a task result (Markdown or plain text)."""
    completed_at = task.get("completed_at", "")
    description  = task.get("description", "")[:200]

    body_html = _md_to_html_body(result)

    css = """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.7;
            color: #1a1a2e;
            background: #f0f4f8;
            padding: 2rem 1rem;
        }
        .container {
            max-width: 860px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0,0,0,.10);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 1.6rem 2rem;
        }
        header h1 { font-size: 1.25rem; font-weight: 700; }
        header .meta { font-size: .8rem; opacity: .8; margin-top: .3rem; }
        .content { padding: 2rem; }
        h1,h2,h3,h4,h5,h6 {
            margin: 1.4em 0 .5em;
            font-weight: 600;
            line-height: 1.3;
        }
        h1 { font-size: 1.6rem; border-bottom: 2px solid #e2e8f0; padding-bottom: .4rem; }
        h2 { font-size: 1.3rem; border-bottom: 1px solid #e2e8f0; padding-bottom: .3rem; }
        h3 { font-size: 1.1rem; }
        p  { margin: .8em 0; }
        a  { color: #667eea; text-decoration: none; }
        a:hover { text-decoration: underline; }
        ul, ol { margin: .6em 0 .6em 1.6em; }
        li { margin: .2em 0; }
        pre {
            background: #1e1e2e;
            color: #cdd6f4;
            border-radius: 8px;
            padding: 1rem 1.2rem;
            overflow-x: auto;
            font-size: .85rem;
            margin: 1em 0;
        }
        code {
            font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace;
        }
        p code {
            background: #eef2ff;
            color: #4c1d95;
            padding: .1em .4em;
            border-radius: 4px;
            font-size: .88em;
        }
        .table-wrap { overflow-x: auto; margin: 1em 0; }
        table {
            border-collapse: collapse;
            width: 100%;
            font-size: .9rem;
        }
        th, td {
            border: 1px solid #e2e8f0;
            padding: .5rem .8rem;
            text-align: left;
        }
        th { background: #f7fafc; font-weight: 600; }
        tr:nth-child(even) { background: #f9fafb; }
        hr { border: none; border-top: 1px solid #e2e8f0; margin: 1.5em 0; }
        strong { font-weight: 600; }
        footer {
            text-align: center;
            font-size: .75rem;
            color: #a0aec0;
            padding: 1rem 2rem;
            border-top: 1px solid #e2e8f0;
        }
    """

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{task_id} — Task Result</title>
  <style>{css}</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Task Result: {task_id}</h1>
      <div class="meta">Completed: {completed_at}</div>
    </header>
    <div class="content">
{body_html}
    </div>
    <footer>Generated by coordination_watcher &nbsp;|&nbsp; {task_id}</footer>
  </div>
</body>
</html>"""
    return html


def save_and_open_result(task_id: str, result: str, task: dict) -> str | None:
    """Render result as HTML, save to output_box/reports/, open in browser.

    Returns the HTML file path, or None if skipped (result too short).
    """
    if len(result) < HTML_MIN_LENGTH:
        return None

    os.makedirs(OUTPUT_REPORTS, exist_ok=True)
    html_path = os.path.join(OUTPUT_REPORTS, f"{task_id}.html")

    # If the result already looks like HTML, save it as-is
    is_html = result.lstrip().startswith("<!DOCTYPE") or result.lstrip().startswith("<html")
    content = result if is_html else render_result_html(task_id, result, task)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

    webbrowser.open(f"file:///{html_path.replace(chr(92), '/')}")
    return html_path


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

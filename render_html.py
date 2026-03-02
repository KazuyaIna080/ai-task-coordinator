#!/usr/bin/env python3
"""
render_html.py — Markdown / plain-text → styled HTML converter

Standalone usage (pipe from claude -p):
    claude --dangerously-skip-permissions -p "..." | python render_html.py
    claude --dangerously-skip-permissions -p "..." | python render_html.py --title "My Report"
    claude --dangerously-skip-permissions -p "..." | python render_html.py --out result.html --no-open

Library usage (imported by coordination_watcher.py):
    from render_html import save_and_open, render_page
"""

import argparse
import datetime
import os
import re
import sys
import webbrowser


# ── Markdown → HTML body ────────────────────────────────────────────────────────

def md_to_html_body(md: str) -> str:
    """Convert a Markdown string to an HTML body fragment (no <html> wrapper)."""

    def escape(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def apply_inline(text: str) -> str:
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"_([^_]+)_", r"<em>\1</em>", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        return text

    lines = md.split("\n")
    parts: list[str] = []
    i = 0
    in_code = False
    code_lang = ""
    code_lines: list[str] = []
    in_list: list[str] = []
    in_table = False
    table_lines: list[str] = []

    def flush_list() -> None:
        while in_list:
            parts.append(f"</{in_list.pop()}>")

    def flush_table() -> None:
        nonlocal in_table, table_lines
        if not table_lines:
            return
        parts.append('<div class="table-wrap"><table>')
        header_done = False
        for tl in table_lines:
            cols = [c.strip() for c in tl.strip().strip("|").split("|")]
            if not header_done:
                parts.append(
                    "<thead><tr>"
                    + "".join(f"<th>{apply_inline(escape(c))}</th>" for c in cols)
                    + "</tr></thead><tbody>"
                )
                header_done = True
            else:
                if all(re.match(r"^[-: ]+$", c) for c in cols):
                    continue
                parts.append(
                    "<tr>"
                    + "".join(f"<td>{apply_inline(escape(c))}</td>" for c in cols)
                    + "</tr>"
                )
        parts.append("</tbody></table></div>")
        table_lines = []
        in_table = False

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.strip().startswith("```"):
            if in_code:
                parts.append(
                    f'<pre><code class="language-{escape(code_lang)}">'
                    + "\n".join(escape(cl) for cl in code_lines)
                    + "</code></pre>"
                )
                code_lines, code_lang, in_code = [], "", False
            else:
                flush_list(); flush_table()
                code_lang = line.strip()[3:].strip()
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Table
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            flush_list()
            in_table = True
            table_lines.append(line)
            i += 1
            continue
        elif in_table:
            flush_table()

        # Heading
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            flush_list()
            lvl = len(m.group(1))
            parts.append(f"<h{lvl}>{apply_inline(escape(m.group(2)))}</h{lvl}>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            flush_list()
            parts.append("<hr>")
            i += 1
            continue

        # Unordered list
        m = re.match(r"^\s*[*\-+]\s+(.*)", line)
        if m:
            if not in_list or in_list[-1] != "ul":
                in_list.append("ul"); parts.append("<ul>")
            parts.append(f"<li>{apply_inline(escape(m.group(1)))}</li>")
            i += 1
            continue

        # Ordered list
        m = re.match(r"^\s*\d+\.\s+(.*)", line)
        if m:
            if not in_list or in_list[-1] != "ol":
                in_list.append("ol"); parts.append("<ol>")
            parts.append(f"<li>{apply_inline(escape(m.group(1)))}</li>")
            i += 1
            continue

        # Blank line
        if line.strip() == "":
            flush_list()
            parts.append("")
            i += 1
            continue

        # Paragraph
        flush_list()
        parts.append(f"<p>{apply_inline(escape(line))}</p>")
        i += 1

    flush_list(); flush_table()
    if in_code and code_lines:
        parts.append(
            f'<pre><code class="language-{escape(code_lang)}">'
            + "\n".join(escape(cl) for cl in code_lines)
            + "</code></pre>"
        )

    return "\n".join(parts)


# ── Full HTML page ──────────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    line-height: 1.7; color: #1a1a2e; background: #f0f4f8; padding: 2rem 1rem;
}
.container {
    max-width: 860px; margin: 0 auto; background: #fff;
    border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,.10); overflow: hidden;
}
header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #fff; padding: 1.6rem 2rem;
}
header h1 { font-size: 1.25rem; font-weight: 700; }
header .meta { font-size: .8rem; opacity: .8; margin-top: .3rem; }
.content { padding: 2rem; }
h1,h2,h3,h4,h5,h6 { margin: 1.4em 0 .5em; font-weight: 600; line-height: 1.3; }
h1 { font-size: 1.6rem; border-bottom: 2px solid #e2e8f0; padding-bottom: .4rem; }
h2 { font-size: 1.3rem; border-bottom: 1px solid #e2e8f0; padding-bottom: .3rem; }
h3 { font-size: 1.1rem; }
p  { margin: .8em 0; }
a  { color: #667eea; text-decoration: none; }
a:hover { text-decoration: underline; }
ul, ol { margin: .6em 0 .6em 1.6em; }
li { margin: .2em 0; }
pre {
    background: #1e1e2e; color: #cdd6f4; border-radius: 8px;
    padding: 1rem 1.2rem; overflow-x: auto; font-size: .85rem; margin: 1em 0;
}
code { font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace; }
p code {
    background: #eef2ff; color: #4c1d95;
    padding: .1em .4em; border-radius: 4px; font-size: .88em;
}
.table-wrap { overflow-x: auto; margin: 1em 0; }
table { border-collapse: collapse; width: 100%; font-size: .9rem; }
th, td { border: 1px solid #e2e8f0; padding: .5rem .8rem; text-align: left; }
th { background: #f7fafc; font-weight: 600; }
tr:nth-child(even) { background: #f9fafb; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 1.5em 0; }
strong { font-weight: 600; }
footer {
    text-align: center; font-size: .75rem; color: #a0aec0;
    padding: 1rem 2rem; border-top: 1px solid #e2e8f0;
}
"""


def render_page(content: str, title: str = "Result", meta: str = "") -> str:
    """Build a complete HTML page from Markdown or plain text."""
    is_html = content.lstrip().startswith(("<!DOCTYPE", "<html"))
    body = content if is_html else md_to_html_body(content)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{title}</h1>
      <div class="meta">{meta}</div>
    </header>
    <div class="content">
{body}
    </div>
    <footer>render_html.py &nbsp;|&nbsp; {meta}</footer>
  </div>
</body>
</html>"""


# ── Public API (used by coordination_watcher.py) ────────────────────────────────

HTML_MIN_LENGTH = 100


def save_and_open(
    content: str,
    title: str = "Result",
    out_path: str | None = None,
    open_browser: bool = True,
) -> str | None:
    """Render content as HTML, save to out_path, optionally open in browser.

    Returns the saved file path, or None when content is too short.
    """
    if len(content) < HTML_MIN_LENGTH:
        return None

    if out_path is None:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(os.path.expanduser("~"), "Desktop", f"result_{ts}.html")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    meta = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = render_page(content, title=title, meta=meta)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    if open_browser:
        webbrowser.open(f"file:///{out_path.replace(os.sep, '/')}")

    return out_path


# ── CLI entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert stdin (Markdown/text) to a styled HTML file and open it."
    )
    parser.add_argument("--title", default="Claude Output", help="Page title")
    parser.add_argument("--out",   default=None, help="Output file path")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    content = sys.stdin.read()
    if not content.strip():
        print("[render_html] No input received.", file=sys.stderr)
        sys.exit(1)

    path = save_and_open(
        content,
        title=args.title,
        out_path=args.out,
        open_browser=not args.no_open,
    )

    if path:
        print(f"[render_html] Saved → {path}", file=sys.stderr)
    else:
        # Content too short — just print to stdout as-is
        print(content)


if __name__ == "__main__":
    main()

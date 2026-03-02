# awesome-claude-code 申請用 Issue テキスト

申請先: https://github.com/hesreallyhim/awesome-claude-code/issues/new/choose

**申請タイミング:** 初回コミット（2026-03-02）から1週間後 = **2026-03-09 以降**

---

## 入力フォーム

### Display Name
```
ai-task-coordinator
```

### Category
```
Tooling
```

### Sub-Category
```
Tooling: Automation
```

### Primary Link
```
https://github.com/KazuyaIna080/ai-task-coordinator
```

### Author Name
```
KazuyaIna080
```

### Author Link
```
https://github.com/KazuyaIna080
```

### License
```
MIT
```

### Description
```
Claude Desktop ↔ Claude Code coordination system with three key features:

1. **`render_html.py` — Standalone Markdown→HTML CLI**: Pipe any `claude -p` output to a styled HTML page that auto-opens in the browser. Zero extra dependencies (Python stdlib only). Supports headings, tables, fenced code blocks, inline formatting, and links.

```bash
claude --dangerously-skip-permissions -p "Analyze this" | python render_html.py --title "Report"
```

2. **`coordination_watcher.py` — Autonomous task dispatcher**: Monitors a `task_box/` directory via watchdog. Detects `status: pending` JSON files, auto-launches `claude -p`, detects completion, renders results as HTML, and sends Windows toast notifications. Strips the `CLAUDECODE` env var from child processes to resolve the nested session issue #573.

3. **`index.js` — MCP Server**: Provides Claude Desktop with `submit_task`, `send_message`, `check_messages`, `check_task_result`, LM Studio second-opinion tools, and Obsidian (PKA) integration.

The two HTML output paths (standalone pipe vs. watcher) are fully independent — no duplicate output.
```

### Validate Claims
```
git clone https://github.com/KazuyaIna080/ai-task-coordinator
cd ai-task-coordinator
echo "## Hello\n\nThis is a **test**." | python render_html.py --title "Test" --no-open
# → Saves result_*.html to ~/Desktop
```

### Specific Task(s)
```
Render Claude CLI output as a styled HTML report and open it in the browser automatically.
```

### Specific Prompt(s)
```
claude --dangerously-skip-permissions -p "Summarize the files in this directory" | python render_html.py
```

### Additional Comments
```
Also addresses the common CLAUDECODE nested session error when spawning claude -p from inside
an active Claude Code session — the fix (strip env var) is documented inline and resolves
https://github.com/anthropics/claude-agent-sdk-python/issues/573
```

### Checklist
- [x] I have checked that this resource hasn't already been submitted
- [x] It has been over one week since the first public commit ← **2026-03-09 以降にチェック**
- [x] All provided links are working and publicly accessible
- [x] I do NOT have any other open issues in this repository
- [x] I am primarily composed of human-y stuff and not electrical circuits

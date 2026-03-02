# AI Task Coordinator

**Claude Desktop ↔ Claude Code coordination system** with autonomous task dispatch, file-system watcher, and Markdown→HTML report rendering.

## Quick Start — Standalone HTML output for `claude -p`

Pipe any `claude -p` output directly to a styled HTML page:

```bash
claude --dangerously-skip-permissions -p "Analyze this codebase" | python render_html.py

# Custom title
claude --dangerously-skip-permissions -p "..." | python render_html.py --title "My Report"

# Save to specific file, don't open browser
claude --dangerously-skip-permissions -p "..." | python render_html.py --out report.html --no-open
```

Output: `~/Desktop/result_YYYYMMDD_HHMMSS.html` (auto-opens in browser)

No extra dependencies — `render_html.py` uses Python stdlib only.

---

## Architecture

```
Claude Desktop
    │ MCP (submit_task / send_message)
    ▼
AI Task Coordinator (index.js)        task_box/*.json
    │                                      │
    │                               coordination_watcher.py
    │                                      │ DISPATCH (watchdog)
    │                                      ▼
    │                               Claude Code (claude -p)
    │                                      │ COMPLETE
    │                                      ▼
    │                        render_html.py → output_box/reports/{id}.html
    │                                      │ webbrowser.open
    │                                      ▼
    └── check_task_result ────── Browser report + Windows Toast
```

Two independent HTML output paths — no duplicate output:

| Path | Trigger | Output |
|------|---------|--------|
| Standalone | `claude -p ... \| python render_html.py` | `~/Desktop/result_*.html` |
| Via watcher | `task_box` JSON `status: completed` | `output_box/reports/{id}.html` |

---

## Components

### `render_html.py` — Markdown → HTML converter

Stdlib-only Markdown→HTML engine. Works as a **standalone CLI** or **imported library**.

Supported elements: headings, lists, tables, fenced code blocks, inline formatting, links, horizontal rules.

**Library API:**
```python
from render_html import save_and_open, render_page, md_to_html_body

path = save_and_open(markdown_text, title="My Report")
html = render_page(markdown_text, title="Page Title", meta="2026-03-02")
body = md_to_html_body(markdown_text)  # fragment only
```

**CSS features:** responsive layout, gradient header, dark-theme code blocks, striped tables.

---

### `coordination_watcher.py` — Autonomous task dispatcher

Monitors `task_box/` for pending tasks and auto-launches Claude Code. Delegates HTML rendering to `render_html.py`.

**Flow:**
1. Detects `status: "pending"` → launches `claude --dangerously-skip-permissions -p`
2. Detects `status: "completed"` → calls `render_html.save_and_open()` → opens browser
3. Sends Windows toast notification (`win11toast` / PowerShell fallback)

> **Note:** Strips the `CLAUDECODE` environment variable from child processes to allow launching Claude Code from inside an active Claude Code session ([known issue #573](https://github.com/anthropics/claude-agent-sdk-python/issues/573)).

**Start:**
```bash
python coordination_watcher.py
# or on Windows:
start_watcher.bat
```

**Dependencies:**
```bash
pip install watchdog win11toast
```

---

### `index.js` — MCP Server

Provides the following tools to Claude Desktop:

#### Messaging
| Tool | Description |
|------|-------------|
| `send_message` | Send message to Claude Code |
| `check_messages` | Check new messages (marks as read) |
| `get_thread` | Get full thread history |

#### Task Management
| Tool | Description |
|------|-------------|
| `submit_task` | Create task JSON in task_box (status: pending) |
| `check_task_result` | Fetch result from output_box → task_box fallback |
| `list_tasks` | List tasks with status breakdown |

#### LM Studio
| Tool | Description |
|------|-------------|
| `get_second_opinion` | Ask local LLM for a second opinion |
| `get_code_review` | Request code review from local LLM |
| `list_local_models` | List available local models |

#### PKA (Obsidian)
| Tool | Description |
|------|-------------|
| `save_insight` | Save insight to Obsidian vault |
| `save_learning` | Save structured learning note |
| `save_conversation_summary` | Save conversation summary |

#### System
| Tool | Description |
|------|-------------|
| `check_services` | Check LM Studio / PKA / path availability |

---

## Setup

### 1. MCP Server (Node.js)

```bash
cd ai-task-coordinator
npm install
cp .env.example .env
# Edit .env for your environment
```

**.env settings:**

| Variable | Description | Example |
|----------|-------------|---------|
| `AI_COORDINATION_BASE` | Base path for AI coordination system | `C:/Users/.../ai_coordination` |
| `LM_STUDIO_URL` | LM Studio API endpoint | `http://localhost:1234/v1` |
| `PKA_API_URL` | Obsidian REST API URL | `https://127.0.0.1:27124` |
| `PKA_API_KEY` | Obsidian REST API key | (generated in Obsidian) |
| `PKA_VAULT_FOLDER` | Target folder name | `Claude-Desktop` |

### 2. Register MCP in Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai-task-coordinator": {
      "command": "node",
      "args": ["/path/to/ai-task-coordinator/index.js"]
    }
  }
}
```

### 3. Start Watcher

```bash
python coordination_watcher.py
```

To auto-start on Windows boot, register `start_watcher.bat` with Task Scheduler.

---

## Task JSON Spec

```json
{
  "id": "task_20260302XXXXXX",
  "type": "development | analysis | review | other",
  "description": "Task description",
  "priority": "high | medium | low",
  "submitted_at": "ISO timestamp",
  "started_at":   "ISO timestamp (written by Claude Code on start)",
  "completed_at": "ISO timestamp (written by Claude Code on finish)",
  "status": "pending | in_progress | completed | failed",
  "result": "Completion summary (written by Claude Code)"
}
```

---

## Directory Structure

```
ai-task-coordinator/
├── render_html.py            # Markdown→HTML converter (CLI + library)
├── coordination_watcher.py   # Autonomous task dispatcher
├── index.js                  # MCP server
├── config.js                 # Path configuration
├── lm-studio-client.js       # LM Studio integration
├── pka-writer.js             # Obsidian REST API integration
├── start_watcher.bat         # Watcher launcher (Windows)
├── .env.example              # Environment template
└── docs/
    ├── ARCHITECTURE.md
    ├── DESKTOP_PROTOCOL_REFERENCE.md
    ├── PKA_INTEGRATION.md
    └── PKA_PROJECT_PROPOSAL.md

# Shared directory (_AI_Coordination)
ai_coordination/
├── task_box/                 # Task JSON input
├── output_box/reports/       # HTML report output
└── messages/
    ├── desktop_to_code/
    ├── code_to_desktop/
    └── threads/
```

---

## Dependencies

**Python (watcher + renderer):**
- Python 3.11+
- `watchdog` — filesystem monitoring
- `win11toast` — Windows toast notifications (optional; falls back to PowerShell)

**Node.js (MCP server):**
- Node.js 18+

**External services (optional):**
- LM Studio — local LLM
- Obsidian + Local REST API plugin — PKA

---

## Version History

| Version | Changes |
|---------|---------|
| v4.1.0 | Extract `render_html.py` as standalone module. Add `claude -p \| python render_html.py` CLI. Eliminate duplicate code from watcher. |
| v4.0.0 | Add `coordination_watcher.py`. Auto HTML report generation, browser auto-open, `CLAUDECODE` env var stripping for nested launch support. |
| v3.1.0 | Add PKA (Obsidian) integration |
| v3.0.0 | File-based messaging |
| v2.0.0 | Agent SDK integration |
| v1.0.0 | Initial release |

---

## License

MIT

# AI Task Coordinator

Claude Desktop 用 MCP サーバー + Claude Code 自律実行ウォッチャー。

Claude Desktop からタスクを投入すると、`coordination_watcher.py` が検知して Claude Code を自動起動し、完了後に結果を HTML でブラウザ表示します。

## アーキテクチャ

```
Claude Desktop
    │ MCP (submit_task / send_message)
    ▼
AI Task Coordinator (index.js)        task_box/*.json
    │                                      │
    │                               coordination_watcher.py
    │                                      │ DISPATCH
    │                                      ▼
    │                               Claude Code (claude -p)
    │                                      │ COMPLETE
    │                                      ▼
    │                               output_box/reports/{id}.html
    │                                      │ webbrowser.open
    │                                      ▼
    └── check_task_result ────────── ブラウザで結果表示 + Toast通知
```

## 主要コンポーネント

### `coordination_watcher.py` — 自律タスクディスパッチャー

`task_box/` を監視し、pending タスクを自動処理します。

**フロー:**
1. `status: "pending"` を検知 → `claude --dangerously-skip-permissions -p` で自動起動
2. `status: "completed"` を検知 → result を HTML レンダリング → ブラウザ自動オープン
3. Windows トースト通知を送信（`win11toast` / PowerShell フォールバック）

**起動:**
```bash
python coordination_watcher.py
# または
start_watcher.bat
```

**依存パッケージ:**
```bash
pip install watchdog win11toast
```

### `index.js` — MCP サーバー

Claude Desktop に以下のツールを提供します。

#### メッセージング
| Tool | 説明 |
|------|------|
| `send_message` | Claude Code へメッセージ送信 |
| `check_messages` | 新着メッセージ確認（既読に更新） |
| `get_thread` | スレッド全履歴取得 |

#### タスク管理
| Tool | 説明 |
|------|------|
| `submit_task` | task_box にタスク JSON を作成（status: pending） |
| `check_task_result` | output_box → task_box フォールバックで結果取得 |
| `list_tasks` | タスク一覧（status 別集計） |

#### LM Studio 連携
| Tool | 説明 |
|------|------|
| `get_second_opinion` | ローカル LLM に意見を求める |
| `get_code_review` | コードレビュー依頼 |
| `list_local_models` | 利用可能モデル一覧 |

#### PKA (Obsidian 連携)
| Tool | 説明 |
|------|------|
| `save_insight` | 知見を Obsidian に保存 |
| `save_learning` | 学び（文脈・例・注意点付き）を保存 |
| `save_conversation_summary` | 会話サマリーを保存 |

#### システム
| Tool | 説明 |
|------|------|
| `check_services` | LM Studio / PKA / パス存在確認 |

## セットアップ

### 1. MCP サーバー（Node.js）

```bash
cd ai-task-coordinator
npm install
cp .env.example .env
# .env を環境に合わせて編集
```

**.env 設定項目:**

| 変数 | 説明 | 例 |
|------|------|---|
| `AI_COORDINATION_BASE` | AI 協調システムのベースパス | `C:/Users/.../ai_coordination` |
| `LM_STUDIO_URL` | LM Studio API エンドポイント | `http://localhost:1234/v1` |
| `PKA_API_URL` | Obsidian REST API URL | `https://127.0.0.1:27124` |
| `PKA_API_KEY` | Obsidian REST API キー | （Obsidian で生成） |
| `PKA_VAULT_FOLDER` | 保存先フォルダ名 | `Claude-Desktop` |

### 2. Claude Desktop に MCP 登録

`claude_desktop_config.json` に追加:

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

### 3. Watcher 起動

```bash
python coordination_watcher.py
```

PC 起動時に自動実行したい場合は `start_watcher.bat` をタスクスケジューラに登録してください。

## タスク JSON 仕様

```json
{
  "id": "task_20260302XXXXXX",
  "type": "development | analysis | review | other",
  "description": "タスク内容",
  "priority": "high | medium | low",
  "submitted_at": "ISO timestamp",
  "started_at":   "ISO timestamp（着手時に自動記入）",
  "completed_at": "ISO timestamp（完了時に自動記入）",
  "status": "pending | in_progress | completed | failed",
  "result": "完了要約（Claude Code が記入）"
}
```

## HTML レポート出力

result が 100 文字以上の場合、完了時に自動で HTML を生成しブラウザで開きます。

- **出力先:** `output_box/reports/{task_id}.html`
- **対応要素:** 見出し、リスト、テーブル、コードブロック、インライン書式、リンク
- **CSS:** レスポンシブ、モノスペースコードブロック、ダークテーマコード

## ディレクトリ構成

```
ai-task-coordinator/
├── coordination_watcher.py   # 自律タスクディスパッチャー（メイン）
├── index.js                  # MCP サーバー
├── config.js                 # パス設定
├── lm-studio-client.js       # LM Studio 連携
├── pka-writer.js             # Obsidian REST API 連携
├── start_watcher.bat         # Watcher 起動スクリプト（Windows）
├── .env.example              # 環境変数テンプレート
└── docs/
    ├── ARCHITECTURE.md
    ├── DESKTOP_PROTOCOL_REFERENCE.md
    └── PKA_INTEGRATION.md

# 共有ディレクトリ（_AI_Coordination）
ai_coordination/
├── task_box/                 # タスク JSON 置き場
├── output_box/reports/       # HTML レポート出力
└── messages/
    ├── desktop_to_code/
    ├── code_to_desktop/
    └── threads/
```

## 依存関係

**Python (watcher):**
- Python 3.11+
- `watchdog` — ファイルシステム監視
- `win11toast` — Windows トースト通知（オプション、なければ PowerShell フォールバック）

**Node.js (MCP サーバー):**
- Node.js 18+

**外部サービス（オプション）:**
- LM Studio — ローカル LLM
- Obsidian + Local REST API plugin — PKA

## バージョン履歴

| バージョン | 変更内容 |
|-----------|---------|
| v4.0.0 | `coordination_watcher.py` 追加。HTML レポート自動生成、ブラウザ自動オープン、CLAUDECODE 環境変数除去によるネスト起動対応 |
| v3.1.0 | PKA (Obsidian 連携) 追加 |
| v3.0.0 | ファイルベースメッセージング |
| v2.0.0 | Agent SDK 統合 |
| v1.0.0 | 初期リリース |

## License

MIT

# AI Task Coordinator

Claude Desktop用MCPサーバー。3つの主要機能を提供：

1. **Claude Desktop ↔ Claude Code メッセージング**
2. **タスク管理** (task_box/output_box)
3. **Local LLM連携** (LM Studio)
4. **PKA** (Personal Knowledge Accumulator) - Obsidian連携

## ツール一覧

### メッセージング
| Tool | Description |
|------|-------------|
| `send_message` | パートナーAIにメッセージ送信 |
| `check_messages` | 新着メッセージ確認 |
| `get_thread` | スレッド履歴取得 |

### タスク管理
| Tool | Description |
|------|-------------|
| `submit_task` | task_boxにタスク投入 |
| `check_task_result` | output_boxから結果取得 |
| `list_tasks` | タスク一覧表示 |

### LM Studio連携
| Tool | Description |
|------|-------------|
| `get_second_opinion` | ローカルLLMに意見を求める |
| `get_code_review` | コードレビュー依頼 |
| `list_local_models` | 利用可能モデル一覧 |

### PKA (Obsidian連携)
| Tool | Description |
|------|-------------|
| `save_insight` | 知見をObsidianに保存 |
| `save_learning` | 学び（文脈・例・注意点付き）を保存 |
| `save_conversation_summary` | 会話サマリーを保存 |

### システム
| Tool | Description |
|------|-------------|
| `check_services` | 全サービス接続状況確認 |

## アーキテクチャ

```
Claude Desktop
    ↓ MCP
AI Task Coordinator (index.js)
    ├── Messages ←→ Claude Code
    ├── task_box/output_box ←→ AI Coordination System
    ├── LM Studio (Local LLM)
    └── PKA → Obsidian Vault → Smart Connections (RAG)
```

## インストール

```bash
cd ai-task-coordinator
npm install
```

## 環境設定

1. `.env.example` を `.env` にコピー
2. 自分の環境に合わせて編集

```bash
cp .env.example .env
```

**.env の設定項目:**

| 変数 | 説明 | 例 |
|-----|------|---|
| `AI_COORDINATION_BASE` | AI協調システムのパス | `C:/Users/.../ai_coordination` |
| `LM_STUDIO_URL` | LM Studio APIエンドポイント | `http://localhost:1234/v1` |
| `PKA_API_URL` | Obsidian REST APIのURL | `https://127.0.0.1:27124` |
| `PKA_API_KEY` | Obsidian REST APIキー | (Obsidianで生成) |
| `PKA_VAULT_FOLDER` | 保存先フォルダ名 | `Claude-Desktop` |

## Claude Desktop設定

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

## ディレクトリ構成

```
ai-task-coordinator/
├── index.js              # MCPサーバー本体
├── config.js             # パス設定
├── lm-studio-client.js   # LM Studio連携
├── pka-writer.js         # Obsidian REST API連携
└── docs/
    ├── ARCHITECTURE.md   # システム構成詳細
    └── PKA_INTEGRATION.md # PKA連携ガイド

_AI_Coordination/ai_coordination/
├── task_box/             # タスク入力
├── output_box/           # 処理結果
└── messages/
    ├── desktop_to_code/  # Desktop→Code
    ├── code_to_desktop/  # Code→Desktop
    └── threads/          # スレッド管理
```

## 使用例

### 学びを保存
```
「Pythonのasyncioについて学んだことをObsidianに保存して」
→ save_learning が呼ばれ、構造化された知見がVaultに保存
```

### Claude Codeに依頼
```
「このコードをClaude Codeにレビューしてもらって」
→ send_message でメッセージ送信
```

### サービス確認
```
「システム状況を確認して」
→ check_services で全接続状態表示
```

## 依存関係

- Node.js 18+
- Obsidian + Local REST API plugin (PKA用)
- LM Studio (ローカルLLM用、オプション)

## バージョン

- **v3.1.0** - PKA (Obsidian連携) 追加
- **v3.0.0** - ファイルベースメッセージング
- **v2.0.0** - Agent SDK統合
- **v1.0.0** - 初期リリース

## License

MIT

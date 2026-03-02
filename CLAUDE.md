# AI Task Coordinator — 共通プロトコル仕様書

**Protocol Version: 1.0.0**
**Last Updated: 2026-03-02**
**対象アクター: Claude Desktop / Claude Code**

---

## 1. 本文書の位置づけ

本文書は Claude Desktop と Claude Code の**双方が参照する唯一の行動規約**である。
ツールの使い方だけでなく、各アクターが相手をどう認知し、何を期待し、どう振る舞うかを定義する。

**読み込み義務:**
- **Claude Code**: プロジェクト開始時に自動読み込み（CLAUDE.md配置による）
- **Claude Desktop**: セッション開始時に本文書を読む（Project Knowledge経由、または手動参照）
- 新セッションの最初の行動は本文書の確認であること

---

## 2. アーキテクチャ概要

```
┌──────────────┐     MCP Server (index.js v3.1)     ┌──────────────┐
│ Claude       │  ─── submit_task ──────────────▶   │ task_box/    │
│ Desktop      │  ─── send_message ────────────▶   │ messages/    │
│              │  ◀── check_messages ───────────   │              │
│              │  ◀── check_task_result ────────   │              │
│              │  ◀── list_tasks ──────────────   │              │
└──────────────┘                                    └──────┬───────┘
                                                           │ ファイルシステム共有
┌──────────────┐                                    ┌──────▼───────┐
│ Claude       │  ── task_box/*.json 直接読取 ────▶ │ _AI_         │
│ Code         │  ── status更新・result書込 ──────▶ │ Coordination │
│ (WSL)        │  ── send_message (MCP) ─────────▶ │              │
│              │  ── check_messages (MCP) ◀───────  │              │
└──────────────┘                                    └──────────────┘
```

### 共有パス
| リソース | パス (Windows) |
|---------|---------------|
| MCP Server | `C:\Users\kazin\Desktop\mobile_workspace\ai-task-coordinator\` |
| task_box | `C:\Users\kazin\Desktop\_AI_Coordination\ai_coordination\task_box\` |
| output_box | `C:\Users\kazin\Desktop\_AI_Coordination\ai_coordination\output_box\` |
| messages D→C | `...\messages\desktop_to_code\` |
| messages C→D | `...\messages\code_to_desktop\` |
| threads | `...\messages\threads\` |

---

## 3. 相互認知モデル

### 3.1 Claude Desktop が知るべきこと（Code の行動モデル）

| 項目 | Codeの振る舞い |
|------|---------------|
| タスク受信 | task_box/*.json を直接読取（MCP経由ではない場合あり） |
| 着手報告 | task_box JSON の status を "in_progress" に更新 |
| 完了報告 | task_box JSON の status を "completed" に更新し、result フィールドに結果記載 |
| 追加報告 | send_message (type: "result") で詳細を送信する場合あり |
| CLAUDE.md | プロジェクトルートの CLAUDE.md を自動読み込みする |
| 実行環境 | **WSLまたはWindows** — パスはWSLマウント形式の場合がある |
| テスト実行 | `python -m pytest tests/ -v` をWSL/Windows上で実行 |

**Desktop の行動規約:**
- `check_task_result` で結果が取れなかった場合、task_box の JSON を直接読む
- Code の実行環境を推測しない。不明なら確認する
- MCP サーバーのソース (index.js) を読まずにツールの挙動を推測しない

### 3.2 Claude Code が知るべきこと（Desktop の行動モデル）

| 項目 | Desktop の振る舞い |
|------|-------------------|
| タスク投入 | `submit_task` で task_box に JSON 作成（status: "pending"） |
| 結果読取 | `check_task_result` → output_box を先に見る → なければ task_box JSON の status/result を読む |
| 一覧参照 | `list_tasks` → task_box JSON の status フィールドで pending/completed 振り分け |
| メッセージ読取 | `check_messages --for desktop` → messages/code_to_desktop/ の pending メッセージ |
| 指示追加 | `send_message` または task_box への新規 JSON 作成 |

**Code の行動規約:**
- 完了時は **必ず** task_box JSON の status を "completed" に更新し、result フィールドに要約を記載する
- 詳細報告は send_message (type: "result") で別途送信してもよい
- Desktop から `check_messages --for code` で指示が来る可能性がある。タスク完了後に確認する

---

## 4. タスクライフサイクル

### 4.1 状態遷移

```
pending ──→ in_progress ──→ completed
                │
                └──→ failed（異常終了時）
```

**正の状態管理場所: task_box/{task_id}.json の status フィールド**
output_box はレガシー互換のみ。新規タスクは task_box JSON で完結する。

### 4.2 タスク JSON 仕様

```json
{
  "id": "task_20260302XXXXXX",
  "type": "development|analysis|review|other",
  "description": "タスク内容",
  "priority": "high|medium|low",
  "constraints": {},
  "submitted_at": "ISO timestamp",
  "started_at": "ISO timestamp (Code が着手時に記入)",
  "completed_at": "ISO timestamp (Code が完了時に記入)",
  "status": "pending|in_progress|completed|failed",
  "result": "完了時の要約テキスト (Code が記入)"
}
```

### 4.3 フロー詳細

1. **Desktop** が `submit_task` → task_box に JSON 作成 (status: "pending")
2. **Code** が task_box を読取 → status を "in_progress" に更新、started_at 記入
3. **Code** が作業実行
4. **Code** が status を "completed" に更新、completed_at と result を記入
5. **Code** が `send_message` (type: "result") で Desktop に通知（推奨）
6. **Desktop** が `check_task_result` または `list_tasks` で結果確認
7. **Desktop** が task_box JSON を直接読んで詳細確認（必要に応じて）

---

## 5. メッセージプロトコル

### 5.1 メッセージ形式

```json
{
  "id": "msg_20260302XXXXXX_xxxx",
  "from": "desktop|code",
  "to": "desktop|code",
  "type": "task|question|answer|result|info",
  "thread_id": "thread_xxx",
  "content": "内容",
  "timestamp": "ISO timestamp",
  "status": "pending|read",
  "protocol_version": "1.0.0"
}
```

### 5.2 protocol_version フィールド

send_message 時に `protocol_version` を content 末尾またはフィールドとして付与する。
受信側がこのバージョンを知らない場合、CLAUDE.md を再読み込みする契機とする。

**注: 現在の index.js は protocol_version フィールドを自動付与しない。
Content 内に `[protocol:1.0.0]` と記載する運用で開始する。**

---

## 6. MCP ツール一覧

### Messaging
| ツール | 用途 |
|--------|------|
| `send_message` | メッセージ送信 |
| `check_messages` | 受信確認（pending のみ返却、read に更新） |
| `get_thread` | スレッド全履歴 |

### Task Management
| ツール | 用途 |
|--------|------|
| `submit_task` | task_box に JSON 作成 |
| `check_task_result` | output_box → task_box フォールバックで結果取得 |
| `list_tasks` | task_box の status フィールドで振り分け + output_box レガシー |

### LM Studio
| ツール | 用途 |
|--------|------|
| `get_second_opinion` | ローカル LLM に意見照会 |
| `get_code_review` | コードレビュー |
| `list_local_models` | 利用可能モデル一覧 |

### PKA (Obsidian 連携)
| ツール | 用途 |
|--------|------|
| `save_insight` | 知見保存 |
| `save_learning` | 学び保存 |
| `save_conversation_summary` | 会話サマリー保存 |

### System
| ツール | 用途 |
|--------|------|
| `check_services` | LM Studio / PKA / パス存在確認 |

---

## 7. 既知の制約と注意事項

- Agent SDK は v3.0.0 で削除済み。全通信はファイルベース
- PKA は Obsidian が起動していないと利用不可（自己署名証明書、SSL 検証スキップ）
- LM Studio は Tailscale 経由 (100.64.100.6:1234)。未起動時はエラー
- output_box ディレクトリ方式はレガシー。新規タスクでは使用しない
- Desktop 側に MCP ツール呼び出しの自動読み込み機構はない。セッション開始時の手動参照が必要

---

## 変更履歴

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-02 | 初版。相互認知モデル追加、タスクライフサイクル定義、プロトコルバージョン導入 |

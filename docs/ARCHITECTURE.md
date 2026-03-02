# AI Task Coordinator - システムアーキテクチャ

## 全体構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Desktop                              │
│  (ユーザーインターフェース・会話・要件定義)                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │ MCP Protocol
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              AI Task Coordinator (Node.js MCP Server)            │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│  │Messaging │  Tasks   │LM Studio │   PKA    │ Services │       │
│  │  Tools   │  Tools   │  Tools   │  Tools   │  Check   │       │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘       │
└───────┼──────────┼──────────┼──────────┼──────────┼─────────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │Messages│ │task_box│ │LM      │ │Obsidian│ │Status  │
   │  Dir   │ │output  │ │Studio  │ │REST API│ │Check   │
   └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────────────┐
  │Claude  │ │AI      │ │Local   │ │TechBusinessVault   │
  │Code    │ │Coord   │ │LLM     │ │  ├─Claude-Desktop/ │
  │(WSL)   │ │System  │ │(qwen)  │ │  └─Smart Connections│
  └────────┘ └────────┘ └────────┘ └────────────────────┘
```

## コンポーネント詳細

### 1. AI Task Coordinator (MCPサーバー)

**役割**: Claude Desktopと各サービスを接続するハブ

```
ai-task-coordinator/
├── index.js              # MCPサーバー本体
│   ├── Tool定義 (ListToolsRequestSchema)
│   └── Tool実行 (CallToolRequestSchema)
├── config.js             # パス・環境設定
├── lm-studio-client.js   # LM Studio API呼び出し
└── pka-writer.js         # Obsidian REST API呼び出し
```

### 2. ファイルベースメッセージング

**目的**: Claude Desktop ↔ Claude Code の非同期通信

```
messages/
├── desktop_to_code/    # Desktop→Code方向
│   └── msg_*.json      # 個別メッセージ
├── code_to_desktop/    # Code→Desktop方向
│   └── msg_*.json
└── threads/            # スレッド管理
    └── thread_*.json   # 会話履歴
```

**フロー**:
1. Desktop: `send_message` でJSONファイル作成
2. Code: ファイル監視 or `check_messages` で取得
3. Code: `send_message` で返信
4. Desktop: `check_messages` で取得

### 3. タスク管理システム

**目的**: 重い処理をClaude Codeに委譲

```
_AI_Coordination/ai_coordination/
├── task_box/           # タスク投入キュー
│   └── task_*.json
└── output_box/         # 処理結果
    └── task_*/
        ├── result.json
        └── artifacts/
```

### 4. LM Studio連携

**目的**: 無料のローカルLLMで補助処理

- **Endpoint**: `http://100.64.100.6:1234/v1`
- **用途**: セカンドオピニオン、コードレビュー
- **モデル**: qwen3-vl-8b, qwen3-coder-30b

### 5. PKA (Personal Knowledge Accumulator)

**目的**: 会話から得た知見をObsidianに永続化

```
Claude Desktop
    ↓ save_learning
pka-writer.js
    ↓ HTTPS PUT
Obsidian REST API (port 27124)
    ↓
TechBusinessVault/Claude-Desktop/
    ↓ 自動
Smart Connections (Embedding・RAG)
```

**Trust Score設計**:
- 信頼度により情報の重み付け
- 将来的にRAG検索時のランキングに活用予定

## データフロー

### パターン1: 質問→即答

```
User → Claude Desktop → 回答
```

### パターン2: 重い処理委譲

```
User → Claude Desktop → submit_task → task_box
                                         ↓
                              AI Coordination System
                                         ↓
                                    output_box
                                         ↓
       User ← Claude Desktop ← check_task_result
```

### パターン3: Claude Code協調

```
User → Claude Desktop → send_message → messages/desktop_to_code
                                              ↓
                                        Claude Code
                                              ↓
                                  messages/code_to_desktop
                                              ↓
       User ← Claude Desktop ← check_messages
```

### パターン4: 知見蓄積

```
会話中の発見 → save_learning → Obsidian Vault
                                    ↓
              後日検索 ← Smart Connections RAG
```

## 設定ファイル

### config.js
```javascript
export const config = {
  coordination: {
    basePath: "C:/Users/kazin/Desktop/_AI_Coordination/ai_coordination",
    taskBox: "...",
    outputBox: "...",
    messages: {
      desktopToCode: "...",
      codeToDesktop: "...",
      threads: "..."
    }
  },
  lmStudio: {
    baseUrl: "http://100.64.100.6:1234/v1"
  }
};
```

### pka-writer.js 設定
```javascript
const PKA_CONFIG = {
  apiUrl: "https://127.0.0.1:27124",
  apiKey: "...",
  vaultFolder: "Claude-Desktop"
};
```

## 拡張ポイント

1. **新規Tool追加**: `index.js` の tools配列とswitch文に追加
2. **新規サービス連携**: 専用クライアントモジュール作成
3. **Trust Score活用**: RAG検索時のスコアリング実装

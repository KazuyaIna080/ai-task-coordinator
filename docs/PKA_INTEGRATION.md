# PKA (Personal Knowledge Accumulator) 連携ガイド

## 概要

PKAはClaude Desktopの会話から得た知見をObsidian Vaultに自動保存し、
Smart Connectionsプラグインで検索可能にする仕組み。

## 前提条件

### 必須
- Obsidian Desktop (起動状態)
- Local REST API プラグイン (有効化済み)
- TechBusinessVault (設定済み)

### 推奨
- Smart Connections プラグイン (RAG検索用)

## セットアップ

### 1. Local REST API プラグイン設定

Obsidian Settings → Community plugins → Local REST API

```
Port: 27124
HTTPS: Enabled
API Key: (自動生成されたキーをコピー)
```

### 2. pka-writer.js 設定確認

```javascript
const PKA_CONFIG = {
  apiUrl: "https://127.0.0.1:27124",
  apiKey: "YOUR_API_KEY_HERE",  // 要更新
  vaultFolder: "Claude-Desktop"
};
```

### 3. 接続確認

Claude Desktopで:
```
check_servicesを実行して
```

期待される出力:
```
PKA (Obsidian): ✅ Connected
```

## 使用方法

### save_insight - 汎用知見保存

```javascript
save_insight({
  title: "タイトル",
  content: "本文",
  tags: ["tag1", "tag2"],
  source: "claude_desktop",
  trustScore: 0.8,
  category: "insight"  // insight|howto|decision|gotcha|reference
})
```

**生成ファイル例**:
```markdown
---
title: "タイトル"
created: 2026-01-27 15:00:00
source: claude_desktop
trust_score: 0.8
category: insight
tags: ["tag1", "tag2"]
---

# タイトル

本文

---
*PKA auto-generated | Source: claude_desktop | Trust: 0.8*
```

### save_learning - 学び保存（推奨）

```javascript
save_learning({
  whatLearned: "学んだこと（タイトルになる）",
  context: "どういう状況で学んだか",
  example: "具体例（オプション）",
  gotcha: "注意点・落とし穴（オプション）",
  tags: ["learning", "topic"]
})
```

**生成ファイル例**:
```markdown
---
title: "学んだこと"
created: 2026-01-27 15:00:00
source: claude_desktop
trust_score: 0.85
category: howto
tags: ["learning", "topic"]
---

# 学んだこと

## 学んだこと
学んだこと（タイトルになる）

## 文脈
どういう状況で学んだか

## 具体例
具体例（オプション）

## ⚠️ 注意点
注意点・落とし穴（オプション）

---
*PKA auto-generated | Source: claude_desktop | Trust: 0.85*
```

### save_conversation_summary - 会話サマリー

```javascript
save_conversation_summary({
  summary: "会話の概要",
  keyPoints: ["ポイント1", "ポイント2"],
  decisions: ["決定事項1"],
  nextActions: ["TODO1", "TODO2"],
  tags: ["project-x"]
})
```

## Trust Score 設計

| Source | Score | 説明 |
|--------|-------|------|
| user | 1.0 | ユーザーが直接入力 |
| claude_code | 0.9 | Claude Codeの出力 |
| claude_desktop | 0.8 | Claude Desktopの出力 |
| gemini | 0.7 | Gemini CLIの出力 |
| web | 0.5 | Web検索結果 |

**将来活用**:
- RAG検索時のスコアリング
- 情報の信頼性フィルタリング
- 汚染情報の低優先化

## Category 一覧

| Category | 用途 |
|----------|------|
| insight | 気づき・洞察 |
| howto | 手順・方法 |
| decision | 決定事項・理由 |
| gotcha | 注意点・落とし穴 |
| reference | 参照情報 |

## ファイル保存場所

```
TechBusinessVault/
└── Claude-Desktop/
    ├── 20260127_150000_タイトル1.md
    ├── 20260127_151000_タイトル2.md
    └── ...
```

**ファイル名形式**: `YYYYMMDD_HHMMSS_SafeTitle.md`

## トラブルシューティング

### 「PKA (Obsidian): ❌ Not connected」

1. Obsidianが起動しているか確認
2. Local REST API プラグインが有効か確認
3. ポート27124が使用可能か確認
4. APIキーが正しいか確認

### 保存エラー

1. Vaultフォルダ `Claude-Desktop` が存在するか確認
2. ファイル名に使用できない文字がないか確認
3. Obsidianのログを確認

### Smart Connectionsに反映されない

1. 手動で「Refresh embeddings」実行
2. 新規ファイルが対象フォルダに含まれているか確認

## 技術詳細

### API呼び出し

```javascript
PUT https://127.0.0.1:27124/vault/{encoded_path}
Headers:
  Authorization: Bearer {api_key}
  Content-Type: text/markdown
Body: (Markdown content)
Response: 204 No Content (success)
```

### 注意点

- 日本語ファイル名は `encodeURIComponent()` でエンコード
- 自己署名証明書のためSSL検証をスキップ
- スペースは `_` に置換

## 関連ファイル

- `pka-writer.js` - API連携実装
- `pka_writer.py` - Python版（参考実装）
- `docs/PKA_PROJECT_PROPOSAL.md` - 当初企画書

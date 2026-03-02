# Personal Knowledge Accumulator (PKA)
## プロジェクト企画書 v1.0

**作成日**: 2026-01-27  
**作成者**: Kazuya + Claude Desktop  
**期間**: 2週間（14日間）  
**ステータス**: 企画段階

---

## エグゼクティブサマリー

### 一言で言うと
**「複数のLLMを使うだけで、知見が自動統合される個人ナレッジシステム」**

### 解決する課題
現状、Claude Desktop / Claude Code / Gemini CLI など複数のLLMを使っていると：
- 各LLMでの会話・知見がバラバラに散逸
- 「前にCodeで解決したはず」が思い出せない
- 同じ問題で何度もハマる
- 過去の成功パターンが再利用できない

### 提供する価値
- **ゼロ入力**: 使っているだけで自動蓄積
- **マルチLLM統合**: Desktop/Code/Gemini全ての知見を一元管理
- **時間価値**: 1年後に強力な個人DBが完成
- **完全無料**: ローカルLLM（LM Studio）ベース

---

## コアバリュー

### 🎯 最大の売り: マルチLLM知見統合

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   Claude Desktop で議論した設計判断                      │
│              ＋                                         │
│   Claude Code で実装した解決策                          │
│              ＋                                         │
│   Gemini CLI で分析した結果                             │
│              ↓                                         │
│   【統合された検索可能な知識ベース】                     │
│                                                         │
│   出典付き: 「これは2026-03-15にClaude Codeで得た知見」  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### なぜLM Studioか？

| 選択肢 | 問題 |
|--------|------|
| Claude API | 有料、コスト懸念 |
| クラウドDB | プライバシー、依存 |
| 手動整理 | 継続できない |
| **LM Studio** | **無料・ローカル・自動** ✅ |

---

## システム概要

### アーキテクチャ全体図

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│Claude Desktop│  │ Claude Code │  │ Gemini CLI  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │               │               │
       │   messages/   │   output_box/ │   gemini_outbox/
       │               │               │
       └───────────────┼───────────────┘
                       ↓
        ┌─────────────────────────────┐
        │      Passive Collector      │
        │    (バックグラウンド収集)     │
        └──────────────┬──────────────┘
                       ↓
        ┌─────────────────────────────┐
        │         LM Studio           │
        │  ┌─────┐ ┌─────┐ ┌─────┐   │
        │  │Embed│ │Class│ │Summ │   │
        │  └─────┘ └─────┘ └─────┘   │
        └──────────────┬──────────────┘
                       ↓
        ┌─────────────────────────────┐
        │    Unified Knowledge DB     │
        │  ├── conversations/         │
        │  ├── tasks/                 │
        │  ├── knowledge/             │
        │  ├── patterns/              │
        │  └── digests/               │
        └─────────────────────────────┘
                       ↓
        ┌─────────────────────────────┐
        │       Query Interface       │
        │  「前に解決した方法は？」      │
        │  「今月何やった？」           │
        │  「よくハマるパターンは？」    │
        └─────────────────────────────┘
```

---

## 5つの機能モジュール

### Module 1: Orchestrator（オーケストレーター）

**目的**: タスクの分割・並列実行・スケジューリング

**機能**:
- 大タスクを小タスクに分割（Split）
- 依存関係・優先度で並び替え（Sort）
- 実行タイミング制御（Schedule）
- 複数Claude Codeパイプラインへの振り分け

**ユースケース**:
```
User: 「このWebアプリ全体を作って」
        ↓
Orchestrator: 
  1. DB設計 → Pipeline A
  2. API実装 → Pipeline B（1完了後）
  3. UI実装 → Pipeline C（1完了後）
  4. 統合テスト → Pipeline A（2,3完了後）
```

**工数**: 3日

---

### Module 2: Task RAG（タスク検索・再利用）

**目的**: 過去のタスク結果を検索・ベストプラクティス提供

**機能**:
- タスク結果のEmbedding保存
- 類似タスク検索
- ベストプラクティス優先表示
- 成功/失敗パターンの学習

**データ構造**:
```json
{
  "task_id": "task_20260127_xxxx",
  "description": "JWTでログイン機能を実装",
  "source_llm": "claude_code",
  "result": { "files": [...], "success": true },
  "embedding": [0.123, ...],
  "quality_score": 0.95,
  "marked_as_best_practice": true,
  "tags": ["auth", "jwt", "python"]
}
```

**工数**: 2日

---

### Module 3: Knowledge Vault（知見タンク）

**目的**: Obsidian/Notionライクな知識管理（自動版）

**機能**:
- 自動タグ付け
- 自動リンク（関連ノート検出）
- 時系列管理
- セマンティック検索

**データ構造**:
```json
{
  "id": "note_20260127_xxxx",
  "title": "ESModule vs CommonJS の互換性問題",
  "content": "...",
  "source": {
    "llm": "claude_desktop",
    "session_id": "session_xxx"
  },
  "tags": {
    "manual": [],
    "auto": ["javascript", "module", "troubleshooting"]
  },
  "links": {
    "references": ["note_xxx"],
    "referenced_by": ["note_yyy"]
  },
  "embedding": [...]
}
```

**工数**: 3日

---

### Module 4: Activity Digest（活動ダイジェスト）

**目的**: 定期的な振り返りレポート自動生成

**機能**:
- 日次/週次/月次/年次レポート
- 完了/進行中/未完了の集計
- 学び・発見の抽出
- TODO候補の提案

**出力例**:
```markdown
## 週次ダイジェスト (2026-01-20 ~ 2026-01-27)

### ✅ 完了 (12件)
- [Claude Code] Agent SDK → ファイルベースに移行
- [Claude Desktop] PKA企画書作成
- [Gemini] 地政学分析レポート

### 🔄 進行中 (3件)
- LM Studio活用拡張

### 💡 今週の学び
- CLI `-p` モードではファイル作成不可
- ファイルベース通信でAPI費用ゼロ化

### 📋 来週のTODO候補
1. [ ] Orchestrator実装
2. [ ] Vector Store選定
```

**工数**: 2日

---

### Module 5: Passive Collector（自動収集）

**目的**: バックグラウンドで全活動を自動収集

**機能**:
- messages/ 監視・収集
- output_box/ 監視・収集
- 会話履歴の定期取得
- 差分検出・重複排除

**収集ポイント**:
| ソース | パス | 収集内容 |
|--------|------|----------|
| Desktop↔Code通信 | messages/ | 双方向メッセージ |
| Codeタスク結果 | output_box/ | 成果物・レポート |
| Gemini結果 | gemini_cli_outbox/ | CLI出力 |
| Desktop会話 | (API or export) | 会話履歴 |

**工数**: 2日

---

## 技術スタック

### LLMモデル（LM Studio）

| 用途 | モデル | 理由 |
|------|--------|------|
| Embedding | nomic-embed-text | 軽量・高品質 |
| 分類・タグ付け | qwen3-vl-8b | バランス良好 |
| 要約・分析 | qwen3-vl-8b | 汎用性 |
| コードレビュー | qwen3-coder-30b | コード特化 |

### Vector Store

| 候補 | 特徴 | 判定 |
|------|------|------|
| ChromaDB | Python親和性高、軽量 | ✅ 第一候補 |
| LanceDB | Rust製、高速 | △ 検討 |
| SQLite + vec | 既存資産活用 | △ 検討 |

### ストレージ構造

```
_AI_Coordination/
├── ai_coordination/          # 既存
│   ├── messages/
│   ├── task_box/
│   └── output_box/
│
└── pka/                      # 新規
    ├── db/
    │   ├── vectors.db        # Embedding DB
    │   └── knowledge.db      # メタデータ
    ├── knowledge/            # 知見ノート
    ├── patterns/             # パターン・学び
    ├── digests/              # レポート
    │   ├── daily/
    │   ├── weekly/
    │   └── monthly/
    └── config/               # 設定
```

---

## 開発スケジュール（2週間）

### Week 1: 基盤構築

| 日 | タスク | 成果物 |
|----|--------|--------|
| Day 1-2 | 環境構築・Vector Store選定 | ChromaDB動作確認 |
| Day 3-4 | Passive Collector実装 | 自動収集デーモン |
| Day 5-6 | Knowledge Vault基本機能 | 保存・検索API |
| Day 7 | 統合テスト・調整 | 基盤動作確認 |

### Week 2: 機能拡張

| 日 | タスク | 成果物 |
|----|--------|--------|
| Day 8-9 | Task RAG実装 | タスク検索機能 |
| Day 10-11 | Activity Digest実装 | レポート生成 |
| Day 12-13 | Orchestrator実装 | タスク分割・並列 |
| Day 14 | 全体統合・ドキュメント | リリース |

### マイルストーン

| マイルストーン | 日 | 達成基準 |
|---------------|-----|---------|
| M1: 基盤完成 | Day 7 | 自動収集・保存が動作 |
| M2: 検索可能 | Day 11 | 知見・タスクが検索可能 |
| M3: 完成 | Day 14 | 全機能動作・ドキュメント完備 |

---

## リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| LM Studio性能不足 | 処理遅延 | バッチ処理化、非同期処理 |
| Embedding品質 | 検索精度低下 | モデル比較検証、閾値調整 |
| ストレージ肥大 | ディスク圧迫 | 古いデータの要約・圧縮 |
| 複雑化 | 開発遅延 | MVP優先、段階的拡張 |

---

## 成功指標

### 定量指標

| 指標 | 目標 | 測定方法 |
|------|------|---------|
| 自動収集率 | 95%以上 | 収集数/実行数 |
| 検索精度 | 80%以上 | 関連性評価 |
| レスポンス時間 | 3秒以内 | 検索応答時間 |
| 稼働率 | 99%以上 | ダウンタイム計測 |

### 定性指標

- [ ] 「あの時どうしたっけ？」がすぐ見つかる
- [ ] 同じエラーで2度ハマらない
- [ ] 週次振り返りが自動で出る
- [ ] 1ヶ月後に「これ便利」と感じる

---

## 将来展望

### Phase 2（1ヶ月後）
- パターン自動検出・提案
- 類似ユーザーとのベストプラクティス共有（オプトイン）
- VS Code拡張連携

### Phase 3（3ヶ月後）
- 予測的タスク提案
- 自動ワークフロー生成
- 他LLM（GPT、Gemini Pro等）対応拡張

---

## 次のステップ

1. [ ] 企画書レビュー・承認
2. [ ] 技術検証（ChromaDB + LM Studio Embedding）
3. [ ] 詳細設計書作成
4. [ ] 開発開始

---

## 付録

### A. 用語定義

| 用語 | 定義 |
|------|------|
| PKA | Personal Knowledge Accumulator |
| Knowledge Vault | 知見を蓄積・管理する機能 |
| Task RAG | タスク結果の検索・再利用機能 |
| Passive Collector | 自動収集デーモン |
| Activity Digest | 定期レポート生成機能 |

### B. 参考資料

- ai-task-coordinator MCP Server v3.0.0
- AI協調システム v6.0 ドキュメント
- LM Studio ドキュメント

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-27

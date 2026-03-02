# AI Task Coordinator — Desktop 側参照規約

**Protocol Version: 1.0.0**

## セッション開始時の必須行動

1. `ai-task-coordinator/CLAUDE.md` を読む
   パス: `C:\Users\kazin\Desktop\mobile_workspace\ai-task-coordinator\CLAUDE.md`
2. `check_messages --for desktop` で未読メッセージを確認する
3. `list_tasks` で未完了タスクの状態を確認する

## タスク結果の読み取り手順

1. `check_task_result(task_id)` を呼ぶ
2. 結果が得られない場合、task_box の JSON を直接読む:
   `C:\Users\kazin\Desktop\_AI_Coordination\ai_coordination\task_box\{task_id}.json`
3. status / result / completed_at フィールドを確認する

## Code の完了報告方式（Desktop が知るべきこと）

Code は task_box JSON の status フィールドを "completed" に更新し、result フィールドに要約を記載する。
output_box へのディレクトリ作成はレガシー方式であり、新規タスクでは使用されない。

## 禁止事項

- MCP サーバーのソース (index.js) を読まずにツールの挙動を推測すること
- Claude Code の実行環境（Windows/WSL）を確認せずにパスを推測すること
- CLAUDE.md の存在・内容を確認せずにファイルを作成・変更すること

## Protocol Version

send_message 時に content 末尾に `[protocol:1.0.0]` を付与する。
相手から未知のバージョンが来た場合、CLAUDE.md を再読み込みする。

## 正文書の場所

本ファイルは参照用の抜粋。正文書は:
`C:\Users\kazin\Desktop\mobile_workspace\ai-task-coordinator\CLAUDE.md`

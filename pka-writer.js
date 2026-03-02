/**
 * PKA Writer - Personal Knowledge Accumulator
 * Claude Desktop → Obsidian Vault 書き込みモジュール
 *
 * v1.1: config.js から設定読み込み
 */

import https from "https";
import { config } from "./config.js";

/**
 * Obsidian REST APIリクエスト
 */
function makeRequest(path, method = "GET", data = null) {
  return new Promise((resolve, reject) => {
    const { apiUrl, apiKey } = config.pka;

    if (!apiKey) {
      resolve({
        status: "error",
        message: "PKA_API_KEY not configured. Set it in .env file.",
      });
      return;
    }

    const encodedPath = encodeURIComponent(path).replace(/%2F/g, "/");
    const url = new URL(`/vault/${encodedPath}`, apiUrl);

    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      method: method,
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "text/markdown",
      },
      rejectUnauthorized: false, // 自己署名証明書対応
    };

    const req = https.request(options, (res) => {
      let body = "";
      res.on("data", (chunk) => (body += chunk));
      res.on("end", () => {
        resolve({
          status: "ok",
          code: res.statusCode,
          data: body,
        });
      });
    });

    req.on("error", (e) => {
      resolve({
        status: "error",
        message: e.message,
      });
    });

    if (data) {
      req.write(data);
    }
    req.end();
  });
}

/**
 * API接続確認
 */
export async function checkConnection() {
  if (!config.pka.apiKey) {
    return false;
  }
  const result = await makeRequest("", "GET");
  return result.status === "ok";
}

/**
 * ファイル名を安全な形式に変換
 */
function sanitizeFilename(title) {
  return title
    .replace(/[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF_-]/g, "_")
    .slice(0, 50)
    .replace(/^_+|_+$/g, "");
}

/**
 * タイムスタンプ生成
 */
function getTimestamp() {
  const now = new Date();
  return now
    .toISOString()
    .replace(/[-:T]/g, "")
    .slice(0, 14);
}

/**
 * Markdownフォーマット
 */
function formatMarkdown({
  title,
  content,
  tags = [],
  source = "claude_desktop",
  trustScore = 0.8,
  category = "insight",
}) {
  const now = new Date().toISOString().replace("T", " ").slice(0, 19);
  const tagsStr = tags.map((t) => `"${t}"`).join(", ");

  return `---
title: "${title}"
created: ${now}
source: ${source}
trust_score: ${trustScore}
category: ${category}
tags: [${tagsStr}]
---

# ${title}

${content}

---
*PKA auto-generated | Source: ${source} | Trust: ${trustScore}*
`;
}

/**
 * 知見を保存
 */
export async function saveInsight({
  title,
  content,
  tags = [],
  source = "claude_desktop",
  trustScore = 0.8,
  category = "insight",
}) {
  const timestamp = getTimestamp();
  const safeTitle = sanitizeFilename(title);
  const filename = `${timestamp}_${safeTitle}.md`;
  const path = `${config.pka.vaultFolder}/${filename}`;

  const markdown = formatMarkdown({
    title,
    content,
    tags,
    source,
    trustScore,
    category,
  });

  const result = await makeRequest(path, "PUT", markdown);

  if (result.status === "ok") {
    result.filename = filename;
    result.path = path;
  }

  return result;
}

/**
 * 学びを保存
 */
export async function saveLearning({
  whatLearned,
  context,
  example = null,
  gotcha = null,
  tags = [],
}) {
  const contentParts = [
    "## 学んだこと",
    whatLearned,
    "",
    "## 文脈",
    context,
  ];

  if (example) {
    contentParts.push("", "## 具体例", example);
  }

  if (gotcha) {
    contentParts.push("", "## ⚠️ 注意点", gotcha);
  }

  return saveInsight({
    title: whatLearned.slice(0, 50),
    content: contentParts.join("\n"),
    tags: [...tags, "learning"],
    category: example ? "howto" : "insight",
    trustScore: 0.85,
  });
}

/**
 * 会話サマリーを保存
 */
export async function saveConversationSummary({
  summary,
  keyPoints = [],
  decisions = [],
  nextActions = [],
  tags = [],
}) {
  const contentParts = [summary, "", "## Key Points"];
  keyPoints.forEach((p) => contentParts.push(`- ${p}`));

  if (decisions.length > 0) {
    contentParts.push("", "## Decisions");
    decisions.forEach((d) => contentParts.push(`- ${d}`));
  }

  if (nextActions.length > 0) {
    contentParts.push("", "## Next Actions");
    nextActions.forEach((a) => contentParts.push(`- [ ] ${a}`));
  }

  const now = new Date().toISOString().slice(0, 10);
  return saveInsight({
    title: `会話サマリー_${now}`,
    content: contentParts.join("\n"),
    tags: [...tags, "conversation", "summary"],
    category: "insight",
    trustScore: 0.9,
  });
}

/**
 * タスク結果から学びを抽出して保存
 */
export async function saveTaskLearning({
  taskId,
  taskDescription,
  result,
  learnings = [],
  tags = [],
}) {
  const contentParts = [
    `## タスク`,
    `**ID:** ${taskId}`,
    `**説明:** ${taskDescription}`,
    "",
    "## 結果サマリー",
    typeof result === "string" ? result : JSON.stringify(result, null, 2),
  ];

  if (learnings.length > 0) {
    contentParts.push("", "## 学び・知見");
    learnings.forEach((l) => contentParts.push(`- ${l}`));
  }

  return saveInsight({
    title: `Task_${taskId}`,
    content: contentParts.join("\n"),
    tags: [...tags, "task", "result"],
    source: "claude_code",
    category: "reference",
    trustScore: 0.9,
  });
}

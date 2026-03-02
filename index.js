#!/usr/bin/env node
/**
 * AI Task Coordinator - MCP Server
 *
 * Claude Desktop から Claude Code と LM Studio を
 * 協調して使用するための MCP サーバー
 *
 * v3.0: File-based messaging (Agent SDK removed)
 * - send_message / check_messages for Desktop <-> Code communication
 * - submit_task / check_task_result for task_box/output_box integration
 * - LM Studio integration maintained
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from "fs";
import { join, basename } from "path";

// LM Studio クライアント
import {
  getSecondOpinion,
  getCodeReview,
  listAvailableModels,
  checkLmStudioAvailable,
} from "./lm-studio-client.js";

// PKA Writer (Obsidian連携)
import {
  saveInsight,
  saveLearning,
  saveConversationSummary,
  saveTaskLearning,
  checkConnection as checkPkaConnection,
} from "./pka-writer.js";

import { config } from "./config.js";

// Ensure directories exist
function ensureDir(dir) {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

// Generate message ID
function generateMessageId() {
  const now = new Date();
  const timestamp = now.toISOString().replace(/[-:T.Z]/g, "").slice(0, 14);
  const random = Math.random().toString(36).slice(2, 6);
  return `msg_${timestamp}_${random}`;
}

// Generate task ID
function generateTaskId(prefix = "task") {
  const now = new Date();
  const timestamp = now.toISOString().replace(/[-:T.Z]/g, "").slice(0, 14);
  return `${prefix}_${timestamp}`;
}

// Create MCP server
const server = new Server(
  {
    name: "ai-task-coordinator",
    version: "3.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      // === Messaging Tools ===
      {
        name: "send_message",
        description: `Send a message to partner AI (Desktop <-> Code).
Use this for:
- Asking questions during task execution
- Reporting progress or results
- Requesting clarification
Messages are stored in the file system for asynchronous communication.`,
        inputSchema: {
          type: "object",
          properties: {
            from: {
              type: "string",
              enum: ["desktop", "code"],
              description: "Sender identity",
            },
            to: {
              type: "string",
              enum: ["desktop", "code"],
              description: "Recipient identity",
            },
            type: {
              type: "string",
              enum: ["task", "question", "answer", "result", "info"],
              description: "Message type",
            },
            content: {
              type: "string",
              description: "Message content",
            },
            thread_id: {
              type: "string",
              description: "Thread ID for conversation tracking (optional)",
            },
          },
          required: ["from", "to", "type", "content"],
        },
      },
      {
        name: "check_messages",
        description: `Check for new messages addressed to you.
Returns unread messages from the partner AI.`,
        inputSchema: {
          type: "object",
          properties: {
            for: {
              type: "string",
              enum: ["desktop", "code"],
              description: "Check messages for this recipient",
            },
            thread_id: {
              type: "string",
              description: "Filter by thread ID (optional)",
            },
            mark_read: {
              type: "boolean",
              description: "Mark messages as read (default: true)",
              default: true,
            },
          },
          required: ["for"],
        },
      },
      {
        name: "get_thread",
        description: "Get all messages in a conversation thread",
        inputSchema: {
          type: "object",
          properties: {
            thread_id: {
              type: "string",
              description: "Thread ID",
            },
          },
          required: ["thread_id"],
        },
      },

      // === Task Box Tools ===
      {
        name: "submit_task",
        description: `Submit a task to task_box for processing.
Tasks are picked up by the AI Coordination system.`,
        inputSchema: {
          type: "object",
          properties: {
            description: {
              type: "string",
              description: "Task description",
            },
            type: {
              type: "string",
              enum: ["development", "analysis", "review", "other"],
              description: "Task type",
              default: "development",
            },
            priority: {
              type: "string",
              enum: ["high", "medium", "low"],
              description: "Task priority",
              default: "medium",
            },
            constraints: {
              type: "object",
              description: "Additional constraints (optional)",
            },
          },
          required: ["description"],
        },
      },
      {
        name: "check_task_result",
        description: "Check result of a submitted task from output_box",
        inputSchema: {
          type: "object",
          properties: {
            task_id: {
              type: "string",
              description: "Task ID to check",
            },
          },
          required: ["task_id"],
        },
      },
      {
        name: "list_tasks",
        description: "List pending tasks in task_box and completed tasks in output_box",
        inputSchema: {
          type: "object",
          properties: {
            status: {
              type: "string",
              enum: ["pending", "completed", "all"],
              description: "Filter by status",
              default: "all",
            },
            limit: {
              type: "number",
              description: "Maximum number of tasks to return",
              default: 20,
            },
          },
        },
      },

      // === LM Studio Tools ===
      {
        name: "get_second_opinion",
        description: `Get a second opinion from a local LLM (LM Studio). Use this for:
- Alternative perspectives on design decisions
- Validating approaches before implementation
- Quick questions that don't need Claude's full capabilities`,
        inputSchema: {
          type: "object",
          properties: {
            question: {
              type: "string",
              description: "The question or topic to get opinion on",
            },
            model: {
              type: "string",
              description: "Model to use (optional, defaults to qwen3-vl-8b)",
            },
            context: {
              type: "string",
              description: "Additional context for the question",
            },
          },
          required: ["question"],
        },
      },
      {
        name: "get_code_review",
        description: "Get a code review from a coding-specialized local LLM",
        inputSchema: {
          type: "object",
          properties: {
            code: {
              type: "string",
              description: "The code to review",
            },
            context: {
              type: "string",
              description: "Context about what the code should do",
            },
          },
          required: ["code"],
        },
      },
      {
        name: "list_local_models",
        description: "List available models on LM Studio",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },

      // === PKA (Personal Knowledge Accumulator) Tools ===
      {
        name: "save_insight",
        description: `Save an insight/knowledge to Obsidian vault.
Use this to persist learnings, discoveries, and important information.`,
        inputSchema: {
          type: "object",
          properties: {
            title: {
              type: "string",
              description: "Title of the insight",
            },
            content: {
              type: "string",
              description: "Main content/body",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Tags for categorization",
            },
            source: {
              type: "string",
              enum: ["claude_desktop", "claude_code", "gemini", "user"],
              description: "Source of the insight",
              default: "claude_desktop",
            },
            trustScore: {
              type: "number",
              description: "Trust score 0.0-1.0",
              default: 0.8,
            },
            category: {
              type: "string",
              enum: ["insight", "howto", "decision", "gotcha", "reference"],
              description: "Category type",
              default: "insight",
            },
          },
          required: ["title", "content"],
        },
      },
      {
        name: "save_learning",
        description: `Save a learning with context, example, and gotchas.
Use this when you discover something new worth remembering.`,
        inputSchema: {
          type: "object",
          properties: {
            whatLearned: {
              type: "string",
              description: "What was learned (becomes title)",
            },
            context: {
              type: "string",
              description: "Context/situation where this was learned",
            },
            example: {
              type: "string",
              description: "Concrete example (optional)",
            },
            gotcha: {
              type: "string",
              description: "Warning/gotcha/pitfall (optional)",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Tags for categorization",
            },
          },
          required: ["whatLearned", "context"],
        },
      },
      {
        name: "save_conversation_summary",
        description: `Save a summary of the current conversation.
Use this at the end of productive conversations to capture key points.`,
        inputSchema: {
          type: "object",
          properties: {
            summary: {
              type: "string",
              description: "Brief summary of the conversation",
            },
            keyPoints: {
              type: "array",
              items: { type: "string" },
              description: "Key points discussed",
            },
            decisions: {
              type: "array",
              items: { type: "string" },
              description: "Decisions made",
            },
            nextActions: {
              type: "array",
              items: { type: "string" },
              description: "Next actions/TODOs",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Tags for categorization",
            },
          },
          required: ["summary", "keyPoints"],
        },
      },

      // === Service Check ===
      {
        name: "check_services",
        description: "Check availability of services (LM Studio, file system paths)",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      // === Messaging ===
      case "send_message": {
        const messageId = generateMessageId();
        const threadId = args.thread_id || `thread_${Date.now()}`;

        // Determine target directory
        const targetDir =
          args.to === "code"
            ? config.coordination.messages.desktopToCode
            : config.coordination.messages.codeToDesktop;

        ensureDir(targetDir);

        const message = {
          id: messageId,
          from: args.from,
          to: args.to,
          type: args.type,
          thread_id: threadId,
          content: args.content,
          timestamp: new Date().toISOString(),
          status: "pending",
        };

        const filePath = join(targetDir, `${messageId}.json`);
        writeFileSync(filePath, JSON.stringify(message, null, 2), "utf8");

        // Also append to thread file
        const threadDir = config.coordination.messages.threads;
        ensureDir(threadDir);
        const threadFile = join(threadDir, `${threadId}.json`);

        let thread = { id: threadId, messages: [] };
        if (existsSync(threadFile)) {
          thread = JSON.parse(readFileSync(threadFile, "utf8"));
        }
        thread.messages.push(message);
        writeFileSync(threadFile, JSON.stringify(thread, null, 2), "utf8");

        return {
          content: [
            {
              type: "text",
              text: `Message sent successfully.\nID: ${messageId}\nThread: ${threadId}\nTo: ${args.to}`,
            },
          ],
        };
      }

      case "check_messages": {
        const sourceDir =
          args.for === "code"
            ? config.coordination.messages.desktopToCode
            : config.coordination.messages.codeToDesktop;

        if (!existsSync(sourceDir)) {
          return { content: [{ type: "text", text: "No messages." }] };
        }

        const files = readdirSync(sourceDir).filter((f) => f.endsWith(".json"));
        const messages = [];

        for (const file of files) {
          const filePath = join(sourceDir, file);
          const msg = JSON.parse(readFileSync(filePath, "utf8"));

          // Filter by thread if specified
          if (args.thread_id && msg.thread_id !== args.thread_id) {
            continue;
          }

          // Only include pending messages
          if (msg.status === "pending") {
            messages.push(msg);

            // Mark as read if requested
            if (args.mark_read !== false) {
              msg.status = "read";
              writeFileSync(filePath, JSON.stringify(msg, null, 2), "utf8");
            }
          }
        }

        if (messages.length === 0) {
          return { content: [{ type: "text", text: "No new messages." }] };
        }

        const formatted = messages
          .map(
            (m) =>
              `[${m.type}] ${m.from} -> ${m.to} (${m.timestamp})\nThread: ${m.thread_id}\n${m.content}`
          )
          .join("\n\n---\n\n");

        return {
          content: [
            {
              type: "text",
              text: `**${messages.length} message(s):**\n\n${formatted}`,
            },
          ],
        };
      }

      case "get_thread": {
        const threadFile = join(
          config.coordination.messages.threads,
          `${args.thread_id}.json`
        );

        if (!existsSync(threadFile)) {
          return {
            content: [{ type: "text", text: `Thread ${args.thread_id} not found.` }],
          };
        }

        const thread = JSON.parse(readFileSync(threadFile, "utf8"));
        const formatted = thread.messages
          .map(
            (m) =>
              `[${m.timestamp}] ${m.from} (${m.type}):\n${m.content}`
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `**Thread: ${args.thread_id}** (${thread.messages.length} messages)\n\n${formatted}`,
            },
          ],
        };
      }

      // === Task Box ===
      case "submit_task": {
        const taskId = generateTaskId();
        ensureDir(config.coordination.taskBox);

        const task = {
          id: taskId,
          type: args.type || "development",
          description: args.description,
          priority: args.priority || "medium",
          constraints: args.constraints || {},
          submitted_at: new Date().toISOString(),
          status: "pending",
        };

        const filePath = join(config.coordination.taskBox, `${taskId}.json`);
        writeFileSync(filePath, JSON.stringify(task, null, 2), "utf8");

        return {
          content: [
            {
              type: "text",
              text: `Task submitted successfully.\nID: ${taskId}\nType: ${task.type}\nPriority: ${task.priority}`,
            },
          ],
        };
      }

      case "check_task_result": {
        // 1. Check output_box (legacy format)
        const outputDir = join(config.coordination.outputBox, args.task_id);
        if (existsSync(outputDir)) {
          const reportFile = join(outputDir, "report.json");
          if (existsSync(reportFile)) {
            const report = JSON.parse(readFileSync(reportFile, "utf8"));
            return {
              content: [
                {
                  type: "text",
                  text: `**Task Result: ${args.task_id}**\n\n${JSON.stringify(report, null, 2)}`,
                },
              ],
            };
          }
          const files = readdirSync(outputDir);
          return {
            content: [
              {
                type: "text",
                text: `**Task ${args.task_id} output files:**\n${files.join("\n")}`,
              },
            ],
          };
        }

        // 2. Fallback: check task_box JSON status/result fields
        const taskFile = join(config.coordination.taskBox, `${args.task_id}.json`);
        if (existsSync(taskFile)) {
          const task = JSON.parse(readFileSync(taskFile, "utf8"));
          if (task.status === "completed") {
            return {
              content: [
                {
                  type: "text",
                  text: `**Task Result: ${args.task_id}**\n\nStatus: ${task.status}\nCompleted: ${task.completed_at || "unknown"}\nResult: ${task.result || "(no result field)"}`,
                },
              ],
            };
          }
          return {
            content: [
              {
                type: "text",
                text: `Task ${args.task_id} is still ${task.status}.`,
              },
            ],
          };
        }

        return {
          content: [
            {
              type: "text",
              text: `Task ${args.task_id} not found.`,
            },
          ],
        };
      }

      case "list_tasks": {
        const results = { pending: [], completed: [] };
        const limit = args.limit || 20;

        // Read all tasks from task_box and classify by status field
        if (existsSync(config.coordination.taskBox)) {
          const files = readdirSync(config.coordination.taskBox).filter((f) =>
            f.endsWith(".json")
          );
          for (const file of files) {
            const task = JSON.parse(
              readFileSync(join(config.coordination.taskBox, file), "utf8")
            );
            const entry = {
              id: task.id,
              type: task.type,
              priority: task.priority,
              submitted: task.submitted_at,
              status: task.status,
            };
            if (task.status === "completed") {
              results.completed.push(entry);
            } else {
              results.pending.push(entry);
            }
          }
        }

        // Also include output_box directories as completed (legacy)
        if (existsSync(config.coordination.outputBox)) {
          const dirs = readdirSync(config.coordination.outputBox, {
            withFileTypes: true,
          })
            .filter((d) => d.isDirectory())
            .map((d) => d.name);
          const existingIds = new Set(results.completed.map((t) => t.id));
          for (const dir of dirs) {
            if (!existingIds.has(dir)) {
              results.completed.push({ id: dir });
            }
          }
        }

        // Apply filters and limits
        const filteredPending = args.status !== "completed" ? results.pending.slice(0, limit) : [];
        const filteredCompleted = args.status !== "pending" ? results.completed.slice(0, limit) : [];

        return {
          content: [
            {
              type: "text",
              text: `**Tasks:**\n\nPending (${filteredPending.length}):\n${
                filteredPending.map((t) => `- ${t.id} [${t.priority || "?"}] ${t.type || ""}`).join("\n") ||
                "None"
              }\n\nCompleted (${filteredCompleted.length}):\n${
                filteredCompleted.map((t) => `- ${t.id}`).join("\n") || "None"
              }`,
            },
          ],
        };
      }

      // === LM Studio ===
      case "get_second_opinion": {
        const systemPrompt = args.context
          ? `You are a helpful assistant. Context: ${args.context}`
          : undefined;
        const result = await getSecondOpinion(args.question, {
          model: args.model,
          systemPrompt,
        });
        return {
          content: [
            {
              type: "text",
              text: result.success
                ? `**Model:** ${result.model}\n\n${result.content}`
                : `Error: ${result.error}`,
            },
          ],
        };
      }

      case "get_code_review": {
        const result = await getCodeReview(args.code, args.context);
        return {
          content: [
            {
              type: "text",
              text: result.success
                ? `**Code Review (${result.model}):**\n\n${result.content}`
                : `Error: ${result.error}`,
            },
          ],
        };
      }

      case "list_local_models": {
        const result = await listAvailableModels();
        return {
          content: [
            {
              type: "text",
              text: result.success
                ? `**Available Models:**\n${result.models.map((m) => `- ${m}`).join("\n")}`
                : `Error: ${result.error}`,
            },
          ],
        };
      }

      // === PKA Tools ===
      case "save_insight": {
        const result = await saveInsight({
          title: args.title,
          content: args.content,
          tags: args.tags || [],
          source: args.source || "claude_desktop",
          trustScore: args.trustScore || 0.8,
          category: args.category || "insight",
        });
        return {
          content: [
            {
              type: "text",
              text: result.status === "ok"
                ? `✅ Insight saved to Obsidian!\nFile: ${result.filename}\nPath: ${result.path}`
                : `❌ Error saving insight: ${result.message}`,
            },
          ],
        };
      }

      case "save_learning": {
        const result = await saveLearning({
          whatLearned: args.whatLearned,
          context: args.context,
          example: args.example,
          gotcha: args.gotcha,
          tags: args.tags || [],
        });
        return {
          content: [
            {
              type: "text",
              text: result.status === "ok"
                ? `✅ Learning saved to Obsidian!\nFile: ${result.filename}`
                : `❌ Error saving learning: ${result.message}`,
            },
          ],
        };
      }

      case "save_conversation_summary": {
        const result = await saveConversationSummary({
          summary: args.summary,
          keyPoints: args.keyPoints || [],
          decisions: args.decisions || [],
          nextActions: args.nextActions || [],
          tags: args.tags || [],
        });
        return {
          content: [
            {
              type: "text",
              text: result.status === "ok"
                ? `✅ Conversation summary saved!\nFile: ${result.filename}`
                : `❌ Error saving summary: ${result.message}`,
            },
          ],
        };
      }

      // === Service Check ===
      case "check_services": {
        const lmStudio = await checkLmStudioAvailable();
        const pkaConnected = await checkPkaConnection();
        const pathsExist = {
          taskBox: existsSync(config.coordination.taskBox),
          outputBox: existsSync(config.coordination.outputBox),
          messages: existsSync(config.coordination.messages.desktopToCode),
        };

        return {
          content: [
            {
              type: "text",
              text: `**Service Status:**
- LM Studio: ${lmStudio ? "✅ Available" : "❌ Not available"}
- PKA (Obsidian): ${pkaConnected ? "✅ Connected" : "❌ Not connected"}
- task_box: ${pathsExist.taskBox ? "✅ Exists" : "❌ Missing"}
- output_box: ${pathsExist.outputBox ? "✅ Exists" : "❌ Missing"}
- messages: ${pathsExist.messages ? "✅ Exists" : "❌ Missing"}

**Paths:**
- Base: ${config.coordination.basePath}
- task_box: ${config.coordination.taskBox}
- output_box: ${config.coordination.outputBox}`,
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("AI Task Coordinator MCP server v3.0 (File-based messaging) started");
}

main().catch(console.error);

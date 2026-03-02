/**
 * AI Task Coordinator Configuration
 *
 * v3.1: PKA (Obsidian) integration added
 *
 * All settings can be overridden via environment variables.
 * See .env.example for available options.
 */

import { config as dotenvConfig } from "dotenv";
import { join } from "path";

// Load .env file
dotenvConfig();

// Base path for AI Coordination system
const AI_COORDINATION_BASE =
  process.env.AI_COORDINATION_BASE ||
  "C:/Users/kazin/Desktop/_AI_Coordination/ai_coordination";

export const config = {
  // LM Studio settings
  lmStudio: {
    baseUrl: process.env.LM_STUDIO_URL || "http://100.64.100.6:1234/v1",
    defaultModel: process.env.LM_STUDIO_DEFAULT_MODEL || "qwen/qwen3.5-35b-a3b",
    coderModel: process.env.LM_STUDIO_CODER_MODEL || "qwen/qwen3.5-35b-a3b",
    timeout: parseInt(process.env.LM_STUDIO_TIMEOUT) || 180000,
  },

  // PKA (Obsidian) settings
  pka: {
    apiUrl: process.env.PKA_API_URL || "https://127.0.0.1:27124",
    apiKey: process.env.PKA_API_KEY || "",
    vaultFolder: process.env.PKA_VAULT_FOLDER || "Claude-Desktop",
  },

  // AI Coordination paths (file-based messaging)
  coordination: {
    basePath: AI_COORDINATION_BASE,
    taskBox: join(AI_COORDINATION_BASE, "task_box"),
    outputBox: join(AI_COORDINATION_BASE, "output_box"),
    messages: {
      desktopToCode: join(AI_COORDINATION_BASE, "messages/desktop_to_code"),
      codeToDesktop: join(AI_COORDINATION_BASE, "messages/code_to_desktop"),
      threads: join(AI_COORDINATION_BASE, "messages/threads"),
    },
  },

  // Working directories
  paths: {
    workspace: process.env.WORKSPACE_PATH || process.cwd(),
    resultsDir: process.env.RESULTS_DIR || "./results",
  },

  // Logging
  logging: {
    enabled: process.env.LOG_ENABLED !== "false",
    level: process.env.LOG_LEVEL || "info",
  },
};

export default config;

import { config } from "./config.js";

/**
 * Get a second opinion from LM Studio local LLM
 */
export async function getSecondOpinion(question, options = {}) {
  const {
    model = config.lmStudio.defaultModel,
    systemPrompt = "You are a fast, practical assistant. Be concise and direct. Default: skip internal reasoning unless the user explicitly asks you to think step-by-step. /no_think",
    temperature = 0.7,
    maxTokens = 2048,
    timeout = config.lmStudio.timeout || 120000, // use config timeout
  } = options;

  console.error(`[LM Studio] Calling ${model} with timeout ${timeout}ms`);

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const response = await fetch(`${config.lmStudio.baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: question },
        ],
        temperature,
        max_tokens: maxTokens,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`LM Studio API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.error(`[LM Studio] Success, tokens: ${data.usage?.total_tokens}`);
    
    return {
      success: true,
      model,
      content: data.choices[0]?.message?.content || "",
      usage: data.usage,
    };
  } catch (error) {
    console.error(`[LM Studio] Error: ${error.message}`);
    return {
      success: false,
      model,
      error: error.message,
    };
  }
}

/**
 * Get code review from coding-specialized model
 */
export async function getCodeReview(code, context = "") {
  const systemPrompt = `You are a pragmatic code reviewer. Be concise and actionable. Focus on bugs, risks, and concrete improvements. Skip praise. /no_think`;

  const question = context 
    ? `Context: ${context}\n\nCode to review:\n\`\`\`\n${code}\n\`\`\``
    : `Code to review:\n\`\`\`\n${code}\n\`\`\``;

  return getSecondOpinion(question, {
    model: config.lmStudio.coderModel,
    systemPrompt,
    temperature: 0.3,
    maxTokens: 2048,
    timeout: config.lmStudio.timeout || 180000, // use config timeout for code review
  });
}

/**
 * List available models on LM Studio
 */
export async function listAvailableModels() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    const response = await fetch(`${config.lmStudio.baseUrl}/models`, {
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`LM Studio API error: ${response.status}`);
    }

    const data = await response.json();
    return {
      success: true,
      models: data.data.map((m) => m.id),
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
}

/**
 * Check if LM Studio is available
 */
export async function checkLmStudioAvailable() {
  try {
    const result = await listAvailableModels();
    return result.success;
  } catch {
    return false;
  }
}

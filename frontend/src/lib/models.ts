export interface Model {
  model: string;
  provider: string;
  default?: boolean;
}

export const AVAILABLE_MODELS: Model[] = [
  // OpenAI models
  { provider: "openai", model: "gpt-4o", default: true },
  { provider: "openai", model: "gpt-4o-mini", default: false },
  { provider: "openai", model: "gpt-4-turbo", default: false },
  { provider: "openai", model: "gpt-3.5-turbo", default: false },

  // Anthropic models
  { provider: "anthropic", model: "claude-3-5-sonnet-20241022", default: true },
  { provider: "anthropic", model: "claude-3-5-haiku-20241022", default: false },
  { provider: "anthropic", model: "claude-3-opus-20240229", default: false },

  // Google models
  { provider: "gemini", model: "gemini-1.5-pro", default: true },
  { provider: "gemini", model: "gemini-1.5-flash", default: false },
  { provider: "gemini", model: "gemini-2.0-flash-exp", default: false },

  // Tutorial model
  { provider: "tutorial", model: "tutorial", default: true },
];

export function getDefaultModel(provider: string): Model | undefined {
  return AVAILABLE_MODELS.find((m) => m.provider === provider && m.default);
}

export function getModelsByProvider(provider: string): Model[] {
  return AVAILABLE_MODELS.filter((m) => m.provider === provider);
}

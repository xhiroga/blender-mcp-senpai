export type Provider = "openai" | "anthropic" | "gemini";

export interface Model {
  model: string;
  provider: Provider;
}

export const REGISTERED_MODELS: Model[] = [
  // OpenAI models
  { provider: "openai", model: "gpt-4o" },
  { provider: "openai", model: "gpt-4o-mini" },
  { provider: "openai", model: "gpt-4-turbo" },
  { provider: "openai", model: "gpt-3.5-turbo" },

  // Anthropic models
  { provider: "anthropic", model: "claude-3-5-sonnet-20241022" },
  { provider: "anthropic", model: "claude-3-5-haiku-20241022" },
  { provider: "anthropic", model: "claude-3-opus-20240229" },

  // Google models
  { provider: "gemini", model: "gemini-1.5-pro" },
  { provider: "gemini", model: "gemini-1.5-flash" },
  { provider: "gemini", model: "gemini-2.0-flash-exp" },
];

export const DEFAULT_MODELS: Record<Provider, string> = {
  openai: "gpt-4o",
  anthropic: "claude-3-5-sonnet-20241022",
  gemini: "gemini-1.5-pro",
};

export function getDefaultModel(provider: Provider): Model | undefined {
  return REGISTERED_MODELS.find((m) => m.provider === provider);
}

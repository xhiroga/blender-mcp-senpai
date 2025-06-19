"use client";

import { AVAILABLE_MODELS } from "@/lib/models";
import { AnthropicProvider, createAnthropic } from "@ai-sdk/anthropic";
import { createGoogleGenerativeAI, GoogleGenerativeAIProvider } from "@ai-sdk/google";
import { createOpenAI, OpenAIProvider } from "@ai-sdk/openai";
import { useChat } from "@ai-sdk/react";
import {
  AssistantRuntimeProvider,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
} from "@assistant-ui/react";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp";
import type { LanguageModelV1, Tool } from "ai";
import {
  experimental_createMCPClient as createMCPClient,
  streamText,
} from "ai";
import { useCallback, useEffect, useState } from "react";
import { ModelIcon } from "./model-icon";

interface Tools {
  [key: string]: Tool;
}

interface ApiKey {
  apiKey: string;
}

interface ApiKeys {
  [provider: string]: ApiKey;
}

interface Providers {
  openai: OpenAIProvider | undefined;
  anthropic: AnthropicProvider | undefined;
  gemini: GoogleGenerativeAIProvider | undefined;
}

const mcpClient = await createMCPClient({
  transport: new StreamableHTTPClientTransport({
    url: `${window.location.origin}/mcp/mcp`,
  }),  
});  

export function SimpleChat() {
  const [mcpTools, setMcpTools] = useState<Tools>({});
  const [languageModel, setLanguageModel] = useState<LanguageModelV1 | undefined>(undefined);
  const [showSettings, setShowSettings] = useState(false);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [apiKeyInputs, setApiKeyInputs] = useState({
    openai: "",
    anthropic: "",
    gemini: "",
  });
  const [apiKeys, setApiKeys] = useState<ApiKeys>({
    openai: { apiKey: "" },
    anthropic: { apiKey: "" },
    gemini: { apiKey: "" },
  });
  const [availableModels, setAvailableModels] = useState<
    typeof AVAILABLE_MODELS
  >([]);
  const [providers, setProviders] = useState<Providers>({
    openai: undefined,
    anthropic: undefined,
    gemini: undefined,
  });


  useEffect(() => {
    const loadTools = async () => {
      const tools = await mcpClient.tools();
      setMcpTools(tools);
    };
    loadTools();
  }, []);

  useEffect(() => {  
    const loadApiKeys = async () => {
      try {
        const response = await fetch("/api/api-keys");
        if (response.ok) {
          const data = await response.json();
          console.log("Loaded API keys from backend:", data);
          const transformedData: ApiKeys = {};
          for (const [provider, state] of Object.entries(data)) {
            transformedData[provider] = {
              apiKey: (state as { api_key: string }).api_key || "",
            };
          }

          setApiKeys(transformedData);
        }
      } catch (error) {
        console.error("Error loading API keys:", error);
      }
    };
    loadApiKeys();
  }, []);

  useEffect(() => {
    const newProviders: Providers = {
      openai: undefined,
      anthropic: undefined,
      gemini: undefined,
    };

    if (apiKeys.openai?.apiKey) {
      newProviders.openai = createOpenAI({ apiKey: apiKeys.openai.apiKey });
    }
    if (apiKeys.anthropic?.apiKey) {
      newProviders.anthropic = createAnthropic({ apiKey: apiKeys.anthropic.apiKey });
    }
    if (apiKeys.gemini?.apiKey) {
      newProviders.gemini = createGoogleGenerativeAI({ apiKey: apiKeys.gemini.apiKey });
    }

    setProviders(newProviders);
  }, [apiKeys]);

  useEffect(() => {
    const updateAvailableModels = () => {
      const available = AVAILABLE_MODELS.filter((model) => {
        const hasApiKey = apiKeys[model.provider]?.apiKey;
        return hasApiKey && hasApiKey.length > 0;
      });

      console.log(
        "Available models updated:",
        available.map((m) => `${m.provider}:${m.model}`)
      );
      setAvailableModels(available);

      // Update current selection if current model is not available
      const currentModelAvailable = available.some(
        (m) =>
          m.provider === selectedModel.provider &&
          m.model === selectedModel.model
      );

      if (!currentModelAvailable && available.length > 0) {
        const firstAvailable = available[0];
        console.log(
          "Current model not available, switching to:",
          firstAvailable
        );
        setSelectedModel({
          provider: firstAvailable.provider,
          model: firstAvailable.model,
        });
      }
    };

    updateAvailableModels();
  }, [apiKeys, selectedModel.provider, selectedModel.model]);

  useEffect(() => {
    // Close dropdowns when clicking outside
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      // Check if click is outside of model selector
      if (!target.closest("[data-model-selector]")) {
        setShowModelSelector(false);
      }
    };

    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  type FetchFunction = typeof globalThis.fetch;
  const customFetch = useCallback<FetchFunction>(
    async (input, init) => {
      if (init?.body === undefined) {
        return new Response("No body provided", { status: 400 });
      }

      const m = JSON.parse(init.body as string) as any;
      console.log(m);

      const result = await streamText({
        model: languageModel!,
        tools: mcpTools,
        messages: m.messages,
      });

      return result.toDataStreamResponse();
    },
    [languageModel, mcpTools]
  );

  // Workaround for static hosting. See <https://github.com/vercel/ai/issues/5140>
  const { messages, input, handleInputChange, handleSubmit } = useChat({
    fetch: customFetch,
  });

  const handleSelectModel = useCallback((provider: string, model: string) => {
    if (provider in providers) {
      const providerInstance = providers[provider as keyof Providers];
      if (providerInstance) {
        setLanguageModel(providerInstance(model));
        setShowModelSelector(false);
        return;
      }
    }
  }, [providers]);

  const handleSaveApiKey = async (provider: string) => {
    try {
      const apiKey = apiKeyInputs[provider as keyof typeof apiKeyInputs];
      if (!apiKey) {
        alert("Please enter an API key");
        return;
      }

      const response = await fetch(`/api/api-keys/${provider}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ api_key: apiKey }),
      });

      // TODO: API Key Validation

      const result = await response.json();
      if (response.ok) {
        setApiKeys((prev) => ({
          ...prev,
          [provider]: { apiKey },
        }));

        // Clear input
        setApiKeyInputs((prev) => ({ ...prev, [provider]: "" }));

        alert("API key saved successfully!");
      } else {
        throw new Error(result.message);
      }
    } catch (error) {
      console.error("Error saving API key:", error);
      alert(
        `Failed to save API key: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  };

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Model Selector */}
            <div className="relative" data-model-selector>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  console.log(
                    "🔄 Model selector clicked, current state:",
                    showModelSelector
                  );
                  setShowModelSelector(!showModelSelector);
                }}
                className="flex items-center gap-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-medium border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors min-w-48"
              >
                <ModelIcon provider={selectedModel.provider} />
                <span>{selectedModel.model}</span>
                <svg
                  className="w-4 h-4 text-gray-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {/* Model selector dropdown */}
              {showModelSelector && (
                <div className="absolute top-full left-0 mt-1 w-64 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg z-10 max-h-60 overflow-y-auto">
                  {["openai", "anthropic", "gemini"].map((provider) => (
                    <div key={provider} className="p-2">
                      <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1 px-2">
                        {provider}
                      </div>
                      {AVAILABLE_MODELS.filter(
                        (m) => m.provider === provider
                      ).map((modelObj) => {
                        const isAvailable = availableModels.some(
                          (availableModel) =>
                            availableModel.provider === provider &&
                            availableModel.model === modelObj.model
                        );

                        return (
                          <button
                            key={`${provider}-${modelObj.model}`}
                            onClick={() => {
                              if (isAvailable) {
                                handleSelectModel(
                                  provider,
                                  modelObj.model
                                );
                              }
                            }}
                            disabled={!isAvailable}
                            className={`w-full text-left px-2 py-1.5 text-sm rounded-md flex items-center gap-2 ${
                              isAvailable
                                ? "text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                                : "text-gray-400 dark:text-gray-600 cursor-not-allowed"
                            }`}
                          >
                            <div className={isAvailable ? "" : "opacity-50"}>
                              <ModelIcon provider={provider} />
                            </div>
                            <span>{modelObj.model}</span>
                            {!isAvailable && (
                              <span className="ml-auto text-xs text-gray-400 dark:text-gray-600">
                                No API key
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Settings Button */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  console.log("⚙️ Settings button clicked");
                  setShowSettings(true);
                }}
                className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
              </button>
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">U</span>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Area with Assistant UI */}
        <div className="flex-1 relative">
          {Object.keys(mcpTools).length > 0 ? (
            <AssistantRuntimeProvider runtime={runtime}>
              <ThreadPrimitive.Root className="h-full flex flex-col">
                {/* Messages */}
                <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto">
                  <div className="max-w-3xl mx-auto px-4">
                    <ThreadPrimitive.Messages
                      components={{
                        UserMessage: () => (
                          <div className="flex justify-end mb-6">
                            <div className="flex gap-3 max-w-2xl">
                              <div className="flex-shrink-0">
                                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                                  <span className="text-white text-sm font-medium">
                                    U
                                  </span>
                                </div>
                              </div>
                              <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-3">
                                <MessagePrimitive.Content />
                              </div>
                            </div>
                          </div>
                        ),
                        AssistantMessage: () => (
                          <div className="flex justify-start mb-6">
                            <div className="flex gap-3 max-w-2xl">
                              <div className="flex-shrink-0">
                                <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                                  <span className="text-white text-sm font-medium">
                                    A
                                  </span>
                                </div>
                              </div>
                              <div className="bg-white dark:bg-gray-800 rounded-lg px-4 py-3 border border-gray-200 dark:border-gray-600">
                                <MessagePrimitive.Content />
                              </div>
                            </div>
                          </div>
                        ),
                      }}
                    />

                    {/* Welcome message when no messages */}
                    <ThreadPrimitive.Empty>
                      <div className="text-center py-8">
                        <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mx-auto mb-4">
                          <svg
                            className="w-6 h-6 text-blue-600 dark:text-blue-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                            />
                          </svg>
                        </div>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                          How can I help you today?
                        </h2>
                        <p className="text-gray-600 dark:text-gray-400">
                          Start a conversation with your AI assistant
                        </p>
                      </div>
                    </ThreadPrimitive.Empty>
                  </div>
                </ThreadPrimitive.Viewport>

                {/* Input */}
                <div className="border-t border-gray-200 dark:border-gray-700 p-4">
                  <div className="max-w-3xl mx-auto">
                    <ComposerPrimitive.Root>
                      <div className="relative flex items-end gap-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 p-3">
                        <ComposerPrimitive.Input
                          placeholder="Message assistant..."
                          className="flex-1 bg-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 resize-none focus:outline-none min-h-[24px] max-h-32"
                          autoFocus
                        />
                        <ComposerPrimitive.Send className="flex-shrink-0 p-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white rounded-lg transition-colors disabled:cursor-not-allowed">
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                            />
                          </svg>
                        </ComposerPrimitive.Send>
                      </div>
                    </ComposerPrimitive.Root>
                  </div>
                </div>
              </ThreadPrimitive.Root>
            </AssistantRuntimeProvider>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-600 dark:text-gray-400">
                  Loading MCP tools...
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-gray-900/50 backdrop-blur-sm"
            onClick={() => setShowSettings(false)}
          />
          <div className="relative bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Settings
              </h2>
              <button
                onClick={() => setShowSettings(false)}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-6">
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">
                  API Keys
                </h3>
                <div className="space-y-4">
                  {["openai", "anthropic", "gemini"].map((provider) => (
                    <div key={provider} className="space-y-2">
                      <label className="block text-sm text-gray-700 dark:text-gray-300 font-medium capitalize">
                        {provider} API Key
                        {apiKeys[provider]?.apiKey && (
                          <span className="ml-2 text-xs text-green-600 dark:text-green-400">
                            ✓ Configured
                          </span>
                        )}
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="password"
                          value={
                            apiKeyInputs[provider as keyof typeof apiKeyInputs]
                          }
                          onChange={(e) =>
                            setApiKeyInputs((prev) => ({
                              ...prev,
                              [provider]: e.target.value,
                            }))
                          }
                          placeholder={
                            apiKeys[provider]?.apiKey
                              ? "********************"
                              : `Enter ${provider} API key`
                          }
                          className="flex-1 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <button
                          onClick={() => handleSaveApiKey(provider)}
                          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-md transition-colors"
                        >
                          Save
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

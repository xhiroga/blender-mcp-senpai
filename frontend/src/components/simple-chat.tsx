"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  AssistantRuntimeProvider,
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
} from "@assistant-ui/react";
import { useDangerousInBrowserRuntime } from "@assistant-ui/react-edge";
import { AVAILABLE_MODELS } from "@/lib/models";
import Image from "next/image";
import type { Tool as AITool } from "ai";

const convertMCPToolsToAssistantUI = (mcpTools: Record<string, AITool>) => {
  console.log("🔧 Converting MCP tools, input:", mcpTools);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const convertedTools: Record<string, any> = {};

  for (const [name, tool] of Object.entries(mcpTools)) {
    console.log(`🔧 Converting tool ${name}:`, tool);
    convertedTools[name] = {
      type: "function",
      description: tool.description || "",
      parameters: tool.parameters,
      execute: tool.execute,
    };
    console.log(`🔧 Converted tool ${name}:`, convertedTools[name]);
  }

  console.log("🔧 Final converted tools:", convertedTools);
  return convertedTools;
};

// Helper function to get model icon components
const getModelIcon = (provider: string) => {
  const iconClass = "w-5 h-5";

  switch (provider) {
    case "openai":
      return (
        <Image
          src="/openai.svg"
          alt="OpenAI"
          width={20}
          height={20}
          className={iconClass}
        />
      );
    case "anthropic":
      return (
        <Image
          src="/anthropic.svg"
          alt="Anthropic"
          width={20}
          height={20}
          className={iconClass}
        />
      );
    case "gemini":
      return (
        <Image
          src="/google.svg"
          alt="Google"
          width={20}
          height={20}
          className={iconClass}
        />
      );
    case "tutorial":
      return <span className="text-lg">📚</span>;
    default:
      return <span className="text-lg">🤖</span>;
  }
};

interface Settings {
  provider: string;
  model: string;
}

interface ApiKeyState {
  apiKey: string;
}

export function SimpleChat() {
  const [settings, setSettings] = useState<Settings>({
    provider: "openai",
    model: "gpt-4o",
  });
  const [showSettings, setShowSettings] = useState(false);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [apiKeyInputs, setApiKeyInputs] = useState({
    openai: "",
    anthropic: "",
    gemini: "",
  });
  const [apiKeys, setApiKeys] = useState<{
    [key: string]: ApiKeyState;
  }>({
    openai: { apiKey: "" },
    anthropic: { apiKey: "" },
    gemini: { apiKey: "" },
  });
  const [mcpTools, setMcpTools] = useState<Record<string, AITool>>({});

  const getApiKey = useCallback(
    (provider: string): string => {
      return apiKeys[provider]?.apiKey || "";
    },
    [apiKeys]
  );

  // Intercept fetch to log LLM requests
  useEffect(() => {
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const [url, options] = args;

      // Check if this is an LLM API call
      if (
        typeof url === "string" &&
        (url.includes("openai.com") ||
          url.includes("anthropic.com") ||
          url.includes("googleapis.com"))
      ) {
        console.log("📡 LLM API Request:", url);
        console.log("📡 Request options:", options);

        if (options?.body) {
          try {
            const body = JSON.parse(options.body as string);
            console.log("📡 Request body:", body);
            console.log(
              "📡 Tools in request:",
              body.tools ? Object.keys(body.tools) : "No tools"
            );
          } catch (error) {
            console.log("📡 Request body (raw):", options.body);
            console.log("📡 JSON parse error:", error);
          }
        }
      }

      const response = await originalFetch(...args);

      if (
        typeof url === "string" &&
        (url.includes("openai.com") ||
          url.includes("anthropic.com") ||
          url.includes("googleapis.com"))
      ) {
        console.log("📡 LLM API Response status:", response.status);
      }

      return response;
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  // Load MCP tools on component mount
  useEffect(() => {
    const loadMcpTools = async () => {
      try {
        console.log("🔍 Starting MCP client creation...");
        const { experimental_createMCPClient } = await import("ai");
        console.log("🔍 MCP client import successful");

        const mcpClient = await experimental_createMCPClient({
          transport: {
            type: "sse",
            url: `${window.location.origin}/sse`,
          },
        });
        console.log("🔍 MCP client created successfully:", mcpClient);

        const tools = await mcpClient.tools();
        console.log("🛠️ MCP Tools loaded for AI:", Object.keys(tools));
        console.log("🔍 Full MCP tools data:", tools);
        setMcpTools(tools);
      } catch (error) {
        console.error("❌ Failed to load MCP tools:", error);
        setMcpTools({});
      }
    };

    loadMcpTools();
  }, []);

  // MCP Tools integration with useDangerousInBrowserRuntime
  const runtime = useDangerousInBrowserRuntime(
    useMemo(() => {
      console.log("🚀 Creating runtime with mcpTools:", Object.keys(mcpTools));
      return {
        model: async () => {
          console.log(
            "🤖 Model function called with provider:",
            settings.provider,
            "model:",
            settings.model
          );
          
          const apiKey = getApiKey(settings.provider);
          if (!apiKey) {
            throw new Error(`API key not configured for provider: ${settings.provider}`);
          }

          // Import AI SDK modules dynamically
          let createProvider;

          switch (settings.provider) {
            case "openai":
              const { createOpenAI } = await import("@ai-sdk/openai");
              createProvider = () => createOpenAI({ apiKey });
              break;
            case "anthropic":
              const { createAnthropic } = await import("@ai-sdk/anthropic");
              createProvider = () => createAnthropic({ apiKey });
              break;
            case "gemini":
              const { createGoogleGenerativeAI } = await import(
                "@ai-sdk/google"
              );
              createProvider = () => createGoogleGenerativeAI({ apiKey });
              break;
            default:
              throw new Error("Unsupported provider");
          }

          const provider = createProvider();
          const model = provider(settings.model);
          console.log("🤖 Model created:", model);
          return model;
        },
        tools: (() => {
          const convertedTools = convertMCPToolsToAssistantUI(mcpTools);
          console.log(
            "🔧 Converted tools for runtime:",
            Object.keys(convertedTools)
          );
          console.log("🔧 Tools being passed to runtime:", convertedTools);
          return convertedTools;
        })(),
        temperature: 0.7,
        maxSteps: 5,
      };
    }, [settings.provider, settings.model, mcpTools, getApiKey])
  );

  useEffect(() => {
    const loadApiKeys = async () => {
      try {
        const response = await fetch("/api/api-keys");
        if (response.ok) {
          const data = await response.json();
          console.log("Loaded API keys from backend:", data);
          
          const transformedData: { [key: string]: ApiKeyState } = {};
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

  const handleProviderModelChange = (provider: string, model: string) => {
    setSettings((prev) => ({
      ...prev,
      provider: provider as "openai" | "anthropic" | "gemini",
      model,
    }));
    setShowModelSelector(false);
  };

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
        // Update local state
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
                {getModelIcon(settings.provider)}
                <span>{settings.model}</span>
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
                      ).map((modelObj) => (
                        <button
                          key={`${provider}-${modelObj.model}`}
                          onClick={() =>
                            handleProviderModelChange(provider, modelObj.model)
                          }
                          className="w-full text-left px-2 py-1.5 text-sm text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md flex items-center gap-2"
                        >
                          {getModelIcon(provider)}
                          <span>{modelObj.model}</span>
                        </button>
                      ))}
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

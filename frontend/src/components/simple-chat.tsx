"use client";

import { REGISTERED_MODELS, Model, DEFAULT_MODELS, Provider } from "@/lib/models";
import { AnthropicProvider, createAnthropic } from "@ai-sdk/anthropic";
import { createGoogleGenerativeAI, GoogleGenerativeAIProvider } from "@ai-sdk/google";
import { createOpenAI, OpenAIProvider } from "@ai-sdk/openai";
import { useChat } from "@ai-sdk/react";
import type { LanguageModelV1, Tool } from "ai";
import {
  experimental_createMCPClient as createMCPClient,
  generateText,
  streamText,
} from "ai";
import { useCallback, useEffect, useState } from "react";
import { ModelIcon } from "./model-icon";

interface Tools {
  [key: string]: Tool;
}

interface ApiKeys {
  openai: string;
  anthropic: string;
  gemini: string;
}

interface ApiKeysResponse {
  openai: { api_key: string };
  anthropic: { api_key: string };
  gemini: { api_key: string };
}

interface Providers {
  openai: OpenAIProvider | undefined;
  anthropic: AnthropicProvider | undefined;
  gemini: GoogleGenerativeAIProvider | undefined;
}

interface Toast {
  id: string;
  message: string;
  type: "error" | "warning" | "info";
}

// MCPクライアントの作成（エラーハンドリング付き）
let mcpClient: any = null;
try {
  // ブラウザ環境でのみ実行
  if (typeof window !== "undefined") {
    mcpClient = await createMCPClient({
      transport: {
        type: "sse",
        url: `${window.location.origin}/mcp/mcp`,
      },
    });
  }
} catch (error) {
  console.error("Failed to create MCP client:", error);
}

export function SimpleChat() {
  const [mcpTools, setMcpTools] = useState<Tools>({});
  const [languageModel, setLanguageModel] = useState<LanguageModelV1 | undefined>(undefined);
  const [showSettings, setShowSettings] = useState(false);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [apiKeyInputs, setApiKeyInputs] = useState({
    openai: "",
    anthropic: "",
    gemini: "",
  });
  const [apiKeys, setApiKeys] = useState<ApiKeys>({
    openai: "",
    anthropic: "",
    gemini: "",
  });
  const [availableModels, setAvailableModels] = useState<Model[]>([]);
  const [providers, setProviders] = useState<Providers>({
    openai: undefined,
    anthropic: undefined,
    gemini: undefined,
  });

  const showToast = useCallback((message: string, type: "error" | "warning" | "info" = "error") => {
    const id = Date.now().toString();
    switch (type) {
      case "error":
        console.error(message);
      case "warning":
        console.warn(message);
      case "info":
        console.info(message);
    }
    setToasts(prev => [...prev, { id, message, type }]);
    
    setTimeout(() => {
      setToasts(prev => prev.filter(error => error.id !== id));
    }, 5000);
  }, [setToasts]);

  const removeError = useCallback((id: string) => {
    setToasts(prev => prev.filter(error => error.id !== id));
  }, []);

  useEffect(() => {
    const loadTools = async () => {
      if (!mcpClient) {
        showToast("MCPクライアントの初期化に失敗しました", "error");
        return;
      }

      try {
        const tools = await mcpClient.tools();
        setMcpTools(tools);
      } catch (error) {
        console.error("Error loading MCP tools:", error);
        showToast("MCPツールの読み込みに失敗しました", "error");
      }
    };
    loadTools();
  }, [showToast]);

  useEffect(() => {  
    const loadApiKeys = async () => {
      try {
        const response = await fetch("/api/api-keys");
        if (response.ok) {
          const data: ApiKeysResponse = await response.json();
          const apiKeys: ApiKeys = {
            openai: data.openai.api_key,
            anthropic: data.anthropic.api_key,
            gemini: data.gemini.api_key,
          };

          setApiKeys(apiKeys);
          setApiKeyInputs(apiKeys);
          console.log("Loaded API keys from backend.");
        } else {
          showToast(`Failed to load API keys from backend: ${response.statusText}`, "warning");
        }
      } catch (error) {
        showToast(`Failed to load API keys from backend: ${error}`, "error");
      }
    };
    loadApiKeys();
  }, [showToast]);

  useEffect(() => {
    const updateAvailableModels = () => {
      const availableProviderKeys = Object.keys(providers).filter(key => providers[key as keyof Providers] !== undefined);
      const availableModels: Model[] = REGISTERED_MODELS.filter(m => availableProviderKeys.includes(m.provider));
      setAvailableModels(availableModels);
    };
    updateAvailableModels();
  }, [providers]);

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

  const handleVerifyApiKey = useCallback(async (providerName: string) => {
    try {
      if (!["openai", "anthropic", "gemini"].includes(providerName)) {
        showToast(`Invalid provider: ${providerName}`, "error");
        return;
      }

      const apiKey = apiKeyInputs[providerName as Provider];
      if (!apiKey) {
        showToast(`API key for ${providerName} is empty`, "warning");
        return;
      } else if (apiKey === apiKeys[providerName as keyof ApiKeys]) {
        showToast(`API key for ${providerName} is not changed`, "info");
        return;
      }

      let provider: OpenAIProvider | AnthropicProvider | GoogleGenerativeAIProvider;
      switch (providerName as Provider) {
        case "openai":
          provider = createOpenAI({ apiKey: apiKey });
          break;
        case "anthropic":
          provider = createAnthropic({ apiKey: apiKey });
          break;
        case "gemini":
          provider = createGoogleGenerativeAI({ apiKey: apiKey });
          break;
      }

      const model = provider.languageModel(DEFAULT_MODELS[providerName as Provider]);
      const {text} = await generateText({
        model: model,
        messages: [{ role: "user", content: "Hello!" }],
      });
      console.log(`${providerName} API key is valid! Model says: ${text}`);

      const updatedApiKeys = {
        ...apiKeys,
        [providerName]: { apiKey },
      };
      setApiKeys(updatedApiKeys);

      const updatedProviders = {
        ...providers,
        [providerName as Provider]: provider,
      };
      setProviders(updatedProviders);

      const response = await fetch(`/api/api-keys/${providerName}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ api_key: apiKey }),
      });

      if (response.ok) {
        showToast(`API key for ${providerName} is saved`, "info");
      } else {
        showToast(`Failed to save API key for ${providerName}: ${response.statusText}`, "error");
      }
    } catch (error) {
      showToast(`Failed to save API key for ${providerName}: ${error}`, "error");
    }
  }, [apiKeyInputs, apiKeys, setApiKeys, providers, setProviders, showToast]);

  const handleSelectModel = useCallback((provider: string, model: string) => {
    if (provider === "openai" && providers.openai) {
      try {
        const newLanguageModel = providers.openai(model);
        setLanguageModel(newLanguageModel);
        setShowModelSelector(false);
        showToast(`モデルを ${model} に変更しました`, "info");
        return;
      } catch (error) {
        showToast(`モデルの変更に失敗しました: ${error}`, "error");
        return;
      }
    }
    
    if (provider === "anthropic" && providers.anthropic) {
      try {
        const newLanguageModel = providers.anthropic(model);
        setLanguageModel(newLanguageModel);
        setSelectedModel({
          provider: "anthropic",
          model,
        });
        setShowModelSelector(false);
        showToast(`モデルを ${model} に変更しました`, "info");
        return;
      } catch (error) {
        showToast(`モデルの変更に失敗しました: ${error}`, "error");
        return;
      }
    }
    
    if (provider === "gemini" && providers.gemini) {
      try {
        const newLanguageModel = providers.gemini(model);
        setLanguageModel(newLanguageModel);
        setSelectedModel({
          provider: "gemini",
          model,
        });
        setShowModelSelector(false);
        showToast(`モデルを ${model} に変更しました`, "info");
        return;
      } catch (error) {
        showToast(`モデルの変更に失敗しました: ${error}`, "error");
        return;
      }
    }
    
    showToast("選択されたプロバイダーが利用できません", "error");
  }, [providers, showToast]);


  type FetchFunction = typeof globalThis.fetch;
  const customFetch = useCallback<FetchFunction>(
    async (input, init) => {
      if (init?.body === undefined) {
        showToast("リクエストボディが提供されていません", "error");
        return new Response("No body provided", { status: 400 });
      }

      if (!languageModel) {
        showToast("言語モデルが選択されていません", "error");
        return new Response("No language model selected", { status: 400 });
      }

      try {
        const m = JSON.parse(init.body as string) as any;
        console.log(m);

        const result = await streamText({
          model: languageModel,
          tools: mcpTools,
          messages: m.messages,
        });

        return result.toDataStreamResponse();
      } catch (error) {
        console.error("Error in customFetch:", error);
        showToast("チャットリクエストの処理中にエラーが発生しました", "error");
        return new Response("Internal server error", { status: 500 });
      }
    },
    [languageModel, mcpTools, showToast]
  );

  // Workaround for static hosting. See <https://github.com/vercel/ai/issues/5140>
  const { messages, input, handleInputChange, handleSubmit } = useChat({
    fetch: customFetch,
  });

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900">
      {/* Error Toast Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((error) => (
          <div
            key={error.id}
            className={`flex items-center gap-3 p-4 rounded-lg shadow-lg max-w-sm transition-all duration-300 ${
              error.type === "error"
                ? "bg-red-500 text-white"
                : error.type === "warning"
                ? "bg-yellow-500 text-white"
                : "bg-blue-500 text-white"
            }`}
          >
            <div className="flex-shrink-0">
              {error.type === "error" && (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
              {error.type === "warning" && (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              )}
              {error.type === "info" && (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <div className="flex-1 text-sm">{error.message}</div>
            <button
              onClick={() => removeError(error.id)}
              className="flex-shrink-0 text-white/80 hover:text-white"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        ))}
      </div>

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
                      {REGISTERED_MODELS.filter(
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
            <div className="h-full flex flex-col">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto">
                <div className="max-w-3xl mx-auto px-4">
                  {messages.length === 0 ? (
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
                  ) : (
                    messages.map((message, index) => (
                      <div
                        key={index}
                        className={`flex mb-6 ${
                          message.role === "user" ? "justify-end" : "justify-start"
                        }`}
                      >
                        <div className="flex gap-3 max-w-2xl">
                          <div className="flex-shrink-0">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                              message.role === "user" ? "bg-blue-500" : "bg-green-500"
                            }`}>
                              <span className="text-white text-sm font-medium">
                                {message.role === "user" ? "U" : "A"}
                              </span>
                            </div>
                          </div>
                          <div className={`rounded-lg px-4 py-3 ${
                            message.role === "user" 
                              ? "bg-gray-100 dark:bg-gray-700" 
                              : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600"
                          }`}>
                            <div className="text-gray-900 dark:text-white">
                              {message.content}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Input */}
              <div className="border-t border-gray-200 dark:border-gray-700 p-4">
                <div className="max-w-3xl mx-auto">
                  <form onSubmit={handleSubmit} className="relative flex items-end gap-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 p-3">
                    <textarea
                      value={input}
                      onChange={handleInputChange}
                      placeholder="Message assistant..."
                      className="flex-1 bg-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 resize-none focus:outline-none min-h-[24px] max-h-32"
                      autoFocus
                    />
                    <button
                      type="submit"
                      disabled={!input.trim()}
                      className="flex-shrink-0 p-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white rounded-lg transition-colors disabled:cursor-not-allowed"
                    >
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
                    </button>
                  </form>
                </div>
              </div>
            </div>
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
                          onClick={() => handleVerifyApiKey(provider)}
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

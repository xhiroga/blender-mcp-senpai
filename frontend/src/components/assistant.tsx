"use client";

import { useState, useEffect, useCallback } from "react";
import { AssistantRuntimeProvider, ThreadPrimitive, ComposerPrimitive, MessagePrimitive } from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { AVAILABLE_MODELS } from "@/lib/models";

interface Settings {
  provider: string;
  apiKey: string;
  model: string;
}

export function Assistant() {
  const [settings, setSettings] = useState<Settings>({
    provider: "openai",
    apiKey: "",
    model: "gpt-4o"
  });
  const [showSettings, setShowSettings] = useState(false);
  const [apiKeyInputs, setApiKeyInputs] = useState({
    openai: "",
    anthropic: "",
    gemini: ""
  });

  const getApiKey = useCallback((provider: string): string => {
    if (typeof window === 'undefined') return "";
    
    const keys = JSON.parse(localStorage.getItem("blender-senpai-api-keys") || "{}");
    return keys[provider] || "";
  }, []);

  // Assistant-UI Runtime setup
  // WORKAROUND: Using API route to enable AI SDK in static export
  // See: https://github.com/vercel/ai/issues/5140
  // In a normal Next.js app, you would use useChat() directly with server-side API keys
  // But for static export, we pass the API key from client and use an API route handler
  const runtime = useChatRuntime({
    api: "/api/chat",
    body: {
      provider: settings.provider,
      model: settings.model,
      apiKey: getApiKey(settings.provider), // WARNING: Passing API key from client side
    },
  });

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;
    
    // Load settings from localStorage
    const savedSettings = localStorage.getItem("blender-senpai-settings");
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }
    
    // Load API keys to input state
    const savedKeys = JSON.parse(localStorage.getItem("blender-senpai-api-keys") || "{}");
    setApiKeyInputs({
      openai: savedKeys.openai || "",
      anthropic: savedKeys.anthropic || "",
      gemini: savedKeys.gemini || ""
    });
  }, []);

  const saveSettings = useCallback((newSettings: Settings) => {
    setSettings(newSettings);
    if (typeof window !== 'undefined') {
      localStorage.setItem("blender-senpai-settings", JSON.stringify(newSettings));
    }
  }, []);

  const saveApiKey = async (provider: string, apiKey: string) => {
    if (typeof window === 'undefined') return;
    
    if (!apiKey.trim()) {
      // Just remove the key if empty
      const keys = JSON.parse(localStorage.getItem("blender-senpai-api-keys") || "{}");
      delete keys[provider];
      localStorage.setItem("blender-senpai-api-keys", JSON.stringify(keys));
      return;
    }

    try {
      // First, test API key by making a small request
      const { createOpenAI } = await import("@ai-sdk/openai");
      const { createAnthropic } = await import("@ai-sdk/anthropic");
      const { createGoogleGenerativeAI } = await import("@ai-sdk/google");
      const { streamText } = await import("ai");

      let testModel;
      let aiProvider;

      switch (provider) {
        case "openai":
          aiProvider = createOpenAI({ apiKey });
          testModel = aiProvider("gpt-4o-mini");
          break;
        case "anthropic":
          aiProvider = createAnthropic({ apiKey });
          testModel = aiProvider("claude-3-5-haiku-20241022");
          break;
        case "gemini":
          aiProvider = createGoogleGenerativeAI({ apiKey });
          testModel = aiProvider("gemini-1.5-flash");
          break;
        default:
          throw new Error(`Unsupported provider: ${provider}`);
      }

      // Test with a simple completion
      const stream = await streamText({
        model: testModel,
        messages: [{ role: "user", content: "Hi" }],
        maxTokens: 5,
      });

      // Consume the stream to test the connection
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for await (const _chunk of stream.textStream) {
        // Just testing, don't need to do anything with the response
        break;
      }

      // If test succeeds, save to backend
      const response = await fetch('/api/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider,
          api_key: apiKey,
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        // Also save to localStorage for frontend use
        const keys = JSON.parse(localStorage.getItem("blender-senpai-api-keys") || "{}");
        keys[provider] = apiKey;
        localStorage.setItem("blender-senpai-api-keys", JSON.stringify(keys));
        
        // Update settings with new API key
        if (settings.provider === provider) {
          saveSettings({ ...settings, apiKey });
        }
        
        alert("API key verified and saved successfully!");
      } else {
        throw new Error(result.message);
      }
    } catch (error) {
      console.error('Error verifying API key:', error);
      alert(`API Key verification failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900">
      {/* Sidebar - Thread List */}
      <div className="w-64 bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <button className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New chat
          </button>
        </div>

        {/* Thread List */}
        <div className="flex-1 overflow-y-auto p-2">
          <div className="space-y-1">
            <div className="p-3 text-sm text-gray-600 dark:text-gray-400 rounded-lg bg-gray-100 dark:bg-gray-700">
              Current conversation
            </div>
          </div>
        </div>

        {/* Settings Toggle */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="w-full flex items-center gap-3 px-3 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="flex items-center justify-center">
            <select 
              value={JSON.stringify({ model: settings.model, provider: settings.provider })}
              onChange={(e) => {
                const selected = JSON.parse(e.target.value);
                saveSettings({ 
                  ...settings, 
                  model: selected.model, 
                  provider: selected.provider,
                  apiKey: getApiKey(selected.provider)
                });
              }}
              className="bg-transparent text-gray-900 dark:text-white font-medium focus:outline-none"
            >
              {AVAILABLE_MODELS.map((model) => (
                <option 
                  key={`${model.provider}-${model.model}`}
                  value={JSON.stringify(model)}
                  className="bg-white dark:bg-gray-800"
                >
                  {model.model} ({model.provider})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 relative">
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
                                <span className="text-white text-sm font-medium">U</span>
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
                                <span className="text-white text-sm font-medium">A</span>
                              </div>
                            </div>
                            <div className="bg-white dark:bg-gray-800 rounded-lg px-4 py-3 border border-gray-200 dark:border-gray-600">
                              <MessagePrimitive.Content />
                              {/* Message Actions */}
                              <div className="mt-2 flex gap-2">
                                <button className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                  </svg>
                                </button>
                                <button className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                  </svg>
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ),
                    }}
                  />
                  
                  {/* Welcome Message when no messages */}
                  <ThreadPrimitive.Empty>
                    <div className="flex flex-col items-center justify-center h-full text-center py-12">
                      <div className="w-16 h-16 bg-blue-500 rounded-full flex items-center justify-center mb-4">
                        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                      </div>
                      <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
                        How can I help you today?
                      </h2>
                      <p className="text-gray-600 dark:text-gray-400">
                        Start a conversation with your AI assistant
                      </p>
                    </div>
                  </ThreadPrimitive.Empty>
                </div>
              </ThreadPrimitive.Viewport>

              {/* Input Area */}
              <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                <div className="max-w-3xl mx-auto px-4 py-4">
                  <ComposerPrimitive.Root>
                    <div className="relative flex items-end gap-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 p-3">
                      <ComposerPrimitive.Input 
                        placeholder="Message assistant..."
                        className="flex-1 bg-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 resize-none focus:outline-none min-h-[24px] max-h-32"
                        autoFocus
                      />
                      <ComposerPrimitive.Send className="flex-shrink-0 p-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white rounded-lg transition-colors disabled:cursor-not-allowed">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                      </ComposerPrimitive.Send>
                    </div>
                  </ComposerPrimitive.Root>
                </div>
              </div>
            </ThreadPrimitive.Root>
          </AssistantRuntimeProvider>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Settings</h2>
                <button
                  onClick={() => setShowSettings(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* API Keys */}
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    OpenAI API Key
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={apiKeyInputs.openai}
                      onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, openai: e.target.value })}
                      placeholder="sk-..."
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => saveApiKey("openai", apiKeyInputs.openai)}
                      className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                    >
                      Verify
                    </button>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Anthropic API Key
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={apiKeyInputs.anthropic}
                      onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, anthropic: e.target.value })}
                      placeholder="sk-ant-api03-..."
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => saveApiKey("anthropic", apiKeyInputs.anthropic)}
                      className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                    >
                      Verify
                    </button>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Gemini API Key
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={apiKeyInputs.gemini}
                      onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, gemini: e.target.value })}
                      placeholder="AIzaSy..."
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => saveApiKey("gemini", apiKeyInputs.gemini)}
                      className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                    >
                      Verify
                    </button>
                  </div>
                </div>

                <div className="pt-4 border-t border-gray-200 dark:border-gray-600">
                  <button
                    onClick={() => {
                      localStorage.removeItem("blender-senpai-messages");
                      window.location.reload();
                    }}
                    className="w-full px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                  >
                    Clear Chat History
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
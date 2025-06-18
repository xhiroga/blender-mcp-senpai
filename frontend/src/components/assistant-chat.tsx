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

export function AssistantChat() {
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
    <div className="flex h-screen bg-gray-50">
      {/* Settings Sidebar */}
      <div className={`${showSettings ? 'w-80' : 'w-0'} transition-all duration-300 bg-white border-r overflow-hidden`}>
        <div className="p-4">
          <h2 className="text-lg font-semibold mb-4">Settings</h2>
          
          {/* Model Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Model</label>
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
              className="w-full p-2 border rounded-md"
            >
              {AVAILABLE_MODELS.map((model) => (
                <option 
                  key={`${model.provider}-${model.model}`}
                  value={JSON.stringify(model)}
                >
                  {model.model} ({model.provider})
                </option>
              ))}
            </select>
          </div>

          {/* API Keys */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">OpenAI API Key</label>
              <div className="flex space-x-2">
                <input
                  type="password"
                  value={apiKeyInputs.openai}
                  onChange={(e) => {
                    setApiKeyInputs({ ...apiKeyInputs, openai: e.target.value });
                  }}
                  placeholder="sk-..."
                  className="flex-1 p-2 border rounded-md"
                />
                <button
                  onClick={() => saveApiKey("openai", apiKeyInputs.openai)}
                  className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                >
                  Verify
                </button>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Anthropic API Key</label>
              <div className="flex space-x-2">
                <input
                  type="password"
                  value={apiKeyInputs.anthropic}
                  onChange={(e) => {
                    setApiKeyInputs({ ...apiKeyInputs, anthropic: e.target.value });
                  }}
                  placeholder="sk-ant-api03-..."
                  className="flex-1 p-2 border rounded-md"
                />
                <button
                  onClick={() => saveApiKey("anthropic", apiKeyInputs.anthropic)}
                  className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                >
                  Verify
                </button>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Gemini API Key</label>
              <div className="flex space-x-2">
                <input
                  type="password"
                  value={apiKeyInputs.gemini}
                  onChange={(e) => {
                    setApiKeyInputs({ ...apiKeyInputs, gemini: e.target.value });
                  }}
                  placeholder="AIzaSy..."
                  className="flex-1 p-2 border rounded-md"
                />
                <button
                  onClick={() => saveApiKey("gemini", apiKeyInputs.gemini)}
                  className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                >
                  Verify
                </button>
              </div>
            </div>
          </div>

          <div className="mt-6">
            <button
              onClick={() => {
                localStorage.removeItem("blender-senpai-messages");
                window.location.reload(); // Simple way to clear chat
              }}
              className="w-full p-2 bg-red-500 text-white rounded-md hover:bg-red-600"
            >
              Clear Chat History
            </button>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b p-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 hover:bg-gray-100 rounded-md"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
            <h1 className="text-xl font-semibold">Blender Senpai</h1>
          </div>
          <div className="text-sm text-gray-500">
            {settings.model} ({settings.provider})
          </div>
        </div>

        {/* Assistant UI Thread */}
        <div className="flex-1">
          <AssistantRuntimeProvider runtime={runtime}>
            <ThreadPrimitive.Root className="h-full flex flex-col">
              <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto p-4">
                <ThreadPrimitive.Messages 
                  components={{
                    UserMessage: () => (
                      <div className="flex justify-end mb-4">
                        <div className="max-w-xs lg:max-w-md px-4 py-2 rounded-lg bg-blue-500 text-white">
                          <MessagePrimitive.Content />
                        </div>
                      </div>
                    ),
                    AssistantMessage: () => (
                      <div className="flex justify-start mb-4">
                        <div className="max-w-xs lg:max-w-md px-4 py-2 rounded-lg bg-white border">
                          <MessagePrimitive.Content />
                        </div>
                      </div>
                    ),
                  }}
                />
              </ThreadPrimitive.Viewport>
              <ThreadPrimitive.ScrollToBottom />
              <div className="p-4 border-t">
                <ComposerPrimitive.Root>
                  <div className="flex space-x-2">
                    <ComposerPrimitive.Input 
                      placeholder="Type your message..."
                      className="flex-1 p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <ComposerPrimitive.Send className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50">
                      Send!
                    </ComposerPrimitive.Send>
                  </div>
                </ComposerPrimitive.Root>
              </div>
            </ThreadPrimitive.Root>
          </AssistantRuntimeProvider>
        </div>
      </div>
    </div>
  );
}
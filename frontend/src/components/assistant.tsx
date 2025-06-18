"use client";

import { useState, useEffect, useCallback } from "react";
import { AssistantRuntimeProvider, ThreadPrimitive, ComposerPrimitive, MessagePrimitive } from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { AVAILABLE_MODELS } from "@/lib/models";
import Image from "next/image";

// Helper function to get model icon components
const getModelIcon = (provider: string) => {
  const iconClass = "w-5 h-5";
  
  switch (provider) {
    case "openai":
      return <Image src="/openai.svg" alt="OpenAI" width={20} height={20} className={iconClass} />;
    case "anthropic":
      return <Image src="/anthropic.svg" alt="Anthropic" width={20} height={20} className={iconClass} />;
    case "gemini":
      return <Image src="/google.svg" alt="Google" width={20} height={20} className={iconClass} />;
    case "tutorial":
      return <span className="text-lg">📚</span>;
    default:
      return <span className="text-lg">🤖</span>;
  }
};

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
  const [showModelSelector, setShowModelSelector] = useState(false);
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
    
    // Load API keys first
    let savedKeys: { [key: string]: string } = {};
    try {
      const keysString = localStorage.getItem("blender-senpai-api-keys");
      if (keysString) {
        savedKeys = JSON.parse(keysString);
        console.log('Loaded API keys:', Object.keys(savedKeys)); // Debug log
      }
    } catch (error) {
      console.error('Error parsing saved API keys:', error);
      savedKeys = {};
    }

    // Update API key inputs state
    setApiKeyInputs({
      openai: savedKeys.openai || "",
      anthropic: savedKeys.anthropic || "",
      gemini: savedKeys.gemini || ""
    });
    
    // Load settings from localStorage
    const savedSettings = localStorage.getItem("blender-senpai-settings");
    if (savedSettings) {
      try {
        const parsedSettings = JSON.parse(savedSettings);
        // Update with current API key for the provider
        const currentApiKey = savedKeys[parsedSettings.provider] || "";
        setSettings({
          ...parsedSettings,
          apiKey: currentApiKey
        });
        console.log('Loaded settings:', parsedSettings.provider, 'API key exists:', !!currentApiKey); // Debug log
      } catch (error) {
        console.error('Error parsing saved settings:', error);
      }
    }
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      if (showModelSelector) {
        setShowModelSelector(false);
      }
    };

    if (showModelSelector) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showModelSelector]);

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
      
      // Update input field to reflect removal
      setApiKeyInputs(prev => ({ ...prev, [provider]: "" }));
      return;
    }

    try {
      // Save to backend first (backend will validate the key format)
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
        // Save to localStorage for frontend use
        const keys = JSON.parse(localStorage.getItem("blender-senpai-api-keys") || "{}");
        keys[provider] = apiKey;
        localStorage.setItem("blender-senpai-api-keys", JSON.stringify(keys));
        
        // Update settings with new API key if this is the current provider
        if (settings.provider === provider) {
          saveSettings({ ...settings, apiKey });
        }
        
        alert("API key saved successfully!");
      } else {
        throw new Error(result.message);
      }
    } catch (error) {
      console.error('Error saving API key:', error);
      alert(`Failed to save API key: ${error instanceof Error ? error.message : 'Unknown error'}`);
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

      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Model Selector - Custom dropdown like assistant-ui */}
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowModelSelector(!showModelSelector);
                }}
                className="flex items-center gap-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-medium border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                {getModelIcon(settings.provider)}
                <span>{settings.model}</span>
                <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Dropdown Menu */}
              {showModelSelector && (
                <div 
                  onClick={(e) => e.stopPropagation()}
                  className="absolute top-full left-0 mt-1 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto"
                >
                  {AVAILABLE_MODELS.map((model) => {
                    const hasApiKey = getApiKey(model.provider);
                    const isDisabled = !hasApiKey && model.provider !== 'tutorial';
                    const isSelected = model.model === settings.model && model.provider === settings.provider;
                    
                    return (
                      <button
                        key={`${model.provider}-${model.model}`}
                        onClick={() => {
                          if (!isDisabled) {
                            saveSettings({ 
                              ...settings, 
                              model: model.model, 
                              provider: model.provider,
                              apiKey: getApiKey(model.provider)
                            });
                            setShowModelSelector(false);
                          }
                        }}
                        disabled={isDisabled}
                        className={`w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
                          isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                        } ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                      >
                        {getModelIcon(model.provider)}
                        <div className="flex-1">
                          <div className={`font-medium ${isDisabled ? 'text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                            {model.model}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {model.provider.charAt(0).toUpperCase() + model.provider.slice(1)}
                          </div>
                        </div>
                        {isSelected && (
                          <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right side controls */}
            <div className="flex items-center gap-3">
              {/* Settings */}
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Settings"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>

              {/* User Avatar */}
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">U</span>
              </div>
            </div>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop with blur effect like ChatGPT */}
          <div 
            className="absolute inset-0 bg-gray-900/50 backdrop-blur-sm"
            onClick={() => setShowSettings(false)}
          />
          
          {/* Modal content */}
          <div className="relative bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-lg border border-gray-200 dark:border-gray-700">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Settings</h2>
              <button
                onClick={() => setShowSettings(false)}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* API Keys Section */}
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">API Keys</h3>
                <div className="space-y-4">
                  {/* OpenAI */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {getModelIcon("openai")}
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        OpenAI
                      </label>
                      {getApiKey("openai") && (
                        <span className="text-xs px-2 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-full">
                          Connected
                        </span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={apiKeyInputs.openai}
                        onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, openai: e.target.value })}
                        placeholder="sk-..."
                        className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                      />
                      <button
                        onClick={() => saveApiKey("openai", apiKeyInputs.openai)}
                        className="px-3 py-2 text-sm bg-gray-900 hover:bg-gray-800 dark:bg-white dark:hover:bg-gray-100 text-white dark:text-gray-900 rounded-md transition-colors font-medium"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                  
                  {/* Anthropic */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {getModelIcon("anthropic")}
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Anthropic
                      </label>
                      {getApiKey("anthropic") && (
                        <span className="text-xs px-2 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-full">
                          Connected
                        </span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={apiKeyInputs.anthropic}
                        onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, anthropic: e.target.value })}
                        placeholder="sk-ant-api03-..."
                        className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                      />
                      <button
                        onClick={() => saveApiKey("anthropic", apiKeyInputs.anthropic)}
                        className="px-3 py-2 text-sm bg-gray-900 hover:bg-gray-800 dark:bg-white dark:hover:bg-gray-100 text-white dark:text-gray-900 rounded-md transition-colors font-medium"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                  
                  {/* Gemini */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {getModelIcon("gemini")}
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Google Gemini
                      </label>
                      {getApiKey("gemini") && (
                        <span className="text-xs px-2 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-full">
                          Connected
                        </span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={apiKeyInputs.gemini}
                        onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, gemini: e.target.value })}
                        placeholder="AIzaSy..."
                        className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                      />
                      <button
                        onClick={() => saveApiKey("gemini", apiKeyInputs.gemini)}
                        className="px-3 py-2 text-sm bg-gray-900 hover:bg-gray-800 dark:bg-white dark:hover:bg-gray-100 text-white dark:text-gray-900 rounded-md transition-colors font-medium"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Data Management */}
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Data</h3>
                <button
                  onClick={() => {
                    if (confirm("Are you sure you want to clear all chat history? This action cannot be undone.")) {
                      localStorage.removeItem("blender-senpai-messages");
                      window.location.reload();
                    }
                  }}
                  className="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium"
                >
                  Clear all chat history
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
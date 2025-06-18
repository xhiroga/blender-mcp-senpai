"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { AssistantRuntimeProvider, ThreadPrimitive, ComposerPrimitive, MessagePrimitive } from "@assistant-ui/react";
import { useDangerousInBrowserRuntime } from "@assistant-ui/react-edge";
import { AVAILABLE_MODELS } from "@/lib/models";
import Image from "next/image";

// Helper function to mask API keys for display
const maskApiKey = (apiKey: string): string => {
  if (!apiKey || apiKey.length <= 8) {
    return "*".repeat(apiKey.length || 8);
  }
  return apiKey.slice(0, 4) + "*".repeat(apiKey.length - 8) + apiKey.slice(-4);
};

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
  const [apiKeyStates, setApiKeyStates] = useState<{[key: string]: {configured: boolean, apiKey: string}}>({
    openai: { configured: false, apiKey: "" },
    anthropic: { configured: false, apiKey: "" },
    gemini: { configured: false, apiKey: "" }
  });

  const getApiKey = useCallback((provider: string): string => {
    // Return the actual API key if configured
    return apiKeyStates[provider]?.configured ? apiKeyStates[provider].apiKey : "";
  }, [apiKeyStates]);


  // Assistant-UI Runtime setup with direct AI SDK integration
  // WORKAROUND: GitHub issue #5140 - enables AI SDK with static export
  const runtime = useDangerousInBrowserRuntime(useMemo(() => ({
    model: async () => {
      // Fetch API key from backend keyring storage
      const apiKeyResponse = await fetch(`${window.location.origin}/api/api-keys/${settings.provider}`);
      if (!apiKeyResponse.ok) {
        throw new Error('API key not configured for provider');
      }
      
      const { api_key: apiKey, configured } = await apiKeyResponse.json();
      if (!configured || !apiKey) {
        throw new Error('API key not configured for provider');
      }

      // Import AI SDK modules dynamically
      let createProvider;
      
      switch (settings.provider) {
        case 'openai':
          const { createOpenAI } = await import('@ai-sdk/openai');
          createProvider = () => createOpenAI({ apiKey });
          break;
        case 'anthropic':
          const { createAnthropic } = await import('@ai-sdk/anthropic');
          createProvider = () => createAnthropic({ apiKey });
          break;
        case 'gemini':
          const { createGoogleGenerativeAI } = await import('@ai-sdk/google');
          createProvider = () => createGoogleGenerativeAI({ apiKey });
          break;
        default:
          throw new Error('Unsupported provider');
      }

      const provider = createProvider();
      return provider(settings.model);
    },
    temperature: 0.7,
  }), [settings.provider, settings.model]));

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;
    
    // Load API key states from backend
    const loadApiKeyStates = async () => {
      try {
        const response = await fetch('/api/api-keys');
        if (response.ok) {
          const keyStates = await response.json();
          console.log('Loaded API key states from backend:', keyStates);
          
          // Update API key states
          setApiKeyStates({
            openai: { configured: keyStates.openai?.configured || false, apiKey: keyStates.openai?.api_key || "" },
            anthropic: { configured: keyStates.anthropic?.configured || false, apiKey: keyStates.anthropic?.api_key || "" },
            gemini: { configured: keyStates.gemini?.configured || false, apiKey: keyStates.gemini?.api_key || "" }
          });
          
          // Update input fields with masked keys for display
          setApiKeyInputs({
            openai: keyStates.openai?.api_key ? maskApiKey(keyStates.openai.api_key) : "",
            anthropic: keyStates.anthropic?.api_key ? maskApiKey(keyStates.anthropic.api_key) : "",
            gemini: keyStates.gemini?.api_key ? maskApiKey(keyStates.gemini.api_key) : ""
          });
        }
      } catch (error) {
        console.error('Error loading API key states:', error);
      }
    };
    
    // Load settings from localStorage (only model preferences, not API keys)
    const savedSettings = localStorage.getItem("blender-senpai-settings");
    if (savedSettings) {
      try {
        const parsedSettings = JSON.parse(savedSettings);
        setSettings({
          provider: parsedSettings.provider || "openai",
          model: parsedSettings.model || "gpt-4o",
          apiKey: "" // Always empty since we don't store keys in localStorage anymore
        });
        console.log('Loaded settings:', parsedSettings.provider, parsedSettings.model);
      } catch (error) {
        console.error('Error parsing saved settings:', error);
      }
    }
    
    loadApiKeyStates();
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

  const saveApiKey = async (provider: string, inputValue: string) => {
    if (typeof window === 'undefined') return;
    
    if (!inputValue.trim()) {
      alert("Please enter an API key");
      return;
    }
    
    // If the input value is masked (contains asterisks), use the stored API key
    // Otherwise, use the new input value
    const apiKey = inputValue.includes("*") && apiKeyStates[provider]?.apiKey 
      ? apiKeyStates[provider].apiKey 
      : inputValue;

    try {
      // Save to backend using Keyring
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
        // Reload API key states from backend
        const statesResponse = await fetch('/api/api-keys');
        if (statesResponse.ok) {
          const keyStates = await statesResponse.json();
          
          // Update API key states
          setApiKeyStates({
            openai: { configured: keyStates.openai?.configured || false, apiKey: keyStates.openai?.api_key || "" },
            anthropic: { configured: keyStates.anthropic?.configured || false, apiKey: keyStates.anthropic?.api_key || "" },
            gemini: { configured: keyStates.gemini?.configured || false, apiKey: keyStates.gemini?.api_key || "" }
          });
          
          // Update input fields with masked keys for display
          setApiKeyInputs({
            openai: keyStates.openai?.api_key ? maskApiKey(keyStates.openai.api_key) : "",
            anthropic: keyStates.anthropic?.api_key ? maskApiKey(keyStates.anthropic.api_key) : "",
            gemini: keyStates.gemini?.api_key ? maskApiKey(keyStates.gemini.api_key) : ""
          });
        }
        
        alert("API key saved successfully and stored securely!");
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
                className="flex items-center gap-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-medium border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors min-w-48"
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
                  className="absolute top-full left-0 mt-1 w-80 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto"
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
                      {apiKeyStates.openai?.configured && (
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
                      {apiKeyStates.anthropic?.configured && (
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
                      {apiKeyStates.gemini?.configured && (
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
                      // Clear chat history (note: chat history is now handled by assistant-ui runtime)
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
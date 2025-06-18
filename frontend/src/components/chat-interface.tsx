"use client";

import { useState, useEffect, useCallback } from "react";
import { createOpenAI } from "@ai-sdk/openai";
import { createAnthropic } from "@ai-sdk/anthropic";
import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { streamText } from "ai";

interface Model {
  model: string;
  provider: string;
  default?: boolean;
}

interface Settings {
  provider: string;
  apiKey: string;
  model: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const AVAILABLE_MODELS: Model[] = [
  { model: "gpt-4o", provider: "openai", default: true },
  { model: "gpt-4o-mini", provider: "openai" },
  { model: "claude-3-5-sonnet-20241022", provider: "anthropic", default: true },
  { model: "claude-3-haiku-20240307", provider: "anthropic" },
  { model: "gemini-1.5-pro", provider: "gemini", default: true },
  { model: "gemini-1.5-flash", provider: "gemini" },
];

export function ChatInterface() {
  const [settings, setSettings] = useState<Settings>({
    provider: "openai",
    apiKey: "",
    model: "gpt-4o"
  });
  const [showSettings, setShowSettings] = useState(false);
  const [availableModels, setAvailableModels] = useState<Model[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;
    
    // Load settings from localStorage
    const savedSettings = localStorage.getItem("blender-senpai-settings");
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }
    
    // Load messages from localStorage  
    const savedMessages = localStorage.getItem("blender-senpai-messages");
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages).map((msg: {role: string; content: string; timestamp: string}) => ({
        ...msg,
        timestamp: new Date(msg.timestamp)
      })));
    }
  }, []);

  const updateAvailableModels = useCallback(() => {
    if (typeof window === 'undefined') return;
    
    const savedKeys = JSON.parse(localStorage.getItem("blender-senpai-api-keys") || "{}");
    const enabledProviders = Object.keys(savedKeys).filter(key => savedKeys[key]);
    
    const enabled = AVAILABLE_MODELS.filter(model => 
      model.provider === "tutorial" || enabledProviders.includes(model.provider)
    );
    
    if (enabled.length === 0) {
      enabled.push({ model: "tutorial", provider: "tutorial", default: true });
    }
    
    setAvailableModels(enabled);
    
    // Update current model if not available
    if (!enabled.some(m => m.model === settings.model && m.provider === settings.provider)) {
      const defaultModel = enabled.find(m => m.default) || enabled[0];
      if (defaultModel) {
        saveSettings({
          ...settings,
          model: defaultModel.model,
          provider: defaultModel.provider,
          apiKey: getApiKey(defaultModel.provider)
        });
      }
    }
  }, [settings]);

  useEffect(() => {
    updateAvailableModels();
  }, [settings.provider, updateAvailableModels]); // Re-update when provider changes

  const saveSettings = (newSettings: Settings) => {
    setSettings(newSettings);
    if (typeof window !== 'undefined') {
      localStorage.setItem("blender-senpai-settings", JSON.stringify(newSettings));
    }
  };

  const saveApiKey = async (provider: string, apiKey: string) => {
    if (typeof window === 'undefined') return;
    
    if (!apiKey.trim()) {
      // Just remove the key if empty
      const keys = JSON.parse(localStorage.getItem("blender-senpai-api-keys") || "{}");
      delete keys[provider];
      localStorage.setItem("blender-senpai-api-keys", JSON.stringify(keys));
      updateAvailableModels();
      return;
    }

    try {
      // Test API key by making a small request
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

      // If we get here, the API key works
      const keys = JSON.parse(localStorage.getItem("blender-senpai-api-keys") || "{}");
      keys[provider] = apiKey;
      localStorage.setItem("blender-senpai-api-keys", JSON.stringify(keys));
      
      // Update settings with new API key
      if (settings.provider === provider) {
        saveSettings({ ...settings, apiKey });
      }
      
      // Update available models
      updateAvailableModels();
      
      alert("API key verified and saved successfully!");
    } catch (error) {
      console.error('Error verifying API key:', error);
      alert(`API Key verification failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const getApiKey = (provider: string): string => {
    if (typeof window === 'undefined') return "";
    
    const keys = JSON.parse(localStorage.getItem("blender-senpai-api-keys") || "{}");
    return keys[provider] || "";
  };

  const saveMessages = (msgs: Message[]) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem("blender-senpai-messages", JSON.stringify(msgs));
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: input.trim(),
      timestamp: new Date()
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      if (settings.provider === "tutorial") {
        const tutorialMessage: Message = {
          role: "assistant",
          content: "Welcome to Blender Senpai! Please configure your API keys in the settings to start chatting with AI models.",
          timestamp: new Date()
        };
        const finalMessages = [...newMessages, tutorialMessage];
        setMessages(finalMessages);
        saveMessages(finalMessages);
      } else {
        // Get API key for current provider
        const apiKey = getApiKey(settings.provider);
        if (!apiKey) {
          throw new Error(`API key not configured for ${settings.provider}`);
        }

        // Create AI provider
        let aiProvider;
        let model;

        switch (settings.provider) {
          case "openai":
            aiProvider = createOpenAI({ apiKey });
            model = aiProvider(settings.model);
            break;
          case "anthropic":
            aiProvider = createAnthropic({ apiKey });
            model = aiProvider(settings.model);
            break;
          case "gemini":
            aiProvider = createGoogleGenerativeAI({ apiKey });
            model = aiProvider(settings.model);
            break;
          default:
            throw new Error(`Unsupported provider: ${settings.provider}`);
        }

        // Prepare conversation history for AI SDK
        const aiMessages = messages.map(msg => ({
          role: msg.role as "user" | "assistant",
          content: msg.content
        }));
        aiMessages.push({
          role: "user",
          content: userMessage.content
        });

        // Create assistant message placeholder
        const assistantMessage: Message = {
          role: "assistant",
          content: "",
          timestamp: new Date()
        };

        // Add the assistant message to state (will be updated as we stream)
        const messagesWithAssistant = [...newMessages, assistantMessage];
        setMessages(messagesWithAssistant);

        // Stream the response
        const stream = await streamText({
          model,
          messages: aiMessages,
          temperature: 0.7,
        });

        let assistantContent = "";
        for await (const chunk of stream.textStream) {
          assistantContent += chunk;
          
          // Update the assistant message in state
          setMessages(prevMessages => {
            const updated = [...prevMessages];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: assistantContent
            };
            return updated;
          });
        }

        // Save final messages
        const finalMessages = [...newMessages, {
          role: "assistant" as const,
          content: assistantContent,
          timestamp: new Date()
        }];
        saveMessages(finalMessages);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${error instanceof Error ? error.message : "Unknown error occurred"}`,
        timestamp: new Date()
      };
      const finalMessages = [...newMessages, errorMessage];
      setMessages(finalMessages);
      saveMessages(finalMessages);
    } finally {
      setIsLoading(false);
    }
  };

  const clearMessages = () => {
    setMessages([]);
    if (typeof window !== 'undefined') {
      localStorage.removeItem("blender-senpai-messages");
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
              {availableModels.map((model) => (
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
              <input
                type="password"
                value={getApiKey("openai")}
                onChange={(e) => saveApiKey("openai", e.target.value)}
                placeholder="sk-..."
                className="w-full p-2 border rounded-md"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Anthropic API Key</label>
              <input
                type="password"
                value={getApiKey("anthropic")}
                onChange={(e) => saveApiKey("anthropic", e.target.value)}
                placeholder="sk-ant-api03-..."
                className="w-full p-2 border rounded-md"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Gemini API Key</label>
              <input
                type="password"
                value={getApiKey("gemini")}
                onChange={(e) => saveApiKey("gemini", e.target.value)}
                placeholder="AIzaSy..."
                className="w-full p-2 border rounded-md"
              />
            </div>
          </div>

          <div className="mt-6">
            <button
              onClick={clearMessages}
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

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-8">
              <p>Welcome to Blender Senpai!</p>
              <p className="text-sm mt-2">Configure your API keys in settings and start chatting.</p>
            </div>
          )}
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.role === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-white border"
                }`}
              >
                <p className="text-sm">{message.content}</p>
                <p className="text-xs opacity-70 mt-1">
                  {message.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border px-4 py-2 rounded-lg">
                <p className="text-sm">Thinking...</p>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="bg-white border-t p-4">
          <div className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Type your message..."
              className="flex-1 p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
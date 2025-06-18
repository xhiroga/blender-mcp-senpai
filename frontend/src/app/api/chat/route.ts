import { createOpenAI } from '@ai-sdk/openai';
import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { streamText } from 'ai';

// WORKAROUND: API Route Handler for AI SDK in static export
// This endpoint exists because AI SDK cannot run directly in the browser
// In a normal Next.js app, this would be handled server-side with env vars
// See: https://github.com/vercel/ai/issues/5140
export async function POST(req: Request) {
  try {
    const { messages, provider, model, apiKey } = await req.json();
    
    // WARNING: Receiving API key from client side - only safe because users provide their own keys
    // In a production SaaS app, API keys should be stored server-side in env vars
    if (!apiKey) {
      return new Response('API key required', { status: 400 });
    }

    // Create AI provider
    let aiProvider;
    let aiModel;

    switch (provider) {
      case 'openai':
        aiProvider = createOpenAI({ apiKey });
        aiModel = aiProvider(model);
        break;
      case 'anthropic':
        aiProvider = createAnthropic({ apiKey });
        aiModel = aiProvider(model);
        break;
      case 'gemini':
        aiProvider = createGoogleGenerativeAI({ apiKey });
        aiModel = aiProvider(model);
        break;
      default:
        return new Response('Unsupported provider', { status: 400 });
    }

    const result = streamText({
      model: aiModel,
      messages,
      temperature: 0.7,
    });

    return result.toDataStreamResponse();
  } catch (error) {
    console.error('Chat API error:', error);
    return new Response('Internal server error', { status: 500 });
  }
}
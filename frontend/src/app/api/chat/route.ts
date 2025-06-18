import { createOpenAI } from '@ai-sdk/openai';
import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { streamText } from 'ai';

export async function POST(req: Request) {
  try {
    const { messages, provider, model, apiKey } = await req.json();
    
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
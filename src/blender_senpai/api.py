import json
import uuid
from logging import getLogger
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .i18n import t
from .llm import ModelConfig, Provider, completion_stream, model_configs
from .repositories.api_key_repository import ApiKeyRepository
from .repositories.history_repository import HistoryRepository

logger = getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    provider: str
    model: str
    conversation_id: Optional[str] = None


class ModelInfo(BaseModel):
    model: str
    provider: str
    default: bool = False


class ApiKeyRequest(BaseModel):
    provider: str
    api_key: str


class ApiKeyResponse(BaseModel):
    success: bool
    message: str


@router.get("/models", response_model=List[ModelInfo])
async def get_available_models():
    """Get list of available models based on configured API keys"""
    api_keys = ApiKeyRepository.list()
    providers = list(api_keys.keys())
    
    enabled_models = [
        ModelInfo(
            model=model["model"],
            provider=model["provider"],
            default=model.get("default", False)
        )
        for model in model_configs
        if model["provider"] == "tutorial" or model["provider"] in providers
    ]
    
    # Always include tutorial model if no other models are available
    if not enabled_models:
        enabled_models.append(ModelInfo(model="tutorial", provider="tutorial", default=True))
    
    return enabled_models


@router.post("/api-keys", response_model=ApiKeyResponse)
async def save_api_key(request: ApiKeyRequest):
    """Save and verify an API key"""
    try:
        from .types.api_key import ApiKey
        import litellm
        
        api_key = ApiKey(request.api_key)
        
        # Test the API key by making a small request
        default_model = next(
            (m for m in model_configs if m["provider"] == request.provider and m.get("default")),
            None
        )
        
        if not default_model:
            raise HTTPException(status_code=400, detail=f"No default model found for provider {request.provider}")
        
        model = f"{request.provider}/{default_model['model']}"
        
        # Test the API key
        litellm.completion(
            model=model,
            api_key=api_key.reveal(),
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5,
        )
        
        # If test succeeds, save the key
        ApiKeyRepository.save(request.provider, api_key)
        
        return ApiKeyResponse(success=True, message="API key verified and saved")
        
    except Exception as e:
        logger.exception(f"Error verifying API key for {request.provider}")
        return ApiKeyResponse(success=False, message=f"API key verification failed: {str(e)}")


@router.get("/api-keys/{provider}")
async def get_api_key(provider: str):
    """Get API key for a provider (returns masked version)"""
    api_key = ApiKeyRepository.get(provider)
    if api_key:
        key_str = api_key.reveal()
        # Mask the key for security
        if len(key_str) > 8:
            masked = key_str[:4] + "*" * (len(key_str) - 8) + key_str[-4:]
        else:
            masked = "*" * len(key_str)
        return {"provider": provider, "api_key": masked, "configured": True}
    return {"provider": provider, "api_key": "", "configured": False}


@router.post("/chat")
async def chat_stream(request: ChatRequest):
    """Stream chat completion"""
    
    async def generate():
        try:
            conversation_id = request.conversation_id or str(uuid.uuid4())
            
            # Save user message to history
            HistoryRepository.create(conversation_id, "user", request.message)
            
            # Handle tutorial mode
            if request.provider == "tutorial":
                tutorial_msg = "Welcome to Blender Senpai! Please configure your API keys to start chatting with AI models."
                HistoryRepository.create(conversation_id, "assistant", tutorial_msg)
                yield f"data: {json.dumps({'content': tutorial_msg, 'done': True})}\n\n"
                return
            
            # Get API key
            api_key = ApiKeyRepository.get(request.provider)
            if not api_key:
                error_msg = f"API key required for {request.provider}"
                HistoryRepository.create(conversation_id, "assistant", error_msg)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return
            
            # Convert request format to internal format
            history = [(msg.content, "") for msg in request.history if msg.role == "user"]
            if len(request.history) > 1:
                for i in range(1, len(request.history), 2):
                    if i < len(request.history) and request.history[i].role == "assistant":
                        if history and len(history[-1]) == 2 and history[-1][1] == "":
                            history[-1] = (history[-1][0], request.history[i].content)
            
            model = f"{request.provider}/{request.model}"
            logger.info(f"Starting chat completion with model: {model}")
            
            tokens = []
            async for token in completion_stream(
                model=model,
                api_key=api_key,
                message=request.message,
                history=history,
                lang="en",  # TODO: get from request or settings
            ):
                tokens.append(token)
                partial = "".join(tokens)
                yield f"data: {json.dumps({'content': partial, 'done': False})}\n\n"
            
            # Save assistant response
            assistant_message = "".join(tokens)
            HistoryRepository.create(conversation_id, "assistant", assistant_message)
            
            yield f"data: {json.dumps({'content': assistant_message, 'done': True})}\n\n"
            
        except Exception as e:
            logger.exception("Error in chat stream")
            error_msg = f"Error: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )
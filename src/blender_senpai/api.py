from logging import getLogger
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from .repositories.api_key_repository import ApiKeyRepository

logger = getLogger(__name__)

router = APIRouter()

# Model configurations (moved from deleted llm.py)
AVAILABLE_MODELS = [
    # OpenAI models
    {"provider": "openai", "model": "gpt-4o", "default": True},
    {"provider": "openai", "model": "gpt-4o-mini", "default": False},
    {"provider": "openai", "model": "gpt-4-turbo", "default": False},
    {"provider": "openai", "model": "gpt-3.5-turbo", "default": False},
    # Anthropic models  
    {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022", "default": True},
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "default": False},
    {"provider": "anthropic", "model": "claude-3-opus-20240229", "default": False},
    # Google models
    {"provider": "gemini", "model": "gemini-1.5-pro", "default": True},
    {"provider": "gemini", "model": "gemini-1.5-flash", "default": False},
    {"provider": "gemini", "model": "gemini-2.0-flash-exp", "default": False},
    # Tutorial model
    {"provider": "tutorial", "model": "tutorial", "default": True},
]


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
        for model in AVAILABLE_MODELS
        if model["provider"] == "tutorial" or model["provider"] in providers
    ]
    
    # Always include tutorial model if no other models are available
    if not enabled_models:
        enabled_models.append(ModelInfo(model="tutorial", provider="tutorial", default=True))
    
    return enabled_models


@router.post("/api-keys", response_model=ApiKeyResponse)
async def save_api_key(request: ApiKeyRequest):
    """Save an API key (validation is done on frontend)"""
    try:
        from .types_models.api_key import ApiKey
        
        api_key = ApiKey(request.api_key)
        ApiKeyRepository.save(request.provider, api_key)
        
        return ApiKeyResponse(success=True, message="API key saved successfully")
        
    except Exception as e:
        logger.exception(f"Error saving API key for {request.provider}")
        return ApiKeyResponse(success=False, message=f"Failed to save API key: {str(e)}")


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
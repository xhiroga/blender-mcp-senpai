from logging import getLogger

from fastapi import APIRouter
from pydantic import BaseModel

from .repositories.api_key_repository import ApiKeyRepository

logger = getLogger(__name__)

router = APIRouter()



class ApiKeyRequest(BaseModel):
    provider: str
    api_key: str


class ApiKeyResponse(BaseModel):
    success: bool
    message: str



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
    """Get API key for a provider"""
    api_key = ApiKeyRepository.get(provider)
    if api_key:
        return {"provider": provider, "api_key": api_key.reveal(), "configured": True}
    return {"provider": provider, "api_key": "", "configured": False}


@router.get("/api-keys")
async def get_all_api_keys():
    """Get all configured API keys"""
    providers = ["openai", "anthropic", "gemini"]
    result = {}
    
    for provider in providers:
        api_key = ApiKeyRepository.get(provider)
        if api_key:
            result[provider] = {"api_key": api_key.reveal(), "configured": True}
        else:
            result[provider] = {"api_key": "", "configured": False}
    
    return result
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
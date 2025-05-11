from logging import getLogger

from blender_senpai.repositories.api_key_repository import ApiKeyRepository
from blender_senpai.types.api_key import ApiKey

logger = getLogger(__name__)


def test_crud():
    ApiKeyRepository.save("test", ApiKey("test"))
    assert ApiKeyRepository.get("test") == ApiKey("test")
    ApiKeyRepository.delete("test")
    assert ApiKeyRepository.get("test") is None

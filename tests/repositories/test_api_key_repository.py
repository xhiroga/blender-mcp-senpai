import sys
from logging import getLogger

import pytest

from blender_senpai.repositories.api_key_repository import ApiKeyRepository
from blender_senpai.types.api_key import ApiKey

logger = getLogger(__name__)


@pytest.mark.skipif(
    sys.platform.startswith("linux"), reason="Workaround. GitHub Actions has no GUI."
)
def test_crud():
    ApiKeyRepository.save("test", ApiKey("test"))
    assert ApiKeyRepository.get("test") == ApiKey("test")
    ApiKeyRepository.delete("test")
    assert ApiKeyRepository.get("test") is None

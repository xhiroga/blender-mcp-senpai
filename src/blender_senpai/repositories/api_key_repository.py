from __future__ import annotations

import json
from logging import getLogger

import keyring  # type: ignore

from ..types.api_key import ApiKey

logger = getLogger(__name__)


class ApiKeyRepository:
    """Repository for persisting API keys.

    * Keys are cached in-memory for fast access.
    * Keys are persisted in the system key-ring so that they survive process restarts.
    * The set of *known* providers is maintained in ``_KNOWN_PROVIDERS``.
      ``list`` enumerates these providers and returns the keys that are
      currently available in the key-ring or in memory.
    """

    _SERVICE_NAME: str = "blender_senpai"
    _ACCOUNT_NAME: str = "api_keys"  # Single record in Keychain

    # In-memory cache. Filled lazily after first access.
    _cache: dict[str, ApiKey] = {}
    _loaded: bool = False

    @classmethod
    def _load_all(cls) -> None:
        """Load the JSON blob from Keychain into the in-memory cache."""
        logger.debug(f"{cls._loaded=}, {cls._cache=}")
        if cls._loaded:
            return

        raw = keyring.get_password(cls._SERVICE_NAME, cls._ACCOUNT_NAME)
        logger.debug(f"{raw is not None=}")

        if raw:
            try:
                data: dict[str, str] = json.loads(raw)
                cls._cache = {k: ApiKey(v) for k, v in data.items()}
            except json.JSONDecodeError:
                logger.warning("JSON decode error")
                cls._cache = {}

        cls._loaded = True

    @classmethod
    def _persist_all(cls) -> None:
        """Persist the entire cache back to Keychain as a JSON blob."""
        logger.debug(f"{cls._cache=}")
        payload = json.dumps({k: v.reveal() for k, v in cls._cache.items()})
        keyring.set_password(cls._SERVICE_NAME, cls._ACCOUNT_NAME, payload)
        logger.debug(f"{len(cls._cache)=}")

    @classmethod
    def save(cls, provider: str, api_key: ApiKey) -> None:
        logger.info(f"{provider=}, {api_key=}")

        cls._load_all()

        cls._cache[provider] = api_key
        cls._persist_all()

    @classmethod
    def get(cls, provider: str) -> ApiKey | None:
        cls._load_all()

        result = cls._cache.get(provider)
        logger.info(f"{provider=}, {result is not None=}")
        return result

    @classmethod
    def list(cls) -> dict[str, ApiKey]:
        cls._load_all()

        return dict(cls._cache)

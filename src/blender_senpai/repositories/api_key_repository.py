from __future__ import annotations

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
    # Providers supported by the application. Update this list when adding new providers.
    _KNOWN_PROVIDERS: tuple[str, ...] = ("openai", "anthropic", "gemini")

    # In-memory cache. Keys are loaded lazily.
    _cache: dict[str, ApiKey] = {}

    # ---------------------------------------------------------------------
    # private helpers
    # ---------------------------------------------------------------------
    @classmethod
    def _load_provider_list(cls) -> list[str]:
        """Return the list of providers that the application knows about."""
        return list(cls._KNOWN_PROVIDERS)

    @classmethod
    def _ensure_loaded(cls, provider: str) -> None:
        """Make sure the cache contains the key for *provider* if it exists in the key-ring."""
        if provider in cls._cache:
            return
        stored_value = keyring.get_password(cls._SERVICE_NAME, provider)
        if stored_value is not None:
            cls._cache[provider] = ApiKey(stored_value)

    # ---------------------------------------------------------------------
    # public interface
    # ---------------------------------------------------------------------
    @classmethod
    def save(cls, provider: str, api_key: ApiKey) -> None:
        logger.info(f"save: {provider=}, {api_key=}")

        cls._cache[provider] = api_key

        keyring.set_password(cls._SERVICE_NAME, provider, api_key.reveal())

    @classmethod
    def get(cls, provider: str) -> ApiKey | None:
        cls._ensure_loaded(provider)
        result = cls._cache.get(provider)
        logger.info(f"get: {provider=} -> {result is not None}")
        return result

    @classmethod
    def list(cls) -> dict[str, ApiKey]:
        # Ensure that every known provider is checked for a stored key
        for provider in cls._KNOWN_PROVIDERS:
            cls._ensure_loaded(provider)
        logger.info(f"list -> {list(cls._cache.keys())}")
        # return a *copy* so callers cannot mutate our cache directly
        return dict(cls._cache)

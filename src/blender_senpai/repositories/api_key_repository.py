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
    * A special user name ``__providers__`` keeps a JSON-encoded list of registered providers
      inside the same key-ring service to make ``list`` feasible.
    """

    _SERVICE_NAME: str = "blender_senpai"
    _PROVIDER_LIST_USERNAME: str = "__providers__"

    # In-memory cache. Keys are loaded lazily.
    _cache: dict[str, ApiKey] = {}

    # ---------------------------------------------------------------------
    # private helpers
    # ---------------------------------------------------------------------
    @classmethod
    def _load_provider_list(cls) -> list[str]:
        raw = keyring.get_password(cls._SERVICE_NAME, cls._PROVIDER_LIST_USERNAME)
        if raw is None:
            return []
        try:
            providers: list[str] = json.loads(raw)
            # Defensive check – list[str] is expected
            if isinstance(providers, list):
                return providers
        except json.JSONDecodeError:
            logger.warning("Failed to decode provider list from key-ring; reset list.")
        return []

    @classmethod
    def _save_provider_list(cls, providers: list[str]) -> None:
        keyring.set_password(
            cls._SERVICE_NAME, cls._PROVIDER_LIST_USERNAME, json.dumps(providers)
        )

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

        # Cache the *masked* instance for fast access.
        cls._cache[provider] = api_key

        # Persist the *raw* secret to the key-ring.
        keyring.set_password(cls._SERVICE_NAME, provider, api_key.reveal())

        # update provider list
        providers = cls._load_provider_list()
        if provider not in providers:
            providers.append(provider)
            cls._save_provider_list(providers)

    @classmethod
    def get(cls, provider: str) -> ApiKey | None:
        cls._ensure_loaded(provider)
        result = cls._cache.get(provider)
        logger.info(f"get: {provider=} -> {result is not None}")
        return result

    @classmethod
    def list(cls) -> dict[str, ApiKey]:
        # make sure every registered provider is in cache
        for provider in cls._load_provider_list():
            cls._ensure_loaded(provider)
        logger.info(f"list -> {list(cls._cache.keys())}")
        # return a *copy* so callers cannot mutate our cache directly
        return dict(cls._cache)

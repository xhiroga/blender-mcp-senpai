from __future__ import annotations

import json
from functools import lru_cache
from logging import getLogger

import keyring  # type: ignore

from ..types.api_key import ApiKey

logger = getLogger(__name__)


class ApiKeyRepository:
    _SERVICE_NAME: str = "blender_senpai"
    _ACCOUNT_NAME: str = "api_keys"

    @staticmethod
    @lru_cache(maxsize=1)
    def _got() -> dict[str, ApiKey]:
        raw = keyring.get_password(
            ApiKeyRepository._SERVICE_NAME, ApiKeyRepository._ACCOUNT_NAME
        )
        logger.debug(f"{raw is not None=}")

        if raw:
            try:
                data: dict[str, str] = json.loads(raw)
                parsed = {k: ApiKey(v) for k, v in data.items()}
                logger.debug(f"{parsed=}")
                return parsed
            except json.JSONDecodeError:
                logger.warning("JSON decode error")

        return {}

    @staticmethod
    def _set(data: dict[str, ApiKey]) -> None:
        payload = json.dumps({k: v.reveal() for k, v in data.items()})
        keyring.set_password(
            ApiKeyRepository._SERVICE_NAME, ApiKeyRepository._ACCOUNT_NAME, payload
        )
        ApiKeyRepository._got.cache_clear()

    @classmethod
    def save(cls, provider: str, api_key: ApiKey) -> None:
        logger.debug(f"{provider=}, {api_key=}")

        updated = dict(cls._got())  # copy to mutate
        updated[provider] = api_key
        cls._set(updated)

    @classmethod
    def get(cls, provider: str) -> ApiKey | None:
        result = cls._got().get(provider)
        logger.debug(f"{provider=}, {result=}")
        return result

    @classmethod
    def list(cls) -> dict[str, ApiKey]:
        return cls._got()

    @classmethod
    def delete(cls, provider: str) -> None:
        updated = dict(cls._got())  # copy to mutate
        if provider in updated:
            del updated[provider]
        cls._set(updated)

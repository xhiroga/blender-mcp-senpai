class ApiKeyRepository:
    on_memory_api_keys = {}

    @classmethod
    def save(cls, provider: str, api_key: str):
        cls.on_memory_api_keys[provider] = api_key

    @classmethod
    def get(cls, provider: str) -> str | None:
        return cls.on_memory_api_keys.get(provider)

    @classmethod
    def list(cls) -> dict[str, str]:
        return cls.on_memory_api_keys

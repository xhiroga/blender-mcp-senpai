class HistoryRepository:
    on_memory_history = []

    @classmethod
    def create(cls, conversation_id: str, role: str, message: str):
        cls.on_memory_history.append((conversation_id, role, message))

    @classmethod
    def list(cls) -> list[tuple[str, str]]:
        return cls.on_memory_history

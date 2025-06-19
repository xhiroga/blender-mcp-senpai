from logging import getLogger

logger = getLogger(__name__)


class ApiKey(str):
    """String subclass whose *str*, *repr*, and *format* output are masked."""

    _VISIBLE_CHARS_HEAD = 3
    _MASK_CHAR = "*"

    def __new__(cls, value: str):
        logger.info(f"ApiKey.__new__: value length={len(value)}")
        return super().__new__(cls, value)

    def _masked(self) -> str:
        if len(self) <= self._VISIBLE_CHARS_HEAD:
            return self
        return self[: self._VISIBLE_CHARS_HEAD] + self._MASK_CHAR * (
            len(self) - self._VISIBLE_CHARS_HEAD
        )

    def __str__(self) -> str:
        return self._masked()

    __repr__ = __str__

    def __format__(self, format_spec: str) -> str:
        if format_spec == "raw":
            return self.reveal()
        return self._masked()

    def reveal(self) -> str:
        return super().__str__()

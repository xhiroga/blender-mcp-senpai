import json
import urllib.request
from functools import lru_cache
from logging import getLogger
from typing import TypedDict

logger = getLogger(__name__)


class QA(TypedDict):
    lang: str
    q: str
    a: str


class Metadata(TypedDict):
    file_name: str
    url: str
    qa: list[QA]


class AssetsRepository:
    _METADATA_URL: str = "https://xhiroga.github.io/bqa/as/metadata.jsonl"

    @staticmethod
    @lru_cache(maxsize=1)
    def _fetched() -> list[Metadata]:
        try:
            with urllib.request.urlopen(
                AssetsRepository._METADATA_URL, timeout=5
            ) as resp:
                text = resp.read().decode("utf-8")
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
            logger.debug(f"{len(records)=}")
            return records
        except Exception as e:
            logger.warning(f"{e!r}")
            return []

    @classmethod
    def list_image_urls(cls) -> list[str]:
        records = cls._fetched()
        urls = [r["url"] for r in records]
        logger.debug(f"{len(urls)=}")
        return urls

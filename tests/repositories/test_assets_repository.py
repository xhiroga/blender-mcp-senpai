from logging import getLogger

from blender_senpai.repositories.assets_repository import AssetsRepository

logger = getLogger(__name__)


def test_list_image_urls():
    urls = AssetsRepository.list_image_urls()

    # Minimal yet meaningful assertions
    assert isinstance(urls, list)
    assert len(urls) > 0
    assert isinstance(urls[0], str)
    assert urls[0].startswith("https://")

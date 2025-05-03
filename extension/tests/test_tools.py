from blender_senpai.log_config import configure
from blender_senpai.tools import get_context

configure(mode="standalone")


def test_get_context():
    result = get_context()
    assert result["status"] == "ok"
    assert result["payload"] is not None

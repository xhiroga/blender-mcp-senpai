import inspect

import pytest

from blender_senpai.log_config import configure
from blender_senpai.tools import get_context

configure(mode="standalone")


async def await_if_awaitable(maybe_result):
    return await maybe_result if inspect.isawaitable(maybe_result) else maybe_result


@pytest.mark.asyncio
async def test_get_context():
    result = await await_if_awaitable(get_context())
    assert result["status"] == "ok"
    assert result["payload"] is not None

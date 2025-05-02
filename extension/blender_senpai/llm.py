from logging import getLogger
from typing import Any, TypedDict

import litellm

from .i18n import Lang
from .tools import get_tools

logger = getLogger(__name__)


class GradioHistoryMessage(TypedDict):
    role: str
    metadata: Any | None
    content: str
    options: Any | None


class OpenAIChatCompletionMessages(TypedDict):
    role: str
    content: str
    # TODO: Tools, etc... from https://platform.openai.com/docs/api-reference/chat


SYSTEM_PROMPT = """
You are a helpful assistant.
"""


def _build_litellm_messages_from_gradio_history(
    user_message: str,
    history: list[GradioHistoryMessage],
    lang: Lang = "en",
) -> list[OpenAIChatCompletionMessages]:
    messages: list[OpenAIChatCompletionMessages] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "system",
            "content": f"Language: {lang}",
        },
    ]

    for message in history:
        messages.append({"role": message["role"], "content": message["content"]})

    messages.append({"role": "user", "content": user_message})
    return messages


def completion(
    model: str,
    api_key: str,
    message: str,
    history: list[GradioHistoryMessage],
    lang: Lang,
) -> str:
    messages = _build_litellm_messages_from_gradio_history(message, history, lang)
    response = litellm.completion(
        model=model,
        api_key=api_key,
        messages=messages,
        tools=get_tools(),
        tool_choice="auto",
    )
    return response["choices"][0]["message"]["content"].strip()

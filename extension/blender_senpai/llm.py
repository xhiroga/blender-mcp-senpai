import inspect
import json
from logging import getLogger
from typing import Any, TypedDict

import litellm
from litellm import ChatCompletionMessageToolCall

from .i18n import Lang
from .system_prompt import SYSTEM_PROMPT
from .tools import tool_functions, tools

logger = getLogger(__name__)


class GradioHistoryMessage(TypedDict):
    role: str
    metadata: Any
    content: str
    options: Any


class OpenAIChatCompletionMessages(TypedDict):
    role: str
    content: str
    # TODO: Tools, etc... from https://platform.openai.com/docs/api-reference/chat


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


async def completion(
    model: str,
    api_key: str,
    message: str,
    history: list[GradioHistoryMessage],
    lang: Lang,
) -> str:
    logger.info(f"completion: {model=} {message[:30]=} {history[-3:]=} {lang=}")
    messages = _build_litellm_messages_from_gradio_history(message, history, lang)

    raw_response = await litellm.acompletion(
        model=model,
        api_key=api_key,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    logger.info(f"acompletion: raw_response={str(raw_response)[:200]}")

    first_choice = raw_response["choices"][0]["message"]
    if (content := first_choice.get("content")) is not None:
        return content.strip()

    tool_calls: list[ChatCompletionMessageToolCall] = first_choice.tool_calls
    if tool_calls is None:
        return ""

    assistant_message: dict[str, Any] = {
        "role": "assistant",
        "content": "",
        "tool_calls": [],
    }
    messages.append(assistant_message)

    for tool_call in tool_calls:
        try:
            function_name = tool_call.function.name
            function_to_call = tool_functions.get(function_name)
            if function_to_call is None:
                logger.warning(f"Unknown tool requested: {function_name}")
                continue

            arguments_json = tool_call.function.arguments
            arguments_dict = json.loads(arguments_json or "{}")

            logger.info(f"tool_call: {function_name=} {arguments_dict=}")
            maybe_result = function_to_call(**arguments_dict)
            # If result is awaitable, await it
            tool_result = (
                await maybe_result
                if inspect.isawaitable(maybe_result)
                else maybe_result
            )
        except Exception as e:
            logger.exception(f"tool_call: {function_name=}, {e=}")
            tool_result = {"status": "error", "payload": str(e)}

        messages.append(
            {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(tool_result),
            }
        )

    followup = await litellm.acompletion(
        model=model, api_key=api_key, messages=messages
    )
    logger.info(f"completion: followup_raw_response={str(followup)[:200]}")
    follow_choice = followup["choices"][0]["message"]
    if (content := follow_choice.get("content")) is not None:
        return content.strip()

    return ""

import inspect
import json
from logging import getLogger
from typing import Any, TypedDict

import litellm

from . import tools as tools_module
from .i18n import Lang
from .tools import get_tools

TOOL_FUNCTIONS: dict[str, Any] = {
    name: func
    for name, func in inspect.getmembers(tools_module)
    if hasattr(func, "__is_tool__")
}

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
    # Build messages for LiteLLM
    messages = _build_litellm_messages_from_gradio_history(message, history, lang)

    # Log function arguments (except api_key for security)
    logger.info(f"completion: {model=} {message[:30]=} {history[-3:]=} {lang=}")

    response = litellm.completion(
        model=model,
        api_key=api_key,
        messages=messages,
        tools=get_tools(),
        tool_choice="auto",
    )

    # Log raw response (truncate to avoid log flooding)
    logger.info(f"completion: raw_response={str(response)[:200]}")

    first_choice = response["choices"][0]["message"]
    content = first_choice.get("content")

    # If content is None, the assistant likely wants to call a tool
    if content is None:
        # Litellm may return pydantic objects, ensure we can always iterate
        tool_calls = (
            first_choice.get("tool_calls", [])
            if isinstance(first_choice, dict)
            else getattr(first_choice, "tool_calls", [])
        )

        logger.info(f"completion: {tool_calls=}")

        # Build an assistant message to represent the tool call as part of the chat history
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": "",  # content is usually empty for tool calls
            "tool_calls": [],
        }

        messages.append(assistant_message)

        # Execute each tool call sequentially and append the results to the conversation
        for call in tool_calls:
            # Extract data depending on the object/dict type
            if hasattr(call, "function"):
                function_name = call.function.name
                arguments_json = call.function.arguments
                call_id = call.id
            else:
                function_name = call["function"]["name"]
                arguments_json = call["function"]["arguments"]
                call_id = call["id"]

            try:
                arguments_dict = json.loads(arguments_json or "{}")
            except json.JSONDecodeError:
                arguments_dict = {}

            # Look up and call the local python function
            tool_func = TOOL_FUNCTIONS.get(function_name)
            if tool_func is None:
                logger.warning(f"Unknown tool requested: {function_name}")
                tool_result = {
                    "status": "error",
                    "payload": f"Unknown tool: {function_name}",
                }
            else:
                # Log function call arguments
                logger.info(f"tool_call: {function_name=} {arguments_dict=}")

                try:
                    tool_result = tool_func(**arguments_dict)
                except Exception as e:
                    tool_result = {"status": "error", "payload": str(e)}

            # Log function return value
            logger.info(f"tool_return: {function_name=} {tool_result=}")

            # Append tool call descriptor for assistant message (OpenAI spec)
            assistant_message["tool_calls"].append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "arguments": arguments_json,
                    },
                }
            )

            # Append the actual tool response message
            messages.append(
                {
                    "tool_call_id": call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result),
                }
            )

        # Request the model again, now that the tool results are in the chat history
        followup_response = litellm.completion(
            model=model,
            api_key=api_key,
            messages=messages,
        )

        logger.info(f"completion: followup_raw_response={str(followup_response)[:200]}")

        followup_choice = followup_response["choices"][0]["message"]
        followup_content = (
            followup_choice.get("content")
            if isinstance(followup_choice, dict)
            else getattr(followup_choice, "content", "")
        )

        result = (followup_content or "").strip()
        logger.info(f"completion: followup {result[:100]=}")
        return result

import base64
import inspect
import json
from logging import getLogger
from typing import Any, AsyncGenerator, Literal, Mapping, TypedDict

import litellm

from .i18n import Lang
from .system_prompt import SYSTEM_PROMPT
from .tools import get_context, tool_functions, tools
from .types.api_key import ApiKey

# To Update models, use search-available models like o4-mini.
# INSTRUCTION: When updating the model, refer to the URL.
Provider = Literal["openai", "gemini", "anthropic", "tutorial"]
ModelConfig = TypedDict("model", {"provider": Provider, "model": str, "default": bool})
model_configs: list[ModelConfig] = [
    # https://platform.openai.com/docs/models
    # https://docs.cursor.com/settings/models
    # https://docs.litellm.ai/docs/providers/openai
    {"provider": "openai", "model": "gpt-5", "default": True},
    {"provider": "openai", "model": "gpt-5-mini", "default": False},
    {"provider": "openai", "model": "gpt-5-nano", "default": False},
    # https://docs.litellm.ai/docs/providers/gemini
    # https://ai.google.dev/gemini-api/docs/models
    {"provider": "gemini", "model": "gemini-2.5-flash-preview-04-17", "default": True},
    {"provider": "gemini", "model": "gemini-2.5-pro-preview-05-06", "default": False},
    {"provider": "gemini", "model": "gemini-2.0-flash", "default": False},
    {"provider": "gemini", "model": "gemini-2.0-flash-lite", "default": False},
    # https://docs.anthropic.com/en/docs/about-claude/models/all-models
    {"provider": "anthropic", "model": "claude-3-7-sonnet-20250219", "default": False},
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "default": True},
    # Debug provider to show the tutorial
    {"provider": "tutorial", "model": "Tutorial", "default": True},
]


logger = getLogger(__name__)


class GradioInputMessage(TypedDict):
    text: str  # Can be empty string but never None
    files: list[str]


class GradioHistoryMessage(TypedDict):
    role: str
    metadata: Any
    content: str
    options: Any


class OpenAIChatCompletionMessages(TypedDict):
    role: str
    content: str
    # TODO: Tools, etc... from https://platform.openai.com/docs/api-reference/chat


def _build_messages(
    model: str,
    user_message: GradioHistoryMessage,
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
        updated = {"role": message["role"]}
        if isinstance(message["content"], str):
            updated["content"] = message["content"]
        elif isinstance(message["content"], tuple):
            updated["content"] = []
            for content in message["content"]:
                if isinstance(content, str) and content.startswith("/"):
                    base64_image = base64.b64encode(open(content, "rb").read()).decode(
                        "utf-8"
                    )
                    updated["content"].append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        }
                    )
                else:
                    pass

        messages.append(updated)

    content = []
    if user_message["text"]:
        content.append({"type": "text", "text": user_message["text"]})
    if user_message["files"]:
        for file in user_message["files"]:
            with open(file, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{base64_image}",
                    }
                )

    messages.append({"role": "user", "content": content})
    return messages


async def completion_stream(
    model: str,
    api_key: ApiKey,
    message: GradioInputMessage,
    history: list[GradioHistoryMessage],
    lang: Lang,
) -> AsyncGenerator[str, None]:
    logger.info(f"{model=} {api_key=} {message=} {history[-3:]=} {lang=}")

    messages = _build_messages(model, message, history, lang)

    messages.append(
        {
            "role": "system",
            "content": json.dumps({"context": await get_context()}),
        }
    )

    first_params = {
        "model": model,
        "messages": messages,
        "stream": True,
        "tools": tools,
        "tool_choice": "auto",
    }
    logger.info(f"litellm.acompletion: {first_params=}")

    first_stream = await litellm.acompletion(**first_params, api_key=api_key.reveal())

    # We reconstruct the full assistant message while streaming
    collected_content: list[str] = []
    # key = index of the tool call
    collected_tool_calls: dict[int, dict[str, Any]] = {}

    async for chunk in first_stream:
        choice_delta = chunk["choices"][0]["delta"]

        # Handle normal content tokens
        if (token := choice_delta.get("content")) is not None:
            collected_content.append(token)
            # Immediately forward the token to the caller
            yield token

        # Handle streaming tool-call deltas (name / arguments arrive in pieces)
        if (tool_call_deltas := choice_delta.get("tool_calls")) is not None:
            for tc in tool_call_deltas:
                tc_dict = _dump_tool_call_delta(tc)

                index = tc_dict.get("index", 0)
                entry = collected_tool_calls.setdefault(
                    index,
                    {
                        "id": tc_dict.get("id", ""),
                        "type": tc_dict.get("type", "function"),
                        "function": {"name": "", "arguments": ""},
                    },
                )

                # id can be provided multiple times – always update to most recent
                if "id" in tc_dict:
                    entry["id"] = tc_dict["id"]

                # type can also be sent multiple times – keep latest, required by OpenAI
                if "type" in tc_dict:
                    entry["type"] = tc_dict["type"]

                if "function" in tc_dict:
                    func_delta = tc_dict["function"]
                    entry_func = entry["function"]
                    # Some providers return the nested function delta as an object too.
                    if not isinstance(func_delta, Mapping):
                        func_delta = _dump_tool_call_delta(func_delta)

                    entry_func["name"] += func_delta.get("name", "")
                    entry_func["arguments"] += func_delta.get("arguments", "")

    # Build the assistant message reconstructed from the streamed chunks
    assistant_message: dict[str, Any] = {
        "role": "assistant",
        "content": "".join(collected_content) if collected_content else None,
    }

    if collected_tool_calls:
        assistant_message["tool_calls"] = list(collected_tool_calls.values())

    messages.append(assistant_message)

    if "tool_calls" not in assistant_message:
        return

    for tool_call in assistant_message["tool_calls"]:
        function_name: str = tool_call["function"]["name"]
        function_to_call = tool_functions.get(function_name)
        if function_to_call is None:
            logger.warning(f"Unknown tool requested: {function_name}")
            continue

        arguments_json: str = tool_call["function"].get("arguments", "")
        try:
            arguments_dict = json.loads(arguments_json or "{}")
        except json.JSONDecodeError:  # pragma: no cover – guard against bad JSON
            logger.exception(f"Failed to decode JSON arguments: {arguments_json}")
            arguments_dict = {}

        logger.info(f"{function_name=} {arguments_dict=}")

        maybe_result = function_to_call(**arguments_dict)
        tool_result = (
            await maybe_result if inspect.isawaitable(maybe_result) else maybe_result
        )

        messages.append(
            {
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": function_name,
                "content": json.dumps(tool_result),
            }
        )

    second_params = {
        "model": model,
        "messages": messages,
        "tools": [],
        "tool_choice": "none",
        "stream": True,
    }
    logger.info(f"litellm.acompletion: {second_params=}")
    second_stream = await litellm.acompletion(**second_params, api_key=api_key.reveal())

    async for chunk in second_stream:
        choice_delta = chunk["choices"][0]["delta"]
        if (token := choice_delta.get("content")) is not None:
            yield token


def _dump_tool_call_delta(delta: Any) -> dict[str, Any]:
    """Return a plain dict representation of a tool-call delta.

    LiteLLM can return either `dict` or a *pydantic* BaseModel (e.g.
    `ChatCompletionDeltaToolCall`).  We normalise both cases into `dict` so
    that the rest of the code can rely on `.get()` access without special
    handling.
    """

    # Fast-path: already a mapping
    if isinstance(delta, Mapping):
        return dict(delta)

    # Newer LiteLLM versions expose a pydantic BaseModel.  Prefer the
    # Pydantic-v2 `model_dump()` API if available, otherwise fallback to v1
    # `.dict()`.
    if hasattr(delta, "model_dump"):
        return delta.model_dump(exclude_none=True, exclude_unset=True)
    if hasattr(delta, "dict"):
        return delta.dict(exclude_none=True, exclude_unset=True)  # type: ignore[arg-type]

    # As a safeguard, cast to str so that unexpected types still yield a value
    logger.warning(f"Unexpected tool call delta type: {type(delta)} -> {delta}")
    return {}

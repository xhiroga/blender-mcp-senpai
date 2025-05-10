import inspect
import json
from logging import getLogger
from typing import Any, AsyncGenerator, TypedDict

import litellm

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


async def completion_stream(
    model: str,
    api_key: str,
    message: str,
    history: list[GradioHistoryMessage],
    lang: Lang,
) -> AsyncGenerator[str, None]:
    """Yield the assistant's response incrementally using OpenAI compatible streaming.

    Compared to :pyfunc:`completion`, this function sets ``stream=True`` when
    calling the LLM and immediately yields any new ``delta.content`` tokens.

    * If the model decides to invoke a *tool*, the first pass of streaming will
      end with ``finish_reason == 'tool_calls'``. Once all tool-call deltas have
      been reconstructed, the tool is executed and its result appended to the
      conversation. A second, non-tool completion is then requested – this one
      is also streamed and its tokens are forwarded to the caller.
    * When no tool call is requested, tokens are simply forwarded as-is.
    """

    logger.info(f"[stream] {model=} {message[:30]=} {history[-3:]=} {lang=}")

    messages = _build_litellm_messages_from_gradio_history(message, history, lang)

    # ------------------------------------------------------------------
    # 1st completion – let the model decide whether it wants to call a tool
    # ------------------------------------------------------------------
    first_stream = await litellm.acompletion(
        model=model,
        api_key=api_key,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        stream=True,
    )

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
                index = tc.get("index", 0)
                entry = collected_tool_calls.setdefault(
                    index,
                    {"id": tc.get("id", ""), "function": {"name": "", "arguments": ""}},
                )

                # id can be provided multiple times – always update to most recent
                if "id" in tc:
                    entry["id"] = tc["id"]

                if "function" in tc:
                    func_delta = tc["function"]
                    entry_func = entry["function"]
                    entry_func["name"] += func_delta.get("name", "")
                    entry_func["arguments"] += func_delta.get("arguments", "")

    # Build the assistant message reconstructed from the streamed chunks
    assistant_message: dict[str, Any] = {
        "role": "assistant",
        "content": "".join(collected_content) if collected_content else None,
    }

    if collected_tool_calls:
        assistant_message["tool_calls"] = list(collected_tool_calls.values())

    messages.append(assistant_message)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Tool execution phase (if any tool was requested)
    # ------------------------------------------------------------------
    if "tool_calls" not in assistant_message:
        # No tool calls – we are done
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

    # ------------------------------------------------------------------
    # 2nd completion – assistant responds after the tool execution
    # ------------------------------------------------------------------
    second_stream = await litellm.acompletion(
        model=model,
        api_key=api_key,
        messages=messages,
        tools=[],
        tool_choice="none",
        stream=True,
    )

    async for chunk in second_stream:
        choice_delta = chunk["choices"][0]["delta"]
        if (token := choice_delta.get("content")) is not None:
            yield token

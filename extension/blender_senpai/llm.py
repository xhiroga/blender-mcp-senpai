import litellm

from .i18n import Lang
from .tools import get_tools

SYSTEM_PROMPT = """
You are a helpful assistant.
"""


def _build_litellm_messages_from_gradio_history(
    user_message: str, history: list[tuple[str, str]], lang: Lang = "en"
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "system",
            "content": f"Language: {lang}",
        },
    ]

    # TODO: フォーマット確認
    for user, assistant in history:
        messages.append({"role": "user", "content": user})
        messages.append({"role": "assistant", "content": assistant})

    messages.append({"role": "user", "content": user_message})
    return messages


def completion(
    model: str,
    api_key: str,
    message: str,
    history: list[tuple[str, str]],
    lang: Lang,
    max_tokens: int,
    temperature: float,
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

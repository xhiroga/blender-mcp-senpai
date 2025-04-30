import logging
from typing import Literal, Optional

import gradio as gr
import litellm

# To Update models, use search-available models like o4-mini.
# INSTRUCTION: When updating the model, refer to the URL.
Provider = Literal["openai", "gemini", "anthropic", "deepseek"]
models: dict[Provider, list[str]] = {
    # https://docs.litellm.ai/docs/providers/openai
    "openai": [
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-1106",
        "gpt-3.5-turbo-16k",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4",
        "gpt-4-0314",
        "gpt-4-0613",
        "gpt-4-32k",
        "gpt-4-32k-0613",
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "o4-mini",
    ],
    # https://docs.litellm.ai/docs/providers/gemini
    # https://ai.google.dev/gemini-api/docs/models
    "gemini": ["gemini-2.5-flash-preview-04-17"],
    # https://docs.litellm.ai/docs/providers/anthropic
    # https://docs.anthropic.com/en/docs/models
    "anthropic": ["claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"],
    # https://docs.litellm.ai/docs/providers/deepseek
    # https://docs.anthropic.com/en/docs/about-claude/models/all-models
    "deepseek": ["deepseek-chat"],
}

# 初期化: ロギング設定
logging.basicConfig(level=logging.INFO)

# グローバル変数としてAPIキーを管理
current_api_keys: dict[str, Optional[str]] = {p: None for p in models.keys()}
enabled_models: dict[str, bool] = {m: True for m in models["openai"]}
current_model_name: str = "gpt-3.5-turbo"


def _build_messages(
    user_message: str, history: list[tuple[str, str]]
) -> list[dict[str, str]]:
    """Gradioのhistoryをlitellmのmessagesフォーマットに変換する。"""
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": "あなたはBlenderの利用をサポートするAIアシスタントです。回答は日本語で行ってください。",
        }
    ]

    # 過去の対話を追加
    for user, assistant in history:
        messages.append({"role": "user", "content": user})
        messages.append({"role": "assistant", "content": assistant})

    # 最新のユーザーメッセージ
    messages.append({"role": "user", "content": user_message})
    return messages


def update_api_settings(*args) -> str:
    """API設定を更新し、結果を返す"""
    global current_api_keys, enabled_models, current_model_name

    # APIキーを辞書に変換
    api_keys = {p: k for p, k in zip(models.keys(), args[:-2])}
    enabled = args[-2]
    model_name = args[-1]

    current_api_keys = api_keys
    for m in enabled_models:
        enabled_models[m] = m in enabled
    current_model_name = model_name
    return "API設定を更新しました。"


def chat_function(message: str, history: list[tuple[str, str]]):
    """litellmを使ってLLMに問い合わせ、応答を返す。"""
    provider = "openai"  # 今回はopenaiのみ
    api_key = current_api_keys.get(provider)
    if not api_key:
        return "APIキーが設定されていません。設定タブでAPIキーを設定してください。"
    messages = _build_messages(message, history)
    try:
        response = litellm.completion(
            model=current_model_name,
            api_key=api_key,
            messages=messages,
        )
        assistant_message: str = response["choices"][0]["message"]["content"].strip()
        return assistant_message
    except Exception as e:
        logging.exception("LLM呼び出し中にエラーが発生しました")
        return f"エラーが発生しました: {e}"


# API設定タブのUI
with gr.Blocks(title="Blender MCP Senpai", theme="soft") as chat_interface:
    gr.Markdown("# Blender MCP Senpai")
    gr.Markdown("BlenderとAIのコラボレーションツール")

    with gr.Tabs():
        with gr.TabItem("チャット"):
            chatbot = gr.ChatInterface(
                chat_function,
                title="",
                description="",
                type="messages",
            )

        with gr.TabItem("API設定"):
            gr.Markdown("## 1. 有効化するモデルを選択")
            enabled_models_input = gr.CheckboxGroup(
                choices=models["openai"],
                value=[m for m, v in enabled_models.items() if v],
                label="有効化モデル",
            )
            gr.Markdown("## 2. プロバイダーごとのAPIキー設定")
            api_key_inputs = {}
            for provider in models.keys():
                api_key_inputs[provider] = gr.Textbox(
                    label=f"{provider.capitalize()} APIキー", type="password"
                )
            model_name_input = gr.Dropdown(
                choices=models["openai"],
                value="gpt-3.5-turbo",
                label="デフォルトモデル",
            )
            save_button = gr.Button("設定を保存")
            status_output = gr.Textbox(label="ステータス", interactive=False)

            save_button.click(
                update_api_settings,
                inputs=[
                    *[api_key_inputs[p] for p in models.keys()],
                    enabled_models_input,
                    model_name_input,
                ],
                outputs=status_output,
            )


if __name__ == "__main__":
    chat_interface.launch()

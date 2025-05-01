import logging
from typing import Literal, Optional

import gradio as gr
import litellm

from .history_db import generate_conversation_id, log_message

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
# APIキーの検証状態を管理
api_key_valid: dict[str, bool] = {p: False for p in models.keys()}

# コンバーセーションIDをセッション単位で生成
conversation_id = generate_conversation_id()


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
        # ユーザーメッセージを DB に記録
        try:
            log_message(conversation_id, "user", message)
        except Exception as db_exc:  # pragma: no cover
            logging.debug("DB logging failed (user msg): %s", db_exc)

        response = litellm.completion(
            model=current_model_name,
            api_key=api_key,
            messages=messages,
        )
        assistant_message: str = response["choices"][0]["message"]["content"].strip()

        # アシスタントの応答も DB に記録
        try:
            log_message(conversation_id, "assistant", assistant_message)
        except Exception as db_exc:  # pragma: no cover
            logging.debug("DB logging failed (assistant msg): %s", db_exc)

        return assistant_message
    except Exception as e:
        logging.exception("LLM呼び出し中にエラーが発生しました")
        return f"エラーが発生しました: {e}"


def verify_api_key(provider: str, api_key: str) -> tuple[str, list[str]]:
    """APIキーの有効性を確認する"""
    global api_key_valid

    if not api_key:
        api_key_valid[provider] = False
        return "APIキーが入力されていません", []

    try:
        # プロバイダーごとのデフォルトモデルを使用
        default_models = {
            "openai": "gpt-3.5-turbo",
            "anthropic": "claude-3-5-haiku-20241022",
            "gemini": "gemini-2.5-flash-preview-04-17",
            "deepseek": "deepseek-chat",
        }

        # 簡単なテストメッセージを送信
        response = litellm.completion(
            model=default_models[provider],
            api_key=api_key,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5,
        )
        api_key_valid[provider] = True

        # 有効なモデルのリストを返す
        available_models = []
        for p, is_valid in api_key_valid.items():
            if is_valid:
                available_models.extend(models[p])

        return "✅ APIキーは有効です", available_models
    except Exception as e:
        api_key_valid[provider] = False
        logging.exception(f"{provider}のAPIキー検証中にエラーが発生")
        return f"❌ エラー: {str(e)}", []


def update_enabled_models() -> list[str]:
    """有効なAPIキーを持つプロバイダーのモデルのみを選択可能にする"""
    available_models = []
    for provider, is_valid in api_key_valid.items():
        if is_valid:
            available_models.extend(models[provider])
    return available_models


def update_model_choices(available_models: list[str]) -> dict:
    """モデル選択の更新とUIの更新"""
    return {
        "choices": available_models,
        "value": [],  # 選択をリセット
    }


# API設定タブのUI
with gr.Blocks(title="Blender MCP Senpai", theme="soft") as chat_interface:
    gr.Markdown("# Blender MCP Senpai")
    gr.Markdown("BlenderとAIのコラボレーションツール")

    with gr.Tabs():
        with gr.TabItem("チャット"):
            with gr.Row():
                model_selector = gr.Dropdown(
                    choices=models["openai"],
                    value=current_model_name,
                    label="使用するモデル",
                    container=False,
                )
            chatbot = gr.ChatInterface(
                chat_function,
                title="",
                description="",
                type="messages",
            )

            def update_current_model(model_name: str):
                global current_model_name
                current_model_name = model_name
                return f"モデルを{model_name}に変更しました"

            model_selector.change(
                fn=update_current_model,
                inputs=[model_selector],
                outputs=[gr.Textbox(visible=False)],
            )

        with gr.TabItem("API設定"):
            with gr.Column():
                gr.Markdown("## 1. プロバイダーごとのAPIキー設定")
                api_key_inputs = {}
                api_key_status = {}

                # モデル選択セクション（先に定義）
                gr.Markdown("## 2. 有効化するモデル")
                enabled_models_input = gr.CheckboxGroup(
                    choices=[],  # 初期状態では空
                    value=[],
                    label="有効化モデル",
                )

                # APIキー入力セクション
                for provider in models.keys():
                    with gr.Row(equal_height=True):
                        api_key_inputs[provider] = gr.Textbox(
                            label=f"{provider.capitalize()} APIキー",
                            type="password",
                            lines=1,
                            scale=8,
                            placeholder=f"{provider.capitalize()}のAPIキーを入力してください",
                        )
                        verify_btn = gr.Button(
                            "Verify",
                            scale=1,
                            min_width=60,
                            variant="secondary",
                            size="sm",
                        )
                        api_key_status[provider] = gr.Textbox(
                            label="ステータス", interactive=False, scale=3
                        )

                        verify_btn.click(
                            fn=verify_api_key,
                            inputs=[
                                gr.Textbox(value=provider, visible=False),
                                api_key_inputs[provider],
                            ],
                            outputs=[
                                api_key_status[provider],
                                enabled_models_input,  # 直接CheckboxGroupを更新
                            ],
                        )

                # 保存ボタンセクション
                save_button = gr.Button("設定を保存")
                status_output = gr.Textbox(label="ステータス", interactive=False)

                save_button.click(
                    update_api_settings,
                    inputs=[
                        *[api_key_inputs[p] for p in models.keys()],
                        enabled_models_input,
                    ],
                    outputs=status_output,
                )


if __name__ == "__main__":
    chat_interface.launch()

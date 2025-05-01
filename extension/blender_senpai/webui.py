import logging
from typing import Literal, Optional

import gradio as gr
import litellm

from .history_db import generate_conversation_id, log_message
from .i18n import Lang, t

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


# ブラウザの言語設定を取得するための関数
def get_browser_lang(request: gr.Request) -> Lang:
    """ブラウザの言語設定を取得し、対応する言語コードを返す"""
    accept_lang = request.headers.get("Accept-Language", "en").split(",")[0].lower()
    lang_map = {
        "ja": "ja",
        "zh": "zh",
        "de": "de",
        "fr": "fr",
        "es": "es",
        "pt": "pt",
        "ru": "ru",
    }
    return lang_map.get(accept_lang[:2], "en")


def _build_messages(
    user_message: str, history: list[tuple[str, str]], lang: Lang = "en"
) -> list[dict[str, str]]:
    """Gradioのhistoryをlitellmのmessagesフォーマットに変換する。"""
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": t("system_prompt", lang),
        }
    ]

    # 過去の対話を追加
    for user, assistant in history:
        messages.append({"role": "user", "content": user})
        messages.append({"role": "assistant", "content": assistant})

    # 最新のユーザーメッセージ
    messages.append({"role": "user", "content": user_message})
    return messages


def update_api_settings(*args, request: gr.Request) -> str:
    """API設定を更新し、結果を返す"""
    global current_api_keys, enabled_models, current_model_name
    lang = get_browser_lang(request)

    # APIキーを辞書に変換
    api_keys = {p: k for p, k in zip(models.keys(), args[:-2])}
    enabled = args[-2]
    model_name = args[-1]

    current_api_keys = api_keys
    for m in enabled_models:
        enabled_models[m] = m in enabled
    current_model_name = model_name
    return t("msg_settings_saved", lang)


def chat_function(message: str, history: list[tuple[str, str]], request: gr.Request):
    """litellmを使ってLLMに問い合わせ、応答を返す。"""
    provider = "openai"  # 今回はopenaiのみ
    api_key = current_api_keys.get(provider)
    if not api_key:
        return t("msg_api_key_required", get_browser_lang(request))

    lang = get_browser_lang(request)
    messages = _build_messages(message, history, lang)
    print(f"{lang=}")

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
        return f"Error: {e}"


def verify_api_key(
    provider: str, api_key: str, request: gr.Request
) -> tuple[str, list[str]]:
    """APIキーの有効性を確認する"""
    global api_key_valid
    lang = get_browser_lang(request)

    if not api_key:
        api_key_valid[provider] = False
        return t("msg_api_key_required", lang), []

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

        return t("msg_api_key_valid", lang), available_models
    except Exception:
        api_key_valid[provider] = False
        logging.exception(f"{provider}のAPIキー検証中にエラーが発生")
        return t("msg_api_key_invalid", lang), []


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


class Translator:
    def __init__(self):
        self.components: list[tuple[gr.Component, dict[str, str]]] = []

    def reg(self, component: gr.Component, mapping: dict[str, str]):
        self.components.append((component, mapping))

    def patched(self, request: gr.Request):
        """
        In gradio 4.x and later, do not use `.update()` when updating components. Instead, you can return the components themselves.
        Components are treated like patches. They are not simple replacements.
        https://www.gradio.app/guides/blocks-and-event-listeners#updating-component-configurations
        """
        lang = get_browser_lang(request)
        patches = []
        for component, mapping in self.components:
            translated = {k: t(v, lang) for k, v in mapping.items()}
            patches.append(component.__class__(**translated))
        return patches

    def outputs(self):
        return [component for component, _ in self.components]


with gr.Blocks(title=t("app_title"), theme="soft") as interface:
    tr = Translator()
    tr.reg(gr.Markdown(**{"value": "app_title"}), {"value": "app_title"})
    tr.reg(gr.Markdown(t("app_desc")), {"value": "app_desc"})

    with gr.Tabs():
        with gr.TabItem(t("tab_chat")) as tab:
            tr.reg(tab, {"label": "tab_chat"})
            with gr.Row():
                model_selector = gr.Dropdown(
                    choices=models["openai"],
                    value=current_model_name,
                    label=t("label_model"),
                    container=False,
                )
                tr.reg(model_selector, {"label": "label_model"})
            chatbot = gr.ChatInterface(
                chat_function,
                title="",
                description="",
                type="messages",
            )

            def update_current_model(model_name: str):
                global current_model_name
                current_model_name = model_name
                return f"Model changed to {model_name}"

            model_selector.change(
                fn=update_current_model,
                inputs=[model_selector],
                outputs=[gr.Textbox(visible=False)],
            )

        with gr.Tab(t("tab_api")) as tab:
            tr.reg(tab, {"label": "tab_api"})
            with gr.Row():
                with gr.Column():
                    # OpenAI API Key
                    openai_key = gr.Textbox(
                        label=t("label_api_key"),
                        placeholder=t("msg_api_key_required"),
                        type="password",
                        value=current_api_keys["openai"],
                    )
                    tr.reg(openai_key, {"label": "label_api_key"})
                    openai_status = gr.Textbox(
                        label=t("label_status"),
                        interactive=False,
                    )
                    tr.reg(openai_status, {"label": "label_status"})
                    openai_verify = gr.Button(t("label_verify"))
                    tr.reg(openai_verify, {"value": "label_verify"})

                    # Anthropic API Key
                    anthropic_key = gr.Textbox(
                        label=t("label_api_key"),
                        placeholder=t("msg_api_key_required"),
                        type="password",
                        value=current_api_keys["anthropic"],
                    )
                    tr.reg(anthropic_key, {"label": "label_api_key"})
                    anthropic_status = gr.Textbox(
                        label=t("label_status"),
                        interactive=False,
                    )
                    tr.reg(anthropic_status, {"label": "label_status"})
                    anthropic_verify = gr.Button(t("label_verify"))

                    # Gemini API Key
                    gemini_key = gr.Textbox(
                        label=t("label_api_key"),
                        placeholder=t("msg_api_key_required"),
                        type="password",
                        value=current_api_keys["gemini"],
                    )
                    tr.reg(gemini_key, {"label": "label_api_key"})
                    gemini_status = gr.Textbox(
                        label=t("label_status"),
                        interactive=False,
                    )
                    tr.reg(gemini_status, {"label": "label_status"})
                    gemini_verify = gr.Button(t("label_verify"))

                    # Deepseek API Key
                    deepseek_key = gr.Textbox(
                        label=t("label_api_key"),
                        placeholder=t("msg_api_key_required"),
                        type="password",
                        value=current_api_keys["deepseek"],
                    )
                    tr.reg(deepseek_key, {"label": "label_api_key"})
                    deepseek_status = gr.Textbox(
                        label=t("label_status"),
                        interactive=False,
                    )
                    deepseek_verify = gr.Button(t("label_verify"))

                with gr.Column():
                    # モデル選択
                    model_choices = gr.CheckboxGroup(
                        label=t("label_model"),
                        choices=update_enabled_models(),
                        value=list(enabled_models.keys()),
                    )
                    tr.reg(model_choices, {"label": "label_model"})
                    current_model = gr.Dropdown(
                        label=t("label_model"),
                        choices=update_enabled_models(),
                        value=current_model_name,
                    )
                    tr.reg(current_model, {"label": "label_model"})
                    save_settings = gr.Button(t("label_save"))
                    tr.reg(save_settings, {"value": "label_save"})

    interface.load(
        fn=tr.patched,
        inputs=[],
        outputs=tr.outputs(),
    )


if __name__ == "__main__":
    interface.launch()

import logging
import uuid
from typing import Any, Callable, Literal, TypeAlias, TypedDict, Union

import gradio as gr
import litellm

from .i18n import Lang, t
from .llm import completion
from .repositories.api_key_repository import ApiKeyRepository
from .repositories.history_repository import HistoryRepository

# To Update models, use search-available models like o4-mini.
# INSTRUCTION: When updating the model, refer to the URL.
Provider = Literal["openai", "gemini", "anthropic", "deepseek"]
ModelConfig = TypedDict("model", {"provider": Provider, "model": str, "default": bool})
model_configs: list[ModelConfig] = [
    # https://docs.litellm.ai/docs/providers/openai
    {"provider": "openai", "model": "gpt-3.5-turbo", "default": True},
    {"provider": "openai", "model": "gpt-3.5-turbo-0613", "default": False},
    {"provider": "openai", "model": "gpt-3.5-turbo-1106", "default": False},
    {"provider": "openai", "model": "gpt-3.5-turbo-16k", "default": False},
    {"provider": "openai", "model": "gpt-3.5-turbo-16k-0613", "default": False},
    {"provider": "openai", "model": "gpt-4", "default": False},
    {"provider": "openai", "model": "gpt-4-0314", "default": False},
    {"provider": "openai", "model": "gpt-4-0613", "default": False},
    # https://docs.litellm.ai/docs/providers/deepseek
    # https://docs.anthropic.com/en/docs/about-claude/models/all-models
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "default": True},
    {"provider": "anthropic", "model": "claude-3-7-sonnet-20250219", "default": False},
    # https://docs.litellm.ai/docs/providers/gemini
    # https://ai.google.dev/gemini-api/docs/models
    {"provider": "gemini", "model": "gemini-2.5-flash-preview-04-17", "default": True},
]


class State(TypedDict):
    api_keys: dict[Provider, str]
    enabled_models: list[ModelConfig]
    current_model: ModelConfig
    current_conversation_id: str
    current_lang: Lang


def get_initial_state() -> State:
    api_keys = ApiKeyRepository.list()
    providers = list(api_keys.keys())
    enabled_models = [
        model for model in model_configs if model["provider"] in providers
    ]
    return {
        "api_keys": api_keys,
        "enabled_models": enabled_models,
        "current_model": enabled_models[0] if enabled_models else {},
        "current_lang": "en",
        "current_conversation_id": str(uuid.uuid4()),
    }


ComponentValue: TypeAlias = Any
HandlerOutputs: TypeAlias = tuple[Union[ComponentValue, gr.Component]]
Handler: TypeAlias = Callable[[*tuple[ComponentValue], gr.Request], HandlerOutputs]


# 初期化: ロギング設定
logging.basicConfig(level=logging.INFO)


def chat_function(
    message: str,
    history: list[tuple[str, str]],
    state: State,
    request: gr.Request,
):
    conversation_id = state["current_conversation_id"]
    HistoryRepository.create(conversation_id, "user", message)
    lang = state["current_lang"]

    provider = state["current_model"]["provider"]
    api_key = state["api_keys"][provider]
    if not api_key:
        return t("msg_api_key_required", lang)

    assistant_message = completion(
        model=state["current_model"]["model"],
        api_key=api_key,
        message=message,
        history=history,
        lang=lang,
    )
    return assistant_message


chat_function: Handler = chat_function


def register_api_key_with(provider: Provider) -> Handler:
    def register_api_key(
        state: State, api_key: str, selected_model: str, _request: gr.Request
    ) -> tuple[State, str, bool, gr.Dropdown]:
        try:
            default_model = next(
                filter(
                    lambda m: m["provider"] == provider and m["default"], model_configs
                )
            )
            litellm.completion(
                model=default_model["model"],
                api_key=api_key,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            ApiKeyRepository.save(provider, api_key)
            api_keys = ApiKeyRepository.list()
            providers = list(api_keys.keys())
            enabled_models = [
                model for model in model_configs if model["provider"] in providers
            ]
            current_model = (
                selected_model
                if selected_model in enabled_models
                else enabled_models[0]
            )

            new_state = {
                "api_keys": api_keys,
                "enabled_models": enabled_models,
                "current_model": current_model,
            }
            result = "OK"
            is_registered = True
            model_selector = gr.Dropdown(
                choices=enabled_models,
                value=current_model,
            )

            return new_state, result, is_registered, model_selector

        except Exception:
            return gr.skip(), "NG", False, gr.skip()

    return register_api_key


def update_current_model(state: State, model_name: str, _request: gr.Request) -> State:
    state["current_model"] = next(
        filter(lambda m: m["model"] == model_name, model_configs)
    )
    return state


update_current_model: Handler = update_current_model


class Translator:
    def __init__(self):
        self.originals: list[tuple[gr.Component, dict[str, str]]] = []

    def reg(self, component: gr.Component, mapping: dict[str, str]):
        self.originals.append((component, mapping))

    def _get_lang(self, request: gr.Request) -> Lang:
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

    def patch(
        self, state: State, request: gr.Request
    ) -> tuple[State, *tuple[gr.Component]]:
        """
        In gradio 4.x and later, do not use `.update()` when updating components. Instead, you can return the components themselves.
        Components are treated like patches. They are not simple replacements.
        https://www.gradio.app/guides/blocks-and-event-listeners#updating-component-configurations
        """
        lang = self._get_lang(request)
        state["current_lang"] = lang

        patches = []
        for component, mapping in self.components:
            translated = {k: t(v, lang) for k, v in mapping.items()}
            # The Textbox specified in output cannot be edited unless interactive = True is explicitly set.
            # https://www.gradio.app/guides/blocks-and-event-listeners#event-listeners-and-interactivity
            # Incidentally, using `hasattr(component, “interactive”)` to determine this is inappropriate.
            # There are components that have interactive as a property but do not accept it as an argument.
            # Furthermore, even if a text box is editable on the UI, it will internally hold None if interactive is not specified when instantiated.
            # And if None is specified as an argument, it will become uneditable.
            if isinstance(component, gr.Textbox):
                translated["interactive"] = component.interactive
            patches.append(component.__class__(**translated))
        return state, *patches

    def components(self):
        return [component for component, _ in self.originals]


with gr.Blocks(title=t("app_title"), theme="soft") as interface:
    state = gr.State(get_initial_state())

    tr = Translator()
    tr.reg(gr.Markdown(**{"value": "app_title"}), {"value": "app_title"})
    tr.reg(gr.Markdown(t("app_desc")), {"value": "app_desc"})

    with gr.Tabs():
        with gr.TabItem(t("tab_chat")) as tab:
            tr.reg(tab, {"label": "tab_chat"})

            model_selector = gr.Dropdown(
                choices=[],
                value=state["current_model"]["model"],
                label=t("label_model"),
                container=False,
            )
            tr.reg(model_selector, {"label": "label_model"})

            model_selector.change(
                fn=update_current_model,
                inputs=[state, model_selector],
                outputs=[state],
            )

        with gr.Tab(t("tab_api")) as tab:
            tr.reg(tab, {"label": "tab_api"})
            with gr.Row():
                openai_key = gr.Textbox(
                    value=state["api_keys"]["openai"],
                    type="password",
                    placeholder=t("msg_api_key_required"),
                    label="OpenAI API Key",
                    interactive=True,
                    submit_btn=t("label_verify"),
                )
                openai_key_checkbox = gr.Checkbox(
                    value=False,
                    interactive=False,
                )
            tr.reg(
                openai_key,
                {
                    "placeholder": "msg_api_key_required",
                    "submit_btn": "label_verify",
                },
            )

            anthropic_key = gr.Textbox(
                type="password",
                placeholder=t("msg_api_key_required"),
                label=t("label_api_key"),
                value=state["api_keys"]["anthropic"],
                interactive=True,
            )
            tr.reg(anthropic_key, {"placeholder": "msg_api_key_required"})
            anthropic_status = gr.Textbox(
                label=t("label_status"),
                interactive=False,
            )
            tr.reg(anthropic_status, {"label": "label_status"})
            anthropic_verify = gr.Button(t("label_verify"))

            result = gr.Textbox(
                label=t("label_status"),
                interactive=False,
            )
            tr.reg(result, {"label": "label_status"})

            openai_key.submit(
                fn=register_api_key_with("openai"),
                inputs=[state, openai_key, model_selector],
                outputs=[state, result, openai_key_checkbox, model_selector],
            )

    interface.load(
        fn=tr.patch,
        inputs=[state],
        outputs=[state, *tr.originals()],
    )


if __name__ == "__main__":
    interface.launch()

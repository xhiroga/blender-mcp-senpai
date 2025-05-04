import json
import uuid
from dataclasses import dataclass, replace
from logging import getLogger
from typing import Any, Callable, Literal, TypeAlias, TypedDict, Union

import gradio as gr
import litellm

from .i18n import Lang, t
from .llm import completion
from .log_config import configure
from .repositories.api_key_repository import ApiKeyRepository
from .repositories.history_repository import HistoryRepository

logger = getLogger(__name__)

# To Update models, use search-available models like o4-mini.
# INSTRUCTION: When updating the model, refer to the URL.
Provider = Literal["openai", "gemini", "anthropic", "tutorial"]
ModelConfig = TypedDict("model", {"provider": Provider, "model": str, "default": bool})
model_configs: list[ModelConfig] = [
    # https://docs.cursor.com/settings/models
    # https://docs.litellm.ai/docs/providers/openai
    {"provider": "openai", "model": "gpt-4o", "default": False},
    {"provider": "openai", "model": "gpt-4o-mini", "default": True},
    {"provider": "openai", "model": "gpt-4.1", "default": False},
    {"provider": "openai", "model": "o1", "default": False},
    {"provider": "openai", "model": "o1-mini", "default": False},
    {"provider": "openai", "model": "o3", "default": False},
    {"provider": "openai", "model": "o3-mini", "default": False},
    {"provider": "openai", "model": "o4-mini", "default": False},
    # https://docs.anthropic.com/en/docs/about-claude/models/all-models
    {"provider": "anthropic", "model": "claude-3-7-sonnet-20250219", "default": False},
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "default": True},
    # https://docs.litellm.ai/docs/providers/gemini
    # https://ai.google.dev/gemini-api/docs/models
    {"provider": "gemini", "model": "gemini-2.5-flash-preview-04-17", "default": True},
    {"provider": "gemini", "model": "gemini-2.5-pro-preview-03-25", "default": False},
    {"provider": "gemini", "model": "gemini-2.0-flash", "default": False},
    {"provider": "gemini", "model": "gemini-2.0-flash-lite", "default": False},
    # Debug provider to show the tutorial
    {"provider": "tutorial", "model": "Tutorial", "default": True},
]


@dataclass(frozen=True)
class State:
    api_keys: dict[Provider, str]
    enabled_models: tuple[ModelConfig, ...]
    current_model: ModelConfig
    current_conversation_id: str
    current_lang: Lang


# region Helper Functions


def get_initial_state() -> State:
    api_keys = ApiKeyRepository.list()
    providers = list(api_keys.keys())
    enabled_models = tuple(
        model
        for model in model_configs
        if model["provider"] == "tutorial" or model["provider"] in providers
    )
    return State(
        api_keys=api_keys,
        enabled_models=enabled_models,
        current_model=enabled_models[0],
        current_lang="en",
        current_conversation_id=str(uuid.uuid4()),
    )


def masked(state: State) -> State:
    return replace(
        state,
        api_keys={k: f"{v[:5]}..." for k, v in state.api_keys.items() if v},
    )


# endregion

# region Event Handlers
# While React declares the UI as a callback to the state, Gradio declares the UI elements themselves.
# Therefore, event handlers can directly reference and update UI = Component. This may be convenient for applications with only one screen.
# However, considering future expansion, this application describes event handlers as pure functions.
# Specifically, state (State and Component) is only accepted as arguments. Additionally, by declaring the event handlers before the interface, we avoid directly referencing the Component.

# When updating state, we use `replace()` for the following reasons:
# 1. Unlike applying differences to a Component, the values passed to outputs are replaced, even if they are dictionaries.
# 2. Therefore, it is better to create a patch instance that updates the existing State values, but updating properties would update the original instance.

ComponentValue: TypeAlias = Any
HandlerOutputs: TypeAlias = tuple[Union[ComponentValue, gr.Component]]
Handler: TypeAlias = Callable[[*tuple[ComponentValue], gr.Request], HandlerOutputs]


async def chat_function(
    message: str,
    history: list[tuple[str, str]],
    state: State,
    request: gr.Request,
):
    """As described in `mainthreadify()`, the results of `bpy` update operations are obtained by waiting in an asynchronous loop.
    In Gradio, when a callback is a synchronous function, Starlette internally offloads the function to a worker thread.
    `anyio.to_thread.run_sync(fn, *args, **kwargs)  # Code is for illustration`
    Therefore, callbacks that indirectly operate on `bpy` should be written as asynchronous functions.
    """
    logger.info(f"{message=}, {history=}, {state=}, {request=}")

    conversation_id = state.current_conversation_id
    HistoryRepository.create(conversation_id, "user", message)
    lang = state.current_lang

    provider = state.current_model["provider"]

    if provider == "tutorial":
        return t("tutorial", lang)

    api_key = state.api_keys.get(provider)
    if not api_key:
        return t("msg_api_key_required", lang)

    model = f"{provider}/{state.current_model['model']}"
    logger.info(f"{model=}")
    assistant_message = await completion(
        model=model,
        api_key=api_key,
        message=message,
        history=history,
        lang=lang,
    )
    HistoryRepository.create(conversation_id, "assistant", assistant_message)

    logger.info(f"{assistant_message=}")
    return assistant_message


# Alias with proper Handler type so static analysis passes
chat_function_alias: Handler = chat_function


def register_api_key_with(provider: Provider) -> Handler:
    def register_api_key(
        state: State, api_key: str, current_model: str, _request: gr.Request
    ) -> tuple[State, str, bool, gr.Dropdown]:
        logger.info(f"{provider=}, api_key={api_key[:5]}..., {current_model=}")
        try:
            default_model = next(
                filter(
                    lambda m: m["provider"] == provider and m["default"], model_configs
                )
            )
            model = f"{provider}/{default_model['model']}"
            litellm.completion(
                model=model,
                api_key=api_key,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            ApiKeyRepository.save(provider, api_key)
            api_keys = ApiKeyRepository.list()
            providers = list(api_keys.keys())
            enabled_models = tuple(
                model for model in model_configs if model["provider"] in providers
            )
            current_model = (
                current_model if current_model in enabled_models else enabled_models[0]
            )

            new_state = replace(
                state,
                api_keys=api_keys,
                enabled_models=enabled_models,
                current_model=current_model,
            )

            result = "OK"
            is_registered = True
            model_selector = gr.Dropdown(
                choices=[
                    (f"{model['model']} ({model['provider']})", json.dumps(model))
                    for model in enabled_models
                ],
                value=json.dumps(current_model),
            )

            # AttributeError: 'Dropdown' object has no attribute 'value'
            logger.info(
                f"{masked(new_state)=}, {result=}, {is_registered=}, {model_selector.change=}"
            )
            return new_state, result, is_registered, model_selector

        except Exception as e:
            logger.exception(e)
            return gr.skip(), f"NG: {e}", False, gr.skip()

    return register_api_key


def update_current_model(state: State, model_json: str, _request: gr.Request) -> State:
    model = json.loads(model_json)
    return replace(
        state,
        current_model=next(
            filter(
                lambda m: m["model"] == model["model"]
                and m["provider"] == model["provider"],
                model_configs,
            )
        ),
    )


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
        new_state = replace(state, current_lang=lang)

        patches = []
        for component, mapping in self.originals:
            translated = {k: t(v, lang) for k, v in mapping.items()}
            # The Textbox specified in output cannot be edited unless interactive = True is explicitly set.
            # https://www.gradio.app/guides/blocks-and-event-listeners#event-listeners-and-interactivity
            # Incidentally, using `hasattr(component, "interactive")` to determine this is inappropriate.
            # There are components that have interactive as a property but do not accept it as an argument.
            # Furthermore, even if a text box is editable on the UI, it will internally hold None if interactive is not specified when instantiated.
            # And if None is specified as an argument, it will become uneditable.
            if isinstance(component, gr.Textbox):
                translated["interactive"] = component.interactive
            patches.append(component.__class__(**translated))
        return new_state, *patches

    def components(self):
        return [component for component, _ in self.originals]


# endregion

CLASS_CHECKBOX_LARGE = "checkbox-large"
ROW_HEIGHT = 40
css = f"""
.{CLASS_CHECKBOX_LARGE} input[type='checkbox'] {{
    width: {ROW_HEIGHT}px;
    height: {ROW_HEIGHT}px;
    border: 2px solid var(--neutral-300, #d1d5db);
}}
footer {{visibility: hidden}}
"""
# Hide footer: https://github.com/gradio-app/gradio/issues/6696

with gr.Blocks(title=t("app_title"), theme="soft", css=css) as interface:
    state = gr.State(get_initial_state())

    tr = Translator()
    tr.reg(gr.Markdown(**{"value": "app_title"}), {"value": "app_title"})

    with gr.Tabs():
        with gr.TabItem(t("tab_chat")) as tab:
            tr.reg(tab, {"label": "tab_chat"})

            model_selector = gr.Dropdown(
                choices=[
                    (f"{model['model']} ({model['provider']})", json.dumps(model))
                    for model in state.value.enabled_models
                ],
                value=json.dumps(state.value.current_model),
                label=t("label_model"),
                container=False,
            )
            tr.reg(model_selector, {"label": "label_model"})

            model_selector.change(
                fn=update_current_model,
                inputs=[state, model_selector],
                outputs=[state],
            )

            chat_interface = gr.ChatInterface(
                fn=chat_function_alias,
                type="messages",
                additional_inputs=[state],
            )
            chat_interface.chatbot.min_height = "60vh"

        with gr.Tab(t("tab_api")) as tab:
            tr.reg(tab, {"label": "tab_api"})

            openai_label = gr.Label(
                value="OpenAI API Key",
                show_label=False,
                container=False,
            )

            with gr.Row(equal_height=True):
                openai_key_checkbox = gr.Checkbox(
                    value=False,
                    label="",
                    show_label=False,
                    container=False,
                    scale=1,
                    interactive=False,
                    elem_classes=CLASS_CHECKBOX_LARGE,
                )

                openai_key = gr.Textbox(
                    value=state.value.api_keys.get("openai", ""),
                    type="password",
                    placeholder="sk-.........",
                    show_label=False,
                    container=False,
                    interactive=True,
                    scale=16,
                )

                openai_key_verify_button = gr.Button(
                    value=t("label_verify"),
                    variant="primary",
                    scale=2,
                )
                tr.reg(openai_key_verify_button, {"value": "label_verify"})

            anthropic_label = gr.Label(
                value="Anthropic API Key",
                show_label=False,
                container=False,
            )

            with gr.Row(equal_height=True):
                anthropic_key_checkbox = gr.Checkbox(
                    value=False,
                    label="",
                    show_label=False,
                    container=False,
                    scale=1,
                    interactive=False,
                    elem_classes=CLASS_CHECKBOX_LARGE,
                )

                anthropic_key = gr.Textbox(
                    value=state.value.api_keys.get("anthropic", ""),
                    type="password",
                    placeholder="sk-ant-api03-.........",
                    show_label=False,
                    container=False,
                    interactive=True,
                    scale=16,
                )

                anthropic_key_verify_button = gr.Button(
                    value=t("label_verify"),
                    variant="primary",
                    scale=2,
                )
                tr.reg(anthropic_key_verify_button, {"value": "label_verify"})

            gemini_label = gr.Label(
                value="Gemini API Key",
                show_label=False,
                container=False,
            )

            with gr.Row(equal_height=True):
                gemini_key_checkbox = gr.Checkbox(
                    value=False,
                    label="",
                    show_label=False,
                    container=False,
                    scale=1,
                    interactive=False,
                    elem_classes=CLASS_CHECKBOX_LARGE,
                )

                gemini_key = gr.Textbox(
                    value=state.value.api_keys.get("gemini", ""),
                    type="password",
                    placeholder="AIzaSy.........",
                    show_label=False,
                    container=False,
                    interactive=True,
                    scale=16,
                )

                gemini_key_verify_button = gr.Button(
                    value=t("label_verify"),
                    variant="primary",
                    scale=2,
                )
                tr.reg(gemini_key_verify_button, {"value": "label_verify"})

            result = gr.Textbox(
                label=t("label_status"),
                interactive=False,
            )
            tr.reg(result, {"label": "label_status"})

            gr.on(
                triggers=[openai_key.submit, openai_key_verify_button.click],
                fn=register_api_key_with("openai"),
                inputs=[state, openai_key, model_selector],
                outputs=[state, result, openai_key_checkbox, model_selector],
            )

            gr.on(
                triggers=[anthropic_key.submit, anthropic_key_verify_button.click],
                fn=register_api_key_with("anthropic"),
                inputs=[state, anthropic_key, model_selector],
                outputs=[state, result, anthropic_key_checkbox, model_selector],
            )

            gr.on(
                triggers=[gemini_key.submit, gemini_key_verify_button.click],
                fn=register_api_key_with("gemini"),
                inputs=[state, gemini_key, model_selector],
                outputs=[state, result, gemini_key_checkbox, model_selector],
            )

    interface.load(
        fn=tr.patch,
        inputs=[state],
        outputs=[state, *tr.components()],
    )


if __name__ == "__main__":
    configure(mode="standalone")
    interface.launch()

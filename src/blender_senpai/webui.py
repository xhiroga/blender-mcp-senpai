import json
import uuid
from dataclasses import dataclass, replace
from logging import getLogger
from typing import Any, Callable, Literal, TypeAlias, TypedDict, Union

import gradio as gr
import litellm

from .i18n import SUPPORTED_LANGUAGES, Lang, t
from .llm import completion
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
    {"provider": "gemini", "model": "gemini-2.5-pro-preview-05-06", "default": False},
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
    i18n: dict[str, dict[str, str]]


# Gradio's State needs to be serializable, which means it cannot contain Components internally
# Therefore, instead of storing the Component itself, we store the Component's ID and its mapping
i18nc: list[gr.Component] = []


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
        i18n={},
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

# In gradio 4.x and later, do not use `.update()` when updating components. Instead, you can return the components themselves.
# Components are treated like patches. They are not simple replacements.
# https://www.gradio.app/guides/blocks-and-event-listeners#updating-component-configurations


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
    logger.info(f"{message=}, {history=}, {masked(state)=}, {request=}")

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


# Since Gradio event listeners cannot receive Component itself as an argument, passing it through a higher-order function.
def register_api_key_with(provider: Provider, button: gr.Button) -> Handler:
    def register_api_key(
        state: State, api_key: str, _request: gr.Request
    ) -> tuple[State, gr.Button, str, gr.Dropdown]:
        logger.info(f"{provider=}, {masked(state)=}, api_key={api_key[:5]}...")
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
                state.current_model
                if state.current_model in enabled_models
                else enabled_models[0]
            )

            new_button_label = "label_verified"
            new_i18n = state.i18n.copy()
            new_i18n[button._id] = {"value": new_button_label}
            new_state = replace(
                state,
                api_keys=api_keys,
                enabled_models=enabled_models,
                current_model=current_model,
                i18n=new_i18n,
            )

            new_button = gr.Button(
                value=t(new_button_label, state.current_lang),
                variant="primary",
            )

            result = "OK"

            model_selector = gr.Dropdown(
                choices=[
                    (f"{model['model']} ({model['provider']})", json.dumps(model))
                    for model in enabled_models
                ],
                value=json.dumps(current_model),
            )

            logger.info(
                f"{masked(new_state)=}, {new_button=}, {result=},{model_selector.change=}"
            )
            return new_state, new_button, result, model_selector

        except Exception as e:
            logger.exception(e)
            new_button_label = "label_verify_error"
            new_i18n = state.i18n.copy()
            new_i18n[button._id] = {"value": new_button_label}
            new_state = replace(
                state,
                i18n=new_i18n,
            )
            new_button = gr.Button(
                value=t(new_button_label, state.current_lang),
                variant="stop",
            )
            return new_state, new_button, f"NG: {e}", gr.skip()

    return register_api_key


def change_api_key_with(provider: Provider, button: gr.Button) -> Handler:
    def change_api_key(state: State, _request: gr.Request) -> tuple[State, gr.Button]:
        new_button_label = "label_verify"
        new_i18n = state.i18n.copy()
        new_i18n[button._id] = {"value": new_button_label}
        new_state = replace(
            state,
            i18n=new_i18n,
        )
        return new_state, gr.Button(
            value=t(new_button_label, state.current_lang),
            variant="huggingface",
        )

    return change_api_key


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


def translate_components(
    state: State, request: gr.Request
) -> tuple[State, *tuple[gr.Component]]:
    # Since some components like gr.Tab cannot be used as inputs, components must be passed through global variables rather than as arguments
    global i18nc

    def _get_lang(request: gr.Request) -> Lang:
        accept_lang = request.headers.get("Accept-Language", "en").split(",")[0].lower()
        return accept_lang[:2] if accept_lang[:2] in SUPPORTED_LANGUAGES else "en"

    lang = _get_lang(request)
    new_state = replace(state, current_lang=lang)

    patched = []
    for component in i18nc:
        for id, mapping in state.i18n.items():
            if id == component._id:
                translated = {k: t(v, lang) for k, v in mapping.items()}
                # The Textbox specified in output cannot be edited unless interactive = True is explicitly set.
                # https://www.gradio.app/guides/blocks-and-event-listeners#event-listeners-and-interactivity
                # Incidentally, using `hasattr(component, "interactive")` to determine this is inappropriate.
                # There are components that have interactive as a property but do not accept it as an argument.
                # Furthermore, even if a text box is editable on the UI, it will internally hold None if interactive is not specified when instantiated.
                # And if None is specified as an argument, it will become uneditable.
                if isinstance(component, gr.Textbox):
                    translated["interactive"] = component.interactive
                patched.append(component.__class__(**translated))

    return new_state, *patched


# endregion

css = """
footer {visibility: hidden}
"""
# Hide footer: https://github.com/gradio-app/gradio/issues/6696
with gr.Blocks(title=t("app_title"), theme="soft", css=css) as interface:
    state = gr.State(get_initial_state())

    title = gr.Markdown(**{"value": t("app_title")})
    state.value.i18n[title._id] = {"value": "app_title"}
    i18nc.append(title)

    with gr.Tabs():
        with gr.TabItem(t("tab_chat")) as tab:
            state.value.i18n[tab._id] = {"label": "tab_chat"}
            i18nc.append(tab)
            model_selector = gr.Dropdown(
                choices=[
                    (f"{model['model']} ({model['provider']})", json.dumps(model))
                    for model in state.value.enabled_models
                ],
                value=json.dumps(state.value.current_model),
                label=t("label_model"),
                container=False,
            )
            state.value.i18n[model_selector._id] = {"label": "label_model"}
            i18nc.append(model_selector)

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
            state.value.i18n[tab._id] = {"label": "tab_api"}
            i18nc.append(tab)

            openai_label = gr.Label(
                value="OpenAI API Key",
                show_label=False,
                container=False,
            )
            with gr.Row(equal_height=True):
                openai_key = state.value.api_keys.get("openai", "")
                openai_key_label = "label_verified" if openai_key else "label_verify"
                openai_key_textbox = gr.Textbox(
                    value=openai_key,
                    type="password",
                    placeholder="sk-.........",
                    show_label=False,
                    container=False,
                    interactive=True,
                    scale=8,
                )
                openai_key_verify_button = gr.Button(
                    value=t(openai_key_label),
                    variant="primary" if openai_key else "huggingface",
                    scale=1,
                )
                state.value.i18n[openai_key_verify_button._id] = {
                    "value": openai_key_label
                }
                i18nc.append(openai_key_verify_button)

            anthropic_label = gr.Label(
                value="Anthropic API Key",
                show_label=False,
                container=False,
            )
            with gr.Row(equal_height=True):
                anthropic_key = state.value.api_keys.get("anthropic", "")
                anthropic_key_label = (
                    "label_verified" if anthropic_key else "label_verify"
                )
                anthropic_key_textbox = gr.Textbox(
                    value=anthropic_key,
                    type="password",
                    placeholder="sk-ant-api03-.........",
                    show_label=False,
                    container=False,
                    interactive=True,
                    scale=8,
                )
                anthropic_key_verify_button = gr.Button(
                    value=t(anthropic_key_label),
                    variant="primary" if anthropic_key else "huggingface",
                    scale=1,
                )
                state.value.i18n[anthropic_key_verify_button._id] = {
                    "value": anthropic_key_label
                }
                i18nc.append(anthropic_key_verify_button)

            gemini_label = gr.Label(
                value="Gemini API Key",
                show_label=False,
                container=False,
            )
            with gr.Row(equal_height=True):
                gemini_key = state.value.api_keys.get("gemini", "")
                gemini_key_label = "label_verified" if gemini_key else "label_verify"
                gemini_key_textbox = gr.Textbox(
                    value=gemini_key,
                    type="password",
                    placeholder="AIzaSy.........",
                    show_label=False,
                    container=False,
                    interactive=True,
                    scale=8,
                )
                gemini_key_verify_button = gr.Button(
                    value=t(gemini_key_label),
                    variant="primary" if gemini_key else "huggingface",
                    scale=1,
                )
                state.value.i18n[gemini_key_verify_button._id] = {
                    "value": gemini_key_label
                }
                i18nc.append(gemini_key_verify_button)

            api_key_interfaces = [
                ("openai", openai_key_textbox, openai_key_verify_button),
                ("anthropic", anthropic_key_textbox, anthropic_key_verify_button),
                ("gemini", gemini_key_textbox, gemini_key_verify_button),
            ]

            result = gr.Textbox(
                label=t("label_status"),
                interactive=False,
            )
            state.value.i18n[result._id] = {"label": "label_status"}
            i18nc.append(result)

            for provider, textbox, verify_button in api_key_interfaces:
                gr.on(
                    triggers=[textbox.submit, verify_button.click],
                    fn=register_api_key_with(provider, verify_button),
                    inputs=[state, textbox],
                    outputs=[state, verify_button, result, model_selector],
                )

                gr.on(
                    triggers=[textbox.change],
                    fn=change_api_key_with(provider, verify_button),
                    inputs=[state],
                    outputs=[state, verify_button],
                )

    # Known issue: Textbox values that are not specified are also reset during redraw
    interface.load(
        fn=translate_components,
        inputs=[state],
        outputs=[state, *i18nc],
    )

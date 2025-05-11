import json
import uuid
from dataclasses import dataclass, replace
from logging import getLogger
from typing import Any, AsyncGenerator, Callable, TypeAlias, Union

import gradio as gr
import litellm

from .i18n import t
from .llm import (
    GradioInputMessage,
    ModelConfig,
    Provider,
    completion_stream,
    model_configs,
)
from .repositories.api_key_repository import ApiKeyRepository
from .repositories.history_repository import HistoryRepository
from .types.api_key import ApiKey

logger = getLogger(__name__)


@dataclass(frozen=True)
class State:
    """Values that are unique per session.
    Conversely, values that are fixed per PC and need to be persisted, like API keys, are managed globally to prevent inconsistencies between frontend and database.
    """

    current_model: ModelConfig
    current_conversation_id: str
    current_lang: str


# region Helper Functions


def get_enabled_models() -> tuple[ModelConfig, ...]:
    api_keys = ApiKeyRepository.list()
    providers = list(api_keys.keys())
    return tuple(
        model
        for model in model_configs
        if model["provider"] == "tutorial" or model["provider"] in providers
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

# In gradio 4.x and 5.x, do not use `.update()` when updating components. Instead, you can return the components themselves.
# Components are treated like patches. They are not simple replacements.
# https://www.gradio.app/guides/blocks-and-event-listeners#updating-component-configurations


ComponentValue: TypeAlias = Any
HandlerOutputs: TypeAlias = tuple[Union[ComponentValue, gr.Component]]
Handler: TypeAlias = Callable[[*tuple[ComponentValue], gr.Request], HandlerOutputs]


def onload(state: State, _request: gr.Request) -> tuple[State, gr.Component]:
    logger.info(f"{state=}")
    enabled_models = get_enabled_models()
    current_model = enabled_models[0]
    model_selector = gr.Dropdown(
        choices=[
            (f"{model['model']} ({model['provider']})", json.dumps(model))
            for model in enabled_models
        ],
        value=json.dumps(current_model),
    )
    new_state = replace(state, current_model=current_model)
    logger.info(f"{new_state=}, {model_selector=}")
    return new_state, model_selector


async def chat_function(
    message: GradioInputMessage,
    history: list[tuple[str, str]],
    state: State,
    request: gr.Request,
) -> "AsyncGenerator[str, None]":
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
        tutorial_msg = t("tutorial", lang)
        HistoryRepository.create(conversation_id, "assistant", tutorial_msg)
        yield tutorial_msg
        return

    api_key = ApiKeyRepository.get(provider)
    if not api_key:
        error_msg = t("msg_api_key_required", lang)
        HistoryRepository.create(conversation_id, "assistant", error_msg)
        yield error_msg
        return

    model = f"{provider}/{state.current_model['model']}"
    logger.info(f"{model=}")
    tokens: list[str] = []
    async for token in completion_stream(
        model=model,
        api_key=api_key,
        message=message,
        history=history,
        lang=lang,
    ):
        tokens.append(token)
        partial = "".join(tokens)
        yield partial

    assistant_message = "".join(tokens)
    HistoryRepository.create(conversation_id, "assistant", assistant_message)

    logger.info(f"{assistant_message=}")


# Since Gradio event listeners cannot receive Component itself as an argument, passing it through a higher-order function.
def register_api_key_with(
    provider: Provider, textbox: gr.Textbox, button: gr.Button
) -> Handler:
    def register_api_key(
        state: State, api_key: str, _request: gr.Request
    ) -> tuple[State, str | gr.Component, gr.Button, str, gr.Dropdown]:
        api_key = ApiKey(api_key)
        logger.info(f"{provider=}, {state=}, api_key={api_key=}")
        try:
            default_model = next(
                filter(
                    lambda m: m["provider"] == provider and m["default"], model_configs
                )
            )
            model = f"{provider}/{default_model['model']}"
            litellm.completion(
                model=model,
                api_key=api_key.reveal(),
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            ApiKeyRepository.save(provider, api_key)
            enabled_models = get_enabled_models()
            current_model = (
                state.current_model
                if state.current_model in enabled_models
                else enabled_models[0]
            )

            new_state = replace(state, current_model=current_model)

            new_textbox_value = api_key.reveal()

            new_button = gr.Button(
                value=t("label_verified", state.current_lang), variant="primary"
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
                f"{new_state=}, {new_button=}, {result=},{model_selector.change=}"
            )
            return new_state, new_textbox_value, new_button, result, model_selector

        except Exception as e:
            logger.exception(e)
            new_button = gr.Button(
                value=t("label_verify_error", state.current_lang), variant="stop"
            )
            return gr.skip(), gr.skip(), new_button, f"NG: {e}", gr.skip()

    return register_api_key


def change_api_key_with(provider: Provider, button: gr.Button) -> Handler:
    def change_api_key(state: State, _request: gr.Request) -> tuple[gr.Button]:
        return gr.Button(value=t("label_verify", state.current_lang), variant="stop")

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


# endregion


def interface(locale: str):
    """At Gradio startup, browser language settings cannot be referenced.
    To reference them, they must be obtained in the `load()` event.
    However, since this would become quite complex, we reference Blender's locale instead.
    """
    lang = locale[:2]

    # Hide footer: https://github.com/gradio-app/gradio/issues/6696
    css = """
    footer {visibility: hidden}
    """

    with gr.Blocks(title=t("app_title"), theme="citrus", css=css) as interface:
        # State values should only be accessed inside event listeners.
        # This is because when a non-Callable is passed to State, the value at server startup remains fixed until the process ends.
        # Honestly, I never figured out the correct way to pass Callable. The function is referenced before being called, both inside Components and event listeners...
        enabled_models = get_enabled_models()
        state = gr.State(
            State(
                current_model=enabled_models[0],
                current_conversation_id=str(uuid.uuid4()),
                current_lang=lang,
            )
        )

        gr.Markdown(**{"value": f"# {t('app_title', lang)}"})

        with gr.Tabs():
            with gr.TabItem(t("tab_chat", lang)):
                # In Gradio, values other than Callable are only updated at server startup
                # Therefore, when referencing anything other than config files (especially DB), we basically pass a Callable
                # Note: Since Callable cannot be passed to Dropdown's choices, we can only update it on load
                model_selector = gr.Dropdown(
                    choices=[""],
                    value="",
                    label=t("label_model", lang),
                    container=False,
                )

                model_selector.change(
                    fn=update_current_model,
                    inputs=[state, model_selector],
                    outputs=[state],
                )

                chat_interface = gr.ChatInterface(
                    fn=chat_function,
                    multimodal=True,
                    type="messages",
                    additional_inputs=[state],
                )
                chat_interface.chatbot.min_height = "60vh"

            with gr.Tab(t("tab_api", lang)):
                gr.Label(
                    value="OpenAI API Key",
                    show_label=False,
                    container=False,
                )
                with gr.Row(equal_height=True):
                    openai_key_textbox = gr.Textbox(
                        value=lambda: (api_key := ApiKeyRepository.get("openai"))
                        and api_key.reveal()
                        or "",
                        type="password",
                        placeholder="sk-.........",
                        show_label=False,
                        container=False,
                        interactive=True,
                        scale=8,
                    )
                    openai_key_verify_button = gr.Button(
                        value=lambda: t(
                            (
                                "label_verified"
                                if ApiKeyRepository.get("openai")
                                else "label_verify"
                            ),
                            lang,
                        ),
                        variant="primary"
                        if ApiKeyRepository.get("openai")
                        else "huggingface",
                        scale=1,
                    )

                gr.Label(
                    value="Anthropic API Key",
                    show_label=False,
                    container=False,
                )
                with gr.Row(equal_height=True):
                    anthropic_key_textbox = gr.Textbox(
                        value=lambda: (api_key := ApiKeyRepository.get("anthropic"))
                        and api_key.reveal()
                        or "",
                        type="password",
                        placeholder="sk-ant-api03-.........",
                        show_label=False,
                        container=False,
                        interactive=True,
                        scale=8,
                    )
                    anthropic_key_verify_button = gr.Button(
                        value=lambda: t(
                            (
                                "label_verified"
                                if ApiKeyRepository.get("anthropic")
                                else "label_verify"
                            ),
                            lang,
                        ),
                        variant="primary"
                        if ApiKeyRepository.get("anthropic")
                        else "huggingface",
                        scale=1,
                    )

                gr.Label(
                    value="Gemini API Key",
                    show_label=False,
                    container=False,
                )
                with gr.Row(equal_height=True):
                    gemini_key_textbox = gr.Textbox(
                        value=lambda: (api_key := ApiKeyRepository.get("gemini"))
                        and api_key.reveal()
                        or "",
                        type="password",
                        placeholder="AIzaSy.........",
                        show_label=False,
                        container=False,
                        interactive=True,
                        scale=8,
                    )
                    gemini_key_verify_button = gr.Button(
                        value=lambda: t(
                            (
                                "label_verified"
                                if ApiKeyRepository.get("gemini")
                                else "label_verify"
                            ),
                            lang,
                        ),
                        variant="primary"
                        if ApiKeyRepository.get("gemini")
                        else "huggingface",
                        scale=1,
                    )

                api_key_interfaces = [
                    ("openai", openai_key_textbox, openai_key_verify_button),
                    ("anthropic", anthropic_key_textbox, anthropic_key_verify_button),
                    ("gemini", gemini_key_textbox, gemini_key_verify_button),
                ]

                result = gr.Textbox(
                    label=t("label_status", lang),
                    interactive=False,
                )

                for provider, textbox, verify_button in api_key_interfaces:
                    gr.on(
                        triggers=[textbox.submit, verify_button.click],
                        fn=register_api_key_with(provider, textbox, verify_button),
                        inputs=[state, textbox],
                        outputs=[state, textbox, verify_button, result, model_selector],
                    )

                    gr.on(
                        triggers=[textbox.change],
                        fn=change_api_key_with(provider, verify_button),
                        inputs=[state],
                        outputs=[verify_button],
                    )

        interface.load(
            fn=onload,
            inputs=[state],
            outputs=[state, model_selector],
        )

    return interface

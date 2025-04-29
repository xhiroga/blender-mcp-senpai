import gradio as gr


def chat_function(message, history):
    return f"あなたは「{message}」と言いました。Blenderとの連携機能は開発中です。"


chat_interface = gr.ChatInterface(
    chat_function,
    title="Blender MCP Senpai",
    description="BlenderとAIのコラボレーションツール",
    theme="soft",
)

if __name__ == "__main__":
    chat_interface.launch()

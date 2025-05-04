from typing import Literal

Lang = Literal["en", "ja", "zh", "de", "fr", "es", "pt", "ru"]

_TEXTS: dict[Lang, dict[str, str]] = {
    "en": {
        "app_title": "# Blender Senpai",
        "app_desc": "Collaboration tool for Blender and AI",
        "tab_chat": "Chat",
        "tab_api": "API Settings",
        "label_model": "Model",
        "label_api_key": "API Key",
        "label_verify": "Verify",
        "label_status": "Status",
        "label_save": "Save Settings",
        "label_openai_api_key": "OpenAI API Key",
        "label_anthropic_api_key": "Anthropic API Key",
        "label_gemini_api_key": "Gemini API Key",
        "msg_api_key_required": "Please set your API key in the settings tab.",
        "msg_api_key_valid": "✅ API key is valid",
        "msg_api_key_invalid": "❌ Error: Invalid API key",
        "msg_settings_saved": "Settings have been updated.",
        "system_prompt": "You are an AI assistant supporting Blender users. Please respond in English.",
        "tutorial": """Select a model. If the model does not appear, please register your API key.
        You can get the API key from the following URL.
        OpenAI: https://platform.openai.com/api-keys
        Anthropic: https://console.anthropic.com/settings/keys
        Gemini: https://aistudio.google.com/apikey
        """,
    },
    "ja": {
        "app_title": "# Blender Senpai",
        "app_desc": "BlenderとAIのコラボレーションツール",
        "tab_chat": "チャット",
        "tab_api": "API設定",
        "label_model": "モデル",
        "label_api_key": "APIキー",
        "label_verify": "登録",
        "label_status": "ステータス",
        "label_save": "設定を保存",
        "label_openai_api_key": "OpenAI APIキー",
        "label_anthropic_api_key": "Anthropic APIキー",
        "label_gemini_api_key": "Gemini APIキー",
        "msg_api_key_required": "設定タブでAPIキーを設定してください。",
        "msg_api_key_valid": "✅ APIキーは有効です",
        "msg_api_key_invalid": "❌ エラー: APIキーが無効です",
        "msg_settings_saved": "設定を更新しました。",
        "system_prompt": "あなたはBlenderの利用をサポートするAIアシスタントです。回答は日本語で行ってください。",
        "tutorial": """モデルを選択してください。モデルが表示されない場合は、APIキーを登録してください。
        次のURLからAPIキーを取得できます。
        OpenAI: https://platform.openai.com/api-keys
        Anthropic: https://console.anthropic.com/settings/keys
        Gemini: https://aistudio.google.com/apikey
        """,
    },
    "zh": {
        "app_title": "# Blender Senpai",
        "app_desc": "Blender与AI协作工具",
        "tab_chat": "聊天",
        "tab_api": "API设置",
        "label_model": "模型",
        "label_api_key": "API密钥",
        "label_verify": "验证",
        "label_status": "状态",
        "label_save": "保存设置",
        "label_openai_api_key": "OpenAI API密钥",
        "label_anthropic_api_key": "Anthropic API密钥",
        "label_gemini_api_key": "Gemini API密钥",
        "msg_api_key_required": "请在设置标签页中设置您的API密钥。",
        "msg_api_key_valid": "✅ API密钥有效",
        "msg_api_key_invalid": "❌ 错误: API密钥无效",
        "msg_settings_saved": "设置已更新。",
        "system_prompt": "你是一个支持Blender用户的AI助手。请用中文回答。",
        "tutorial": """选择一个模型。如果模型没有显示，请注册您的API密钥。
        您可以从以下URL获取API密钥。
        OpenAI: https://platform.openai.com/api-keys
        Anthropic: https://console.anthropic.com/settings/keys
        Gemini: https://aistudio.google.com/apikey
        """,
    },
    "de": {
        "app_title": "# Blender Senpai",
        "app_desc": "Kollaborationstool für Blender und KI",
        "tab_chat": "Chat",
        "tab_api": "API-Einstellungen",
        "label_model": "Modell",
        "label_api_key": "API-Schlüssel",
        "label_verify": "Überprüfen",
        "label_status": "Status",
        "label_save": "Einstellungen speichern",
        "label_openai_api_key": "OpenAI API-Schlüssel",
        "label_anthropic_api_key": "Anthropic API-Schlüssel",
        "label_gemini_api_key": "Gemini API-Schlüssel",
        "msg_api_key_required": "Bitte setzen Sie Ihren API-Schlüssel in den Einstellungen.",
        "msg_api_key_valid": "✅ API-Schlüssel ist gültig",
        "msg_api_key_invalid": "❌ Fehler: Ungültiger API-Schlüssel",
        "msg_settings_saved": "Einstellungen wurden aktualisiert.",
        "system_prompt": "Sie sind ein KI-Assistent, der Blender-Benutzer unterstützt. Bitte antworten Sie auf Deutsch.",
        "tutorial": """Wählen Sie ein Modell. Wenn das Modell nicht angezeigt wird, registrieren Sie Ihren API-Schlüssel.
        Sie können den API-Schlüssel von folgenden URLs erhalten.
        OpenAI: https://platform.openai.com/api-keys
        Anthropic: https://console.anthropic.com/settings/keys
        Gemini: https://aistudio.google.com/apikey
        """,
    },
    "fr": {
        "app_title": "# Blender Senpai",
        "app_desc": "Outil de collaboration pour Blender et l'IA",
        "tab_chat": "Chat",
        "tab_api": "Paramètres API",
        "label_model": "Modèle",
        "label_api_key": "Clé API",
        "label_verify": "Vérifier",
        "label_status": "Statut",
        "label_save": "Enregistrer les paramètres",
        "label_openai_api_key": "Clé API OpenAI",
        "label_anthropic_api_key": "Clé API Anthropic",
        "label_gemini_api_key": "Clé API Gemini",
        "msg_api_key_required": "Veuillez définir votre clé API dans l'onglet des paramètres.",
        "msg_api_key_valid": "✅ La clé API est valide",
        "msg_api_key_invalid": "❌ Erreur: Clé API invalide",
        "msg_settings_saved": "Les paramètres ont été mis à jour.",
        "system_prompt": "Vous êtes un assistant IA qui aide les utilisateurs de Blender. Veuillez répondre en français.",
        "tutorial": """Sélectionnez un modèle. Si le modèle n'apparaît pas, veuillez enregistrer votre clé API.
        Vous pouvez obtenir la clé API depuis les URL suivantes.
        OpenAI: https://platform.openai.com/api-keys
        Anthropic: https://console.anthropic.com/settings/keys
        Gemini: https://aistudio.google.com/apikey
        """,
    },
    "es": {
        "app_title": "# Blender Senpai",
        "app_desc": "Herramienta de colaboración para Blender e IA",
        "tab_chat": "Chat",
        "tab_api": "Configuración API",
        "label_model": "Modelo",
        "label_api_key": "Clave API",
        "label_verify": "Verificar",
        "label_status": "Estado",
        "label_save": "Guardar configuración",
        "label_openai_api_key": "Clave API de OpenAI",
        "label_anthropic_api_key": "Clave API de Anthropic",
        "label_gemini_api_key": "Clave API de Gemini",
        "msg_api_key_required": "Por favor, configure su clave API en la pestaña de configuración.",
        "msg_api_key_valid": "✅ La clave API es válida",
        "msg_api_key_invalid": "❌ Error: Clave API inválida",
        "msg_settings_saved": "La configuración ha sido actualizada.",
        "system_prompt": "Eres un asistente de IA que apoya a los usuarios de Blender. Por favor, responde en español.",
        "tutorial": """Seleccione un modelo. Si el modelo no aparece, registre su clave API.
        Puede obtener la clave API desde las siguientes URLs.
        OpenAI: https://platform.openai.com/api-keys
        Anthropic: https://console.anthropic.com/settings/keys
        Gemini: https://aistudio.google.com/apikey
        """,
    },
    "pt": {
        "app_title": "# Blender Senpai",
        "app_desc": "Ferramenta de colaboração para Blender e IA",
        "tab_chat": "Chat",
        "tab_api": "Configurações API",
        "label_model": "Modelo",
        "label_api_key": "Chave API",
        "label_verify": "Verificar",
        "label_status": "Status",
        "label_save": "Salvar configurações",
        "label_openai_api_key": "Chave API OpenAI",
        "label_anthropic_api_key": "Chave API Anthropic",
        "label_gemini_api_key": "Chave API Gemini",
        "msg_api_key_required": "Por favor, defina sua chave API na aba de configurações.",
        "msg_api_key_valid": "✅ A chave API é válida",
        "msg_api_key_invalid": "❌ Erro: Chave API inválida",
        "msg_settings_saved": "As configurações foram atualizadas.",
        "system_prompt": "Você é um assistente de IA que apoia usuários do Blender. Por favor, responda em português.",
        "tutorial": """Selecione um modelo. Se o modelo não aparecer, registre sua chave API.
        Você pode obter a chave API a partir das seguintes URLs.
        OpenAI: https://platform.openai.com/api-keys
        Anthropic: https://console.anthropic.com/settings/keys
        Gemini: https://aistudio.google.com/apikey
        """,
    },
    "ru": {
        "app_title": "# Blender Senpai",
        "app_desc": "Инструмент для совместной работы Blender и ИИ",
        "tab_chat": "Чат",
        "tab_api": "Настройки API",
        "label_model": "Модель",
        "label_api_key": "Ключ API",
        "label_verify": "Проверить",
        "label_status": "Статус",
        "label_save": "Сохранить настройки",
        "label_openai_api_key": "Ключ API OpenAI",
        "label_anthropic_api_key": "Ключ API Anthropic",
        "label_gemini_api_key": "Ключ API Gemini",
        "msg_api_key_required": "Пожалуйста, установите ваш ключ API в настройках.",
        "msg_api_key_valid": "✅ Ключ API действителен",
        "msg_api_key_invalid": "❌ Ошибка: Недействительный ключ API",
        "msg_settings_saved": "Настройки обновлены.",
        "system_prompt": "Вы - ИИ-ассистент, поддерживающий пользователей Blender. Пожалуйста, отвечайте на русском языке.",
        "tutorial": """Выберите модель. Если модель не отображается, зарегистрируйте ваш API-ключ.
        Вы можете получить API-ключ из следующих URL.
        OpenAI: https://platform.openai.com/api-keys
        Anthropic: https://console.anthropic.com/settings/keys
        Gemini: https://aistudio.google.com/apikey
        """,
    },
}


def t(key: str, lang: Lang = "en") -> str:
    return _TEXTS.get(lang, {}).get(key, key)

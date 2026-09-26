"""
Compatibility bridge for legacy gemini_assistant imports.
Redirects to the new SiriAssistant engine powered by local Qwen 2.5 1.5B and neural voice synthesis.
"""

from src.modules.siri_assistant import siri_assistant, SiriAssistant

class GeminiAssistantBridge:
    """Wrapper that routes all calls to siri_assistant."""
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.api_key: str = "local-offline"

    @property
    def model(self) -> str:
        return siri_assistant.model

    @model.setter
    def model(self, val: str):
        siri_assistant.set_model(val)

    @property
    def voice_enabled(self) -> bool:
        return siri_assistant.voice_enabled

    @voice_enabled.setter
    def voice_enabled(self, val: bool):
        siri_assistant.set_voice_enabled(val)

    def load_config(self):
        siri_assistant.load_config()

    def save_config(self):
        siri_assistant.save_config()

    def set_api_key(self, key: str):
        self.api_key = key

    def set_model(self, model: str):
        siri_assistant.set_model(model)

    def set_voice_enabled(self, enabled: bool):
        siri_assistant.set_voice_enabled(enabled)

    def validate_api_key(self, test_key=None):
        status, msg = siri_assistant.check_local_model_status()
        return status, f"Mô hình Local Qwen 2.5 1.5B: {msg}", ["qwen2.5:1.5b"]

    def speak(self, text: str):
        siri_assistant.speak(text)

    def stop_speaking(self):
        siri_assistant.stop_speaking()

    def check_system_action(self, prompt: str):
        return siri_assistant.check_fast_system_action(prompt)

    def query(self, prompt: str, callback=None) -> str:
        return siri_assistant.query(prompt, callback=callback)

gemini_assistant = GeminiAssistantBridge.get_instance()

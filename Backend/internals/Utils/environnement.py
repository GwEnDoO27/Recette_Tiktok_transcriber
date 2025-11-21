import os
from typing import Tuple


def get_environment() -> Tuple[str, str, str]:
    whisper_model = os.getenv("WHISPER_MODEL", "base")
    ollama_model_primary = os.getenv("OLLAMA_MODEL_PRIMARY", "llama3.2")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    return whisper_model, ollama_model_primary, ollama_url

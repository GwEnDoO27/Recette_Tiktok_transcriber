import os
from typing import Optional

import requests  # type: ignore


class WhisperClient:
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url
        self.api_transcribe = f"{base_url}/transcribe"
        self.api_health = f"{base_url}/health"

    def check_connection(self) -> bool:
        try:
            response = requests.get(self.api_health, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Optional[str]:
        """
        Send audio file to external Whisper service for transcription.

        Args:
            audio_path: Path to audio file
            language: Optional language code (None for auto-detect)

        Returns:
            Transcribed text or None on failure
        """
        try:
            params = {}
            if language:
                params["language"] = language

            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
                response = requests.post(
                    self.api_transcribe,
                    files=files,
                    params=params,
                    timeout=300,
                )

            if response.status_code == 200:
                data = response.json()
                return data.get("text", "").strip()
            else:
                print(f"  ✗ Whisper service error: status {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"  ✗ Whisper connection error: {e}")
            return None

import json
from typing import Optional

import requests  # type: ignore


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama client for recipe extraction

        Args:
            base_url (str): Base URL for Ollama API
        """
        self.base_url = base_url
        self.api_generate = f"{base_url}/api/generate"
        self.api_tags = f"{base_url}/api/tags"

    def check_connection(self) -> bool:
        """
        Check if Ollama is running and accessible

        Returns:
            bool: True if connected, False otherwise
        """
        try:
            response = requests.get(self.api_tags, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def list_models(self) -> list:
        """
        List all available models in Ollama

        Returns:
            list: List of model names
        """
        try:
            response = requests.get(self.api_tags, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except requests.exceptions.RequestException:
            return []

    def generate(
        self,
        prompt: str,
        model: str = "llama3.2",
        temperature: float = 0.3,
        format: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate text using Ollama

        Args:
            prompt (str): The prompt to send to the model
            model (str): Model name to use
            temperature (float): Temperature for generation
            format (str): Format of the output (e.g., "json")

        Returns:
            Optional[str]: Generated text or None if failed
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        
        if format:
            payload["format"] = format

        try:
            response = requests.post(self.api_generate, json=payload, timeout=180)

            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                print(f"  ✗ Ollama error: status {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"  ✗ Connection error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON error: {e}")
            return None

    def extract_recipe(
        self, transcription: str, model: str = "llama3.2"
    ) -> Optional[dict]:
        """
        Extract structured recipe from TikTok cooking video transcription

        Args:
            transcription (str): Raw transcription from Whisper
            model (str): Model name to use

        Returns:
            Optional[dict]: Formatted recipe dict or None if failed
        """
        prompt = f"""Tu es un expert en extraction de recettes de cuisine à partir de vidéos TikTok.

MISSION: Extraire une recette structurée à partir de la transcription d'une vidéo TikTok de cuisine.

FORMAT DE SORTIE (JSON UNIQUEMENT):
{{
    "title": "Titre de la recette",
    "category": "Catégorie (ex: Entrée, Plat, Dessert, Boisson, Snack)",
    "ingredients": [
        "quantité ingrédient 1",
        "quantité ingrédient 2"
    ],
    "steps": [
        "étape 1",
        "étape 2"
    ]
}}

RÈGLES STRICTES:
- Sois TRÈS concis.
- Extrais UNIQUEMENT les infos présentes dans la transcription.
- Si une quantité n'est pas mentionnée, écris juste l'ingrédient.
- Reformule les étapes de façon claire et courte.
- Réponds UNIQUEMENT avec le JSON valide.

TRANSCRIPTION:
{transcription}
"""

        print(f"\n{'=' * 60}")
        print(f"EXTRACTION DE RECETTE - {model.upper()}")
        print(f"{'=' * 60}\n")
        print("  → Analyse de la transcription...")

        response_text = self.generate(
            prompt=prompt,
            model=model,
            temperature=0.2,
            format="json",
        )

        if response_text:
            try:
                recipe_json = json.loads(response_text)
                print("  ✓ Extraction terminée (JSON valide)\n")
                return recipe_json
            except json.JSONDecodeError:
                print("  ✗ Erreur: La réponse n'est pas un JSON valide\n")
                return None
        else:
            print("  ✗ Échec de l'extraction\n")
            return None

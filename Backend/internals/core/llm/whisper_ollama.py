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
        self, transcription: str, model: str = "llama3.2", metadata: Optional[dict] = None
    ) -> Optional[dict]:
        """
        Extract structured recipe from TikTok cooking video transcription

        Args:
            transcription (str): Raw transcription from Whisper
            model (str): Model name to use
            metadata (Optional[dict]): Video metadata including description

        Returns:
            Optional[dict]: Formatted recipe dict or None if failed
        """
        # Construire le contexte avec la description si disponible
        context_section = ""
        if metadata and metadata.get("description"):
            context_section = f"""
DESCRIPTION DE LA VIDÉO:
{metadata['description']}

IMPORTANT: Si la description contient déjà des quantités précises pour les ingrédients, utilise-les PRIORITAIREMENT.
La description est souvent plus fiable que la transcription audio pour les quantités exactes.
"""

        prompt = f"""Tu es un expert en extraction de recettes de cuisine à partir de vidéos TikTok et de contenu vidéo parlé.

CONTEXTE: Les vidéos TikTok de cuisine contiennent souvent du bruit (hésitations, répétitions, appels à l'action).
Ton rôle est d'extraire UNIQUEMENT le contenu culinaire pertinent.
{context_section}

FORMAT DE SORTIE (JSON STRICT):
{{
    "title": "Titre descriptif de la recette",
    "category": "Une seule catégorie parmi: Entrée, Plat, Dessert, Boisson, Snack, Accompagnement, Sauce",
    "servings": "Nombre de portions (ex: '4 personnes', '2 portions') OU null si non mentionné",
    "prep_time": "Temps de préparation (ex: '15 min', '1h30') OU null si non mentionné",
    "cook_time": "Temps de cuisson (ex: '20 min', '45 min') OU null si non mentionné",
    "difficulty": "Facile, Moyen ou Difficile OU null si non déductible",
    "ingredients": [
        "quantité + unité + ingrédient (ex: '200g de farine', '3 œufs', '1 pincée de sel')"
    ],
    "steps": [
        "Étape claire et concise avec verbe d'action"
    ],
    "tips": [
        "Conseils ou astuces mentionnés (optionnel)"
    ]
}}

RÈGLES D'EXTRACTION:

1. TITRE:
   - Déduis un titre clair si non explicitement mentionné
   - Utilise les ingrédients principaux (ex: "Gâteau au chocolat", "Salade César")

2. INGRÉDIENTS:
   - Standardise les quantités: g, kg, ml, L, c. à soupe, c. à café
   - Conserve "une pincée", "un peu de", "au goût" si mentionné
   - Si aucune quantité: écris juste l'ingrédient (ex: "sel", "poivre")
   - Regroupe les ingrédients identiques

3. ÉTAPES:
   - Commence chaque étape par un verbe d'action (Mélanger, Cuire, Préchauffer, etc.)
   - Sois concis mais précis (température, durée, technique)
   - Ignore les répétitions et hésitations
   - Numérotation logique (préparation → cuisson → finition)

4. CONTENU À IGNORER:
   - Appels à l'action ("like", "abonne-toi", "partage", "commente")
   - Transitions non-culinaires ("alors", "du coup", "voilà")
   - Répétitions et hésitations ("euh", "donc euh", redites)

5. MÉTADONNÉES:
   - Utilise null (pas de guillemets) si l'info n'est pas dans la transcription
   - Ne JAMAIS inventer ou supposer des informations

EXEMPLE DE SORTIE:
{{
    "title": "Cookies au chocolat",
    "category": "Dessert",
    "servings": "12 cookies",
    "prep_time": "15 min",
    "cook_time": "12 min",
    "difficulty": "Facile",
    "ingredients": [
        "200g de farine",
        "100g de beurre mou",
        "150g de pépites de chocolat",
        "1 œuf",
        "100g de sucre",
        "1 c. à café de levure"
    ],
    "steps": [
        "Préchauffer le four à 180°C",
        "Mélanger le beurre et le sucre jusqu'à obtenir une crème",
        "Ajouter l'œuf et bien incorporer",
        "Incorporer la farine et la levure",
        "Ajouter les pépites de chocolat",
        "Former des boules et déposer sur une plaque",
        "Cuire 12 minutes jusqu'à ce qu'ils soient dorés"
    ],
    "tips": [
        "Ne pas trop cuire pour garder un cœur moelleux"
    ]
}}

TRANSCRIPTION À ANALYSER:
{transcription}

RÉPONDS UNIQUEMENT AVEC LE JSON VALIDE. AUCUN TEXTE AVANT OU APRÈS."""

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

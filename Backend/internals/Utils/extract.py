from typing import Any, Literal

from internals.core.llm.whisper_ollama import OllamaClient


def extract_recipes(
    ollama_url: str,
    ollama_model_primary: str,
    transcription: Any | Literal[""],
):
    # Step 3: Extract recipe with Ollama
    print("\nSTEP 3: Extracting recipe with LLM")
    print("-" * 60)
    ollama = OllamaClient(base_url=ollama_url)

    # Check Ollama connection
    if not ollama.check_connection():
        print(f"✗ Cannot connect to Ollama at {ollama_url}")
        print("\n  Skipping recipe extraction...\n")
        return

    print(f"✓ Connected to Ollama at {ollama_url}")
    # Extract recipe with primary model
    recipe = ollama.extract_recipe(transcription, model=ollama_model_primary)

    return recipe

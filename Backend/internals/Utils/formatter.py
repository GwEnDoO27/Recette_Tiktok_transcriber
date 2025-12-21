from typing import Dict, Any, Optional


def format_recipe_for_display(recipe: Dict[str, Any], video_url: Optional[str] = None) -> str:
    """
    Formate une recette en texte lisible pour Apple Shortcuts/Notes.

    Args:
        recipe (Dict[str, Any]): Dictionnaire de la recette
        video_url (Optional[str]): URL de la vidéo source

    Returns:
        str: Texte formaté prêt à afficher
    """
    lines = []

    # Titre
    title = recipe.get("title", "Recette sans titre")
    lines.append(f"📝 {title}")
    lines.append("")

    # Catégorie
    category = recipe.get("category")
    if category:
        lines.append(f"#{category}")
        lines.append("")

    # Métadonnées
    metadata_lines = []
    if recipe.get("prep_time"):
        metadata_lines.append(f"⏱ Préparation: {recipe['prep_time']}")
    if recipe.get("cook_time"):
        metadata_lines.append(f"🔥 Cuisson: {recipe['cook_time']}")
    if recipe.get("servings"):
        metadata_lines.append(f"👥 Portions: {recipe['servings']}")
    if recipe.get("difficulty"):
        metadata_lines.append(f"📊 Difficulté: {recipe['difficulty']}")

    if metadata_lines:
        lines.extend(metadata_lines)
        lines.append("")

    # Ingrédients
    ingredients = recipe.get("ingredients", [])
    if ingredients:
        lines.append("📋 Ingrédients:")
        servings = recipe.get("servings")
        if servings:
            lines.append(f"(Pour {servings})")
        for ingredient in ingredients:
            lines.append(f"  • {ingredient}")
        lines.append("")

    # Étapes
    steps = recipe.get("steps", [])
    if steps:
        lines.append("👨‍🍳 Étapes:")
        for i, step in enumerate(steps, 1):
            lines.append(f"  {i}. {step}")
        lines.append("")

    # Astuces
    tips = recipe.get("tips", [])
    if tips:
        lines.append("💡 Astuces:")
        for tip in tips:
            lines.append(f"  • {tip}")
        lines.append("")

    # Lien source
    if video_url:
        lines.append(f"🔗 Lien: {video_url}")

    return "\n".join(lines)

from typing import Optional, Tuple, Dict, Any, Union
import re

from internals.core.Downloading.Insta import InstaDownloader
from internals.core.Downloading.Tiktok import TikTokDownloader
from internals.core.Downloading.Url import RecipbyWebsite


def find_the_downloader(link: str) -> Tuple[Optional[Union[str, Dict[str, str]]], Optional[Dict[str, Any]]]:
    """
    Détecte automatiquement la plateforme et télécharge la vidéo avec ses métadonnées,
    ou extrait la recette depuis un site web.

    Args:
        link (str): URL de la vidéo TikTok, Instagram ou d'un site de recettes

    Returns:
        Tuple[Optional[Union[str, Dict[str, str]]], Optional[Dict[str, Any]]]:
            - Chemin du fichier téléchargé (pour vidéos) ou dictionnaire avec recette (pour sites web), ou None si échec
            - Métadonnées de la vidéo (description, titre, etc.), ou None si non disponible

    Raises:
        ValueError: Si l'URL n'est pas reconnue ou invalide
        Exception: Si le téléchargement/extraction échoue
    """
    # Patterns de validation
    tiktok_pattern = r"https?://((?:vm|vt|www)\.)?tiktok\.com/"
    instagram_pattern = r"https?://(www\.)?instagram\.com/(p|reel|reels|tv)/"

    # Détection et validation de la plateforme
    if re.match(tiktok_pattern, link):
        downloader = TikTokDownloader()
        if not downloader.validate_url(link):
            raise ValueError("URL TikTok invalide")

        # Récupérer les métadonnées avant le téléchargement
        metadata = downloader.get_video_info(link)
        video_path = downloader.download_video(link)

        return video_path, metadata

    elif re.match(instagram_pattern, link):
        downloader = InstaDownloader()
        if not downloader.validate_url(link):
            raise ValueError("URL Instagram invalide")

        # Instagram n'a pas encore de récupération de métadonnées
        video_path = downloader.download_video(link)
        return video_path, None

    # Si ce n'est ni TikTok ni Instagram, vérifier si c'est un site de recettes
    elif RecipbyWebsite.verify_if_url_is_good(link):
        try:
            recipe_data = RecipbyWebsite.extract_from_website(link)
            # Retourner les données de recette directement au lieu d'un chemin de fichier
            return recipe_data, None
        except Exception as e:
            raise ValueError(f"Impossible d'extraire la recette depuis le site web: {str(e)}")

    else:
        raise ValueError(
            "URL non reconnue. Seuls TikTok, Instagram et les sites de recettes sont supportés."
        )

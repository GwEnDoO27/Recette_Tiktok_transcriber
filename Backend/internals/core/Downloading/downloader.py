from typing import Optional, Tuple, Dict, Any
import re

from internals.core.Downloading.Insta import InstaDownloader
from internals.core.Downloading.Tiktok import TikTokDownloader


def find_the_downloader(link: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Détecte automatiquement la plateforme et télécharge la vidéo avec ses métadonnées.

    Args:
        link (str): URL de la vidéo TikTok ou Instagram

    Returns:
        Tuple[Optional[str], Optional[Dict[str, Any]]]:
            - Chemin du fichier téléchargé, ou None si échec
            - Métadonnées de la vidéo (description, titre, etc.), ou None si non disponible

    Raises:
        ValueError: Si l'URL n'est pas reconnue ou invalide
        Exception: Si le téléchargement échoue
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

    else:
        raise ValueError(
            "URL non reconnue. Seuls TikTok et Instagram sont supportés."
        )

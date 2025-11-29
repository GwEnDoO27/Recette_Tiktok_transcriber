from typing import Optional
import re

from internals.core.Downloading.Insta import InstaDownloader
from internals.core.Downloading.Tiktok import TikTokDownloader


def find_the_downloader(link: str) -> Optional[str]:
    """
    Détecte automatiquement la plateforme et télécharge la vidéo.

    Args:
        link (str): URL de la vidéo TikTok ou Instagram

    Returns:
        Optional[str]: Chemin du fichier téléchargé, ou None si échec

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
        return downloader.download_video(link)

    elif re.match(instagram_pattern, link):
        downloader = InstaDownloader()
        if not downloader.validate_url(link):
            raise ValueError("URL Instagram invalide")
        return downloader.download_video(link)

    else:
        raise ValueError(
            "URL non reconnue. Seuls TikTok et Instagram sont supportés."
        )

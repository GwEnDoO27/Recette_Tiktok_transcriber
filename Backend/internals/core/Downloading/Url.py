import re
from urllib.request import urlopen

from recipe_scrapers import scrape_html

class RecipbyWebsite:
    @staticmethod
    def verify_if_url_is_good(url):
        tiktok_pattern = r"https?://((?:vm|vt|www)\.)?tiktok\.com/.*"
        instagram_pattern = (
            r"https?://(www\.)?instagram\.com/(p|reel|reels|tv)/[\w-]+/?"
        )

        if re.match(instagram_pattern, url) or re.match(tiktok_pattern, url):
            return False
        else:
            return True

    @staticmethod
    def extract_from_website(url):
        html = urlopen(url).read().decode("utf-8")
        scraper = scrape_html(html, org_url=url)
        return {"title": scraper.title(), "instruction": scraper.instructions()}

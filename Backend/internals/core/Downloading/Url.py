import re
from urllib.request import urlopen
from typing import Dict, List

from recipe_scrapers import scrape_html
from bs4 import BeautifulSoup

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
    def _fallback_parser(html: str, url: str) -> Dict:
        """
        Parser de secours utilisant BeautifulSoup pour extraire les recettes
        des sites non supportés par recipe-scrapers.
        """
        soup = BeautifulSoup(html, 'lxml')

        # Extraire le titre
        title = "Recette sans titre"

        # Stratégies de recherche du titre (par ordre de priorité)
        title_selectors = [
            ('h1', {'class': lambda x: x and 'recipe' in x.lower()}),
            ('h1', {'class': lambda x: x and 'title' in x.lower()}),
            ('h1', {}),
            ('meta', {'property': 'og:title'}),
            ('title', {})
        ]

        for tag, attrs in title_selectors:
            if tag == 'meta':
                element = soup.find(tag, attrs)
                if element and element.get('content'):
                    title = element['content']
                    break
            else:
                element = soup.find(tag, attrs)
                if element and element.get_text(strip=True):
                    title = element.get_text(strip=True)
                    break

        # Extraire les ingrédients
        ingredients = []

        # Stratégies de recherche des ingrédients
        ingredient_patterns = [
            # Journaldesfemmes.fr - structure spécifique
            ('ul', {'class': lambda x: x and 'app_recipe_list' in str(x)}),
            # Balises avec classes spécifiques aux ingrédients
            ('ul', {'class': lambda x: x and any(keyword in str(x).lower() for keyword in ['ingredient', 'ingr'])}),
            ('ol', {'class': lambda x: x and any(keyword in str(x).lower() for keyword in ['ingredient', 'ingr'])}),
            # Schema.org
            ('ul', {'itemprop': 'recipeIngredient'}),
        ]

        for tag, attrs in ingredient_patterns:
            element = soup.find(tag, attrs)
            if element:
                items = element.find_all('li', recursive=False)
                if items:
                    for item in items:
                        text = item.get_text(strip=True)
                        # Nettoyer les espaces multiples
                        text = ' '.join(text.split())
                        if text and len(text) > 2:
                            ingredients.append(text)
                    if ingredients:
                        break

        # Extraire les instructions
        instructions = "Instructions non disponibles"

        # Stratégies de recherche des instructions
        instruction_patterns = [
            # Journaldesfemmes.fr - structure spécifique
            ('li', {'class': lambda x: x and 'bu_cuisine_recette_prepa' in str(x)}),
            # Balises avec classes spécifiques aux recettes
            ('div', {'class': lambda x: x and any(keyword in str(x).lower() for keyword in ['instruction', 'preparation', 'etape', 'step'])}),
            ('ol', {'class': lambda x: x and any(keyword in str(x).lower() for keyword in ['instruction', 'preparation', 'etape', 'step'])}),
            ('ul', {'class': lambda x: x and any(keyword in str(x).lower() for keyword in ['instruction', 'preparation', 'etape', 'step'])}),
            # Balises itemprop schema.org
            ('div', {'itemprop': 'recipeInstructions'}),
            ('ol', {'itemprop': 'recipeInstructions'}),
            # Recherche plus large
            ('div', {'class': lambda x: x and 'recipe' in str(x).lower()}),
        ]

        for tag, attrs in instruction_patterns:
            # Pour les <li> spécifiques (comme journaldesfemmes), on cherche tous les éléments
            if tag == 'li':
                elements = soup.find_all(tag, attrs)
                if elements:
                    steps = []
                    for elem in elements:
                        text = elem.get_text(strip=True)
                        # Enlever le numéro d'étape au début (ex: "1Préparation..." -> "Préparation...")
                        text = re.sub(r'^\d+', '', text)
                        steps.append(text)
                    if steps:
                        instructions = '\n'.join([f"{i+1}. {step}" for i, step in enumerate(steps)])
                        break
            else:
                element = soup.find(tag, attrs)
                if element:
                    # Si c'est une liste (ol/ul), extraire les items
                    if tag in ['ol', 'ul']:
                        steps = element.find_all('li')
                        if steps:
                            instructions = '\n'.join([f"{i+1}. {step.get_text(strip=True)}"
                                                     for i, step in enumerate(steps)])
                            break
                    else:
                        # Rechercher des listes à l'intérieur de la div
                        lists = element.find_all(['ol', 'ul'])
                        if lists:
                            all_steps = []
                            for lst in lists:
                                steps = lst.find_all('li')
                                all_steps.extend([step.get_text(strip=True) for step in steps])
                            if all_steps:
                                instructions = '\n'.join([f"{i+1}. {step}"
                                                         for i, step in enumerate(all_steps)])
                                break
                        else:
                            # Sinon prendre tout le texte
                            text = element.get_text(strip=True)
                            if len(text) > 50:  # Au moins 50 caractères pour être valide
                                instructions = text
                                break

        return {"title": title, "instruction": instructions, "ingredients": ingredients}

    @staticmethod
    def extract_from_website(url):
        html = urlopen(url).read().decode("utf-8")

        # Essayer d'abord avec recipe-scrapers
        try:
            scraper = scrape_html(html, org_url=url)
            return {
                "title": scraper.title(),
                "instruction": scraper.instructions(),
                "ingredients": scraper.ingredients()
            }
        except Exception as e:
            # Si recipe-scrapers échoue, utiliser le parser de secours
            print(f"recipe-scrapers failed for {url}: {str(e)}")
            print("Using fallback HTML parser...")
            return RecipbyWebsite._fallback_parser(html, url)

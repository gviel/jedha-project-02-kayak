import argparse
import asyncio
import glob
import logging
import os
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

load_dotenv()

# Configuration
DATE_FORMAT = "%Y-%m-%d"
USER_AGENT = os.environ.get("USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TOP_N = 5
x=10
y=200

DATA_DIR      = Path("data")
HTML_DIR      = DATA_DIR / "html"
SNAP_DIR      = HTML_DIR / "snap"
CSV_DIR       = DATA_DIR / "csv"
TODAY         = datetime.now().strftime("%Y%m%d")
CSV_DIR_TODAY = CSV_DIR / TODAY

BASE_URL = "https://www.booking.com"
CLICK_TIMEOUT = 25000  # Délai d'attente pour le clic et le chargement de la nouvelle page (en ms)
PAGE_LOAD_TIMEOUT = 60000  # Délai d'attente max pour charger la page initiale (en ms)
REFRESH_TIMEOUT=3000 # délai d'attente pour u nrefresh de REACT


# MAX_CLICKS = 3  # Nombre maximum de clics sur "Afficher plus de résultats"
#CLICK_TIMEOUT = 25000  # Délai d'attente pour le clic et le chargement des nouveaux résultats (en ms)
#PAGE_LOAD_TIMEOUT = 60000  # Délai d'attente maximum pour charger la page initiale (en ms)
#NEXT_PAGE_BUTTON_SELECTOR = 'button:has-text("Afficher plus de résultats")'
#HOTEL_CONTAINER_XPATH = '//div[@data-testid="property-card"]'

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_top_cities(n: int = TOP_N) -> list[str]:
    """Return top-N cities by mean weather score for today."""
    import pandas as pd
    files = sorted(glob.glob(str(CSV_DIR / TODAY / f"weather-scores-{TODAY}.csv")))
    if not files:
        raise FileNotFoundError(
            f"No weather_scores file found for {TODAY} — run score_weather.py first."
        )
    df = pd.read_csv(files[-1])
    return df.sort_values("mean", ascending=False).head(n)["city_id"].tolist()


async def save_html(page, ville: str, hotel_name: str = None):
    """Sauvegarde le HTML de la page dans data/html/ et
       un snapshot PNG de la page dans data/html/snap/
    """
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    if hotel_name:
        filename = f"{ville}_{hotel_name.replace(' ', '_')}.html"
        filesnap = f"{ville}_{hotel_name.replace(' ', '_')}.png"
    else:
        filename = f"{ville}_liste.html"
        filesnap = f"{ville}__liste.png"
    filepath = HTML_DIR / filename

    html = await page.content()

    # save HTML page
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"HTML sauvegardé: {filepath}")

    # save a snapshot for debug
    filepath_snap = SNAP_DIR / filesnap
    await page.screenshot(path=filepath_snap)
    logger.info(f"Image sauvegardée: {filepath_snap}")

    return filepath

async def click_xy(page,x,y):
    await page.mouse.move(x, y)
    await page.wait_for_timeout(CLICK_TIMEOUT)
    await page.mouse.click(x, y)

# async def refuse_cookies(page):
#     ''' Permet de cliquer sur le bouton de refus des cookies '''
#     try:
#         await page.wait_for_selector('button#onetrust-reject-all-handler', timeout=PAGE_LOAD_TIMEOUT)
#         if await page.locator('button#onetrust-reject-all-handler').is_visible():
#             await page.click('button#onetrust-reject-all-handler')
#         else:
#             logger.info("Bouton pour refuser les cookies non visible")
#         logger.info("Cookies refusés avec succès.")
#     except Exception as e:
#         logger.warning(f"Impossible de refuser les cookies : {e}")
#         pass

# async def accept_cookies(page):
#     ''' Permet de cliquer sur le bouton accepter des cookies '''
#     try:
#         await page.wait_for_selector('button#onetrust-accept-btn-handler', timeout=PAGE_LOAD_TIMEOUT)
#         if await page.locator('button#onetrust-accept-btn-handler').is_visible():
#             await page.click('button#onetrust-accept-btn-handler')
#             logger.info("Cookies acceptés avec succès.")
#         else:
#             logger.info("Bouton pour accepter les cookies non visible")
#     except Exception as e:
#         logger.warning(f"Impossible d'accepter les cookies : {e}")
#         pass

# --- Fonction universelle pour fermer les popups Booking ---
async def close_popups(page):
    """
        Ferme automatiquement les popups (cookies, Genius, etc.) si elles apparaissent.
    """
    selectors = [
        # Cookies
        "'button#onetrust-accept-btn-handler", # le bouton identifié
        "button:has-text('Tout accepter')",
        "button:has-text('Accepter')",
        "button:has-text('Accept all')",
        "button[aria-label*='cookies']",

        # Genius / login / modales diverses
        "div:has-text('Genius') button",
        "button[aria-label*='Fermer']",
        "button[aria-label*='Close']",
        "button[data-testid*='close']",
        "div[role='dialog'] button[aria-label*='Fermer']",
        "div[data-testid='modal-window'] button",
    ]
    for sel in selectors:
        try:
            locator = page.locator(sel)
            if await locator.is_visible():
                await locator.click()
                logger.info(f"Selector {sel} visible => click!")
                await page.wait_for_timeout(REFRESH_TIMEOUT)
        except Exception:
            continue  # ignore les sélecteurs absents

async def safe_check_visible(page, locator_str: str, timeout: int = 25000):
    """
    Coche la première case visible correspondant au sélecteur donné,
    même s'il y a plusieurs doublons ou overlays qui bloquent le clic.

    Args:
        page: Playwright Page
        locator_str: sélecteur CSS de la checkbox
        timeout: délai maximal en ms
    """

    # Récupérer tous les éléments correspondant au sélecteur
    locators = page.locator(locator_str)
    count = await locators.count()
    if count == 0:
        raise ValueError(f"[safe_check_visible] ❌ Aucun élément trouvé pour {locator_str}")

    # Chercher la première case visible
    visible_element = None
    for i in range(count):
        el = locators.nth(i)
        if await el.is_visible():
            visible_element = el
            break

    if visible_element is None:
        raise ValueError(f"[safe_check_visible] ❌ Aucun élément visible trouvé pour {locator_str}")

    # --- Étape 1 : essai direct ---
    try:
        if not await visible_element.is_checked():
            await visible_element.check(timeout=timeout)
        print(f"[safe_check_visible] ✅ Checkbox cochée (direct) : {locator_str}")
        return
    except Exception:
        pass

    # --- Étape 2 : supprimer les overlays Booking ---
    await page.evaluate("""
    () => {
        const selectors = ['.bbe73dce14', '.b8ef7618ca', '.c2110a275e', '.abcc616ecb'];
        selectors.forEach(sel => {
            const el = document.querySelector(sel);
            if (el) el.style.display = 'none';
        });
    }
    """)

    # --- Étape 3 : cocher via JS si nécessaire ---
    try:
        element_handle = await visible_element.element_handle()
        if element_handle:
            await page.evaluate("(el) => { if (!el.checked) el.click(); }", element_handle)
            print(f"[safe_check_visible] ✅ Checkbox cochée via JS : {locator_str}")
            return
    except Exception:
        pass

    # --- Étape 4 : clic par coordonnées comme dernier recours ---
    box = await visible_element.bounding_box()
    if box:
        await page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
        print(f"[safe_check_visible] ✅ Checkbox cochée par coordonnées : {locator_str}")
        return

    # Si tout échoue
    raise RuntimeError(f"[safe_check_visible] ❌ Impossible de cocher la checkbox : {locator_str}")

async def safe_click(page, locator_str: str, timeout: int = 25000):
    """
    Clique de manière fiable sur un élément, même si un overlay ou une popup bloque l'accès.
    - page: objet Playwright Page
    - locator_str: sélecteur CSS de l'élément à cliquer
    - timeout: délai d'attente maximal (ms)
    """
    locator = page.locator(locator_str)

    # 1️ Attente que l'élément existe et soit visible
    await page.wait_for_selector(locator_str, timeout=timeout)
    await locator.wait_for(state="visible", timeout=timeout)

    # 2️ Tentative de clic direct
    try:
        await locator.click(timeout=timeout)
        return
    except Exception as e:
        print(f"[safe_click] ⚠️ Clic normal bloqué sur {locator_str}: {e}")

    # 3️ Suppression des overlays courants (Booking, bannières, etc.)
    await page.evaluate("""
    () => {
        const selectors = [
            '.bbe73dce14',    // overlay Booking
            '.b8ef7618ca',    // popup Genius / cookies
            '.c2110a275e',    // div générique opaque
            '.abcc616ecb'     // autre version d'overlay Booking
        ];
        selectors.forEach(sel => {
            const el = document.querySelector(sel);
            if (el) el.style.display = 'none';
        });
    }
    """)

    # 4️ Nouvelle tentative de clic (via JS direct)
    try:
        element_handle = await locator.element_handle()
        if element_handle:
            await page.evaluate("(el) => el.click()", element_handle)
            print(f"[safe_click] Clic JS réussi sur {locator_str}")
            return
    except Exception as e:
        print(f"[safe_click] Clic JS échoué: {e}")

    # 5 Dernier recours : clic par coordonnées
    try:
        box = await locator.bounding_box()
        if box:
            await page.mouse.click(
                box["x"] + box["width"] / 2,
                box["y"] + box["height"] / 2
            )
            print(f"[safe_click] ✅ Clic souris par coordonnées sur {locator_str}")
            return
    except Exception as e:
        print(f"[safe_click] ❌ Échec total du clic sur {locator_str}: {e}")
        raise e

# async def select_dates(page, from_date: str, to_date: str):
#     """Sélectionne les dates dans le calendrier Booking.com."""
#     logger.info(f"Sélection des dates : {from_date} -> {to_date}")
#     await page.locator("button[data-testid='searchbox-dates-container']").click()
#     await page.wait_for_selector(f"td[data-date='{from_date}']", timeout=CLICK_TIMEOUT)
#     await page.locator(f"td[data-date='{from_date}']").click()
#     await page.locator(f"td[data-date='{to_date}']").click()
#     await page.wait_for_timeout(REFRESH_TIMEOUT)
#     start_display = await page.locator("[data-testid='date-display-field-start']").inner_text()
#     end_display = await page.locator("[data-testid='date-display-field-end']").inner_text()
#     logger.info(f"Dates affichées dans le champ : {start_display} -> {end_display}")

async def scrap_hotel_list(page):
    hotels = {}
    logger.info("Parse hotel list...")
    await page.wait_for_selector('[data-testid="title-link"]', timeout=PAGE_LOAD_TIMEOUT)
    links = await page.get_by_test_id("title-link").all()
    #logger.info(type(links))

    for link in links:
        url_hotel = await link.get_attribute("href")
        title = link.get_by_test_id("title").first
        hotel_name = await title.all_text_contents()
        hotel_name = hotel_name[0]
        logger.info(f"Hotel={hotel_name} => {url_hotel}")
        hotels[hotel_name] = url_hotel
    return hotels

async def scrap_hotel(hotel_page):
    # scrap loc, description, score
    await hotel_page.wait_for_selector('[data-testid="map-entry-point-desktop-wrapper"]', timeout=CLICK_TIMEOUT)
    divLoc = await hotel_page.get_by_test_id("map-entry-point-desktop-wrapper").all()
    loc = await divLoc[0].get_attribute("data-atlas-latlng")
    lat, lon = loc.split(",")
    logger.info(f"long={lon} lat={lat}")

    await hotel_page.wait_for_selector('[data-testid="property-description"]', timeout=CLICK_TIMEOUT)
    description = await hotel_page.get_by_test_id("property-description").text_content()
    logger.info(f"desc={description[:200]}")

    score = None
    try:
        await hotel_page.wait_for_selector('[data-testid="review-score-component"]', timeout=CLICK_TIMEOUT)
        mainDivScore = hotel_page.get_by_test_id("review-score-component").first
        divScore = mainDivScore.locator("div.f63b14ab7a.dff2e52086")
        scoreStr = await divScore.text_content()
        score = float(scoreStr.strip().replace(',', '.'))
    except Exception:
        logger.warning("Score non disponible pour cet hôtel")
    logger.info(f"score={score}")
    return (lat, lon, description, score)


async def main(from_date: datetime, to_date: datetime, top_n: int = TOP_N):

    top_city_ids = load_top_cities(top_n)
    logger.info(f"Top {top_n} cities to scrape: {top_city_ids}")

    # fromDate = from_date.strftime(DATE_FORMAT)
    # toDate = to_date.strftime(DATE_FORMAT)

    async with async_playwright() as p:
        # création du browser, du contexte et de la page initiale
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                f'--user-agent={USER_AGENT}'
            ])
        context = await browser.new_context()
        page = await context.new_page()

        # charger la page d'accueil de booking.com
        await page.goto(f"{BASE_URL}/index.fr.html", wait_until="load", timeout=PAGE_LOAD_TIMEOUT)
        await page.wait_for_load_state('networkidle')

        # on clique n'importe ou sur la gauche pour supprimer éventuelle popup de pub
        #await click_xy(page,x,y)
        # on refuse les cookies de la popup
        #await accept_cookies(page)
        # on passe une dernière fois pour etre sur d'avoir fermé toutes les popups
        await close_popups(page)

        # récupération des cookies
        cookies = await context.cookies()
        #logger.info(f"Cookies: {cookies}")

        # Sauvegarder l'état de la session (incluant les cookies) dans un fichier JSON
        storage_state = await context.storage_state()
        with open(str(DATA_DIR / "session.json"), "w") as f:
            json.dump(storage_state, f)

        # pour chaque ville on va rechercher la liste
        for city_id in top_city_ids:
            city_name = city_id.replace("_", " ")
            logger.info(f"Try to get hotel list for {city_name}...")

            # on attend d'avoir l'input de saisie de la destination
            #await page.wait_for_selector("input[name='ss']", timeout=CLICK_TIMEOUT)

            # on clic dessus, on sélectionne tout et on efface
            #search_box = page.locator('input[name="ss"]')
            #await search_box.click(timeout=CLICK_TIMEOUT)
            search_box = page.locator('input[name="ss"]')
            await safe_click(page, 'input[name="ss"]', CLICK_TIMEOUT)
            await search_box.press("Control+A")
            await search_box.press("Delete")

            # on y saisie la ville avec un delay de saisie pour simuler saisie manuelle
            await search_box.type(city_name, delay=500)

            # on attend l'apparition de la liste de proposition et on clique sur la première suggestion
            #await page.wait_for_selector("li#autocomplete-result-0 div[role='button']", timeout=CLICK_TIMEOUT)
            #first_suggestion = page.locator("li#autocomplete-result-0 div[role='button']")
            #await first_suggestion.click(timeout=CLICK_TIMEOUT)
            await safe_click(page, "li#autocomplete-result-0 div[role='button']", CLICK_TIMEOUT)
            await page.wait_for_timeout(REFRESH_TIMEOUT)

            value = await search_box.input_value()
            logger.debug("Valeur finale dans l'input : %s", value)

            # si on veut en plus choisir une plage de dates
            #await select_dates(page, fromDate, toDate)
            await save_html(page, f"Formulaire destination {city_name}")

            # valider et lancer la recherche
            #await page.click('button[type="submit"]:has-text("Rechercher")', timeout=CLICK_TIMEOUT)
            await safe_click(page, 'button[type="submit"]:has-text("Rechercher")', timeout=PAGE_LOAD_TIMEOUT)
            await page.wait_for_load_state('networkidle')

            # on clique à gauche de la page pour enlever la popup
            await click_xy(page,x,y)
            await close_popups(page)

            # tentative de click sur la case à cocher Hotel
            #await page.wait_for_selector('div[data-filters-group="ht_id"] input[name="ht_id=204"]', timeout=REFRESH_TIMEOUT)
            #await page.locator('div[data-filters-group="ht_id"] input[name="ht_id=204"]:visible').check()
            await safe_check_visible(page, 'div[data-filters-group="ht_id"] input[name="ht_id=204"]', timeout=PAGE_LOAD_TIMEOUT)
            await page.wait_for_load_state("networkidle")
            logger.info("Filtre 'Hôtels' appliqué")

            await save_html(page, city_name)
            logger.info(f"--- OK page hotel sauvée pour {city_name}")

            # parsing des noms d'hotel + url de la fiche
            map_url_by_hotel = await scrap_hotel_list(page)
            logger.info(f"--- OK liste des hotels scrapée pour {city_name}")

            hotel_records = []
            for hotel_name in map_url_by_hotel.keys():
                # aller sur chaque page en ouvrant un nouvel onglet à chaque hotel
                url_hotel = map_url_by_hotel[hotel_name]
                hotel_page = await page.context.new_page()
                try:
                    await hotel_page.goto(url_hotel, wait_until="load", timeout=PAGE_LOAD_TIMEOUT)
                    await hotel_page.wait_for_load_state("networkidle")
                    await save_html(page, city_name, hotel_name)
                    lat, lon, description, score = await scrap_hotel(hotel_page)
                except Exception as e:
                    logger.warning(f"Skipping {hotel_name}: {e}")
                    await hotel_page.close()
                    continue

                hotel_records.append({
                    "city_id":     city_id,
                    "city_name":   city_name,
                    "hotel_name":  hotel_name,
                    "lat":         lat,
                    "lon":         lon,
                    "description": description,
                    "score":       score,
                    "url":         url_hotel,
                })

            # sauvegarde CSV par ville
            if hotel_records:
                CSV_DIR_TODAY.mkdir(parents=True, exist_ok=True)
                out = CSV_DIR_TODAY / f"hotels-{city_id}-{TODAY}.csv"
                pd.DataFrame(hotel_records).to_csv(out, index=False, encoding="utf-8")
                logger.info(f"CSV sauvegardé : {out}")

        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape hotels on Booking.com for top-N cities.")
    parser.add_argument("top_n",     nargs="?", type=int,
                        default=TOP_N,
                        help=f"nombre de villes à scraper (défaut: {TOP_N})")
    parser.add_argument("from_date", nargs="?",
                        type=lambda s: datetime.strptime(s, DATE_FORMAT),
                        default=None,
                        help="date d'arrivée YYYY-MM-DD (défaut: J+1)")
    parser.add_argument("to_date",   nargs="?",
                        type=lambda s: datetime.strptime(s, DATE_FORMAT),
                        default=None,
                        help="date de départ YYYY-MM-DD (défaut: from_date + 4j)")
    args = parser.parse_args()

    if args.from_date is None:
        args.from_date = datetime.now() + timedelta(days=1)
    if args.to_date is None:
        args.to_date = args.from_date + timedelta(days=4)

    logger.info(f"top_n={args.top_n}  from_date={args.from_date.date()}  to_date={args.to_date.date()}")
    asyncio.run(main(args.from_date, args.to_date, args.top_n))

import json
import os, sys
import random
import time
import undetected_chromedriver as uc
import requests
import logging
import re
import sqlite3
import chromedriver_autoinstaller
from fuzzywuzzy import process
import csv
import io

# Calculate the project root as the parent directory of the frontend folder.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print("Project root added to sys.path:", PROJECT_ROOT)

from flask import Flask, request, jsonify, Response
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
from modules.scrapers import scrape_barcode_lookup, scrape_amazon_price, scrape_ebay_prices, scrape_cex_price


app = Flask(__name__)

IGDB_CLIENT_ID = "nal5c75b0hwuvmsgs1cdowvi81tg5y"
IGDB_CLIENT_SECRET = "lgea285xk7qsm4lhh9tio54bw3pek7"

# Specify the exact path to the ChromeDriver binary
driver_path = "/opt/homebrew/bin/chromedriver"  # Replace with the actual path

# Specify the path to the SQLite database

# External for local
# database_path = "/Volumes/backup_proxmox/lukabratzee/games.db"
###### DB LOAD ######

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env variables
load_dotenv()

# Get database path from .env
database_path = os.getenv("DATABASE_PATH", "").strip()

print(f"📜 DATABASE_PATH from .env: '{database_path}'")

# If the path is not absolute, then join with BASE_DIR
if not os.path.isabs(database_path):
    # If database_path already starts with "backend/", remove it
    if database_path.startswith("backend/"):
        database_path = database_path.replace("backend/", "", 1)
    database_path = os.path.join(BASE_DIR, database_path)

print(f"✅ Final Database Path: {database_path}")
print(f"🧐 File Exists: {os.path.exists(database_path)}")

####################

# -------------------------
# Price Source Configuration Management
# -------------------------
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config():
    """Load configuration from JSON file, create default if doesn't exist"""
    default_config = {"price_source": "eBay"}
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Ensure price_source exists and is valid
                if "price_source" not in config or config["price_source"] not in ["eBay", "Amazon", "CeX"]:
                    config["price_source"] = "eBay"
                return config
        except (json.JSONDecodeError, IOError):
            pass
    
    # Create default config file
    save_config(default_config)
    return default_config

def save_config(config):
    """Save configuration to JSON file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        logging.error(f"Failed to save config: {e}")

def get_price_source():
    """Get current price source preference"""
    config = load_config()
    return config.get("price_source", "eBay")

def set_price_source(price_source):
    """Set price source preference"""
    if price_source not in ["eBay", "Amazon", "CeX"]:
        return False
    
    config = load_config()
    config["price_source"] = price_source
    save_config(config)
    return True

####################
# Set up logging
logging.basicConfig(level=logging.DEBUG)

# List of common console names and abbreviations to exclude
CONSOLE_NAMES = [
    "PlayStation",
    "PS",
    "PS1",
    "PS2",
    "Gamecube",
    "PlayStation 3",
    "PS3",
    "PlayStation 4",
    "PS4",
    "PlayStation 5",
    "PS5",
    "Xbox 360",
    "Xbox One",
    "Xbox Series X",
    "Nintendo Switch",
    "Wii U",
    "PC",
]

COMPANY_NAMES = [
    "Sony",
    "Microsoft",
    "Nintendo",
    "Electronic Arts",
    "Ubisoft",
    "Square Enix",
    "Activision",
    "Bethesda",
    "Capcom",
    "Bandai Namco",
]


def get_db_connection():
    try:
        print(f"📂 Attempting to connect to database at: {database_path}")
        conn = sqlite3.connect(database_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError as e:
        print(f"🚨 Database Connection Error: {e}")
        raise

# Get IGDB access token
def get_igdb_access_token():
    url = f"https://id.twitch.tv/oauth2/token?client_id={IGDB_CLIENT_ID}&client_secret={IGDB_CLIENT_SECRET}&grant_type=client_credentials"
    response = requests.post(url)
    logging.debug(f"IGDB access token response: {response.json()}")
    return response.json().get("access_token")

# def scrape_ebay_prices(game_title):
    """
    Opens eBay UK homepage, enters the game_title in the search box,
    waits for the results, and returns the first price found as a float.
    """
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    # Set a realistic user agent
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    service = ChromeService(driver_path)
    driver = uc.Chrome(service=service, options=options)

    try:
        # 1. Navigate to eBay UK homepage.
        driver.get("https://www.ebay.co.uk/")
        time.sleep(2)  # Wait for the page to load.

        # 2. Locate the search box. (eBay's search box typically has id 'gh-ac')
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "gh-ac"))
        )
        # 3. Enter the game title and press Enter.
        search_box.send_keys(game_title)
        time.sleep(1)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)  # Wait for search results to load.

        # 4. Find price elements. Many eBay listings have a price element with class 's-item__price'
        price_elements = driver.find_elements(By.CSS_SELECTOR, "span.s-item__price")
        if price_elements:
            # For now, we return just the first price.
            price_text = price_elements[0].text.strip()
            # Clean up the price text by removing currency symbols and extra words.
            # Typical formats are "£42.00" or "GBP 42.00"
            price_text = price_text.replace("£", "").replace("GBP", "").strip()
            # Sometimes the text might include additional text (e.g., "to" a second price), so take the first token.
            price_token = price_text.split()[0].replace(",", "")
            logging.debug(f"Scraped eBay price text: {price_token}")
            return float(price_token)
        else:
            logging.warning("No price elements found on eBay search page.")
            return None
    except Exception as e:
        logging.error(f"Error scraping eBay: {e}")
        return None
    finally:
        driver.quit()

# Scrape Amazon for the game price
def scrape_amazon_prices(game_title):
    """
    Opens Amazon's homepage, performs a search for the given game title,
    waits for any captcha to be resolved manually, and returns a list of price values found.
    """
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    # Use a realistic user agent:
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/115.0.0.0 Safari/537.36")

    service = ChromeService(driver_path)
    driver = uc.Chrome(service=service, options=options)
    prices = []
    try:
        # 1. Go to Amazon's homepage
        driver.get("https://www.amazon.co.uk/")
        time.sleep(2)

        # 2. Locate the search box and type the game title, then press Enter
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "twotabsearchtextbox"))
        )
        search_box.send_keys(game_title)
        time.sleep(1)
        search_box.send_keys(Keys.RETURN)

        # 3. Wait for search results to load and for any captcha to be solved
        max_wait = 60  # Maximum total wait time (seconds)
        wait_interval = 5
        total_wait = 0
        while "captcha" in driver.page_source.lower() and total_wait < max_wait:
            logging.info("Captcha detected. Waiting for captcha resolution...")
            time.sleep(wait_interval)
            total_wait += wait_interval

        if "captcha" in driver.page_source.lower():
            logging.error("Captcha still present after waiting; aborting Amazon scrape.")
            return []  # Or return None to indicate failure

        # 4. Now, attempt to gather all price elements
        price_elements = driver.find_elements(By.CSS_SELECTOR, "span.a-price-whole")
        if price_elements:
            for el in price_elements:
                price_text = el.text.strip().replace(",", "")
                try:
                    price = float(price_text)
                    prices.append(price)
                except ValueError:
                    continue
        else:
            logging.warning("No price elements found on Amazon search page.")
    except Exception as e:
        logging.error(f"Error scraping Amazon: {e}")
    finally:
        driver.quit()
    return prices

# Scrape the barcode lookup website for the game title using undetected_chromedriver
def scrape_barcode_lookup(barcode):

    # Set up Chrome options
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Use the Service class to specify the ChromeDriver path and avoid caching issues
    service = ChromeService(driver_path)

    # Initialize the Chrome browser using undetected_chromedriver with the given service and options
    driver = uc.Chrome(service=service, options=options)

    url = f"https://www.barcodelookup.com/{barcode}"
    driver.get(url)

    try:
        # Wait for the page to load and the expected element to be located
        try:
            WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.col-50.product-details")
            )
            )
        except Exception as e:
            logging.error(f"Failed to find barcode")
            game_title = None
            average_price = None
            driver.quit()
            return game_title, average_price

        # Extract the game title
        game_title_element = driver.find_element(
            By.CSS_SELECTOR, "div.col-50.product-details h4"
        )
        game_title = game_title_element.text.strip()
        logging.debug(f"Game title found: {game_title}")

        # Extract prices and calculate the average price
        price_elements = driver.find_elements(By.CSS_SELECTOR, "div.store-list li")
        prices = []
        for price_element in price_elements:
            price_text = price_element.text
            # Extract the price using regex (assuming the price is formatted as $X.XX or £X.XX)
            price_match = re.search(r"[\$\£]\d+(\.\d{2})?", price_text)
            if price_match:
                price = float(price_match.group()[1:])
                prices.append(price)

        average_price = round(sum(prices) / len(prices), 2) if prices else None
        logging.debug(f"Average price calculated: {average_price}")

    except Exception as e:
        logging.error(f"Failed to find elements: {e}")
        game_title = None
        average_price = None
    finally:
        driver.quit()

    return game_title, average_price


# Clean the game title by removing console names
def clean_game_title(game_title):
    for console in CONSOLE_NAMES:
        game_title = re.sub(rf"\b{console}\b", "", game_title, flags=re.IGNORECASE)
    for company in COMPANY_NAMES:
        game_title = re.sub(rf"\b{company}\b", "", game_title, flags=re.IGNORECASE)
    return game_title.strip()


# Search for game information on IGDB
def search_igdb_game(game_name, auth_token):
    url = "https://api.igdb.com/v4/games"
    headers = {
        "Client-ID": IGDB_CLIENT_ID,
        "Authorization": f"Bearer {auth_token}",
    }
    body = f'search "{game_name}"; fields name, cover.url, summary, platforms.name, genres.name, involved_companies.company.name, first_release_date;'

    timeout_duration = 10 if len(game_name) > 30 else 5  # Longer timeout for long names
    logging.debug(f"IGDB API Request for {game_name} (Timeout: {timeout_duration}s)")

    try:
        # Encode the body in UTF-8
        response = requests.post(url, headers=headers, data=body.encode('utf-8'), timeout=timeout_duration)
        response.raise_for_status()
        response_json = response.json()
        return response_json
    except requests.exceptions.Timeout:
        logging.error(f"Timeout while querying IGDB for {game_name}")
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"IGDB API error: {e}")
        return []


# Remove the last word from the game title
def remove_last_word(game_title):
    words = game_title.split()
    if len(words) > 1:
        return " ".join(words[:-1])
    return game_title

def fuzzy_match_title(search_title, igdb_results):
    """
    Uses fuzzy matching to find the closest game title from IGDB results.
    """
    game_titles = [game["name"] for game in igdb_results if "name" in game]

    if not game_titles:
        return None  # No valid game titles found

    best_match, score = process.extractOne(search_title, game_titles)

    if score > 80:  # Only accept high-confidence matches
        for game in igdb_results:
            if game["name"] == best_match:
                logging.debug(f"Fuzzy match found: {best_match} (Score: {score})")
                return game

    return None  # No good fuzzy match found


# Generate a random ID for the game
def generate_random_id():
    return random.randint(1000, 9999)

class GameScan:
    response_data = None  # Class variable to store response data

    @staticmethod
    @app.route("/scan", methods=["POST"])
    def scan():
        try:
            data = request.json
            barcode = data.get("barcode")
            logging.debug(f"Received barcode: {barcode}")

            igdb_access_token = get_igdb_access_token()
            if not igdb_access_token:
                logging.error("Failed to retrieve IGDB access token")
                return jsonify({"error": "Failed to retrieve IGDB access token"}), 500

            # Lookup via barcode to obtain game title (and optional barcode price)
            game_title, barcode_price = scrape_barcode_lookup(barcode)
            game_title = game_title if game_title else "Unknown Game"

            # Check if the game already exists in the database.
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(BASE_DIR, database_path)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM games WHERE title = ?", (game_title,))
            existing_game = cursor.fetchone()
            conn.close()
            if existing_game:
                return jsonify({
                    "error": f"Game with title '{game_title}' already exists in the DB",
                    "id": existing_game[0]
                }), 200

            # We do not perform any price scraping here; set combined_price to None.
            combined_price = None

            # Perform IGDB fuzzy search using game_title (without platform info)
            exact_match, alternative_matches = search_game_fuzzy_with_alternates(game_title, igdb_access_token)
            if not exact_match and not alternative_matches:
                return jsonify({"error": "No results found on IGDB"}), 404

            # Store the IGDB results for later use in /confirm
            GameScan.response_data = {
                "exact_match": exact_match,
                "alternative_matches": alternative_matches,
                "average_price": combined_price,
            }

            response = {
                "exact_match": {
                    "index": 1,
                    "name": exact_match["name"],
                    "platforms": [p["name"] for p in exact_match.get("platforms", [])],
                } if exact_match else {},
                "alternative_matches": [
                    {
                        "index": idx,
                        "name": alt["name"],
                        "platforms": [p["name"] for p in alt.get("platforms", [])],
                    }
                    for idx, alt in enumerate(alternative_matches, start=2)
                ],
                "average_price": combined_price,
            }
            logging.debug(f"Returning /scan response: {response}")
            return jsonify(response)
        except Exception as e:
            logging.error(f"Error in /scan route: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @app.route("/confirm", methods=["POST"])
    def confirm():
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(BASE_DIR, database_path)
            logging.debug(f"Database path: {db_path}")

            data = request.json
            logging.debug(f"Received /confirm payload: {json.dumps(data, indent=2)}")

            if not GameScan.response_data:
                return jsonify({"error": "No stored game data available"}), 400

            selection_str = data.get("selection")
            if not selection_str:
                return jsonify({"error": "No selection provided"}), 400

            try:
                selection_idx = int(selection_str)
            except ValueError:
                return jsonify({"error": "Selection must be an integer"}), 400

            exact_match = GameScan.response_data.get("exact_match")
            all_alts = GameScan.response_data.get("alternative_matches", [])
            if selection_idx == 1:
                selected_game = exact_match
            else:
                alt_index = selection_idx - 2
                if alt_index < 0 or alt_index >= len(all_alts):
                    return jsonify({"error": "Invalid selection index"}), 400
                selected_game = all_alts[alt_index]

            if not selected_game:
                return jsonify({"error": "No game found for that selection"}), 404

            # Safely extract cover image
            cover = selected_game.get("cover")
            if cover and isinstance(cover, dict):
                cover_image = cover.get("url", "")
            else:
                cover_image = ""

            # Build basic game_data
            game_data = {
                "title": selected_game.get("name", "").strip(),
                "cover_image": cover_image,
                "description": selected_game.get("summary"),
                "publisher": [
                    company["company"]["name"]
                    for company in selected_game.get("involved_companies", [])
                    if "company" in company and "name" in company["company"]
                ],
                "platforms": [
                    platform["name"] for platform in selected_game.get("platforms", [])
                    if "name" in platform
                ],
                "genres": [genre["name"] for genre in selected_game.get("genres", [])],
                "series": [
                    series["name"] for series in selected_game.get("franchise", [])
                ],
                "release_date": None,
                "average_price": None,  # will be updated below
            }

            # Override platforms if the user provided a selected platform
            selected_platform = data.get("selected_platform", "").strip()
            if selected_platform:
                game_data["platforms"] = [selected_platform]

            if selected_game.get("first_release_date"):
                game_data["release_date"] = time.strftime("%Y-%m-%d", time.gmtime(selected_game["first_release_date"]))

            # Build the combined search query using the game title and selected platform
            search_query = game_data["title"]
            if selected_platform:
                search_query += " " + selected_platform
            logging.debug(f"Using price scrape query: '{search_query}'")

            # Get the price source from backend configuration
            price_source = get_price_source()
            logging.debug(f"Using price source: {price_source}")

            # Perform price scraping using the selected source
            if price_source == "Amazon":
                scraped_price = scrape_amazon_price(search_query)
            elif price_source == "CeX":
                scraped_price = scrape_cex_price(search_query)
            else:  # Default to eBay
                scraped_price = scrape_ebay_prices(search_query)
            
            game_data["average_price"] = scraped_price

            logging.debug(f"Scraped price from {price_source}: {scraped_price}")

            inserted = save_game_to_db(game_data)
            if not inserted:
                return jsonify({
                    "error": f"Game with title '{game_data['title']}' already exists in the database."
                }), 200

            logging.debug(f"Game '{game_data['title']}' added with price: {scraped_price}")
            return jsonify(game_data)

        except Exception as e:
            logging.error(f"Error in /confirm route: {e}")
            return jsonify({"error": str(e)}), 500
    
def search_game_fuzzy_with_alternates(game_name, auth_token, max_attempts=30, fuzzy_threshold=60):
    search_attempts = [game_name]
    attempt_count = 0
    best_results = []

    while search_attempts and attempt_count < max_attempts:
        current_title = search_attempts.pop(0).strip()
        attempt_count += 1
        logging.debug(f"IGDB Search Attempt {attempt_count}/{max_attempts} for: {current_title}")

        igdb_response = search_igdb_game(current_title, auth_token)
        if igdb_response:
            best_results = igdb_response
            break

        cleaned_title = clean_game_title(current_title)
        if cleaned_title and cleaned_title != current_title:
            search_attempts.append(cleaned_title)
        next_attempt = remove_last_word(current_title)
        while next_attempt and next_attempt != current_title:
            search_attempts.append(next_attempt)
            current_title = next_attempt
            next_attempt = remove_last_word(current_title)

    if not best_results:
        return None, []

    game_names = [g["name"] for g in best_results if "name" in g]
    if not game_names:
        return None, []

    # Best fuzzy match for the entire list:
    best_match_name, best_score = process.extractOne(game_name, game_names)
    if best_score < fuzzy_threshold:
        # The top match isn't even above threshold => no results
        return None, []

    exact_match = None
    alternative_matches = []
    for g in best_results:
        if "name" not in g:
            continue
        # Compare this game’s name to the user’s original search
        score = process.extractOne(game_name, [g["name"]])[1]
        logging.debug(f"Candidate: {g['name']} => Score: {score}")

        if g["name"] == best_match_name:
            exact_match = g
        else:
            if score >= fuzzy_threshold:
                alternative_matches.append(g)

    return exact_match, alternative_matches


def search_game_with_fuzzy_matching(game_name, auth_token, max_attempts=30):
    """
    Searches IGDB using a combination of exact matches, simplified title matches, 
    and fuzzy matching to find the best possible game match.
    Always returns a tuple: (exact_match, alternative_match), with alternative_match as None if not available.
    """
    search_attempts = [game_name]
    attempt_count = 0  

    while search_attempts and attempt_count < max_attempts:
        current_title = search_attempts.pop(0).strip()
        attempt_count += 1

        logging.debug(f"IGDB Search Attempt {attempt_count}/{max_attempts} for: {current_title}")
        igdb_response = search_igdb_game(current_title, auth_token)

        if igdb_response:
            # Check for an exact match
            for game in igdb_response:
                if "name" in game and game["name"].lower() == current_title.lower():
                    logging.debug(f"✅ Exact match found: {game['name']}")
                    return game, None  # Always return a tuple (exact_match, alternative_match)

            # Try fuzzy matching if no exact match is found
            fuzzy_match = fuzzy_match_title(current_title, igdb_response)
            if fuzzy_match:
                return fuzzy_match, None

        # If no match, generate new variations of the title
        if attempt_count < max_attempts:
            cleaned_title = clean_game_title(current_title)
            if cleaned_title and cleaned_title != current_title:
                search_attempts.append(cleaned_title)
            next_attempt = remove_last_word(current_title)
            while next_attempt and next_attempt != current_title:
                search_attempts.append(next_attempt)
                current_title = next_attempt  # Continue trimming
                next_attempt = remove_last_word(current_title)

    logging.warning("⏳ Max API attempts reached. Returning best available results.")
    return None, None


def search_game_with_alternatives(game_name, auth_token, max_attempts=50):
    search_attempts = [game_name]
    exact_match = None
    alternative_matches = []
    attempt_count = 0

    while search_attempts and attempt_count < max_attempts:
        current_title = search_attempts.pop(0).strip()
        attempt_count += 1
        logging.debug(f"IGDB Search Attempt {attempt_count}/{max_attempts} for: {current_title}")
        igdb_response = search_igdb_game(current_title, auth_token)

        if igdb_response:
            # Find an exact match (case insensitive)
            for game in igdb_response:
                if "name" in game and game["name"].lower() == current_title.lower():
                    if not exact_match:
                        exact_match = game
                        logging.debug(f"Exact match found: {game['name']}")

            # Consider all games that are not the exact match as potential alternatives.
            for game in igdb_response:
                if exact_match and game["name"].lower() != exact_match["name"].lower():
                    # Optionally, use fuzzy matching to ensure quality (e.g., score > 60)
                    score = process.extractOne(game_name, [game["name"]])[1]
                    if score > 60:
                        alternative_matches.append(game)
                        logging.debug(f"Alternative match candidate (score {score}): {game['name']}")
                elif not exact_match:
                    # If there's no exact match yet, add all as alternatives.
                    alternative_matches.append(game)
                    logging.debug(f"Alternative match candidate: {game['name']}")

            if exact_match or alternative_matches:
                return exact_match, alternative_matches

        # If no match, try modifying the title
        cleaned_title = clean_game_title(current_title)
        if cleaned_title and cleaned_title != current_title:
            search_attempts.append(cleaned_title)
        next_attempt = remove_last_word(current_title)
        if next_attempt and next_attempt != current_title:
            search_attempts.append(next_attempt)

    logging.warning("⏳ Max API attempts reached. Returning best available results.")
    return exact_match, alternative_matches

@app.route("/top_games", methods=["GET"])
def get_top_games():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, database_path)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM games WHERE average_price IS NOT NULL ORDER BY average_price DESC LIMIT 5")
    games = cursor.fetchall()
    conn.close()

    game_list = []
    for game in games:
        game_list.append(
            {
                "id": game[0],
                "title": game[1],
                "cover_image": game[2],
                "description": game[3],
                "publisher": game[4],
                "platforms": game[5],
                "genres": game[6],
                "series": game[7],
                "release_date": game[8],
                "average_price": game[9],
            }
        )

    return jsonify(game_list)

@app.route("/search_game_by_id", methods=["POST"])
def search_game_by_id():
    try:
        data = request.json
        igdb_id = data.get("igdb_id")

        igdb_access_token = get_igdb_access_token()
        if not igdb_access_token:
            return jsonify({"error": "Failed to retrieve IGDB access token"}), 500

        url = f"https://api.igdb.com/v4/games"
        headers = {
            "Client-ID": IGDB_CLIENT_ID,
            "Authorization": f"Bearer {igdb_access_token}",
        }
        body = f"fields name, cover.url, summary, platforms.name, genres.name, involved_companies.company.name, franchises.name, first_release_date; where id = {igdb_id};"
        response = requests.post(url, headers=headers, data=body)
        response_json = response.json()
        logging.debug(f"IGDB search response for ID {igdb_id}: {response_json}")

        if response_json:
            return jsonify(response_json[0]), 200
        else:
            return jsonify({"error": "No results found"}), 404

    except Exception as e:
        logging.error(f"Error in /search_game_by_id route: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/search_game_by_name", methods=["POST"])
def search_game_by_name():
    try:
        data = request.json
        game_name = data.get("game_name")

        igdb_access_token = get_igdb_access_token()
        if not igdb_access_token:
            return jsonify({"error": "Failed to retrieve IGDB access token"}), 500

        exact_match, alternative_matches = search_game_with_alternatives(game_name, igdb_access_token)

        if exact_match or alternative_matches:
            # A helper function to fetch game details
            def get_game_details(game):
                return {
                    "name": game.get("name"),
                    "cover_url": game.get("cover", {}).get("url"),
                    "summary": game.get("summary"),
                    "platforms": [platform["name"] for platform in game.get("platforms", [])],
                    "genres": [genre["name"] for genre in game.get("genres", [])],
                    "release_date": game.get("first_release_date"),
                    "franchises": [franchise["name"] for franchise in game.get("franchises", [])],
                    "series": [series["name"] for series in game.get("series", [])],
                    "involved_companies": [company["company"]["name"] for company in game.get("involved_companies", [])]
                }

            exact_match_details = get_game_details(exact_match) if exact_match else None
            alternative_match_details = [get_game_details(game) for game in alternative_matches] if alternative_matches else []

            return jsonify({
                "exact_match": exact_match_details,
                "alternative_matches": alternative_match_details
            }), 200
        else:
            return jsonify({"error": "No results found"}), 404

    except Exception as e:
        logging.error(f"Error in /search_game_by_name route: {e}")
        return jsonify({"error": str(e)}), 500

def save_game_to_db(game_data):
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, database_path)
        conn = get_db_connection()
        cursor = conn.cursor()
        logging.debug(f"Inserting game data: {game_data}")

        release_date = game_data.get("release_date") or "1900-01-01"
        
        # Use TRIM on title and check for matching platform as well.
        # We'll consider the first platform from the list for comparison.
        platform_str = ""
        if game_data["platforms"]:
            platform_str = game_data["platforms"][0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM games WHERE TRIM(title) = ? AND platforms LIKE ?",
            (game_data["title"].strip(), f"%{platform_str}%")
        )
        count = cursor.fetchone()[0]

        if count == 0:
            # Ensure cover_image is a string.
            cover_image = game_data.get("cover_image")
            if cover_image is None:
                cover_image = ""
            cursor.execute(
                """
                INSERT INTO games (id, title, cover_image, description, publisher, platforms, genres, series, release_date, average_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generate_random_id(),
                    game_data["title"],
                    cover_image,
                    game_data["description"],
                    ", ".join(game_data["publisher"]),
                    ", ".join(game_data["platforms"]),
                    ", ".join(game_data["genres"]),
                    ", ".join(game_data["series"]),
                    game_data["release_date"],
                    game_data["average_price"],
                ),
            )
            conn.commit()
            logging.debug("Data inserted into database successfully.")
            return True
        else:
            logging.debug(f"Game with title '{game_data['title']}' and platform '{platform_str}' already exists in the database")
            return False
    except Exception as e:
        logging.error(f"Error saving game to database: {e}")
        return False
    finally:
        conn.close()

@app.route("/games", methods=["GET"])
def get_games():
    publisher = request.args.get("publisher")
    platform = request.args.get("platform")
    genre = request.args.get("genre")
    year = request.args.get("year")
    title = request.args.get("title")
    sort = request.args.get("sort")  # e.g. "alphabetical"

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, database_path)

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM games WHERE 1=1"
    params = []

    if publisher:
        query += " AND publisher LIKE ?"
        params.append(f"%{publisher}%")

    if platform:
        query += " AND platforms LIKE ?"
        params.append(f"%{platform}%")

    if genre:
        query += " AND genres LIKE ?"
        params.append(f"%{genre}%")

    if year:
        query += ' AND strftime("%Y", release_date) = ?'
        params.append(year)

    if title:
        query += " AND title LIKE ?"
        params.append(f"%{title}%")  # Allow partial matches

    if sort == "alphabetical":
        query += " ORDER BY title ASC"
    elif sort == "highest":
        query += " ORDER BY average_price DESC"
        #Handles NULLS by placing them at the end
        query += " NULLS LAST"

    cursor.execute(query, params)
    games = cursor.fetchall()
    conn.close()

    game_list = []
    for game in games:
        game_list.append(
            {
                "id": game[0],
                "title": game[1],
                "cover_image": game[2],
                "description": game[3],
                "publisher": game[4],
                "platforms": game[5],
                "genres": game[6],
                "series": game[7],
                "release_date": game[8],
                "average_price": game[9],
            }
        )

    # logging.debug(f"Fetched games: {game_list}")
    return jsonify(game_list)


@app.route("/consoles", methods=["GET"])
def get_consoles():
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT platforms FROM games")
    platforms = cursor.fetchall()
    conn.close()

    console_set = set()
    for platform_tuple in platforms:
        platform_list = platform_tuple[0].split(", ")
        console_set.update(platform_list)

    return jsonify(list(console_set))


@app.route("/unique_values", methods=["GET"])
def get_unique_values():
    value_type = request.args.get("type")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, database_path)
    conn = get_db_connection()
    cursor = conn.cursor()

    if value_type == "publisher":
        cursor.execute("SELECT DISTINCT publisher FROM games")
    elif value_type == "platform":
        cursor.execute("SELECT DISTINCT platforms FROM games")
    elif value_type == "genre":
        cursor.execute("SELECT DISTINCT genres FROM games")
    elif value_type == "year":
        cursor.execute('SELECT DISTINCT strftime("%Y", release_date) FROM games')
    else:
        conn.close()
        return jsonify([]), 400

    values = cursor.fetchall()
    conn.close()

    unique_values = set()
    for value_tuple in values:
        # Get the raw value
        value = value_tuple[0]
        # Skip if value is None or an empty string
        if not value or value.strip() == "":
            continue

        if value_type == "year":
            unique_values.add(value)
        else:
            value_list = value.split(", ")
            unique_values.update(value_list)

    return jsonify(list(unique_values))


@app.route("/add_game", methods=["POST"])
def add_game():
    game_data = request.json
    save_game_to_db(game_data)
    return jsonify({"message": "Game added successfully"}), 201


@app.route("/delete_game", methods=["POST"])
def delete_game():
    data = request.json
    game_id = data.get("id")
    logging.debug(f"Received request to delete game with ID: {game_id}")

    if not isinstance(game_id, int):
        logging.error(f"Game ID is not an integer: {game_id}")
        return jsonify({"error": "Invalid game ID type"}), 400

    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, database_path)
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the game ID exists
        cursor.execute("SELECT COUNT(*) FROM games WHERE id = ?", (game_id,))
        count = cursor.fetchone()[0]
        if count == 0:
            logging.debug(f"No game found with ID: {game_id}")
            return jsonify({"error": "No game found with the given ID"}), 404

        # Perform the deletion
        cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
        conn.commit()
        logging.debug(f"Deleted game with ID: {game_id}")

        conn.close()
        return jsonify(), 200

    except Exception as e:
        logging.error(f"Error deleting game: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/update_game/<int:game_id>", methods=["PUT"])
def update_game(game_id):
    data = request.json
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, database_path)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update game data, including average_price
        cursor.execute("""
            UPDATE games
            SET title = ?, cover_image = ?, description = ?, publisher = ?, platforms = ?, genres = ?, series = ?, release_date = ?, average_price = ?
            WHERE id = ?
        """, (
            data["title"],
            data["cover_image"],
            data["description"],
            ", ".join(data["publisher"]),
            ", ".join(data["platforms"]),
            ", ".join(data["genres"]),
            ", ".join(data["series"]),
            data["release_date"],
            data["average_price"],
            game_id
        ))

        conn.commit()
        conn.close()
        return jsonify({"message": "Game updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/game/<int:game_id>", methods=["GET"])
def fetch_game_by_id(game_id):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, database_path)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        game = cursor.fetchone()
        conn.close()

        if game:
            return jsonify({
                "id": game[0],
                "title": game[1],
                "cover_image": game[2],
                "description": game[3],
                "publisher": game[4].split(", "),
                "platforms": game[5].split(", "),
                "genres": game[6].split(", "),
                "series": game[7].split(", "),
                "release_date": game[8],
                "average_price": game[9],
            }), 200
        else:
            return jsonify({"error": "Game not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/export_csv", methods=["GET"])
def export_csv():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, database_path)

    # Get filter parameters from query string
    publisher = request.args.get("publisher", "")
    platform = request.args.get("platform", "")
    genre = request.args.get("genre", "")
    year = request.args.get("year", "")
    title = request.args.get("title", "")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Build a dynamic query
    query = "SELECT * FROM games WHERE 1=1"
    params = []

    if publisher:
        query += " AND publisher LIKE ?"
        params.append(f"%{publisher}%")
    if platform:
        query += " AND platforms LIKE ?"
        params.append(f"%{platform}%")
    if genre:
        query += " AND genres LIKE ?"
        params.append(f"%{genre}%")
    if year:
        query += ' AND strftime("%Y", release_date) = ?'
        params.append(year)
    if title:
        query += " AND title LIKE ?"
        params.append(f"%{title}%")

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow(["id", "title", "cover_image", "description", "publisher",
                     "platforms", "genres", "series", "release_date", "average_price"])
    for row in rows:
        writer.writerow(row)

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=games_export.csv"}
    )

# -------------------------
# Price Source Configuration Endpoints
# -------------------------

@app.route("/price_source", methods=["GET"])
def get_price_source_endpoint():
    """Get current price source preference"""
    try:
        current_price_source = get_price_source()
        return jsonify({"price_source": current_price_source}), 200
    except Exception as e:
        logging.error(f"Error getting price source: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/price_source", methods=["POST"])
def set_price_source_endpoint():
    """Set price source preference"""
    try:
        data = request.json
        price_source = data.get("price_source")
        
        if not price_source:
            return jsonify({"error": "price_source is required"}), 400
        
        if set_price_source(price_source):
            logging.debug(f"Price source updated to: {price_source}")
            return jsonify({"message": f"Price source set to {price_source}"}), 200
        else:
            return jsonify({"error": "Invalid price source. Must be eBay, Amazon, or CeX"}), 400
            
    except Exception as e:
        logging.error(f"Error setting price source: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)

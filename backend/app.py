import json
import os, sys
import random
import time
import requests
import logging
import re
import sqlite3
from fuzzywuzzy import process
import csv
import shutil
from datetime import datetime
import io
import unicodedata

# Import YouTube trailer fetcher function
try:
    from fetch_youtube_trailers import get_youtube_video_id
except ImportError:
    print("Warning: YouTube trailer fetcher not available")
    def get_youtube_video_id(query):
        return None

# Conditional imports for Docker vs local environment
try:
    # Try Docker-compatible imports first
    if os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv'):
        print("🐳 Docker environment detected - using standard selenium")
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.chrome.service import Service as ChromeService
    else:
        # Local environment imports
        print("💻 Local environment detected - using undetected-chromedriver")
        import undetected_chromedriver as uc
        import chromedriver_autoinstaller
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.chrome.service import Service as ChromeService
except ImportError as e:
    print(f"⚠️ Import warning: {e}")
    # Fallback to basic selenium - will disable old functions
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.chrome.service import Service as ChromeService
    except ImportError:
        print("❌ No selenium available - old scraper functions will be disabled")
        # Define dummy classes to prevent NameError
        class DummyClass:
            pass
        webdriver = DummyClass()
        Service = DummyClass
        Options = DummyClass
        By = DummyClass()
        WebDriverWait = DummyClass
        EC = DummyClass()
        Keys = DummyClass()
        ChromeService = DummyClass

# Calculate paths
# PROJECT_ROOT is the parent of the backend folder in local dev, but will be '/'
# inside the container. Use APP_ROOT for container-safe absolute base.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print("Project root added to sys.path:", PROJECT_ROOT)

# Import scraper functions robustly from canonical modules directory
try:
    # Prefer canonical package import
    from modules.scrapers import (
        scrape_barcode_lookup,
        scrape_amazon_price,
        scrape_ebay_prices,
        scrape_cex_price,
        scrape_pricecharting_price,
        get_best_pricecharting_price,
        get_pricecharting_price_by_condition,
    )
    print("✅ Successfully imported scrapers from modules.scrapers")
except ImportError:
    # Ensure the modules directory itself is on sys.path and import as flat module
    modules_path = os.path.join(PROJECT_ROOT, 'modules')
    if modules_path not in sys.path:
        sys.path.insert(0, modules_path)
    from scrapers import (
        scrape_barcode_lookup,
        scrape_amazon_price,
        scrape_ebay_prices,
        scrape_cex_price,
        scrape_pricecharting_price,
        get_best_pricecharting_price,
        get_pricecharting_price_by_condition,
    )
    print("✅ Successfully imported scrapers from modules directory path")

from flask import Flask, request, jsonify, Response, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv


app = Flask(__name__)

# IGDB credentials default from environment (used as final fallback)
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID", "")
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET", "")

# Specify the exact path to the ChromeDriver binary
# driver_path = "/opt/homebrew/bin/chromedriver"  # Replace with the actual path - NOT USED IN DOCKER

# Legacy driver path for old functions (not used in Docker)
try:
    if os.path.exists("/opt/homebrew/bin/chromedriver"):
        driver_path = "/opt/homebrew/bin/chromedriver" 
    else:
        driver_path = None  # Will disable old functions
except:
    driver_path = None

# Specify the path to the SQLite database

# External for local
# database_path = "/Volumes/backup_proxmox/lukabratzee/games.db"
###### DB LOAD ######

# Get the project root directory (one level up from backend)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env variables
load_dotenv()

# Get database path from .env
database_path = os.getenv("DATABASE_PATH", "").strip()

print(f"📜 DATABASE_PATH from .env: '{database_path}'")

# If the path is not absolute, then join with BASE_DIR (project root)
if not os.path.isabs(database_path):
    database_path = os.path.join(BASE_DIR, database_path)

print(f"✅ Final Database Path: {database_path}")
print(f"🧐 File Exists: {os.path.exists(database_path)}")

####################

# -------------------------
# Artwork storage configuration (for uploads and serving)
# Use the directory that holds the database (e.g., /app/data) so files persist.
# -------------------------
DATA_DIR = os.path.dirname(database_path) if os.path.isabs(database_path) else os.path.join(PROJECT_ROOT, os.path.dirname(database_path))
ARTWORK_DIR = os.path.join(DATA_DIR, "artwork")
GRID_DIR = os.path.join(ARTWORK_DIR, "grids")
HERO_DIR = os.path.join(ARTWORK_DIR, "heroes")
LOGO_DIR = os.path.join(ARTWORK_DIR, "logos")
ICON_DIR = os.path.join(ARTWORK_DIR, "icons")

for directory in [DATA_DIR, ARTWORK_DIR, GRID_DIR, HERO_DIR, LOGO_DIR, ICON_DIR]:
    os.makedirs(directory, exist_ok=True)

# -------------------------
# Text Normalization for Search
# -------------------------
def normalize_for_search(text):
    """
    Normalize text for search by removing accents and special characters.
    This allows 'Pokemon' to match 'Pokémon', etc.
    """
    if not text:
        return ""
    
    # Normalize unicode characters (NFD = decomposed form)
    normalized = unicodedata.normalize('NFD', text)
    
    # Remove combining characters (accents)
    ascii_text = ''.join(char for char in normalized 
                        if unicodedata.category(char) != 'Mn')
    
    # Convert to lowercase for case-insensitive search
    return ascii_text.lower()

# -------------------------
# Price Source Configuration Management
# -------------------------

# Determine config file path based on environment
if os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv'):
    # In Docker, the config is mounted at /app/config
    CONFIG_FILE = "/app/config/config.json"
else:
    # Local development - config is relative to project root
    CONFIG_FILE = os.path.join(BASE_DIR, "config", "config.json")

def load_config():
    """Load configuration from JSON file, create default if doesn't exist"""
    default_config = {
        "price_source": "PriceCharting",
        "steamgriddb_api_key": "your_steamgriddb_api_key_here_get_from_https://www.steamgriddb.com/profile/preferences/api",
        "igdb_client_id": "",
        "igdb_client_secret": ""
    }
    
    # Debug logging
    logging.info(f"Loading config from: {CONFIG_FILE}")
    logging.info(f"Config file absolute path: {os.path.abspath(CONFIG_FILE)}")
    logging.info(f"Docker environment: {os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv')}")
    
    # Ensure config directory exists
    config_dir = os.path.dirname(CONFIG_FILE)
    logging.info(f"Config directory: {config_dir}")
    logging.info(f"Config directory absolute path: {os.path.abspath(config_dir)}")
    
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir, exist_ok=True)
            logging.info(f"✅ Created config directory: {config_dir}")
        except OSError as e:
            logging.error(f"❌ Failed to create config directory: {e}")
            return default_config
    else:
        logging.info(f"✅ Config directory already exists: {config_dir}")
    
    if os.path.exists(CONFIG_FILE):
        try:
            logging.info(f"✅ Config file exists, loading...")
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Ensure price_source exists and is valid
                if "price_source" not in config or config["price_source"] not in ["eBay", "Amazon", "CeX", "PriceCharting"]:
                    config["price_source"] = "PriceCharting"
                
                # Ensure keys exist; add placeholders if missing
                changed = False
                if "steamgriddb_api_key" not in config:
                    config["steamgriddb_api_key"] = "your_steamgriddb_api_key_here_get_from_https://www.steamgriddb.com/profile/preferences/api"
                    changed = True
                if "igdb_client_id" not in config:
                    config["igdb_client_id"] = ""
                    changed = True
                if "igdb_client_secret" not in config:
                    config["igdb_client_secret"] = ""
                    changed = True
                if changed:
                    logging.info(f"📝 Updating config with missing keys...")
                    save_config(config)
                
                logging.info(f"✅ Config loaded successfully from {CONFIG_FILE}")
                return config
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"⚠️  Failed to load config file: {e}, creating default config")
    else:
        logging.info(f"📝 Config file does not exist at {CONFIG_FILE}")
    
    # Create default config file
    logging.info(f"📝 Creating default config file at: {CONFIG_FILE}")
    save_config(default_config)
    return default_config

def save_config(config):
    """Save configuration to JSON file"""
    try:
        # Ensure config directory exists
        config_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            logging.info(f"Created config directory: {config_dir}")
        
        # Debug logging
        logging.info(f"Attempting to save config to: {CONFIG_FILE}")
        logging.info(f"Config file absolute path: {os.path.abspath(CONFIG_FILE)}")
        logging.info(f"Config directory exists: {os.path.exists(config_dir)}")
        logging.info(f"Config directory writable: {os.access(config_dir, os.W_OK) if os.path.exists(config_dir) else False}")
        logging.info(f"Config file writable: {os.access(os.path.dirname(CONFIG_FILE), os.W_OK) if os.path.dirname(CONFIG_FILE) else False}")
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logging.info(f"✅ Config saved successfully to: {CONFIG_FILE}")
        
        # Verify the file was created and has the right content
        if os.path.exists(CONFIG_FILE):
            file_size = os.path.getsize(CONFIG_FILE)
            logging.info(f"Config file created successfully. Size: {file_size} bytes")
        else:
            logging.error(f"❌ Config file was not created at {CONFIG_FILE}")
            
    except IOError as e:
        logging.error(f"❌ Failed to save config to {CONFIG_FILE}: {e}")
        # In Docker, try to use a fallback location
        if os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv'):
            try:
                fallback_config = "/tmp/config.json"
                with open(fallback_config, 'w') as f:
                    json.dump(config, f, indent=2)
                logging.warning(f"Config saved to fallback location: {fallback_config}")
            except Exception as fallback_error:
                logging.error(f"Failed to save config to fallback location: {fallback_error}")
        raise  # Re-raise the exception so the calling function knows it failed

def get_price_source():
    """Get current price source preference"""
    config = load_config()
    return config.get("price_source", "PriceCharting")

def get_default_region():
    """Get current default region preference"""
    config = load_config()
    return config.get("default_region", "PAL")

def set_default_region(region):
    """Set default region preference"""
    if region not in ["PAL", "NTSC", "Japan"]:
        logging.warning(f"Invalid region attempted: {region}")
        return False
    
    try:
        config = load_config()
        config["default_region"] = region
        save_config(config)
        logging.info(f"Default region set to: {region}")
        return True
    except Exception as e:
        logging.error(f"Failed to set default region: {e}")
        return False

def set_price_source(price_source):
    """Set price source preference"""
    if price_source not in ["eBay", "Amazon", "CeX", "PriceCharting"]:
        logging.warning(f"Invalid price source attempted: {price_source}")
        return False
    
    logging.info(f"Setting price source to: {price_source}")
    logging.info(f"Config file path: {CONFIG_FILE}")
    logging.info(f"Config file absolute path: {os.path.abspath(CONFIG_FILE)}")
    
    config = load_config()
    config["price_source"] = price_source
    
    # Log the current config before saving
    logging.info(f"Current config before saving: {config}")
    
    save_config(config)
    
    # Verify the save was successful by reading it back
    try:
        with open(CONFIG_FILE, 'r') as f:
            saved_config = json.load(f)
            logging.info(f"Config file after saving: {saved_config}")
            if saved_config.get("price_source") == price_source:
                logging.info(f"✅ Price source '{price_source}' saved successfully to {CONFIG_FILE}")
            else:
                logging.error(f"❌ Price source verification failed. Expected: {price_source}, Got: {saved_config.get('price_source')}")
                return False
    except Exception as e:
        logging.error(f"❌ Failed to verify saved config: {e}")
        return False
    
    return True

####################
# Set up logging
logging.basicConfig(level=logging.DEBUG)
# Helper to resolve IGDB credentials from config or env at call time
def get_igdb_credentials() -> tuple[str, str]:
    cfg = load_config()
    client_id = (cfg.get("igdb_client_id") or os.getenv("IGDB_CLIENT_ID", "")).strip()
    client_secret = (cfg.get("igdb_client_secret") or os.getenv("IGDB_CLIENT_SECRET", "")).strip()
    return client_id, client_secret


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
    client_id, client_secret = get_igdb_credentials()
    
    # Check if credentials are properly configured
    if not client_id or not client_secret:
        logging.error("IGDB credentials not configured")
        return None
    
    if client_id.startswith("your_igdb_client_id") or client_secret.startswith("your_igdb_client_secret"):
        logging.error("IGDB credentials are set to placeholder values")
        return None
    
    try:
        url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
        response = requests.post(url)
        response.raise_for_status()
        response_data = response.json()
        
        if "error" in response_data:
            logging.error(f"IGDB authentication error: {response_data.get('error_description', 'Unknown error')}")
            return None
            
        access_token = response_data.get("access_token")
        if not access_token:
            logging.error("No access token received from IGDB")
            return None
            
        return access_token
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to get IGDB access token: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error getting IGDB access token: {e}")
        return None

# Clean the game title by removing console names

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

# NOTE: Old functions below are for compatibility - use modules/scrapers.py instead

# Legacy Amazon scraper (use modules.scrapers.scrape_amazon_price instead)
def legacy_scrape_amazon_prices(game_title):
    """
    Legacy function - redirects to modular scraper or returns empty list
    """
    if driver_path is None:
        print("⚠️ Legacy scraper disabled in Docker environment")
        return []
    
    # Original function body would be here, but disabled for Docker
    # Opens Amazon's homepage, performs a search for the given game title,
    # waits for any captcha to be resolved manually, and returns a list of price values found.
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

# Legacy barcode scraper (use modules.scrapers.scrape_barcode_lookup instead)
def legacy_scrape_barcode_lookup(barcode):
    """
    Legacy function - redirects to modular scraper or returns None values
    """
    if driver_path is None:
        print("⚠️ Legacy barcode scraper disabled in Docker environment - using modular scraper")
        # This should call the imported function instead, but for now just return safe values
        return None, None

    # Original function would continue here but is disabled for Docker compatibility
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
    client_id, _ = get_igdb_credentials()
    headers = {
        "Client-ID": client_id,
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

# -------------------------
# Health Check Endpoint
# -------------------------
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker/Portainer monitoring"""
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "database_path": database_path,
    }
    
    try:
        # Check if database file exists
        health_data["database_exists"] = os.path.exists(database_path)
        health_data["database_readable"] = os.access(database_path, os.R_OK) if os.path.exists(database_path) else False
        health_data["database_writable"] = os.access(database_path, os.W_OK) if os.path.exists(database_path) else False
        
        # Check database connectivity
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.execute("SELECT COUNT(*) FROM games")
        game_count = cursor.fetchone()[0]
        conn.close()
        
        health_data["database"] = "connected"
        health_data["game_count"] = game_count
        
        return jsonify(health_data), 200
    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["error"] = str(e)
        health_data["error_type"] = type(e).__name__
        
        # Additional debug info on failure
        try:
            health_data["database_dir_exists"] = os.path.exists(os.path.dirname(database_path))
            health_data["database_dir_writable"] = os.access(os.path.dirname(database_path), os.W_OK) if os.path.exists(os.path.dirname(database_path)) else False
        except:
            pass
            
        return jsonify(health_data), 503

class GameScan:
    response_data = None  # Class variable to store response data

    @staticmethod
    @app.route("/scan", methods=["POST"])
    def scan():
        try:
            data = request.json
            barcode = data.get("barcode")
            logging.debug(f"Received barcode: {barcode}")

            # Check IGDB credentials first
            client_id, client_secret = get_igdb_credentials()
            if not client_id or not client_secret:
                return jsonify({
                    "error": "IGDB API credentials not configured",
                    "details": "Please add 'igdb_client_id' and 'igdb_client_secret' to your config.json file",
                    "instructions": "Get your credentials from https://dev.twitch.tv/console/apps"
                }), 400
            
            if client_id.startswith("your_igdb_client_id") or client_secret.startswith("your_igdb_client_secret"):
                return jsonify({
                    "error": "IGDB API credentials are set to placeholder values",
                    "details": "Please update your config.json file with actual IGDB credentials",
                    "instructions": "Get your credentials from https://dev.twitch.tv/console/apps"
                }), 400

            igdb_access_token = get_igdb_access_token()
            if not igdb_access_token:
                return jsonify({
                    "error": "Failed to authenticate with IGDB",
                    "details": "Unable to retrieve access token. Please check your IGDB credentials.",
                    "instructions": "Verify your 'igdb_client_id' and 'igdb_client_secret' in config.json"
                }), 500

            # Lookup via barcode to obtain game title
            game_title, _ = scrape_barcode_lookup(barcode)
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

            # Do not perform any price scraping here; pricing happens after platform selection in /confirm
            combined_price = None

            # Perform IGDB fuzzy search using game_title (without platform info)
            exact_match, alternative_matches = search_game_fuzzy_with_alternates(game_title, igdb_access_token)
            if not exact_match and not alternative_matches:
                return jsonify({"error": "No results found on IGDB"}), 404



            # Store the IGDB results (keep original for internal use in /confirm)
            GameScan.response_data = {
                "barcode": barcode,
                "game_title": game_title,
                "exact_match": exact_match,
                "alternative_matches": alternative_matches,
                "combined_price": combined_price
            }

            # Return response in exact format that the iOS Shortcut expects
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

            # Check if we need platform selection
            selected_platform_raw = data.get("selected_platform", "").strip()
            
            # If selected_platform contains newlines (multiple platforms), show platform selection
            if selected_platform_raw and "\n" in selected_platform_raw:
                # Extract platform names from the selected game
                platform_names = []
                for platform in selected_game.get("platforms", []):
                    if isinstance(platform, dict) and platform.get("name"):
                        platform_names.append(platform.get("name"))
                    elif isinstance(platform, str):
                        platform_names.append(platform)
                
                platforms_raw = "\n".join(platform_names)
                logging.warning("Client sent newline-separated platforms; returning platform options for selection")
                return jsonify({
                    "need_platform_selection": True,
                    "selected_game_name": selected_game.get("name"),
                    "platform_options": platform_names,
                    "platforms": platforms_raw
                }), 200

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

            # Get region preference from request or use configured default
            region = data.get("region")
            if not region:
                region = get_default_region()
            logging.debug(f"Using region for price scraping: {region}")
            
            # Perform price scraping using the selected source
            if price_source == "Amazon":
                scraped_price = scrape_amazon_price(search_query)
            elif price_source == "CeX":
                scraped_price = scrape_cex_price(search_query)
            elif price_source == "PriceCharting":
                # Use region from request or default to PAL
                pricecharting_data = scrape_pricecharting_price(search_query, None, region)
                # Get condition preference from request (default to CiB preference)
                prefer_boxed = data.get("prefer_boxed", True)
                # Use condition-aware pricing based on preference
                scraped_price = get_pricecharting_price_by_condition(pricecharting_data, prefer_boxed)
                
                if pricecharting_data:
                    logging.debug(f"PriceCharting pricing breakdown - Loose: £{pricecharting_data.get('loose_price')}, "
                                f"CIB: £{pricecharting_data.get('cib_price')}, New: £{pricecharting_data.get('new_price')}")
                    logging.debug(f"Selected price: £{scraped_price}")
            else:  # Default to eBay
                scraped_price = scrape_ebay_prices(search_query)
            
            game_data["average_price"] = scraped_price
            game_data["region"] = region

            logging.debug(f"Scraped price from {price_source}: {scraped_price}")
            logging.debug(f"Using region: {region}")

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
        # Compare this game's name to the user's original search
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
    cursor.execute("SELECT * FROM games WHERE average_price IS NOT NULL AND id != -1 ORDER BY average_price DESC LIMIT 5")
    games = cursor.fetchall()
    conn.close()

    game_list = []
    for game in games:
        game_list.append(
            {
                "id": game[0],
                "title": game[1],
                "cover_image": None,  # cover_image column doesn't exist in data/games.db
                "description": game[2],
                "publisher": game[3],
                "platforms": game[4],
                "genres": game[5],
                "series": game[6],
                "release_date": game[7],
                "average_price": game[8],
                "youtube_trailer_url": game[9] if len(game) > 9 else None,
                # High-resolution artwork (if available)
                "high_res_cover_url": game[10] if len(game) > 10 else None,
                "high_res_cover_path": game[11] if len(game) > 11 else None,
                "hero_image_url": game[12] if len(game) > 12 else None,
                "hero_image_path": game[13] if len(game) > 13 else None,
                "logo_image_url": game[14] if len(game) > 14 else None,
                "logo_image_path": game[15] if len(game) > 15 else None,
                "icon_image_url": game[16] if len(game) > 16 else None,
                "icon_image_path": game[17] if len(game) > 17 else None,
                "steamgriddb_id": game[18] if len(game) > 18 else None,
                "artwork_last_updated": game[19] if len(game) > 19 else None,
                "region": (game[20] if len(game) > 20 else None) or "PAL",
            }
        )

    return jsonify(game_list)

@app.route("/search_game_by_id", methods=["POST"])
def search_game_by_id():
    try:
        data = request.json
        igdb_id = data.get("igdb_id")

        # Check IGDB credentials first
        client_id, client_secret = get_igdb_credentials()
        if not client_id or not client_secret:
            return jsonify({
                "error": "IGDB API credentials not configured",
                "details": "Please add 'igdb_client_id' and 'igdb_client_secret' to your config.json file",
                "instructions": "Get your credentials from https://dev.twitch.tv/console/apps"
            }), 400
        
        if client_id.startswith("your_igdb_client_id") or client_secret.startswith("your_igdb_client_secret"):
            return jsonify({
                "error": "IGDB API credentials are set to placeholder values",
                "details": "Please update your config.json file with actual IGDB credentials",
                "instructions": "Get your credentials from https://dev.twitch.tv/console/apps"
            }), 400

        igdb_access_token = get_igdb_access_token()
        if not igdb_access_token:
            return jsonify({
                "error": "Failed to authenticate with IGDB",
                "details": "Unable to retrieve access token. Please check your IGDB credentials.",
                "instructions": "Verify your 'igdb_client_id' and 'igdb_client_secret' in config.json"
            }), 500

        url = f"https://api.igdb.com/v4/games"
        client_id, _ = get_igdb_credentials()
        headers = {
            "Client-ID": client_id,
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

        # Check IGDB credentials first
        client_id, client_secret = get_igdb_credentials()
        if not client_id or not client_secret:
            return jsonify({
                "error": "IGDB API credentials not configured",
                "details": "Please add 'igdb_client_id' and 'igdb_client_secret' to your config.json file",
                "instructions": "Get your credentials from https://dev.twitch.tv/console/apps"
            }), 400
        
        if client_id.startswith("your_igdb_client_id") or client_secret.startswith("your_igdb_client_secret"):
            return jsonify({
                "error": "IGDB API credentials are set to placeholder values",
                "details": "Please update your config.json file with actual IGDB credentials",
                "instructions": "Get your credentials from https://dev.twitch.tv/console/apps"
            }), 400

        igdb_access_token = get_igdb_access_token()
        if not igdb_access_token:
            return jsonify({
                "error": "Failed to authenticate with IGDB",
                "details": "Unable to retrieve access token. Please check your IGDB credentials.",
                "instructions": "Verify your 'igdb_client_id' and 'igdb_client_secret' in config.json"
            }), 500

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
        
        # Use TRIM on title and check for matching platform AND region as well.
        # We'll consider the first platform from the list for comparison.
        platform_str = ""
        if game_data["platforms"]:
            platform_str = game_data["platforms"][0]
        # Default region to PAL if not provided
        region = (game_data.get("region") or "PAL").strip().upper()
        
        cursor.execute(
            "SELECT COUNT(*) FROM games WHERE TRIM(title) = ? AND platforms LIKE ? AND UPPER(IFNULL(region, 'PAL')) = ?",
            (game_data["title"].strip(), f"%{platform_str}%", region)
        )
        count = cursor.fetchone()[0]

        if count == 0:
            # Generate YouTube trailer URL
            youtube_trailer_url = None
            title = game_data.get("title", "")
            platforms = game_data.get("platforms", [])
            if title and platforms:
                platform = platforms[0] if platforms else ""
                search_query = f"{title} {platform}"
                try:
                    video_id = get_youtube_video_id(search_query)
                    if video_id:
                        youtube_trailer_url = f"https://www.youtube.com/watch?v={video_id}"
                        logging.debug(f"Found YouTube trailer: {youtube_trailer_url}")
                except Exception as e:
                    logging.warning(f"Failed to fetch YouTube trailer for {title}: {e}")
            
            game_id = generate_random_id()
            cursor.execute(
                """
                INSERT INTO games (id, title, description, publisher, platforms, genres, series, release_date, average_price, youtube_trailer_url, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    game_data["title"],
                    game_data["description"],
                    ", ".join(game_data["publisher"]),
                    ", ".join(game_data["platforms"]),
                    ", ".join(game_data["genres"]),
                    ", ".join(game_data["series"]),
                    game_data["release_date"],
                    game_data["average_price"],
                    youtube_trailer_url,
                    region,
                ),
            )
            conn.commit()
            logging.debug("Data inserted into database successfully.")
            
            # Automatically attempt to fetch high-resolution artwork for the new game
            try:
                fetch_artwork_for_game(game_id)
                logging.debug(f"Attempted to fetch high-res artwork for game ID: {game_id}")
            except Exception as e:
                logging.warning(f"Failed to fetch high-res artwork for new game {game_id}: {e}")
            
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
    
    # Pagination parameters
    page = int(request.args.get("page", 1))
    per_page = request.args.get("per_page")
    if per_page:
        per_page = min(int(per_page), 10000)  # Cap at 10000 games per page for price range calculations

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, database_path)

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM games WHERE 1=1 AND id != -1"
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
        # Enhanced search with special character normalization
        # This allows "Pokemon" to find "Pokémon" and vice versa
        normalized_search = normalize_for_search(title)
        
        # Search using both the original term and the accent-stripped version
        # Use REPLACE to strip accents from database titles for comparison
        query += """ AND (
            LOWER(title) LIKE ? OR 
            LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                title, 'é', 'e'), 'è', 'e'), 'ê', 'e'), 'ë', 'e'), 
                'á', 'a'), 'à', 'a'), 'ä', 'a'), 'â', 'a'),
                'ó', 'o'), 'ò', 'o')) LIKE ?
        )"""
        params.append(f"%{title.lower()}%")
        params.append(f"%{normalized_search}%")

    # Optional region filter
    region = request.args.get("region")
    if region:
        query += " AND UPPER(IFNULL(region, 'PAL')) = ?"
        params.append(region.upper())
    
    # Optional price range filter
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    if price_min:
        try:
            query += " AND average_price >= ?"
            params.append(float(price_min))
        except (ValueError, TypeError):
            pass
    if price_max:
        try:
            query += " AND average_price <= ?"
            params.append(float(price_max))
        except (ValueError, TypeError):
            pass

    if sort == "alphabetical":
        query += " ORDER BY title ASC"
    elif sort == "highest":
        query += " ORDER BY average_price DESC"
        #Handles NULLS by placing them at the end
        query += " NULLS LAST"

    # Handle pagination if requested
    if per_page:
        # Get total count first
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        try:
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"/games count query failed: {e}")
            conn.close()
            return jsonify({"error": "Count query failed"}), 500
        
        # Add pagination to main query
        offset = (page - 1) * per_page
        query += f" LIMIT {per_page} OFFSET {offset}"
    
    try:
        cursor.execute(query, params)
        games = cursor.fetchall()
    except Exception as e:
        logging.error(f"/games query failed: {e}\nQuery: {query}\nParams: {params}")
        conn.close()
        return jsonify({"error": "Query failed"}), 500
    conn.close()

    game_list = []
    for game in games:
        game_list.append(
            {
                "id": game[0],
                "title": game[1],
                "cover_image": None,  # cover_image column doesn't exist in data/games.db
                "description": game[2],
                "publisher": game[3],
                "platforms": game[4],
                "genres": game[5],
                "series": game[6],
                "release_date": game[7],
                "average_price": game[8],
                "youtube_trailer_url": game[9] if len(game) > 9 else None,
                # High-resolution artwork (if available)
                "high_res_cover_url": game[10] if len(game) > 10 else None,
                "high_res_cover_path": game[11] if len(game) > 11 else None,
                "hero_image_url": game[12] if len(game) > 12 else None,
                "hero_image_path": game[13] if len(game) > 13 else None,
                "logo_image_url": game[14] if len(game) > 14 else None,
                "logo_image_path": game[15] if len(game) > 15 else None,
                "icon_image_url": game[16] if len(game) > 16 else None,
                "icon_image_path": game[17] if len(game) > 17 else None,
                "steamgriddb_id": game[18] if len(game) > 18 else None,
                "artwork_last_updated": game[19] if len(game) > 19 else None,
                "region": (game[20] if len(game) > 20 else None) or "PAL",
            }
        )

    # Return with pagination info if requested, otherwise just the games list
    if per_page:
        total_pages = (total_count + per_page - 1) // per_page
        return jsonify({
            "games": game_list,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "per_page": per_page,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        })
    else:
        # Backward compatibility - return just the list
        return jsonify(game_list)


@app.route("/consoles", methods=["GET"])
def get_consoles():
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT platforms FROM games WHERE id != -1")
    platforms = cursor.fetchall()
    conn.close()

    console_set = set()
    for platform_tuple in platforms:
        platform_list = platform_tuple[0].split(", ")
        console_set.update(platform_list)

    return jsonify(list(console_set))


@app.route("/unique_values", methods=["GET"])
def get_unique_values():
    try:
        value_type = request.args.get("type")

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, database_path)
        conn = get_db_connection()
        cursor = conn.cursor()

        if value_type == "publisher":
            cursor.execute("SELECT DISTINCT publisher FROM games WHERE id != -1")
        elif value_type == "platform":
            cursor.execute("SELECT DISTINCT platforms FROM games WHERE id != -1")
        elif value_type == "genre":
            cursor.execute("SELECT DISTINCT genres FROM games WHERE id != -1")
        elif value_type == "year":
            cursor.execute('SELECT DISTINCT strftime("%Y", release_date) FROM games WHERE id != -1')
        elif value_type == "region":
            cursor.execute("SELECT DISTINCT UPPER(IFNULL(region, 'PAL')) FROM games WHERE id != -1")
        else:
            conn.close()
            return jsonify([]), 400

        values = cursor.fetchall()
        conn.close()

        unique_values = set()
        for value_tuple in values:
            # Get the raw value
            value = value_tuple[0]
            # Skip if value is None, empty string, or placeholder
            if not value or value.strip() == "" or value == "__PLACEHOLDER__":
                continue

            if value_type in ("year", "region"):
                unique_values.add(value)
            else:
                value_list = value.split(", ")
                # Filter out placeholder values from the list
                filtered_values = [v.strip() for v in value_list if v.strip() != "__PLACEHOLDER__"]
                unique_values.update(filtered_values)

        return jsonify(list(unique_values))
    except Exception as e:
        print(f"Error in get_unique_values: {e}")
        return jsonify([]), 500


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

        # Update game data, including average_price and youtube_trailer_url
        # Default region handling
        region = (data.get("region") or "PAL").strip().upper()

        cursor.execute("""
            UPDATE games
            SET title = ?, description = ?, publisher = ?, platforms = ?, genres = ?, series = ?, release_date = ?, average_price = ?, youtube_trailer_url = ?, region = ?
            WHERE id = ?
        """, (
            data["title"],
            data["description"],
            ", ".join(data["publisher"]),
            ", ".join(data["platforms"]),
            ", ".join(data["genres"]),
            ", ".join(data["series"]),
            data["release_date"],
            data["average_price"],
            data.get("youtube_trailer_url", ""),
            region,
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
                "cover_image": None,  # cover_image column doesn't exist in data/games.db
                "description": game[2],
                "publisher": game[3].split(", "),
                "platforms": game[4].split(", "),
                "genres": game[5].split(", "),
                "series": game[6].split(", "),
                "release_date": game[7],
                "average_price": game[8],
                "youtube_trailer_url": game[9] if len(game) > 9 else None,
                # High-resolution artwork (if available)
                "high_res_cover_url": game[10] if len(game) > 10 else None,
                "high_res_cover_path": game[11] if len(game) > 11 else None,
                "hero_image_url": game[12] if len(game) > 12 else None,
                "hero_image_path": game[13] if len(game) > 13 else None,
                "logo_image_url": game[14] if len(game) > 14 else None,
                "logo_image_path": game[15] if len(game) > 15 else None,
                "icon_image_url": game[16] if len(game) > 16 else None,
                "icon_image_path": game[17] if len(game) > 17 else None,
                "steamgriddb_id": game[18] if len(game) > 18 else None,
                "artwork_last_updated": game[19] if len(game) > 19 else None,
                "region": (game[20] if len(game) > 20 else None) or "PAL",
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
    query = "SELECT * FROM games WHERE 1=1 AND id != -1"
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
        # Enhanced search with special character normalization
        normalized_search = normalize_for_search(title)
        
        # Search using both the original term and the accent-stripped version
        query += """ AND (
            LOWER(title) LIKE ? OR 
            LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                title, 'é', 'e'), 'è', 'e'), 'ê', 'e'), 'ë', 'e'), 
                'á', 'a'), 'à', 'a'), 'ä', 'a'), 'â', 'a'),
                'ó', 'o'), 'ò', 'o')) LIKE ?
        )"""
        params.append(f"%{title.lower()}%")
        params.append(f"%{normalized_search}%")

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
        
        logging.info(f"Received price source change request: {price_source}")
        logging.info(f"Request data: {data}")
        
        if not price_source:
            logging.error("No price_source provided in request")
            return jsonify({"error": "price_source is required"}), 400
        
        if price_source not in ["eBay", "Amazon", "CeX", "PriceCharting"]:
            logging.error(f"Invalid price source requested: {price_source}")
            return jsonify({"error": "Invalid price source. Must be eBay, Amazon, CeX, or PriceCharting"}), 400
        
        logging.info(f"Attempting to set price source to: {price_source}")
        
        if set_price_source(price_source):
            logging.info(f"✅ Price source successfully changed to: {price_source}")
            return jsonify({"message": f"Price source updated to {price_source}", "price_source": price_source}), 200
        else:
            logging.error(f"❌ Failed to set price source to: {price_source}")
            return jsonify({"error": "Failed to update price source"}), 500
            
    except Exception as e:
        logging.error(f"❌ Error in set_price_source_endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/default_region", methods=["GET"])
def get_default_region_endpoint():
    """Get current default region preference"""
    try:
        current_region = get_default_region()
        return jsonify({"default_region": current_region}), 200
    except Exception as e:
        logging.error(f"Error getting default region: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/default_region", methods=["POST"])
def set_default_region_endpoint():
    """Set default region preference"""
    try:
        data = request.json
        region = data.get("default_region")
        
        logging.info(f"Received default region change request: {region}")
        
        if not region:
            logging.error("No default_region provided in request")
            return jsonify({"error": "default_region is required"}), 400
        
        if region not in ["PAL", "NTSC", "Japan"]:
            logging.error(f"Invalid region requested: {region}")
            return jsonify({"error": "Invalid region. Must be PAL, NTSC, or Japan"}), 400
        
        logging.info(f"Attempting to set default region to: {region}")
        
        if set_default_region(region):
            logging.info(f"✅ Default region successfully changed to: {region}")
            return jsonify({"message": f"Default region updated to {region}", "default_region": region}), 200
        else:
            logging.error(f"❌ Failed to set default region to: {region}")
            return jsonify({"error": "Failed to update default region"}), 500
            
    except Exception as e:
        logging.error(f"❌ Error in set_default_region_endpoint: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------------
# Update Game Price Endpoint
# -------------------------

@app.route("/update_game_price/<int:game_id>", methods=["POST"])
def update_game_price(game_id):
    """Update the price of an existing game based on current price source configuration"""
    try:
        # Get the current game data
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        game = cursor.fetchone()
        conn.close()
        
        if not game:
            return jsonify({"error": "Game not found"}), 404
        
        # Extract game info for price lookup
        game_title = game[1]  # title column
        platforms = game[4]   # platforms column (cover_image removed from schema)
        
        # Use the first platform for price lookup
        selected_platform = ""
        if platforms:
            platform_list = platforms.split(", ")
            if platform_list:
                selected_platform = platform_list[0]
        
        # Build search query
        search_query = game_title
        if selected_platform:
            search_query += " " + selected_platform
        
        logging.debug(f"Updating price for game ID {game_id}: '{search_query}'")
        
        # Get the current price source configuration
        price_source = get_price_source()
        logging.debug(f"Using price source: {price_source}")
        
        # Perform price scraping based on current configuration
        new_price = None
        used_source = price_source
        if price_source == "Amazon":
            new_price = scrape_amazon_price(search_query)
        elif price_source == "CeX":
            new_price = scrape_cex_price(search_query)
        elif price_source == "PriceCharting":
            # Get region from request or current default region setting
            region = request.json.get("region") if request.json else None
            if not region:
                region = get_default_region()
            logging.debug(f"Using region for price update: {region}")
            
            pricecharting_data = scrape_pricecharting_price(search_query, None, region)
            # Get condition preference from request or default to CiB preference
            prefer_boxed = request.json.get("prefer_boxed", True) if request.json else True
            # Use condition-aware pricing based on preference
            new_price = get_pricecharting_price_by_condition(pricecharting_data, prefer_boxed)
            if pricecharting_data:
                logging.debug(
                    f"PriceCharting pricing breakdown - Loose: £{pricecharting_data.get('loose_price')}, "
                    f"CIB: £{pricecharting_data.get('cib_price')}, New: £{pricecharting_data.get('new_price')}"
                )
        else:  # Default to eBay
            new_price = scrape_ebay_prices(search_query)

        logging.debug(f"Scraped new price from {price_source}: {new_price}")

        # Only write to DB if we have a valid new price. Never overwrite with NULL/None
        if new_price is not None:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # For PriceCharting, also update the region field
            if price_source == "PriceCharting":
                cursor.execute(
                    "UPDATE games SET average_price = ?, region = ? WHERE id = ?",
                    (new_price, region, game_id)
                )
                logging.debug(f"Updated game price to £{new_price} and region to {region}")
            else:
                cursor.execute(
                    "UPDATE games SET average_price = ? WHERE id = ?",
                    (new_price, game_id)
                )
            # Record into price_history as well for auditing
            from datetime import datetime
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                """
                INSERT INTO price_history (game_id, price, price_source, date_recorded, currency)
                VALUES (?, ?, ?, ?, ?)
                """,
                (game_id, new_price, used_source, current_date, 'GBP')
            )
            conn.commit()
            conn.close()
        else:
            # No price found; preserve existing price. Do not write history.
            used_source = price_source
        
        return jsonify({
            "message": f"Price updated successfully using {used_source}",
            "game_id": game_id,
            "game_title": game_title,
            "old_price": game[8],  # average_price column
            "new_price": new_price,
            "price_source": used_source
        }), 200
        
    except Exception as e:
        logging.error(f"Error updating game price: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------------
# Update Game Artwork Endpoint
# -------------------------

@app.route("/update_game_artwork/<int:game_id>", methods=["POST"])
def update_game_artwork_endpoint(game_id):
    """Update the artwork of an existing game using SteamGridDB API"""
    try:
        # Import the artwork fetcher
        from fetch_high_res_artwork import HighResArtworkFetcher
        
        # Get the current game data to verify it exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM games WHERE id = ?", (game_id,))
        game = cursor.fetchone()
        conn.close()
        
        if not game:
            return jsonify({"error": "Game not found"}), 404
        
        game_title = game[1]  # title column
        
        # Get API key from config.json
        config = load_config()
        api_key = config.get("steamgriddb_api_key")
        
        # Debug logging for API key
        logging.info(f"SteamGridDB API key from config: {'***' + api_key[-4:] if api_key and len(api_key) > 4 else 'None/Empty'}")
        
        if not api_key or api_key.startswith("your_steamgriddb_api_key"):
            return jsonify({
                "error": "SteamGridDB API key not configured in config.json",
                "instructions": "Add 'steamgriddb_api_key' to your config.json file. Get your API key from https://www.steamgriddb.com/profile/preferences/api"
            }), 400
        
        logging.debug(f"Updating artwork for game ID {game_id}: '{game_title}'")
        
        # Initialize the artwork fetcher
        fetcher = HighResArtworkFetcher(api_key=api_key)
        
        # Process the single game
        success = fetcher.process_single_game(game_id)
        
        if success:
            return jsonify({
                "message": "Artwork updated successfully",
                "game_id": game_id,
                "game_title": game_title
            }), 200
        else:
            return jsonify({
                "error": "Failed to update artwork",
                "game_id": game_id,
                "game_title": game_title,
                "details": "SteamGridDB may not have artwork for this game"
            }), 422
        
    except ImportError as e:
        logging.error(f"Error importing artwork fetcher: {e}")
        return jsonify({"error": "Artwork fetcher module not available"}), 500
    except Exception as e:
        logging.error(f"Error updating game artwork: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------------
# Manual Artwork Upload & Serving
# -------------------------

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def _allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@app.route("/upload_game_artwork/<int:game_id>", methods=["POST"])
def upload_game_artwork(game_id: int):
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part in request"}), 400

        file = request.files["file"]
        artwork_type = request.form.get("artwork_type", "grid")  # grid|hero|logo|icon

        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        if not _allowed_image(file.filename):
            return jsonify({"error": "Unsupported file type"}), 400

        # Ensure game exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Game not found"}), 404

        # Save file to proper folder
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        dest_dir = GRID_DIR if artwork_type == "grid" else HERO_DIR if artwork_type == "hero" else LOGO_DIR if artwork_type == "logo" else ICON_DIR
        final_filename = f"{game_id}_{artwork_type}_manual{ext.lower()}"
        dest_path = os.path.join(dest_dir, final_filename)
        file.save(dest_path)

        # Build simple, stable URL rooted at /media/artwork/ ... regardless of container paths
        subdir = "grids" if artwork_type == "grid" else "heroes" if artwork_type == "hero" else "logos" if artwork_type == "logo" else "icons"
        url_path = f"/media/artwork/{subdir}/{final_filename}"
        # Also store a relative DB path under data/ for reference
        rel_path = os.path.relpath(dest_path, DATA_DIR).replace('\\', '/')  # e.g., artwork/grids/file.png

        # Update DB columns
        column_map = {
            "grid": ("high_res_cover_url", "high_res_cover_path"),
            "hero": ("hero_image_url", "hero_image_path"),
            "logo": ("logo_image_url", "logo_image_path"),
            "icon": ("icon_image_url", "icon_image_path"),
        }
        url_col, path_col = column_map.get(artwork_type, column_map["grid"])
        cursor.execute(
            f"UPDATE games SET {url_col} = ?, {path_col} = ?, artwork_last_updated = ? WHERE id = ?",
            (url_path, rel_path, time.strftime("%Y-%m-%dT%H:%M:%S"), game_id),
        )
        conn.commit()
        conn.close()

        file_exists = os.path.isfile(dest_path)

        return jsonify({
            "message": "Artwork uploaded successfully",
            "game_id": game_id,
            "artwork_type": artwork_type,
            "url": url_path,
            "file_exists": file_exists,
            "path": rel_path,
        }), 200
    except Exception as e:
        logging.error(f"Error uploading artwork: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/media/<path:filename>")
def serve_media(filename: str):
    # Serve files from project root so /media/data/artwork/... works
    directory = PROJECT_ROOT
    # Security: ensure requested path stays within project root
    safe_path = os.path.normpath(os.path.join(directory, filename))
    if not safe_path.startswith(directory):
        return jsonify({"error": "Invalid path"}), 400
    rel_dir, fname = os.path.split(filename)
    return send_from_directory(os.path.join(directory, rel_dir), fname)

@app.route("/media/artwork/<path:subpath>")
def serve_artwork(subpath: str):
    # Serve files from the ARTWORK_DIR for cleaner URLs
    # subpath is like "grids/123_grid_manual.png"
    return send_from_directory(ARTWORK_DIR, subpath)

# -------------------------
# Gallery API Endpoints - Phase 1
# -------------------------

@app.route('/api/gallery/games', methods=['GET'])
def get_gallery_games():
    """
    Get paginated gallery view of games with enhanced metadata and filtering
    
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Games per page (default: 20, max: 10000)
    - title: Filter by title (partial match)
    - platform: Filter by platform
    - genre: Filter by genre
    - tags: Filter by tags (comma-separated)
    - year_min: Minimum release year
    - year_max: Maximum release year
    - completion_status: Filter by completion status
    - sort: Sort order (title_asc, title_desc, date_desc, date_asc, rating_desc, rating_asc, price_desc, price_asc, priority_desc)
    """
    try:
        # Parse query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 10000)  # Cap at 10000 for price range calculations
        
        # Filter parameters (updated to match new API)
        search_filter = request.args.get('search', '').strip()  # Changed from title to search
        platform_filter = request.args.get('platform', '').strip()
        genre_filter = request.args.get('genre', '').strip()
        region_filter = request.args.get('region', '').strip()  # New region filter
        year_min = request.args.get('year_min')
        year_max = request.args.get('year_max')
        completion_status = request.args.get('completion_status', '').strip()
        sort_order = request.args.get('sort', 'title_asc')
        
        # Also support "limit" parameter (in addition to per_page) to match gallery_api.py
        if request.args.get('limit'):
            per_page = min(int(request.args.get('limit', 20)), 10000)
        
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Build the base query (simplified - no more tag joins)
        base_query = """
        FROM games g
        LEFT JOIN game_gallery_metadata ggm ON g.id = ggm.game_id
        """
        
        # Build WHERE conditions
        where_conditions = []
        params = []
        
        if search_filter:
            # Enhanced search with special character normalization
            normalized_search = normalize_for_search(search_filter)
            
            # Search using both the original term and the accent-stripped version
            where_conditions.append("""(
                LOWER(g.title) LIKE ? OR 
                LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    g.title, 'é', 'e'), 'è', 'e'), 'ê', 'e'), 'ë', 'e'), 
                    'á', 'a'), 'à', 'a'), 'ä', 'a'), 'â', 'a'),
                    'ó', 'o'), 'ò', 'o')) LIKE ?
            )""")
            params.append(f"%{search_filter.lower()}%")
            params.append(f"%{normalized_search}%")
        
        if platform_filter:
            # Platform filtering with support for both string and JSON array data
            # Handle both simple strings and JSON arrays
            where_conditions.append("""
                (g.platforms IS NOT NULL AND (
                    g.platforms = ? OR
                    (g.platforms LIKE '[%' AND EXISTS (
                        SELECT 1 FROM json_each(g.platforms) 
                        WHERE json_each.value = ?
                    ))
                ))
            """)
            params.extend([platform_filter, platform_filter])
        
        if genre_filter:
            where_conditions.append("g.genres LIKE ?")
            params.append(f"%{genre_filter}%")
        
        if region_filter:
            where_conditions.append("UPPER(IFNULL(g.region, 'PAL')) = ?")
            params.append(region_filter.upper())
        
        if year_min:
            where_conditions.append("CAST(substr(g.release_date, 1, 4) AS INTEGER) >= ?")
            params.append(int(year_min))
        
        if year_max:
            where_conditions.append("CAST(substr(g.release_date, 1, 4) AS INTEGER) <= ?")
            params.append(int(year_max))
        
        # Price range filters
        price_min = request.args.get('price_min')
        price_max = request.args.get('price_max')
        if price_min:
            try:
                where_conditions.append("g.average_price >= ?")
                params.append(float(price_min))
            except (ValueError, TypeError):
                pass
        if price_max:
            try:
                where_conditions.append("g.average_price <= ?")
                params.append(float(price_max))
            except (ValueError, TypeError):
                pass
        
        if completion_status:
            where_conditions.append("ggm.completion_status = ?")
            params.append(completion_status)
        
        # Combine WHERE conditions
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Count total games matching filters
        count_query = f"SELECT COUNT(DISTINCT g.id) {base_query} {where_clause}"
        cursor.execute(count_query, params)
        total_games = cursor.fetchone()[0]
        
        # Calculate pagination
        total_pages = (total_games + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Build sort order
        sort_mapping = {
            'title_asc': 'g.title ASC',
            'title_desc': 'g.title DESC',
            'date_desc': 'g.release_date DESC',
            'date_asc': 'g.release_date ASC',
            'rating_desc': 'ggm.personal_rating DESC',
            'rating_asc': 'ggm.personal_rating ASC',
            'price_desc': 'g.average_price DESC',
            'price_asc': 'g.average_price ASC',
            'priority_desc': 'ggm.display_priority DESC'
        }
        
        order_by = sort_mapping.get(sort_order, 'g.title ASC')
        
        # Main query to fetch games with gallery metadata and high-res artwork
        main_query = f"""
        SELECT DISTINCT
            g.id,
            g.title,
            g.description,
            g.publisher,
            g.platforms,
            g.genres,
            g.series,
            g.release_date,
            g.average_price,
            g.youtube_trailer_url,
            g.region,
            ggm.completion_status,
            ggm.personal_rating,
            ggm.play_time_hours,
            ggm.notes,
            ggm.display_priority,
            ggm.favorite,
            ggm.date_acquired,
            ggm.date_completed,
            g.high_res_cover_url,
            g.high_res_cover_path,
            g.hero_image_url,
            g.hero_image_path,
            g.logo_image_url,
            g.logo_image_path,
            g.icon_image_url,
            g.icon_image_path,
            g.steamgriddb_id
        {base_query}
        {where_clause}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """
        
        cursor.execute(main_query, params + [per_page, offset])
        games_data = cursor.fetchall()
        
        # Process games (no longer fetching tags)
        games = []
        for game_row in games_data:
            game_id = game_row[0]
            
            # Parse release year
            release_year = None
            if game_row[7]:  # release_date (now column 7 instead of 8)
                try:
                    release_year = int(game_row[7][:4])
                except (ValueError, TypeError):
                    pass
            
            # Format platform (take first platform if multiple)
            platform = ""
            if game_row[4]:  # platforms (now column 4 instead of 5)
                try:
                    platforms = json.loads(game_row[4])
                    if isinstance(platforms, list) and platforms:
                        platform = platforms[0]
                    elif isinstance(platforms, str):
                        platform = platforms
                except (json.JSONDecodeError, TypeError):
                    platform = str(game_row[4])
            
            # Split genres into list (for individual genre filtering)
            genres_list = []
            if game_row[5]:  # genres column
                genres_list = [g.strip() for g in game_row[5].split(',') if g.strip()]
                
            # Split platforms into list 
            platforms_list = []
            if game_row[4]:  # platforms column
                try:
                    # Try to parse as JSON first
                    platforms_data = json.loads(game_row[4])
                    if isinstance(platforms_data, list):
                        platforms_list = platforms_data
                    else:
                        platforms_list = [str(platforms_data)]
                except (json.JSONDecodeError, TypeError):
                    # Fall back to comma-separated string
                    platforms_list = [p.strip() for p in str(game_row[4]).split(',') if p.strip()]
            
            game = {
                'id': game_id,
                'title': game_row[1],
                'description': game_row[2],
                'publisher': game_row[3],
                'platform': platform,  # Single platform for display (backward compatibility)
                'platforms': platforms_list,  # Convert platforms to list
                'genres': genres_list,  # Convert to list for frontend
                'series': game_row[6],
                'release_date': game_row[7],
                'release_year': release_year,
                'average_price': game_row[8],
                'youtube_trailer_url': game_row[9],
                'region': game_row[10] or 'PAL',  # New region field
                'completion_status': game_row[11],
                'personal_rating': game_row[12],
                'play_time_hours': game_row[13],
                'notes': game_row[14],
                'display_priority': game_row[15],
                'is_favorite': bool(game_row[16]),
                'date_acquired': game_row[17],
                'date_completed': game_row[18],
                # High-resolution artwork from SteamGridDB  
                'high_res_cover_url': game_row[19],
                'high_res_cover_path': game_row[20],
                'hero_image_url': game_row[21],
                'hero_image_path': game_row[22],
                'logo_image_url': game_row[23],
                'logo_image_path': game_row[24],
                'icon_image_url': game_row[25],
                'icon_image_path': game_row[26],
                'steamgriddb_id': game_row[27]
            }
            games.append(game)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'games': games,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_count': total_games,
                    'per_page': per_page,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'filters_applied': {
                    'search': search_filter,
                    'platform': platform_filter,
                    'genre': genre_filter,
                    'region': region_filter,
                    'year_min': year_min,
                    'year_max': year_max,
                    'completion_status': completion_status,
                    'sort': sort_order
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# -------------------------
# Database Backup Endpoints
# -------------------------

@app.route('/api/backup_db', methods=['POST'])
def backup_database_endpoint():
    """Create a timestamped backup of the SQLite database under data/backups/ and return its info"""
    try:
        # Ensure database exists
        if not os.path.exists(database_path):
            return jsonify({'success': False, 'error': 'Database file not found'}), 404

        # Build backup directory under the data directory next to DB
        backups_dir = os.path.join(DATA_DIR, 'backups')
        os.makedirs(backups_dir, exist_ok=True)

        # Create timestamped filename
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"games_backup_{ts}.db"
        backup_abs_path = os.path.join(backups_dir, backup_filename)

        # Copy DB
        shutil.copy2(database_path, backup_abs_path)

        # Compute relative path for media serving (only works if within project root)
        rel_path = os.path.relpath(backup_abs_path, PROJECT_ROOT)
        url_path = f"/media/{rel_path}" if not rel_path.startswith('..') else None

        return jsonify({
            'success': True,
            'backup_file': backup_filename,
            'backup_path': rel_path,
            'download_url': url_path
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/backups', methods=['GET'])
def list_backups_endpoint():
    """List available database backup files with optional download URLs"""
    try:
        backups_dir = os.path.join(DATA_DIR, 'backups')
        if not os.path.isdir(backups_dir):
            return jsonify({'success': True, 'backups': []})

        files = []
        for name in sorted(os.listdir(backups_dir)):
            path = os.path.join(backups_dir, name)
            if os.path.isfile(path):
                rel_path = os.path.relpath(path, PROJECT_ROOT)
                url_path = f"/media/{rel_path}" if not rel_path.startswith('..') else None
                files.append({'name': name, 'path': rel_path, 'download_url': url_path, 'size_bytes': os.path.getsize(path)})

        return jsonify({'success': True, 'backups': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/gallery/game/<int:game_id>', methods=['GET'])
def get_gallery_game_detail(game_id):
    """Get detailed information for a single game including gallery metadata"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get game with gallery metadata
        query = """
        SELECT 
            g.id, g.title, g.description, g.publisher,
            g.platforms, g.genres, g.series, g.release_date, g.average_price,
            ggm.completion_status, ggm.personal_rating, ggm.play_time_hours,
            ggm.notes, ggm.display_priority, ggm.favorite,
            ggm.date_acquired, ggm.date_completed
        FROM games g
        LEFT JOIN game_gallery_metadata ggm ON g.id = ggm.game_id
        WHERE g.id = ?
        """
        
        cursor.execute(query, (game_id,))
        game_row = cursor.fetchone()
        
        if not game_row:
            return jsonify({
                'success': False,
                'error': 'Game not found'
            }), 404
        
        # Get tags for this game
        tags_query = """
        SELECT gt.id, gt.tag_name, gt.tag_description 
        FROM game_tag_associations gta 
        JOIN game_tags gt ON gta.tag_id = gt.id 
        WHERE gta.game_id = ?
        ORDER BY gt.tag_name
        """
        cursor.execute(tags_query, (game_id,))
        tags = [{'id': row[0], 'name': row[1], 'description': row[2]} for row in cursor.fetchall()]
        
        # Parse release year
        release_year = None
        if game_row[8]:  # release_date
            try:
                release_year = int(game_row[8][:4])
            except (ValueError, TypeError):
                pass
        
        game = {
            'id': game_row[0],
            'title': game_row[1],
            'description': game_row[2],
            'publisher': game_row[3],
            'platforms': game_row[4],
            'genres': game_row[5],
            'series': game_row[6],
            'release_date': game_row[7],
            'release_year': release_year,
            'average_price': game_row[8],
            'gallery_metadata': {
                'completion_status': game_row[9],
                'personal_rating': game_row[10],
                'play_time_hours': game_row[11],
                'notes': game_row[12],
                'display_priority': game_row[13],
                'is_favorite': bool(game_row[14]),
                'date_acquired': game_row[15],
                'date_completed': game_row[16]
            },
            'tags': tags
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'game': game
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/gallery/filters', methods=['GET'])
def get_gallery_filters():
    """Get all available filter options for the gallery"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get unique platforms from both string and JSON data
        cursor.execute("""
            SELECT DISTINCT platforms 
            FROM games 
            WHERE platforms IS NOT NULL AND platforms != '' AND platforms != '__PLACEHOLDER__'
            ORDER BY platforms
        """)
        platform_rows = cursor.fetchall()
        platforms = []
        for row in platform_rows:
            platform_data = row[0]
            if platform_data.startswith('['):
                # Handle JSON array data
                try:
                    parsed_data = json.loads(platform_data)
                    if isinstance(parsed_data, list):
                        platforms.extend(parsed_data)
                    elif isinstance(parsed_data, str):
                        platforms.append(parsed_data)
                except (json.JSONDecodeError, TypeError):
                    # If JSON parsing fails, treat as string
                    platforms.append(platform_data)
            else:
                # Handle simple string data
                if ',' in platform_data:
                    # Split comma-separated platforms
                    split_platforms = [p.strip() for p in platform_data.split(',') if p.strip()]
                    platforms.extend(split_platforms)
                else:
                    platforms.append(platform_data.strip())
        
        # Remove duplicates and filter out empty entries
        unique_platforms = []
        for platform in platforms:
            platform = platform.strip()
            if platform and platform not in unique_platforms:
                unique_platforms.append(platform)
        
        platforms = sorted(unique_platforms)
        
        # Get unique genres (split from comma-separated strings)
        cursor.execute("""
            SELECT DISTINCT genres 
            FROM games 
            WHERE genres IS NOT NULL AND genres != ''
            ORDER BY genres
        """)
        genre_rows = cursor.fetchall()
        genres = []
        for row in genre_rows:
            genre_data = row[0]
            if genre_data:
                # Split comma-separated genres and flatten
                for genre in genre_data.split(','):
                    genre = genre.strip()
                    if genre and genre not in genres:
                        genres.append(genre)
        genres.sort()
        
        # Get unique regions
        cursor.execute("""
            SELECT DISTINCT IFNULL(region, 'PAL') as region
            FROM games 
        """)
        region_rows = cursor.fetchall()
        regions = sorted(list(set([row[0] for row in region_rows if row[0]])))
        
        # Ensure standard regions are available
        if 'PAL' not in regions:
            regions.append('PAL')
        if 'NTSC' not in regions:
            regions.append('NTSC')
        if 'JP' not in regions:
            regions.append('JP')
        regions.sort()
        
        # Get release years
        cursor.execute("""
            SELECT DISTINCT CAST(substr(release_date, 1, 4) AS INTEGER) as year
            FROM games 
            WHERE release_date IS NOT NULL 
            AND release_date != '' 
            AND length(release_date) >= 4
            AND substr(release_date, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
            ORDER BY year
        """)
        release_years = [row[0] for row in cursor.fetchall()]
        
        # Get completion statuses
        cursor.execute("""
            SELECT DISTINCT completion_status 
            FROM game_gallery_metadata 
            WHERE completion_status IS NOT NULL AND completion_status != ''
            ORDER BY completion_status
        """)
        completion_statuses = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'platforms': platforms,
                'genres': genres,  
                'regions': regions,
                'completion_statuses': completion_statuses,
                'sort_options': [
                    {'value': 'title_asc', 'label': 'Title (A-Z)'},
                    {'value': 'title_desc', 'label': 'Title (Z-A)'},
                    {'value': 'date_desc', 'label': 'Release Date (Newest)'},
                    {'value': 'date_asc', 'label': 'Release Date (Oldest)'},
                    {'value': 'rating_desc', 'label': 'Personal Rating (High)'},
                    {'value': 'rating_asc', 'label': 'Personal Rating (Low)'},
                    {'value': 'price_desc', 'label': 'Price (High)'},
                    {'value': 'price_asc', 'label': 'Price (Low)'},
                    {'value': 'priority_desc', 'label': 'Display Priority'}
                ]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# -------------------------
# Price History API Endpoints
# -------------------------

@app.route('/api/price_history/<int:game_id>', methods=['GET'])
def get_price_history(game_id):
    """Get price history for a specific game"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get price history for the game (include entry id)
        cursor.execute("""
            SELECT id, price, price_source, date_recorded, currency
            FROM price_history
            WHERE game_id = ?
            ORDER BY date_recorded ASC
        """, (game_id,))
        
        history_rows = cursor.fetchall()
        
        # Format the data for frontend consumption
        price_history = []
        for entry_id, price, source, date_recorded, currency in history_rows:
            price_history.append({
                'id': entry_id,
                'price': price,
                'price_source': source,
                'date_recorded': date_recorded,
                'currency': currency or 'GBP'
            })
        
        # Also get game details for context
        cursor.execute("SELECT title FROM games WHERE id = ?", (game_id,))
        game_result = cursor.fetchone()
        game_title = game_result[0] if game_result else f"Game {game_id}"
        
        conn.close()
        
        return jsonify({
            'success': True,
            'game_id': game_id,
            'game_title': game_title,
            'price_history': price_history,
            'total_entries': len(price_history)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/price_history/<int:entry_id>', methods=['DELETE'])
def delete_price_history_entry(entry_id: int):
    """Delete a specific price history entry by its ID"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Verify it exists and get game_id for optional context
        cursor.execute("SELECT game_id FROM price_history WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Entry not found'}), 404
        game_id = row[0]

        cursor.execute("DELETE FROM price_history WHERE id = ?", (entry_id,))
        
        # After deletion, recompute latest price for the game and update games.average_price
        cursor.execute(
            """
            SELECT price
            FROM price_history
            WHERE game_id = ?
            ORDER BY datetime(date_recorded) DESC, id DESC
            LIMIT 1
            """,
            (game_id,),
        )
        latest_row = cursor.fetchone()
        if latest_row is not None:
            latest_price = latest_row[0]
            cursor.execute("UPDATE games SET average_price = ? WHERE id = ?", (latest_price, game_id))
        else:
            # No history remains; clear the current price
            cursor.execute("UPDATE games SET average_price = NULL WHERE id = ?", (game_id,))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Entry deleted', 'entry_id': entry_id, 'game_id': game_id}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/price_history', methods=['POST'])
def add_price_history_entry():
    """Add a new price history entry for a game"""
    try:
        data = request.get_json()
        game_id = data.get('game_id')
        price = data.get('price')
        price_source = data.get('price_source', 'Manual')
        
        if not game_id or price is None:
            return jsonify({
                'success': False,
                'error': 'game_id and price are required'
            }), 400
        
        from datetime import datetime
        
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Add the price history entry
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO price_history (game_id, price, price_source, date_recorded, currency)
            VALUES (?, ?, ?, ?, ?)
        """, (game_id, price, price_source, current_date, 'GBP'))
        
        # Update the game's current average_price as well
        cursor.execute("""
            UPDATE games SET average_price = ? WHERE id = ?
        """, (price, game_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Price history entry added for game {game_id}',
            'price': price,
            'price_source': price_source,
            'date_recorded': current_date
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def fetch_artwork_for_game(game_id):
    """Helper function to fetch high-resolution artwork for a single game"""
    try:
        import subprocess
        import sys
        import os
        
        # Check if SteamGridDB API key is available
        api_key = None
        
        # Try to get API key from environment
        api_key = os.getenv('STEAMGRIDDB_API_KEY')
        
        # Try to get API key from config file
        if not api_key:
            try:
                # Use the same config loading logic as other functions
                config = load_config()
                api_key = config.get('steamgriddb_api_key')
            except Exception:
                pass
        
        # If no API key is available, skip artwork fetching silently
        if not api_key:
            logging.debug(f"No SteamGridDB API key available, skipping artwork fetch for game {game_id}")
            return False
        
        # Build command to fetch artwork for this specific game
        script_path = os.path.join(os.path.dirname(__file__), 'fetch_high_res_artwork.py')
        cmd = [
            sys.executable, script_path,
            '--game-id', str(game_id),
            '--api-key', api_key
        ]
        
        # Run the artwork fetcher in the background (don't block the main request)
        subprocess.Popen(cmd, cwd=os.path.dirname(__file__))
        logging.debug(f"Started background artwork fetch for game {game_id}")
        return True
        
    except Exception as e:
        logging.warning(f"Failed to start artwork fetch for game {game_id}: {e}")
        return False

@app.route('/api/high_res_artwork', methods=['POST'])
def fetch_high_res_artwork():
    """Trigger high resolution artwork fetching for games"""
    try:
        data = request.get_json()
        game_id = data.get('game_id')  # Optional: fetch for specific game
        bulk_mode = data.get('bulk', False)  # Fetch for all games without artwork
        api_key = data.get('api_key')  # Optional: SteamGridDB API key
        
        if not bulk_mode and not game_id:
            return jsonify({
                'success': False,
                'error': 'Either game_id or bulk=true must be specified'
            }), 400
        
        # Import and run the high-res artwork fetcher
        import subprocess
        import sys
        
        # Build command
        cmd = [sys.executable, 'fetch_high_res_artwork.py']
        
        if game_id:
            cmd.extend(['--game-id', str(game_id)])
        elif bulk_mode:
            cmd.append('--bulk')
        
        if api_key:
            cmd.extend(['--api-key', api_key])
        
        # Run the script
        try:
            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(__file__),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': 'High resolution artwork fetching completed',
                    'output': result.stdout,
                    'game_id': game_id if game_id else None,
                    'bulk_mode': bulk_mode
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Artwork fetching failed',
                    'output': result.stderr or result.stdout
                }), 500
                
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error': 'Artwork fetching timed out (5 minutes)'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/high_res_artwork/status', methods=['GET'])
def check_high_res_artwork_status():
    """Check high resolution artwork status for games"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Count games with and without high-res artwork
        cursor.execute("""
            SELECT 
                COUNT(*) as total_games,
                COUNT(high_res_cover_url) as games_with_covers,
                COUNT(hero_image_url) as games_with_heroes,
                COUNT(logo_image_url) as games_with_logos,
                COUNT(icon_image_url) as games_with_icons
            FROM games 
            WHERE id != -1
        """)
        
        stats = cursor.fetchone()
        
        # Get games without high-res covers (most important metric)
        cursor.execute(
            """
            SELECT id, title, platforms AS platform
            FROM games
            WHERE id != -1 AND (high_res_cover_url IS NULL OR high_res_cover_url = '')
            ORDER BY title
            LIMIT 10
            """
        )
        
        games_without_artwork = [
            {'id': row[0], 'title': row[1], 'platform': row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_games': stats[0],
                'games_with_covers': stats[1],
                'games_with_heroes': stats[2],
                'games_with_logos': stats[3],
                'games_with_icons': stats[4],
                'coverage_percentage': round((stats[1] / stats[0]) * 100, 1) if stats[0] > 0 else 0
            },
            'games_without_artwork': games_without_artwork,
            'needs_artwork': len(games_without_artwork) > 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route("/debug/config", methods=["GET"])
def debug_config():
    """Debug endpoint to show config file location and contents"""
    try:
        config_info = {
            "config_file": CONFIG_FILE,
            "config_file_absolute": os.path.abspath(CONFIG_FILE),
            "config_file_exists": os.path.exists(CONFIG_FILE),
            "config_dir": os.path.dirname(CONFIG_FILE),
            "config_dir_exists": os.path.exists(os.path.dirname(CONFIG_FILE)),
            "docker_environment": os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv'),
            "base_dir": BASE_DIR,
            "current_working_dir": os.getcwd()
        }
        
        # Try to read the actual config file
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config_contents = json.load(f)
                config_info["config_contents"] = config_contents
                config_info["config_file_size"] = os.path.getsize(CONFIG_FILE)
            except Exception as e:
                config_info["config_read_error"] = str(e)
        else:
            config_info["config_contents"] = "File does not exist"
        
        return jsonify(config_info), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/test/config_save", methods=["POST"])
def test_config_save():
    """Test endpoint to verify config saving functionality"""
    try:
        data = request.json
        test_key = data.get("test_key", "test_value")
        test_value = data.get("test_value", "test_value")
        
        logging.info(f"Testing config save with key: {test_key}, value: {test_value}")
        
        # Load current config
        config = load_config()
        original_value = config.get(test_key)
        
        # Set test value
        config[test_key] = test_value
        
        # Save config
        save_config(config)
        
        # Verify save by reading back
        with open(CONFIG_FILE, 'r') as f:
            saved_config = json.load(f)
        
        if saved_config.get(test_key) == test_value:
            # Restore original value
            config[test_key] = original_value
            save_config(config)
            
            result = {
                "success": True,
                "message": f"Config save test successful. Test value '{test_value}' was saved and retrieved correctly.",
                "config_file": CONFIG_FILE,
                "config_file_absolute": os.path.abspath(CONFIG_FILE),
                "test_key": test_key,
                "test_value": test_value,
                "saved_value": saved_config.get(test_key)
            }
            return jsonify(result), 200
        else:
            result = {
                "success": False,
                "message": "Config save test failed. Value was not saved correctly.",
                "expected": test_value,
                "actual": saved_config.get(test_key)
            }
            return jsonify(result), 500
            
    except Exception as e:
        logging.error(f"Config save test failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    # Initialize configuration on startup
    print("🔧 Initializing configuration...")
    print(f"📁 Config file location: {CONFIG_FILE}")
    print(f"📁 Config file absolute path: {os.path.abspath(CONFIG_FILE)}")
    print(f"🐳 Docker environment: {os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv')}")
    
    config = load_config()
    print(f"✅ Configuration loaded. Price source: {config.get('price_source', 'Unknown')}")
    if 'steamgriddb_api_key' in config:
        if config['steamgriddb_api_key'].startswith('your_steamgriddb_api_key'):
            print("⚠️  SteamGridDB API key is set to placeholder. Update config/config.json with your actual API key.")
        else:
            print("✅ SteamGridDB API key configured")
    
    print("🚀 Starting Flask application...")
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)

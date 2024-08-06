import json
import os
import random
import time
import undetected_chromedriver as uc
import requests
import logging
import re
import sqlite3
import chromedriver_autoinstaller

from flask import Flask, request, jsonify
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


app = Flask(__name__)

# Replace with your actual API keys
IGDB_CLIENT_ID = "nal5c75b0hwuvmsgs1cdowvi81tg5y"
IGDB_CLIENT_SECRET = "lgea285xk7qsm4lhh9tio54bw3pek7"

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# List of common console names and abbreviations to exclude
CONSOLE_NAMES = [
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


# Get IGDB access token
def get_igdb_access_token():
    url = f"https://id.twitch.tv/oauth2/token?client_id={IGDB_CLIENT_ID}&client_secret={IGDB_CLIENT_SECRET}&grant_type=client_credentials"
    response = requests.post(url)
    logging.debug(f"IGDB access token response: {response.json()}")
    return response.json().get("access_token")


# Scrape the barcode lookup website for the game title using undetected_chromedriver
def scrape_barcode_lookup(barcode):
    # Specify the exact path to the ChromeDriver binary
    driver_path = "/opt/homebrew/bin/chromedriver"  # Replace with the actual path

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
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.col-50.product-details")
            )
        )

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
    body = f'search "{game_name}"; fields name, cover.url, summary, platforms.name, genres.name, involved_companies.company.name, franchises.name, first_release_date, alternative_names.name;'
    response = requests.post(url, headers=headers, data=body)
    response_json = response.json()
    logging.debug(f"IGDB search response for {game_name}: {response_json}")

    for game in response_json:
        if "alternative_names" in game:
            logging.debug(
                f"Alternative names for {game['name']}: {[alt['name'] for alt in game['alternative_names']]}"
            )

    return response_json


# Remove the last word from the game title
def remove_last_word(game_title):
    words = game_title.split()
    if len(words) > 1:
        return " ".join(words[:-1])
    return game_title


# Generate a random ID for the game
def generate_random_id():
    return random.randint(1000, 9999)

class GameScan:
    response_data = None  # Class variable to store response data

    @staticmethod
    @app.route("/scan", methods=["POST"])
    def scan():
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(BASE_DIR, "games.db")
            logging.debug(f"Database path: {db_path}")

            data = request.json
            barcode = data.get("barcode")
            logging.debug(f"Received barcode: {barcode}")

            game_title, average_price = scrape_barcode_lookup(barcode)
            if not game_title:
                logging.error("Failed to scrape game title from barcode lookup")
                return jsonify({"error": "Failed to retrieve game title"}), 404

            logging.debug(f"Average price for the game: {average_price}")

            igdb_access_token = get_igdb_access_token()
            if not igdb_access_token:
                logging.error("Failed to retrieve IGDB access token")
                return jsonify({"error": "Failed to retrieve IGDB access token"}), 500

            exact_match, alternative_match = search_game_with_alternatives(
                game_title, igdb_access_token
            )

            if not exact_match and not alternative_match:
                return jsonify({"error": "No results found on IGDB"}), 404

            # Log the matches
            logging.debug(
                json.dumps(
                    {
                        "matches": {
                            "exact_match": (
                                exact_match["name"] if exact_match else "No exact match"
                            ),
                            "alternative_match": (
                                alternative_match["name"]
                                if alternative_match
                                else "No alternative match"
                            ),
                        }
                    },
                    indent=4,
                )
            )

            # Store both exact and alternative matches for later use
            GameScan.response_data = {
                "exact_match": exact_match,
                "alternative_match": alternative_match,
                "average_price": average_price,
            }

            # if exact_match and alternative_match are the same, only send exact_match
            if exact_match and alternative_match and exact_match["id"] == alternative_match["id"]:
                alternative_match = None
            

            # Return both exact and alternative matches for user selection
            response = {
                "exact_match": (
                    {
                        "index": 1,
                        "name": exact_match["name"] if exact_match else "No exact match",
                    }
                    if exact_match
                    else {}
                ),
                "alternative_match": (
                    {
                        "index": 2,
                        "name": (
                            alternative_match["name"]
                            if alternative_match
                            else "No alternative match"
                        ),
                    }
                    if alternative_match
                    else {}
                ),
            }
            return jsonify(response)

        except Exception as e:
            logging.error(f"Error in /scan route: {e}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @app.route("/confirm", methods=["POST"])
    def confirm():
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(BASE_DIR, "games.db")
            logging.debug(f"Database path: {db_path}")

            data = request.json
            selection = data.get("selection")  # Expected to be '1' for exact_match or '2' for alternative_match
            logging.debug(f"Received selection: {selection}")

            # Ensure we have stored response_data from the /scan route
            if not GameScan.response_data:
                return jsonify({"error": "No stored game data available"}), 400

            # Use the appropriate game info based on the user's selection
            selected_game = GameScan.response_data["exact_match"] if selection == "1" else GameScan.response_data["alternative_match"]
            average_price = GameScan.response_data["average_price"]
            if not selected_game:
                return jsonify({"error": "Selected game information not found"}), 404

            game_data = {
                "title": selected_game.get("name"),
                "cover_image": selected_game.get("cover", {}).get("url"),
                "description": selected_game.get("summary"),
                "publisher": [
                    company["company"]["name"]
                    for company in selected_game.get("involved_companies", [])
                ],
                "platforms": [
                    platform["name"] for platform in selected_game.get("platforms", [])
                ],
                "genres": [genre["name"] for genre in selected_game.get("genres", [])],
                "series": [
                    franchise["name"] for franchise in selected_game.get("franchises", [])
                ],
                "release_date": None,
                "average_price": average_price,  # Not needed to be sent back, handled internally if needed
            }

            if selected_game.get("first_release_date"):
                game_data["release_date"] = time.strftime(
                    "%Y-%m-%d", time.gmtime(selected_game["first_release_date"])
                )

            save_game_to_db(game_data)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, average_price FROM games WHERE title = ?",
                (game_data["title"],),
            )
            rows = cursor.fetchall()
            conn.close()

            games_with_prices = []
            for row in rows:
                games_with_prices.append(
                    {"id": row[0], "title": row[1], "average_price": row[2]}
                )

            logging.debug(f"Games with prices: {games_with_prices}")

            return jsonify(game_data)

        except Exception as e:
            logging.error(f"Error in /confirm route: {e}")
            return jsonify({"error": str(e)}), 500



def search_game_with_alternatives(game_name, auth_token):
    search_attempts = [game_name]
    exact_match = None
    alternative_match = None

    while search_attempts:
        current_title = search_attempts.pop(0)
        igdb_response = search_igdb_game(current_title, auth_token)
        if igdb_response:
            for game in igdb_response:
                if "name" in game and not exact_match:
                    exact_match = game
                    logging.debug(f"Exact match found: {game['name']}")
                    # return exact_match, alternative_match  # Return immediately after finding the first exact match

                if "alternative_names" in game and not alternative_match:
                    for alt in game["alternative_names"]:
                        alternative_match = game
                        logging.debug(
                            f"Using alternative name: {alt['name']} for game: {game['name']}"
                        )
                        if exact_match or alternative_match:
                            return exact_match, alternative_match

        cleaned_title = clean_game_title(current_title)
        if cleaned_title and cleaned_title != current_title:
            search_attempts.append(cleaned_title)

        next_attempt = remove_last_word(current_title)
        if next_attempt and next_attempt != current_title:
            search_attempts.append(next_attempt)

    logging.debug(f"Exact match: {exact_match}")
    logging.debug(f"Alternative match: {alternative_match}")

    return exact_match, alternative_match

@app.route("/search_game_by_name", methods=["POST"])
def search_game_by_name():
    try:
        data = request.json
        game_name = data.get("game_name")

        igdb_access_token = get_igdb_access_token()
        if not igdb_access_token:
            return jsonify({"error": "Failed to retrieve IGDB access token"}), 500

        exact_match, alternative_match = search_game_with_alternatives(game_name, igdb_access_token)

        if exact_match or alternative_match:
            return jsonify({
                "exact_match": exact_match,
                "alternative_match": alternative_match
            }), 200
        else:
            return jsonify({"error": "No results found"}), 404

    except Exception as e:
        logging.error(f"Error in /search_game_by_name route: {e}")
        return jsonify({"error": str(e)}), 500


def save_game_to_db(game_data):
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, "games.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logging.debug(f"Inserting game data: {game_data}")

        # Check if a game with the same title already exists
        cursor.execute(
            "SELECT COUNT(*) FROM games WHERE title = ?", (game_data["title"],)
        )
        count = cursor.fetchone()[0]

        if count == 0:
            cursor.execute(
                """
            INSERT INTO games (id, title, cover_image, description, publisher, platforms, genres, series, release_date, average_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    generate_random_id(),
                    game_data["title"],
                    game_data["cover_image"],
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
            logging.debug("Data committed to the database")
        else:
            logging.debug(
                f"Game with title '{game_data['title']}' already exists in the database"
            )
    except Exception as e:
        logging.error(f"Error saving game to database: {e}")
    finally:
        conn.close()


@app.route("/games", methods=["GET"])
def get_games():
    publisher = request.args.get("publisher")
    platform = request.args.get("platform")
    genre = request.args.get("genre")
    year = request.args.get("year")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "games.db")

    conn = sqlite3.connect(db_path)
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

    logging.debug(f"Fetched games: {game_list}")
    return jsonify(game_list)


@app.route("/consoles", methods=["GET"])
def get_consoles():
    conn = sqlite3.connect("games.db")
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
    db_path = os.path.join(BASE_DIR, "games.db")
    conn = sqlite3.connect(db_path)
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
        return jsonify([]), 400

    values = cursor.fetchall()
    conn.close()

    unique_values = set()
    for value_tuple in values:
        if value_type == "year":
            unique_values.add(value_tuple[0])
        else:
            value_list = value_tuple[0].split(", ")
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
        db_path = os.path.join(BASE_DIR, "games.db")
        conn = sqlite3.connect(db_path)
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
    db_path = os.path.join(BASE_DIR, "games.db")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Update game data
        cursor.execute("""
            UPDATE games
            SET title = ?, cover_image = ?, description = ?, publisher = ?, platforms = ?, genres = ?, series = ?, release_date = ?
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
    db_path = os.path.join(BASE_DIR, "games.db")

    try:
        conn = sqlite3.connect(db_path)
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



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

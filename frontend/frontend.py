import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import os, sys
import logging
import html

# Configure Streamlit page - MUST be the very first Streamlit command!
st.set_page_config(
    page_title="Video Game Catalogue",
    page_icon="🎮"
)

# Global button style: prevent text wrapping on buttons
st.markdown(
    """
    <style>
    .stButton > button, .stForm .stButton > button {
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Calculate the project root as the parent directory of the frontend folder.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print("Project root added to sys.path:", PROJECT_ROOT)


from modules.scrapers import scrape_ebay_prices, scrape_amazon_price, scrape_barcode_lookup, scrape_cex_price, scrape_pricecharting_price, get_best_pricecharting_price, get_pricecharting_price_by_condition

# Retrieve the backend host from environment variables
backend_host = os.getenv("BACKEND_HOST", "localhost")
backend_port = int(os.getenv("BACKEND_PORT", "5001"))

# Backend API base URL (used for server-side requests from the frontend container)
BACKEND_URL = f"http://{backend_host}:{backend_port}"
print(f"Connecting to backend (server-side) at {BACKEND_URL}")  # Debugging output

# Browser-facing base URL for assets (what the user's browser can reach)
# If running in Docker, the backend host inside the network is 'backend', but the browser cannot resolve that.
# Use localhost for the browser in that case. Allow override via BACKEND_BROWSER_BASE_URL.
BACKEND_BROWSER_BASE_URL = os.getenv(
    "BACKEND_BROWSER_BASE_URL",
    f"http://localhost:{backend_port}" if backend_host == "backend" else BACKEND_URL,
)
print(f"Browser will load assets from {BACKEND_BROWSER_BASE_URL}")

# iCloud shortcut link (replace with actual link as needed)
ICLOUD_LINK = "https://www.icloud.com/shortcuts/024bf54a6f584cc78c3ed394bcda8e84"
ICLOUD_LINK_ALT = "https://www.icloud.com/shortcuts/bea9f60437194f0fad2f89b87c9d1fff"

# -------------------------
# Backend API Helper Functions
# -------------------------

def fetch_games(filters=None, page=1, per_page=None):
    """Fetch games with optional pagination support"""
    try:
        params = filters.copy() if filters else {}
        
        # Add pagination if per_page is specified
        if per_page:
            params["page"] = page
            params["per_page"] = per_page
        
        response = requests.get(f"{BACKEND_URL}/games", params=params)
        if response.status_code == 200:
            result = response.json()
            
            # If pagination was requested, return with pagination info
            if per_page and isinstance(result, dict) and "games" in result:
                return result
            # Otherwise return just the games list (backward compatibility)
            elif isinstance(result, list):
                return result
            else:
                return result.get("games", [])
        else:
            try:
                # Attempt to parse error JSON if provided
                return response.json()
            except Exception:
                # Log raw body for debugging and fail gracefully
                print(f"Error fetching games: HTTP {response.status_code} body=\n{response.text}")
                return []
    except Exception as e:
        print(f"Error fetching games: {e}")
        return []

def fetch_consoles():
    response = requests.get(f"{BACKEND_URL}/consoles")
    return response.json()

def fetch_unique_values(value_type):
    try:
        response = requests.get(f"{BACKEND_URL}/unique_values", params={"type": value_type})
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error fetching unique values for {value_type}: {e}")
        return []  # Return empty list on error

def calculate_total_cost(games):
    total = 0
    # Handle case where games might be an error string instead of a list
    if not isinstance(games, list):
        return total
    
    for game in games:
        # Skip if game is not a dictionary (shouldn't happen with proper data)
        if not isinstance(game, dict):
            continue
            
        price = game.get("average_price")
        if price is not None:
            try:
                # Convert to float in case it's a string
                total += float(price)
            except (ValueError, TypeError):
                # Skip invalid price values
                continue
    return total

def normalize_region(region):
    """Normalize region values to standard codes: PAL, NTSC, JP"""
    if not region:
        return "PAL"
    
    region_upper = region.upper().strip()
    
    # Map various region formats to standard codes
    if region_upper in {"JAPAN", "JP", "JPN"}:
        return "JP"
    elif region_upper in {"NTSC", "US", "USA", "UNITED STATES", "NORTH AMERICA", "NA"}:
        return "NTSC"
    elif region_upper in {"PAL", "EU", "EUROPE", "EUROPEAN"}:
        return "PAL"
    else:
        # Default to PAL for unknown regions
        return "PAL"


def backend_to_frontend_region(backend_region):
    """Convert backend region format to frontend display format."""
    if not backend_region:
        return "PAL"
    
    region = backend_region.upper().strip()
    if region in ["PAL", "NTSC"]:
        return region
    elif region in ["JAPAN", "JP", "JPN"]:
        return "JP"
    else:
        return "PAL"



def add_game(game_data):
    # Normalize the region before sending to backend
    if "region" in game_data:
        game_data["region"] = normalize_region(game_data["region"])
    
    response = requests.post(f"{BACKEND_URL}/add_game", json=game_data)
    return response.status_code == 201

def delete_game(game_id):
    response = requests.post(f"{BACKEND_URL}/delete_game", json={"id": int(game_id)})
    return response.status_code == 200

def update_game(game_id, game_data):
    # Normalize the region before sending to backend
    if "region" in game_data:
        game_data["region"] = normalize_region(game_data["region"])
    
    response = requests.put(f"{BACKEND_URL}/update_game/{game_id}", json=game_data)
    return response.status_code == 200

def update_game_price(game_id):
    """Update the price of a game using the current price source configuration"""
    # Include current region and condition preferences for PriceCharting
    payload = {}
    if st.session_state.get("pricecharting_region"):
        frontend_region = st.session_state.get("pricecharting_region")
        # Convert JP to Japan for backend compatibility
        backend_region = "Japan" if frontend_region == "JP" else frontend_region
        payload["region"] = backend_region
    if "pricecharting_boxed" in st.session_state:
        payload["prefer_boxed"] = st.session_state.get("pricecharting_boxed", True)
    
    response = requests.post(f"{BACKEND_URL}/update_game_price/{game_id}", json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def update_game_artwork(game_id):
    """Update the artwork of a game using SteamGridDB API"""
    response = requests.post(f"{BACKEND_URL}/update_game_artwork/{game_id}")
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400:
        # API key not configured
        return {"error": "api_key_missing", "details": response.json()}
    elif response.status_code == 422:
        # No artwork found
        return {"error": "no_artwork_found", "details": response.json()}
    else:
        return None

def get_price_source():
    """Get the current price source from backend configuration"""
    try:
        response = requests.get(f"{BACKEND_URL}/price_source")
        if response.status_code == 200:
            return response.json().get("price_source", "eBay")
        else:
            return "eBay"  # fallback
    except:
        return "eBay"  # fallback

def search_game_by_name(game_name):
    try:
        response = requests.post(f"{BACKEND_URL}/search_game_by_name", json={"game_name": game_name})
        if response.status_code == 200:
            return response.json()
        else:
            # Try to get error details from response
            try:
                error_data = response.json()
                return {"error": error_data.get("error", "Unknown error"), "details": error_data.get("details"), "instructions": error_data.get("instructions")}
            except:
                return {"error": f"Search failed with status {response.status_code}", "details": "Unable to search for games", "instructions": "Please check your configuration"}
    except Exception as e:
        return {"error": "Connection error", "details": f"Failed to connect to backend: {str(e)}", "instructions": "Please ensure the backend service is running"}

def search_game_by_id(igdb_id):
    try:
        response = requests.post(f"{BACKEND_URL}/search_game_by_id", json={"igdb_id": igdb_id})
        if response.status_code == 200:
            return response.json()
        else:
            # Try to get error details from response
            try:
                error_data = response.json()
                return {"error": error_data.get("error", "Unknown error"), "details": error_data.get("details"), "instructions": error_data.get("instructions")}
            except:
                return {"error": f"Search failed with status {response.status_code}", "details": "Unable to search for games", "instructions": "Please check your configuration"}
    except Exception as e:
        return {"error": "Connection error", "details": f"Failed to connect to backend: {str(e)}", "instructions": "Please ensure the backend service is running"}

def fetch_top_games():
    try:
        response = requests.get(f"{BACKEND_URL}/top_games")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching top games: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching top games: {e}")
        return []

def fetch_game_by_id(game_id):
    response = requests.get(f"{BACKEND_URL}/game/{game_id}")
    if response.status_code == 200:
        return response.json()
    else:
        return None

# -------------------------
# Artwork Helper Functions
# -------------------------

def normalize_asset_url(url: str) -> str:
    """Normalize asset URLs:
    - Convert protocol-relative URLs to https
    - Prefix backend host for media served by backend ("/media/..." or relative paths under data/artwork)
    - Return as-is for full http(s) URLs
    """
    if not url:
        return ""
    if isinstance(url, str) and url.startswith("//"):
        return f"https:{url}"
    if isinstance(url, str) and url.startswith("/media/"):
        return f"{BACKEND_BROWSER_BASE_URL}{url}"
    if isinstance(url, str) and (url.startswith("data/artwork/") or url.startswith("./data/artwork/")):
        # Ensure backend serves this path
        cleaned = url.lstrip("./")
        return f"{BACKEND_BROWSER_BASE_URL}/media/{cleaned}"
    return url


def get_best_cover_image(game):
    """Return the best visual to display as a cover, with sensible fallbacks.

    Priority:
    1) High-res grid cover (SteamGridDB)
    2) Hero image (SteamGridDB) – as a fallback if no grid cover exists
    3) Logo image (SteamGridDB)
    4) Icon image (SteamGridDB)
    5) Regular cover from IGDB/DB (cover_image or cover_url)
    6) Placeholder
    """

    # SteamGridDB fields
    for key in [
        "high_res_cover_url",
        "hero_image_url",
        "logo_image_url",
        "icon_image_url",
    ]:
        value = normalize_asset_url(game.get(key))
        if value:
            return value

    # Legacy/IGDB fields
    for key in ["cover_image", "cover_url"]:
        value = normalize_asset_url(game.get(key))
        if value:
            return value

    return "https://via.placeholder.com/400x600?text=No+Image"

def get_hero_image(game):
    """Get the hero banner image if available"""
    return normalize_asset_url(game.get("hero_image_url"))

def get_logo_image(game):
    """Get the game logo if available"""
    return game.get("logo_image_url")


def get_platform_display(game) -> str:
    """Return a human-readable platform string from either `platforms` or `platform` fields.
    - If `platforms` is a list, join with ", ".
    - If `platforms` is a string, return as-is.
    - Else fall back to `platform` string if present.
    - Otherwise return "Unknown".
    """
    value = game.get("platforms") or game.get("platform")
    if isinstance(value, list):
        return ", ".join([str(v) for v in value if str(v).strip()]) or "Unknown"
    if isinstance(value, str) and value.strip():
        return value
    return "Unknown"

def get_icon_image(game):
    """Get the game icon if available"""
    return game.get("icon_image_url")

def scan_game(barcode):
    response = requests.post(f"{BACKEND_URL}/scan", json={"barcode": barcode})
    return response.json()

# -------------------------
# Gallery API Helper Functions
# -------------------------

def fetch_gallery_games(filters=None, page=1, per_page=20):
    """Fetch games for gallery display with pagination and filtering"""
    params = {"page": page, "limit": per_page}  # API uses "limit" not "per_page"
    if filters:
        params.update(filters)
    response = requests.get(f"{BACKEND_URL}/api/gallery/games", params=params)
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            data = result.get("data", {})
            # Transform to match expected frontend structure
            return {
                "games": data.get("games", []),
                "pagination": data.get("pagination", {}),
                "total_games": data.get("pagination", {}).get("total_count", 0),
                "total_pages": data.get("pagination", {}).get("total_pages", 0)
            }
        else:
            return {"games": [], "pagination": {}, "total_games": 0, "total_pages": 0}
    else:
        return {"games": [], "pagination": {}, "total_games": 0, "total_pages": 0}

def fetch_gallery_filters():
    """Fetch available filter options for gallery"""
    response = requests.get(f"{BACKEND_URL}/api/gallery/filters")
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            return result.get("data", {})
        else:
            return {"platforms": [], "genres": [], "regions": [], "completion_statuses": [], "sort_options": []}
    else:
        return {"platforms": [], "genres": [], "regions": [], "completion_statuses": [], "sort_options": []}

def store_gallery_state():
    """Store the current gallery state before navigating to game detail"""
    gallery_state = {}
    
    # Store only specific gallery state keys, avoiding widget-specific ones
    safe_keys = [
        "gallery_per_page", "gallery_platform_filter", 
        "gallery_genre_filter", "gallery_search_filter", "gallery_year_range",
        "gallery_region_filter", "gallery_completion_filter", "gallery_sort_order",
        "gallery_price_range"
    ]
    
    for key in safe_keys:
        if key in st.session_state:
            gallery_state[key] = st.session_state[key]
    
    # Store the current page type
    gallery_state["previous_page"] = "gallery"
    
    # Store the state
    st.session_state["stored_gallery_state"] = gallery_state

def restore_gallery_state():
    """Restore the previously stored gallery state when returning from game detail"""
    stored_state = st.session_state.get("stored_gallery_state", {})
    
    if stored_state:
        # Restore only safe gallery session state
        safe_keys = [
            "gallery_per_page", "gallery_platform_filter", 
            "gallery_genre_filter", "gallery_search_filter", "gallery_year_range",
            "gallery_region_filter", "gallery_completion_filter", "gallery_sort_order",
            "gallery_price_range"
        ]
        
        for key, value in stored_state.items():
            if key in safe_keys and key != "previous_page":  # Don't restore meta keys
                try:
                    st.session_state[key] = value
                except Exception as e:
                    # Log any issues with specific keys but continue
                    pass
        
        # Clear the stored state
        if "stored_gallery_state" in st.session_state:
            del st.session_state["stored_gallery_state"]

def fetch_price_history(game_id):
    """Fetch price history for a specific game"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/price_history/{game_id}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "price_history": [], "error": "Failed to fetch price history"}
    except Exception as e:
        return {"success": False, "price_history": [], "error": str(e)}

def delete_price_history_entry(entry_id: int):
    """Delete a price history entry by ID"""
    try:
        resp = requests.delete(f"{BACKEND_URL}/api/price_history/{entry_id}")
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None

def add_price_history_entry(game_id: int, price: float, source: str = "Manual"):
    """Add a price history entry via backend API and return response JSON or None"""
    try:
        payload = {"game_id": game_id, "price": price, "price_source": source}
        response = requests.post(f"{BACKEND_URL}/api/price_history", json=payload)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

# -------------------------
# Flash Notification Helpers
# -------------------------
def set_flash(message: str, level: str = "success"):
    """
    Store a transient notification in session so it survives st.rerun().
    level: 'success' | 'info' | 'warning' | 'error'
    """
    try:
        st.session_state["__flash__"] = {
            "message": str(message),
            "level": str(level),
            "ts": time.time(),
        }
    except Exception:
        # Fall back silently if session is unavailable
        pass

def show_flash():
    """
    Display and clear any pending flash notification.
    Call near the top of each page render.
    """
    data = st.session_state.pop("__flash__", None)
    if not data:
        return
    lvl = (data.get("level") or "info").lower()
    msg = data.get("message") or ""
    if lvl == "success":
        st.success(msg)
    elif lvl == "warning":
        st.warning(msg)
    elif lvl == "error":
        st.error(msg)
    else:
        st.info(msg)

# -------------------------
# CSS Styling for Layout
# -------------------------
st.markdown(
    """
    <style>
    .game-container {
        display: flex;
        align-items: flex-start;
        padding: 10px;
        border: 1px solid #ddd;
        margin-bottom: 10px;
        background-color: #f9f9f9;
        border-radius: 5px;
    }
    .game-image {
        width: 150px;
        margin-right: 20px;
        border-radius: 10px;
    }
    .game-details {
        flex: 1;
    }
    .search-bar {
        margin-bottom: 20px;
    }
    .music-player {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        color: white;
    }
    .music-player iframe {
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .music-player-title {
        text-align: center;
        margin-bottom: 10px;
        font-weight: bold;
        color: white;
    }
    .music-player-subtitle {
        text-align: center;
        font-size: 0.9em;
        opacity: 0.9;
        margin-bottom: 15px;
    }
    
    .gallery-tile {
        border: 1px solid #ddd;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 20px;
        background: linear-gradient(145deg, #f8f9fa, #ffffff);
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        text-align: center;
        height: 420px;
        overflow: hidden;
        cursor: pointer;
        position: relative;
        transform-style: preserve-3d;
        perspective: 1000px;
    }
    .gallery-tile::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: linear-gradient(45deg, #667eea, #764ba2, #f093fb, #f5576c);
        border-radius: 15px;
        opacity: 0;
        transition: opacity 0.3s ease;
        z-index: -1;
    }
    .gallery-tile:hover::before {
        opacity: 1;
    }
    .gallery-tile:hover {
        transform: translateY(-8px) rotateX(5deg) rotateY(5deg) scale(1.02);
        box-shadow: 0 20px 60px rgba(0,0,0,0.25), 0 8px 20px rgba(102, 126, 234, 0.3);
        border-color: transparent;
    }
    .gallery-tile img {
        width: 100%;
        height: 220px;
        object-fit: cover;
        border-radius: 12px;
        margin-bottom: 12px;
        transition: all 0.4s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .gallery-tile:hover img {
        transform: scale(1.08) translateZ(20px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }
    .gallery-tile-content {
        transform-style: preserve-3d;
        transition: transform 0.4s ease;
    }
    .gallery-tile:hover .gallery-tile-content {
        transform: translateZ(10px);
    }
    .gallery-tag {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 9px;
        margin: 1px;
        color: white;
        font-weight: bold;
    }
    .gallery-grid {
        display: grid;
        gap: 15px;
        margin: 20px 0;
    }
    .gallery-controls {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 4px solid #4CAF50;
    }
    .filter-chip {
        display: inline-block;
        background: #e3f2fd;
        color: #1976d2;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin: 2px;
        border: 1px solid #bbdefb;
    }
    
    /* Enhanced clickable tile styles */
    .clickable-game-tile {
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        cursor: pointer;
        position: relative;
        transform-style: preserve-3d;
        perspective: 1000px;
    }
    .clickable-game-tile::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: linear-gradient(45deg, #667eea, #764ba2, #f093fb, #f5576c);
        border-radius: 15px;
        opacity: 0;
        transition: opacity 0.3s ease;
        z-index: -1;
    }
    .clickable-game-tile:hover::before {
        opacity: 1;
    }
    .clickable-game-tile:hover {
        border-color: transparent;
    }
    .clickable-game-tile img {
        transition: all 0.4s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .clickable-game-tile:hover img {
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# New Function: Display Game with Edit and Delete Options
# -------------------------
def display_game_item(game):
    with st.container():
        col_details, col_buttons = st.columns([3, 1])
        with col_details:
            # Use best available cover image (prioritize high-res grid artwork)
            cover_image_url = get_best_cover_image(game)
            
            # Format the average price display
            price_value = game.get("average_price")
            if price_value is not None:
                try:
                    average_price = f"£{float(price_value):.2f}"
                except (ValueError, TypeError):
                    average_price = "N/A"
            else:
                average_price = "N/A"
            # Display game details using HTML formatting with proper escaping
            st.markdown(
                f"""
                <div class="game-container">
                    <img src="{html.escape(cover_image_url)}" class="game-image">
                    <div class="game-details">
                        <div><strong>ID:</strong> {html.escape(str(game.get('id', 'N/A')))}</div>
                        <div><strong>Title:</strong> {html.escape(str(game.get('title', 'N/A')))}</div>
                        <div><strong>Description:</strong> {html.escape(str(game.get('description', 'N/A')))}</div>
                        <div><strong>Publisher:</strong> {html.escape(str(game.get('publisher', 'N/A')))}</div>
                        <div><strong>Platforms:</strong> {html.escape(str(game.get('platforms', 'N/A')))}</div>
                        <div><strong>Genres:</strong> {html.escape(str(game.get('genres', 'N/A')))}</div>
                        <div><strong>Series:</strong> {html.escape(str(game.get('series', 'N/A')))}</div>
                        <div><strong>Release Date:</strong> {html.escape(str(game.get('release_date', 'N/A')))}</div>
                        <div><strong>Region:</strong> {html.escape(str(backend_to_frontend_region(game.get('region') or 'PAL')))}</div>
                        <div><strong>Average Price:</strong> {html.escape(str(average_price))}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_buttons:
            # When the Delete button is clicked, set a confirmation flag.
            if st.button("Delete", key=f"delete_{game.get('id')}"):
                st.session_state[f"confirm_delete_{game.get('id')}"] = True

            # If the confirmation flag is set, display confirmation buttons.
            if st.session_state.get(f"confirm_delete_{game.get('id')}", False):
                st.write("Are you sure you want to delete this game?")
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Yes", key=f"yes_delete_{game.get('id')}"):
                        if delete_game(game.get("id")):
                            st.success(f"Deleted game: {game.get('title')}")
                        else:
                            st.error("Delete failed!")
                        st.session_state[f"confirm_delete_{game.get('id')}"] = False
                with cancel_col:
                    if st.button("Cancel", key=f"cancel_delete_{game.get('id')}"):
                        st.session_state[f"confirm_delete_{game.get('id')}"] = False

            # Edit button as before.
            if st.button("Edit", key=f"edit_{game.get('id')}"):
                st.session_state.editing_game_id = game.get("id")

            # Update Price button with confirmation
            if st.button("Update Price", key=f"update_price_{game.get('id')}"):
                st.session_state[f"confirm_update_price_{game.get('id')}"] = True

            # If the confirmation flag is set, display confirmation buttons.
            if st.session_state.get(f"confirm_update_price_{game.get('id')}", False):
                current_price_source = get_price_source()
                st.write(f"Update price using **{current_price_source}**?")
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Yes", key=f"yes_update_price_{game.get('id')}"):
                        with st.spinner(f"Updating price using {current_price_source}..."):
                            result = update_game_price(game.get("id"))
                            if result:
                                st.success(f"✅ Price updated!")
                                old_price = f"£{result['old_price']:.2f}" if result['old_price'] else "Not set"
                                new_price = f"£{result['new_price']:.2f}" if result['new_price'] else "Not found"
                                st.info(f"**{result['game_title']}**: {old_price} → {new_price}")
                            else:
                                st.error("Failed to update price!")
                        st.session_state[f"confirm_update_price_{game.get('id')}"] = False
                        st.rerun()  # Refresh to show updated price
                with cancel_col:
                    if st.button("Cancel", key=f"cancel_update_price_{game.get('id')}"):
                        st.session_state[f"confirm_update_price_{game.get('id')}"] = False

    # Inline edit form (only shown if this game is marked for editing)
    if st.session_state.get("editing_game_id") == game.get("id"):
        st.markdown("#### Edit Game")
        new_title = st.text_input("Title", game.get("title"), key=f"edit_title_{game.get('id')}")
        new_desc = st.text_area("Description", game.get("description"), key=f"edit_desc_{game.get('id')}")
        new_pub = st.text_input("Publisher", game.get("publisher"), key=f"edit_pub_{game.get('id')}")
        
        # Handle platforms: convert string to list if needed
        platforms_data = game.get("platforms", [])
        if isinstance(platforms_data, str):
            platforms_data = [platforms_data]
        raw_platforms = ", ".join(platforms_data)
        raw_platforms_input = st.text_input("Platforms (comma separated)", raw_platforms, key=f"edit_platforms_{game.get('id')}")
        new_platforms_list = [p.strip() for p in raw_platforms_input.split(",") if p.strip()]
        
        # Handle genres: convert string to list if needed
        genres_data = game.get("genres", [])
        if isinstance(genres_data, str):
            genres_data = [genres_data]
        raw_genres = ", ".join(genres_data)
        raw_genres_input = st.text_input("Genres (comma separated)", raw_genres, key=f"edit_genres_{game.get('id')}")
        new_genres_list = [g.strip() for g in raw_genres_input.split(",") if g.strip()]
        
        new_series = st.text_input("Series", game.get("series"), key=f"edit_series_{game.get('id')}")
        new_release = st.text_input("Release Date", game.get("release_date"), key=f"edit_release_{game.get('id')}")
        # Region selector
        region_options = ["PAL", "NTSC", "JP"]
        current_region = backend_to_frontend_region(game.get("region") or "PAL")
        if current_region not in region_options:
            current_region = "PAL"
        region_index = region_options.index(current_region)
        new_region = st.selectbox("Region", region_options, index=region_index, key=f"edit_region_{game.get('id')}")
        new_price = st.number_input("Average Price", value=game.get("average_price") or 0.0, step=0.01, format="%.2f", key=f"edit_price_{game.get('id')}")
        new_youtube_url = st.text_input("YouTube Trailer URL", game.get("youtube_trailer_url", ""), key=f"edit_youtube_{game.get('id')}", help="Full YouTube URL (e.g., https://www.youtube.com/watch?v=...)")
        
        if st.button("Save", key=f"save_{game.get('id')}"):
            # Convert frontend region format to backend format for storage
            backend_region = "Japan" if new_region == "JP" else new_region
            
            updated_game_data = {
                "title": new_title,
                "description": new_desc,
                "publisher": [new_pub],
                "platforms": new_platforms_list,
                "genres": new_genres_list,
                "series": [new_series],
                "release_date": new_release,
                "average_price": new_price,
                "youtube_trailer_url": new_youtube_url,
                "region": backend_region,
            }
            if update_game(game.get("id"), updated_game_data):
                st.success("Game updated successfully!")
                st.session_state.editing_game_id = None  # Exit edit mode
            else:
                st.error("Failed to update game")

# -------------------------
# Game Detail Page Function  
# -------------------------
def game_detail_page():
    """Individual game detail page with external links and comprehensive information"""
    game = st.session_state.get("selected_game_detail")
    if not game:
        st.error("No game selected. Returning to library...")
        restore_gallery_state()
        st.session_state["page"] = "gallery"
        st.rerun()
        return
    
    # Add Back button at the top
    col_back, col_spacer = st.columns([1, 4])
    with col_back:
        if st.button("← Back to Library", type="secondary", use_container_width=True):
            restore_gallery_state()
            st.session_state["page"] = "gallery"
            st.rerun()
    # Always refresh the selected game's data from the backend so price/rating reflects latest
    try:
        game_id = game.get("id")
        if game_id:
            fresh = fetch_game_by_id(game_id)
            if isinstance(fresh, dict) and fresh:
                st.session_state["selected_game_detail"] = fresh
                game = fresh
    except Exception:
        # Non-fatal; keep existing session copy if refresh fails
        pass
    
    # Surface any pending notifications
    show_flash()
    # Precompute current game id for sidebar controls
    current_game_id = str(game.get("id", ""))
    
    # If any detail filter changed, navigate back to library with filters
    if st.session_state.get("__detail_apply_filters_now__", False):
        try:
            filters = {}
            ts = st.session_state.get("detail_gallery_title_search")
            if ts:
                filters["search"] = ts
            sp = st.session_state.get("detail_gallery_platform_filter")
            if sp and sp != "All":
                filters["platform"] = sp
            sg = st.session_state.get("detail_gallery_genre_filter")
            if sg and sg != "All":
                filters["genre"] = sg
            sr = st.session_state.get("detail_gallery_region_filter")
            if sr and sr != "All":
                filters["region"] = sr
            yr = st.session_state.get("detail_gallery_year_range")
            if isinstance(yr, tuple) and len(yr) == 2:
                filters["year_min"] = yr[0]
                filters["year_max"] = yr[1]
            pr = st.session_state.get("detail_gallery_price_range")
            if isinstance(pr, tuple) and len(pr) == 2:
                try:
                    filters["price_min"] = float(pr[0])
                    filters["price_max"] = float(pr[1])
                except Exception:
                    pass
            per_page = st.session_state.get("detail_gallery_per_page_select") or 20
            grid_cols = st.session_state.get("detail_gallery_grid_cols") or 4
            st.session_state["gallery_filters"] = filters
            st.session_state["gallery_per_page"] = per_page
            st.session_state["gallery_page"] = 1
            st.session_state["gallery_grid_cols"] = grid_cols
            if ts: st.session_state["gallery_title_search"] = ts
            if sp and sp != "All": st.session_state["gallery_platform_filter"] = sp
            if sg and sg != "All": st.session_state["gallery_genre_filter"] = sg
            if sr and sr != "All": st.session_state["gallery_region_filter"] = sr
            if isinstance(yr, tuple) and len(yr) == 2:
                st.session_state["gallery_year_range"] = yr
        finally:
            st.session_state["__detail_apply_filters_now__"] = False
        st.session_state["page"] = "gallery"
        st.rerun()
    
    # Callback to trigger library navigation on any detail filter change
    def _detail_trigger_nav():
        st.session_state["__detail_apply_filters_now__"] = True
    
    # -------------------------
    # Game Detail Sidebar: Same as Library for Consistency
    # -------------------------
    # Music Player Section
    music_expander = st.sidebar.expander("Video Game Music Player")
    with music_expander:
        st.markdown("### VIPVGM - Video Game Music")
        st.markdown("*Load the embedded player on demand to prevent autoplay.*")
        if not st.session_state.get("vipvgm_detail_embedded"):
            if st.button("Load Embedded Player", key="vipvgm_detail_load"):
                st.session_state["vipvgm_detail_embedded"] = True

        if st.session_state.get("vipvgm_detail_embedded"):
            iframe_html = """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; padding: 15px; margin: 10px 0;">
                <iframe 
                    src="https://www.vipvgm.net/" 
                    width="100%" 
                    height="400" 
                    frameborder="0" 
                    scrolling="yes"
                    allow="encrypted-media; fullscreen"
                    title="VIPVGM Video Game Music Player"
                    style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"
                ></iframe>
            </div>
            """
            components.html(iframe_html, height=450)

    
    
    # Load filter options for the gallery filters
    filter_options = fetch_gallery_filters()
    
    # Create filter interface in sidebar (same as library)
    st.sidebar.markdown("### Library Filters")
    
    # Search by title
    title_search = st.sidebar.text_input("Search titles", key="detail_gallery_title_search", on_change=_detail_trigger_nav)
    
    # Platform filter
    available_platforms = filter_options.get("platforms", [])
    selected_platform = st.sidebar.selectbox(
        "Platform",
        ["All"] + available_platforms,
        key="detail_gallery_platform_filter",
        on_change=_detail_trigger_nav
    )
    
    # Genre filter
    available_genres = filter_options.get("genres", [])
    selected_genre = st.sidebar.selectbox(
        "Genre",
        ["All"] + available_genres,
        key="detail_gallery_genre_filter",
        on_change=_detail_trigger_nav
    )
    
    # Region filter
    available_regions = filter_options.get("regions", ["PAL", "NTSC", "JP"])
    selected_region = st.sidebar.selectbox(
        "Region",
        ["All"] + available_regions,
        key="detail_gallery_region_filter",
        on_change=_detail_trigger_nav
    )
    
    # Release year range
    available_years = filter_options.get("release_years", [])
    if available_years:
        min_year, max_year = min(available_years), max(available_years)
        year_range = st.sidebar.slider(
            "Release Year Range",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
            key="detail_gallery_year_range",
            on_change=_detail_trigger_nav
        )
    else:
        year_range = None
    
    # Price range filter
    st.sidebar.markdown("### Price Filters")
    
    # Get price range from all games for slider bounds
    try:
        # Fetch price range from backend or calculate from current games
        all_games_for_price = fetch_gallery_games(filters={}, per_page=10000)  # Get all games for price range
        games_with_prices = [g for g in all_games_for_price.get("games", []) if g.get("average_price") is not None and g.get("average_price") > 0]
        
        if games_with_prices:
            prices = [float(g["average_price"]) for g in games_with_prices]
            min_price, max_price = min(prices), max(prices)
            
            if min_price < max_price:
                detail_price_range = st.sidebar.slider(
                    "Price Range (£)",
                    min_value=float(min_price),
                    max_value=float(max_price),
                    value=(float(min_price), float(max_price)),
                    step=0.50,
                    format="£%.2f",
                    key="detail_gallery_price_range",
                    on_change=_detail_trigger_nav
                )
            else:
                st.sidebar.info(f"Only price available: £{min_price:.2f}")
                detail_price_range = (min_price, max_price)
        else:
            detail_price_range = None
    except Exception as e:
        detail_price_range = None
    
    # Gallery view options
    st.sidebar.markdown("### Display Options")
    per_page = st.sidebar.selectbox(
        "Games per page",
        [12, 20, 40, 60],
        index=1,  # Default to 20
        key="detail_gallery_per_page_select",
        on_change=_detail_trigger_nav
    )
    
    # Grid columns selector
    default_detail_grid_cols = st.session_state.get("detail_gallery_grid_cols", 4)  # Get existing value or default to 4
    grid_cols = st.sidebar.selectbox(
        "Grid columns",
        [3, 4, 5, 6],
        index=[3, 4, 5, 6].index(default_detail_grid_cols) if default_detail_grid_cols in [3, 4, 5, 6] else 1,
        key="detail_gallery_grid_cols",
        on_change=_detail_trigger_nav
    )
    
    # Apply filters button - when clicked, go to library with these filters
    if st.sidebar.button("Apply Filters & Go to Library", key="detail_apply_filters", type="primary"):
        # Build filters dictionary
        filters = {}
        if title_search:
            filters["search"] = title_search  # Changed to match API
        if selected_platform != "All":
            filters["platform"] = selected_platform
        if selected_genre != "All":
            filters["genre"] = selected_genre
        if selected_region != "All":
            filters["region"] = selected_region
        if year_range and year_range != (min_year, max_year):
            filters["year_min"] = year_range[0]
            filters["year_max"] = year_range[1]
        if detail_price_range:
            # Add price filtering - always apply if detail_price_range is set
            try:
                filters["price_min"] = detail_price_range[0]
                filters["price_max"] = detail_price_range[1]
            except Exception:
                pass
        
        # Apply the filters to the library session state
        st.session_state["gallery_filters"] = filters
        st.session_state["gallery_per_page"] = per_page
        st.session_state["gallery_page"] = 1  # Reset to first page
        st.session_state["gallery_per_page"] = per_page
        st.session_state["gallery_grid_cols"] = grid_cols
        
        # Set the corresponding library filter keys so they show up when we switch
        if title_search:
            st.session_state["gallery_title_search"] = title_search
        if selected_platform != "All":
            st.session_state["gallery_platform_filter"] = selected_platform
        if selected_genre != "All":
            st.session_state["gallery_genre_filter"] = selected_genre
        if selected_region != "All":
            st.session_state["gallery_region_filter"] = selected_region
        if year_range and year_range != (min_year, max_year):
            st.session_state["gallery_year_range"] = year_range
        
        # Navigate to library (don't restore state here as we're intentionally setting new filters)
        st.session_state["page"] = "gallery"
        st.rerun()
    
    # Clear filters button
    if st.sidebar.button("Clear All Filters", key="detail_gallery_clear_filters"):
        # Clear all filter session state keys for detail page (including year range)
        for key in list(st.session_state.keys()):
            if key.startswith("detail_gallery_"):
                del st.session_state[key]
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # -------------------------
    # Update Sections (moved to bottom like Library)
    # -------------------------
    update_price_expander = st.sidebar.expander("Update Game Price")
    with update_price_expander:
        st.markdown("**Update price using current price source configuration**")
        
        current_price_source = get_price_source()
        st.info(f"Current price source: **{current_price_source}**")
        
        update_price_game_id = st.text_input("Game ID to Update Price", value=current_game_id, key="detail_update_price_game_id")
        confirm_update_price = st.checkbox("I confirm that I want to update this game's price", key="detail_update_price_confirm")
        
        if st.button("Update Price", key="detail_update_price_button") and confirm_update_price:
            if update_price_game_id:
                with st.spinner(f"Updating price using {current_price_source}..."):
                    result = update_game_price(update_price_game_id)
                    if result:
                        old_price = f"£{result['old_price']:.2f}" if result.get('old_price') else "Not set"
                        new_price = f"£{result['new_price']:.2f}" if result.get('new_price') else "Not found"
                        set_flash(f"Price updated: {result.get('game_title','Game')} {old_price} → {new_price} via {result.get('price_source','')}", "success")
                        try:
                            fresh = fetch_game_by_id(update_price_game_id)
                            if isinstance(fresh, dict) and fresh:
                                st.session_state["selected_game_detail"] = fresh
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error("Failed to update game price. Please check the Game ID and try again.")
            else:
                st.warning("Please enter a Game ID.")
    
    update_artwork_expander = st.sidebar.expander("Update Game Artwork")
    with update_artwork_expander:
        st.markdown("**Update artwork using SteamGridDB API**")
        st.info("Fetches high-resolution grid covers, heroes, logos, and icons")
        
        update_artwork_game_id = st.text_input("Game ID to Update Artwork", value=current_game_id, key="detail_update_artwork_game_id")
        mode = st.selectbox(
            "Artwork update mode",
            options=["Automatic (SteamGridDB)", "Manual upload"],
            index=0,
            key="detail_artwork_update_mode",
        )
    
        if mode == "Automatic (SteamGridDB)":
            confirm_update_artwork = st.checkbox(
                "I confirm that I want to update this game's artwork",
                key="detail_update_artwork_confirm",
            )
            if st.button("Update Artwork", key="detail_update_artwork_button") and confirm_update_artwork:
                if update_artwork_game_id:
                    with st.spinner("Fetching artwork from SteamGridDB..."):
                        result = update_game_artwork(update_artwork_game_id)
                        if result and "error" not in result:
                            set_flash(f"Artwork updated for Game ID {result.get('game_id', update_artwork_game_id)} • {result.get('game_title','')}", "success")
                            try:
                                fresh = fetch_game_by_id(update_artwork_game_id)
                                if isinstance(fresh, dict) and fresh:
                                    st.session_state["selected_game_detail"] = fresh
                            except Exception:
                                pass
                            st.rerun()
                        elif result and result.get("error") == "api_key_missing":
                            st.error("❌ SteamGridDB API key not configured")
                            st.info("To use this feature:")
                            st.write("1. Get an API key from https://www.steamgriddb.com/profile/preferences/api")
                            st.write("2. Add `steamgriddb_api_key` to your `config.json` file")
                            st.write("3. Restart the backend service")
                        elif result and result.get("error") == "no_artwork_found":
                            st.warning("⚠️ No artwork found for this game")
                            st.write(f"**Game:** {result['details']['game_title']}")
                            st.info("SteamGridDB may not have artwork for this specific game. Try manually adding artwork or check if the game name matches exactly.")
                        else:
                            st.error("Failed to update game artwork. Please check the Game ID and try again.")
        else:
            st.markdown("**Manually upload artwork** (grid/hero/logo/icon)")
            artwork_type = st.selectbox(
                "Artwork type",
                options=["grid", "hero", "logo", "icon"],
                index=0,
                key="detail_manual_art_type",
                help="Select which artwork slot to fill",
            )
            upload_file = st.file_uploader(
                "Choose an image file (png/jpg/jpeg/webp)",
                type=["png", "jpg", "jpeg", "webp"],
                key="detail_manual_art_file",
            )
            if st.button("Upload Artwork", key="detail_manual_art_upload"):
                if not update_artwork_game_id:
                    st.error("Please enter a Game ID")
                elif not upload_file:
                    st.error("Please choose an image file to upload")
                else:
                    with st.spinner("Uploading artwork..."):
                        files = {"file": (upload_file.name, upload_file.getvalue(), upload_file.type or "application/octet-stream")}
                        data = {"artwork_type": artwork_type}
                        resp = requests.post(
                            f"{BACKEND_URL}/upload_game_artwork/{update_artwork_game_id}",
                            files=files,
                            data=data,
                            timeout=30,
                        )
                        if resp.status_code == 200:
                            rj = resp.json()
                            set_flash(f"Artwork uploaded successfully • Game ID {rj.get('game_id')} • Type {rj.get('artwork_type')}", "success")
                            try:
                                fresh = fetch_game_by_id(update_artwork_game_id)
                                if isinstance(fresh, dict) and fresh:
                                    st.session_state["selected_game_detail"] = fresh
                            except Exception:
                                pass
                            st.rerun()
                        else:
                            try:
                                st.error(resp.json())
                            except Exception:
                                st.error(f"Upload failed: HTTP {resp.status_code}")
    # -------------------------
    # HERO BANNER AT TOP
    # -------------------------
    hero_image_url = get_hero_image(game)
    if hero_image_url:
        st.markdown(
            f"""
            <div style="
                background: url('{hero_image_url}');
                background-size: cover;
                background-position: center;
                height: 300px;
                border-radius: 10px;
                display: flex;
                align-items: end;
                padding: 0;
                margin-bottom: 20px;
                position: relative;
                overflow: hidden;
            ">
                <div style="
                    background: linear-gradient(90deg, 
                        rgba(255,255,255,0.95) 0%, 
                        rgba(255,255,255,0.9) 30%, 
                        rgba(255,255,255,0.7) 50%, 
                        rgba(255,255,255,0.3) 70%, 
                        rgba(255,255,255,0) 100%);
                    backdrop-filter: blur(2px);
                    padding: 15px 30px 15px 20px;
                    border-radius: 0 0 0 10px;
                    position: relative;
                    min-width: 40%;
                    max-width: 60%;
                ">
                    <h1 style="
                        margin: 0; 
                        font-size: 2rem; 
                        font-weight: bold; 
                        color: #1a1a1a;
                        text-shadow: none;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    ">{html.escape(str(game.get("title", "Unknown Game")))}</h1>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Fallback: Use logo as title or plain text
        logo_image_url = get_logo_image(game)
        if logo_image_url:
            col_logo, col_platform = st.columns([3, 1])
            with col_logo:
                st.image(logo_image_url, width=400)
            with col_platform:
                st.markdown(f"### {game.get('platforms', 'Unknown Platform')}")
        else:
            st.title(game.get("title", "Unknown Game"))

    # Main layout: Image + Details
    col_image, col_details = st.columns([1, 2])

    with col_image:
        # Game cover image - use best available cover
        cover_url = get_best_cover_image(game)
        st.image(cover_url, caption=game.get("title", "Unknown Game"), use_column_width=True)
        
        # Price and rating section
        st.markdown("### Price & Rating")
        price = game.get("average_price")
        if price:
            st.metric("Current Price", f"£{price:.2f}")
        else:
            st.info("No price data available")
        
        # Personal rating
        personal_rating = game.get("personal_rating")
        if personal_rating:
            stars = "★" * personal_rating + "☆" * (10 - personal_rating)
            st.markdown(f"**Personal Rating:** {stars} ({personal_rating}/10)")
        
        # Play time
        play_time = game.get("play_time_hours")
        if play_time:
            st.markdown(f"**Play Time:** {play_time} hours")
    
    with col_details:
        # Game information
        st.markdown("### Game Information")
        
        # Basic details in organized format
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown(f"**Game ID:** {game.get('id', 'Unknown')}")
            st.markdown(f"**Platform:** {get_platform_display(game)}")
            st.markdown(f"**Region:** {backend_to_frontend_region(game.get('region') or 'PAL')}")
            
            # Release date and year
            release_date = game.get("release_date")
            release_year = game.get("release_year")
            if release_date:
                st.markdown(f"**Release Date:** {release_date}")
            elif release_year:
                st.markdown(f"**Release Year:** {release_year}")
            
            # Publisher
            publisher = game.get("publisher", "")
            if publisher:
                if isinstance(publisher, str):
                    st.markdown(f"**Publisher:** {publisher}")
                elif isinstance(publisher, list):
                    st.markdown(f"**Publisher:** {', '.join(publisher)}")
        
        with col_right:
            # Series
            series = game.get("series", "")
            if series and series != "":
                if isinstance(series, str):
                    st.markdown(f"**Series:** {series}")
                elif isinstance(series, list) and series:
                    st.markdown(f"**Series:** {', '.join(series)}")
            
            # Genres
            genres = game.get("genres", "")
            if genres:
                if isinstance(genres, str):
                    st.markdown(f"**Genres:** {genres}")
                elif isinstance(genres, list):
                    st.markdown(f"**Genres:** {', '.join(genres)}")
            
            # Favorite status
            is_favorite = game.get("is_favorite", False)
            if is_favorite:
                st.markdown("**Favorite Game**")
        
        # Description
        description = game.get("description", "")
        if description and description.strip():
            st.markdown("### Description")
            st.markdown(description)
        
        # Tags
        tags = game.get("tags", [])
        if tags:
            st.markdown("### Tags")
            tag_colors = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7", "#dda0dd", "#f093fb", "#74b9ff"]
            
            tag_html = ""
            for i, tag in enumerate(tags):
                color = tag_colors[i % len(tag_colors)]
                tag_html += f'<span style="background: {color}; color: white; padding: 4px 8px; border-radius: 15px; font-size: 12px; margin: 3px; display: inline-block;">{html.escape(str(tag))}</span> '
            
            st.markdown(tag_html, unsafe_allow_html=True)
        
        # Personal notes
        notes = game.get("notes", "")
        if notes and notes.strip():
            st.markdown("### Personal Notes")
            st.markdown(notes)

    # Price History & Manual Entry
    st.markdown("---")
    st.markdown("### Price History")
    gid = game.get("id")
    history_data = fetch_price_history(gid)
    if history_data.get("success") and history_data.get("price_history"):
        try:
            import pandas as pd
            df = pd.DataFrame(history_data["price_history"])  # type: ignore
            df["date_recorded"] = pd.to_datetime(df["date_recorded"])  # type: ignore
            df = df.sort_values("date_recorded")
            st.line_chart(df.set_index("date_recorded")["price"])  # type: ignore
        except Exception:
            for entry in history_data["price_history"]:
                st.write(f"{entry.get('date_recorded')}: £{entry.get('price')} ({entry.get('price_source')})")
        # Deletion controls and page update action inside one box
        with st.expander("Manage Price History Entries", expanded=False):
            # Update prices for all games on current page using current price source
            if st.button("Update Prices (This Page)", key="update_prices_page"):
                updated = 0
                current_page_games = st.session_state.get("current_gallery_games", [])
                for g in current_page_games:
                    gid2 = g.get("id")
                    if gid2:
                        try:
                            _ = update_game_price(gid2)
                            updated += 1
                        except Exception:
                            pass
                st.success(f"Triggered price updates for {updated} games on this page")

            st.markdown("---")
            for entry in history_data["price_history"]:
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.caption(entry.get("date_recorded"))
                with c2:
                    st.caption(f"£{entry.get('price')} ({entry.get('price_source')})")
                with c3:
                    if st.button("Delete", key=f"del_price_{entry.get('id')}"):
                        res = delete_price_history_entry(int(entry.get("id")))
                        if res and res.get("success"):
                            st.success("Deleted entry")
                            # Refresh game details so the 'Price & Rating' section reflects fallback value
                            try:
                                fresh = fetch_game_by_id(gid)
                                if isinstance(fresh, dict) and fresh:
                                    st.session_state["selected_game_detail"] = fresh
                            except Exception:
                                pass
                            st.rerun()
                        else:
                            st.error("Failed to delete")
    else:
        st.info("No price history entries yet.")

    with st.form(key="add_price_history_form"):
        col_a, col_b = st.columns([1, 1])
        with col_a:
            price_val = st.number_input("Price (£)", min_value=0.0, step=0.5, format="%.2f")
        with col_b:
            source_val = st.text_input("Source", value="Manual")

        # Actions row mirrors the two input columns so edges align with Price/Source
        actions_left, actions_right = st.columns([1, 1])
        with actions_left:
            submitted_add = st.form_submit_button("Add Entry")
        with actions_right:
            # Create an inner spacer to push the button to the far right edge of the Source column
            # Nudge slightly left to align with Source field edge
            _sp, right_btn_col = st.columns([0.85, 0.5])
            with right_btn_col:
                submitted_update = st.form_submit_button("Update Prices")

        if submitted_add:
            if price_val and price_val > 0:
                result = add_price_history_entry(gid, float(price_val), source_val or "Manual")
                if result and result.get("success"):
                    st.success("Price history entry added.")
                    st.rerun()
                else:
                    st.error("Failed to add price history entry.")
            else:
                st.warning("Enter a valid price.")
        elif submitted_update:
            # Update price for the current game only
            try:
                res = update_game_price(gid)
                if res and isinstance(res, dict):
                    if res.get("new_price") is not None:
                        st.success("Price updated")
                        # Reload game details to refresh 'Price & Rating'
                        try:
                            fresh = fetch_game_by_id(gid)
                            if isinstance(fresh, dict) and fresh:
                                st.session_state["selected_game_detail"] = fresh
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.info("No new price found. Kept existing price.")
                else:
                    st.info("No response from backend for price update")
            except Exception:
                st.error("Failed to update price for this game")

    # Moved the page update button into the Manage Price History Entries expander above
    
    # YouTube Trailer Section
    st.markdown("---")
    st.markdown("### Game Trailer")
    
    # Create search query for use throughout this section
    game_title = game.get("title", "")
    platform = game.get("platform", "")
    search_query = f"{game_title} {platform}".strip()
    
    # Check if we have a YouTube trailer URL
    youtube_url = game.get("youtube_trailer_url")
    
    if youtube_url:
        # Extract video ID from YouTube URL
        import re
        video_id_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', youtube_url)
        
        if video_id_match:
            video_id = video_id_match.group(1)
            
            # Embed the YouTube video
            st.markdown(f"""
            <div style="text-align: center; margin: 20px 0;">
                <iframe 
                    width="100%" 
                    height="400" 
                    src="https://www.youtube.com/embed/{video_id}" 
                    frameborder="0" 
                    allowfullscreen
                    style="border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                </iframe>
            </div>
            """, unsafe_allow_html=True)
        else:
            # If URL format is unexpected, show link
            st.markdown(f"[Watch Trailer on YouTube]({youtube_url})")
    else:
        # Fallback: show search button
        trailer_query = f"{search_query} trailer".replace(" ", "+")
        trailer_url = f"https://www.youtube.com/results?search_query={trailer_query}"
        
        st.info("No trailer found for this game yet.")
        st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <a href="{trailer_url}" target="_blank" style="
                display: inline-block;
                background: linear-gradient(135deg, #ff0000, #cc0000);
                color: white;
                padding: 15px 30px;
                border-radius: 25px;
                text-decoration: none;
                font-weight: bold;
                font-size: 16px;
                box-shadow: 0 4px 15px rgba(255,0,0,0.3);
                transition: all 0.3s ease;
            " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                Search for '{html.escape(str(game_title))}' Trailer on YouTube
            </a>
        </div>
        """, unsafe_allow_html=True)

    # External links section
    st.markdown("---")
    st.markdown("<h3 style='text-align: center;'>External Links & Resources</h3>", unsafe_allow_html=True)
    
    # Create search queries for external sites
    url_safe_query = search_query.replace(" trailer", "").replace(" ", "+")
    
    # External links in organized columns
    st.markdown("#### Guides & Info")
    
    # Create 3 equal columns for the guide buttons
    col_gamefaqs, col_powerpyx, col_metacritic = st.columns(3)
    
    with col_gamefaqs:
        # GameFAQs
        gamefaqs_url = f"https://gamefaqs.gamespot.com/search?game={url_safe_query}"
        st.link_button("GameFAQs", gamefaqs_url, use_container_width=True)
    
    with col_powerpyx:
        # PowerPyx (for trophies/achievements)
        powerpyx_url = f"https://www.powerpyx.com/?s={url_safe_query}"
        st.link_button("PowerPyx Guides", powerpyx_url, use_container_width=True)
    
    with col_metacritic:
        # Metacritic
        metacritic_url = f"https://www.metacritic.com/search/{url_safe_query}/"
        st.link_button("Metacritic", metacritic_url, use_container_width=True)

    # Price comparison section
        # Removed Digital Stores section as requested
        
    
    # with col_social: # Removed section
        # Removed Community & Social section as requested
        
    
    # Price comparison section
    st.markdown("---")
    st.markdown("### Price Comparison")
    
    price_col1, price_col2, price_col3 = st.columns(3)
    
    with price_col1:
        # eBay
        ebay_url = f"https://www.ebay.co.uk/sch/i.html?_nkw={url_safe_query}"
        st.link_button("eBay UK", ebay_url, use_container_width=True)
        
        # Amazon
        amazon_url = f"https://www.amazon.co.uk/s?k={url_safe_query}"
        st.link_button("Amazon UK", amazon_url, use_container_width=True)
    
    with price_col2:
        # CeX
        cex_url = f"https://uk.webuy.com/search?stext={url_safe_query}"
        st.link_button("CeX UK", cex_url, use_container_width=True)
        
        # PriceCharting
        pricecharting_url = f"https://www.pricecharting.com/search-products?type=prices&q={url_safe_query}"
        st.link_button("PriceCharting", pricecharting_url, use_container_width=True)
    
    with price_col3:
        # GAME
        game_uk_url = f"https://www.game.co.uk/webapp/wcs/stores/servlet/SearchDisplay?searchTerm={url_safe_query}"
        st.link_button("GAME UK", game_uk_url, use_container_width=True)
        
        # Argos
        argos_url = f"https://www.argos.co.uk/search/{url_safe_query}/"
        st.link_button("Argos", argos_url, use_container_width=True)

# -------------------------
# Gallery Page Function
# -------------------------
def gallery_page():
    """Library page with visual game display, filtering, and 3D-ready layout"""
    st.title("Game Library")
    st.markdown("*Visual game collection browser with advanced filtering*")
    # Show any persisted notifications from prior actions
    show_flash()

    # Artwork coverage widget (optional)
    try:
        resp = requests.get(f"{BACKEND_URL}/api/high_res_artwork/status")
        if resp.status_code == 200:
            stats = resp.json()
            if stats.get("success"):
                s = stats.get("stats", {})
                cov = s.get("coverage_percentage", 0)
                with st.container():
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        st.metric("Artwork Coverage", f"{cov}%")
                    with c2:
                        missing = stats.get("games_without_artwork", [])
                        if missing:
                            st.caption("Games missing high‑res covers (top 10):")
                            for g in missing:
                                st.write(f"• {g.get('title')} (ID {g.get('id')})")
                        else:
                            st.caption("All games have high‑res covers.")
    except Exception:
        pass

    # Initialize gallery session state
    if "gallery_page" not in st.session_state:
        st.session_state["gallery_page"] = 1
    if "gallery_per_page" not in st.session_state:
        st.session_state["gallery_per_page"] = 20
    if "gallery_filters" not in st.session_state:
        st.session_state["gallery_filters"] = {}
    
    # Load filter options
    filter_options = fetch_gallery_filters()
    
    # -------------------------
    # Library Sidebar: Music Player Section (moved to top)
    # -------------------------
    music_expander = st.sidebar.expander("Video Game Music Player")
    with music_expander:
        st.markdown("### VIPVGM - Video Game Music")
        st.markdown("*Load the embedded player on demand to prevent autoplay.*")
        if not st.session_state.get("vipvgm_gallery_embedded"):
            if st.button("Load Embedded Player", key="vipvgm_gallery_load"):
                st.session_state["vipvgm_gallery_embedded"] = True

        if st.session_state.get("vipvgm_gallery_embedded"):
            iframe_html = """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; padding: 15px; margin: 10px 0;">
                <iframe 
                    src="https://www.vipvgm.net/" 
                    width="100%" 
                    height="400" 
                    frameborder="0" 
                    scrolling="yes"
                    allow="encrypted-media; fullscreen"
                    title="VIPVGM Video Game Music Player"
                    style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"
                ></iframe>
            </div>
            """
            components.html(iframe_html, height=450)
    
    # Load filter options for the gallery filters
    filter_options = fetch_gallery_filters()
    
    # Create filter interface in sidebar (same as library)
    st.sidebar.markdown("### Library Filters")
    
    # Search by title
    title_search = st.sidebar.text_input("Search titles", key="gallery_title_search", on_change=lambda: st.session_state.update({"gallery_page": 1}))
    
    # Platform filter
    available_platforms = filter_options.get("platforms", [])
    selected_platform = st.sidebar.selectbox(
        "Platform", 
        ["All"] + available_platforms,
        key="gallery_platform_filter"
    )
    
    # Genre filter (individual genres like tags)
    available_genres = filter_options.get("genres", [])
    selected_genre = st.sidebar.selectbox(
        "Genre", 
        ["All"] + available_genres,
        key="gallery_genre_filter"
    )
    
    # Region filter
    available_regions = filter_options.get("regions", ["PAL", "NTSC", "JP"])
    selected_region = st.sidebar.selectbox(
        "Region", 
        ["All"] + available_regions,
        key="gallery_region_filter"
    )
    
    # Release year range
    available_years = filter_options.get("release_years", [])
    if available_years:
        min_year, max_year = min(available_years), max(available_years)
        if min_year < max_year:
            year_range = st.sidebar.slider(
                "Release Year Range",
                min_value=min_year,
                max_value=max_year,
                value=(min_year, max_year),
                key="gallery_year_range"
            )
        else:
            st.sidebar.info(f"Only year available: {min_year}")
            year_range = (min_year, max_year)
    else:
        year_range = None
    
    # Price range filter
    st.sidebar.markdown("### Price Filters")
    
    # Get price range from all games for slider bounds
    try:
        # Fetch price range from backend or calculate from current games
        all_games_for_price = fetch_gallery_games(filters={}, per_page=10000)  # Get all games for price range
        games_with_prices = [g for g in all_games_for_price.get("games", []) if g.get("average_price") is not None and g.get("average_price") > 0]
        
        if games_with_prices:
            prices = [float(g["average_price"]) for g in games_with_prices]
            min_price, max_price = min(prices), max(prices)
            
            if min_price < max_price:
                price_range = st.sidebar.slider(
                    "Price Range (£)",
                    min_value=float(min_price),
                    max_value=float(max_price),
                    value=(float(min_price), float(max_price)),
                    step=0.50,
                    format="£%.2f",
                    key="gallery_price_range"
                )
            else:
                st.sidebar.info(f"Only price available: £{min_price:.2f}")
                price_range = (min_price, max_price)
        else:
            price_range = None
    except Exception as e:
        price_range = None
    
    # Library view options
    st.sidebar.markdown("### Display Options")
    per_page = st.sidebar.selectbox(
        "Games per page",
        [12, 20, 40, 60],
        index=1,  # Default to 20
        key="gallery_per_page_select"
    )
    
    # Grid columns selector
    default_grid_cols = st.session_state.get("gallery_grid_cols", 4)  # Get existing value or default to 4
    grid_cols = st.sidebar.selectbox(
        "Grid columns",
        [3, 4, 5, 6],
        index=[3, 4, 5, 6].index(default_grid_cols) if default_grid_cols in [3, 4, 5, 6] else 1,
        key="gallery_grid_cols"
    )
    
    # Clear filters button
    if st.sidebar.button("Clear All Filters", key="gallery_clear_filters"):
        # Reset page to 1
        st.session_state["gallery_page"] = 1
        
        # Clear all filter session state keys (including year range)
        for key in list(st.session_state.keys()):
            if key.startswith("gallery_") and key not in ["gallery_page", "gallery_per_page"]:
                del st.session_state[key]
        st.rerun()
    
    # Build filters dictionary
    filters = {}
    if title_search:
        filters["search"] = title_search  # Changed from "title" to "search" to match backend API
    if selected_platform != "All":
        filters["platform"] = selected_platform
    if selected_genre != "All":
        filters["genre"] = selected_genre
    if selected_region != "All":
        filters["region"] = selected_region
    if year_range and year_range != (min_year, max_year):
        filters["year_min"] = year_range[0]
        filters["year_max"] = year_range[1]
    if price_range:
        # Add price filtering - always apply if price_range is set
        try:
            filters["price_min"] = price_range[0]
            filters["price_max"] = price_range[1]
        except Exception:
            pass
    
    # Update session state
    st.session_state["gallery_filters"] = filters
    st.session_state["gallery_per_page"] = per_page
    
    # -------------------------
    # Library Sidebar: Update Game Price Section (moved below filters)
    # -------------------------
    st.sidebar.markdown("---")  # Add separator
    update_price_expander = st.sidebar.expander("Update Game Price")
    with update_price_expander:
        st.markdown("**Update price using current price source configuration**")
        
        # Get current price source for display
        current_price_source = get_price_source()
        st.info(f"Current price source: **{current_price_source}**")
        
        # Individual game price update
        st.markdown("**Single Game Price Update**")
        update_price_game_id = st.text_input("Game ID to Update Price", key="gallery_update_price_game_id")
        confirm_update_price = st.checkbox("I confirm that I want to update this game's price", key="gallery_update_price_confirm")
        
        if st.button("Update Price", key="gallery_update_price_button") and confirm_update_price:
            if update_price_game_id:
                with st.spinner(f"Updating price using {current_price_source}..."):
                    result = update_game_price(update_price_game_id)
                    if result:
                        old_price = f"£{result['old_price']:.2f}" if result.get('old_price') else "Not set"
                        new_price = f"£{result['new_price']:.2f}" if result.get('new_price') else "Not found"
                        set_flash(f"Price updated: {result.get('game_title','Game')} {old_price} → {new_price} via {result.get('price_source','')}", "success")
                        st.rerun()
                    else:
                        st.error("Failed to update game price. Please check the Game ID and try again.")
            else:
                st.warning("Please enter a Game ID.")
        
        # ---- Bulk: Update Games Without Prices ----
        st.markdown("---")
        st.markdown("**Bulk: Update Games Without Prices**")
        
        # Show games that would be processed (games without prices)
        try:
            resp = requests.get(f"{BACKEND_URL}/api/games")
            if resp.status_code == 200:
                all_games = resp.json()
                games_without_prices = [game for game in all_games if not game.get('price') or game.get('price') == 0]
                if games_without_prices:
                    st.info(f"📋 **{len(games_without_prices)} games** need price updates")
                    
                    # Show expandable list of games to be processed
                    with st.expander(f"View games without prices ({len(games_without_prices)})", expanded=False):
                        for i, game in enumerate(games_without_prices[:20]):  # Show first 20
                            current_price = f"£{game.get('price', 0):.2f}" if game.get('price') else "No price"
                            st.write(f"• **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')}) - {current_price}")
                        if len(games_without_prices) > 20:
                            st.caption(f"... and {len(games_without_prices) - 20} more games")
                else:
                    st.success("✅ All games already have prices!")
                    st.info("No games need price updates at this time.")
        except Exception:
            st.warning("Could not check price status")
        
        confirm_bulk_price = st.checkbox(
            "I confirm I want to update all games without prices",
            key="gallery_bulk_price_confirm",
        )
        
        # Enhanced bulk processing with real-time current game display
        if st.button("Update All Games Without Prices", key="gallery_bulk_price_button") and confirm_bulk_price:
            # Check if any games actually need updating
            games_without_prices = []
            try:
                resp = requests.get(f"{BACKEND_URL}/api/games")
                if resp.status_code == 200:
                    all_games = resp.json()
                    games_without_prices = [game for game in all_games if not game.get('price') or game.get('price') == 0]
                    if not games_without_prices:
                        st.warning("No games need price updates. All games already have prices!")
                        st.stop()
                    
                    st.info(f"🚀 Starting bulk price update for {len(games_without_prices)} games...")
            except Exception:
                st.error("Could not check which games need price updates")
                st.stop()
            
            # Process games one by one to show current game being processed
            progress_bar = st.progress(0)
            current_game_status = st.empty()
            
            successful_updates = []
            failed_updates = []
            
            for i, game in enumerate(games_without_prices):
                # Update current game display
                current_game_status.info(f"💰 **Processing:** {game.get('title', 'Unknown')} (ID: {game.get('id', 'N/A')}) • {i+1}/{len(games_without_prices)}")
                
                # Update progress bar
                progress = (i + 1) / len(games_without_prices)
                progress_bar.progress(progress)
                
                # Process this individual game
                try:
                    game_id = game.get('id')
                    if game_id:
                        result = update_game_price(game_id)
                        if result and result.get('new_price'):
                            successful_updates.append(game)
                        else:
                            failed_updates.append(game)
                    else:
                        failed_updates.append(game)
                        
                    # Small delay to make progress visible
                    time.sleep(0.1)
                        
                except Exception as e:
                    failed_updates.append(game)
                    continue
            
            # Clear current game status and show final results
            current_game_status.empty()
            
            # Show completion stats
            st.success(f"✅ Bulk price update completed!")
            
            # Show detailed results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Games Processed", len(games_without_prices))
            with col2:
                st.metric("Successful Updates", len(successful_updates))
            with col3:
                st.metric("Errors", len(failed_updates))
            
            # Store results in session state to display outside expander
            st.session_state["bulk_price_results"] = {
                "successful_updates": successful_updates,
                "failed_updates": failed_updates
            }
            
            # Auto-refresh to show updated prices
            st.rerun()
        
        # ---- Bulk: Update ALL Game Prices ----
        st.markdown("---")
        st.markdown("**⚠️ Bulk: Update ALL Game Prices**")
        st.warning("⚠️ **WARNING:** This will update prices for ALL games in your database. This operation will take a very long time and may hit rate limits.")
        
        # Show total games count
        try:
            resp = requests.get(f"{BACKEND_URL}/api/games")
            if resp.status_code == 200:
                all_games = resp.json()
                st.info(f"📋 **{len(all_games)} total games** would be processed")
                st.caption("⏱️ Estimated time: ~5-10 seconds per game")
        except Exception:
            st.warning("Could not get total games count")
        
        confirm_bulk_all_prices = st.checkbox(
            "⚠️ I understand this will take a very long time and want to update ALL game prices",
            key="gallery_bulk_all_price_confirm",
        )
        
        # Enhanced bulk processing for ALL games
        if st.button("⚠️ Update ALL Game Prices", key="gallery_bulk_all_price_button") and confirm_bulk_all_prices:
            # Get all games
            all_games = []
            try:
                resp = requests.get(f"{BACKEND_URL}/api/games")
                if resp.status_code == 200:
                    all_games = resp.json()
                    if not all_games:
                        st.warning("No games found in database!")
                        st.stop()
                    
                    st.info(f"🚀 Starting bulk price update for ALL {len(all_games)} games...")
                    st.warning("⏱️ This operation may take several hours. Please be patient and do not close this tab.")
            except Exception:
                st.error("Could not fetch games from database")
                st.stop()
            
            # Process games one by one to show current game being processed
            progress_bar = st.progress(0)
            current_game_status = st.empty()
            
            successful_updates = []
            failed_updates = []
            
            for i, game in enumerate(all_games):
                # Update current game display
                current_game_status.info(f"💰 **Processing:** {game.get('title', 'Unknown')} (ID: {game.get('id', 'N/A')}) • {i+1}/{len(all_games)}")
                
                # Update progress bar
                progress = (i + 1) / len(all_games)
                progress_bar.progress(progress)
                
                # Process this individual game
                try:
                    game_id = game.get('id')
                    if game_id:
                        result = update_game_price(game_id)
                        if result:
                            successful_updates.append(game)
                        else:
                            failed_updates.append(game)
                    else:
                        failed_updates.append(game)
                        
                    # Small delay to make progress visible and avoid rate limits
                    time.sleep(0.2)
                        
                except Exception as e:
                    failed_updates.append(game)
                    continue
            
            # Clear current game status and show final results
            current_game_status.empty()
            
            # Show completion stats
            st.success(f"✅ Bulk price update for ALL games completed!")
            
            # Show detailed results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Games Processed", len(all_games))
            with col2:
                st.metric("Successful Updates", len(successful_updates))
            with col3:
                st.metric("Errors", len(failed_updates))
            
            # Store results in session state to display outside expander
            st.session_state["bulk_price_results"] = {
                "successful_updates": successful_updates,
                "failed_updates": failed_updates
            }
            
            # Auto-refresh to show updated prices
            st.rerun()
    
    # -------------------------
    # Library Sidebar: Update Game Artwork Section (moved below filters)
    # -------------------------
    update_artwork_expander = st.sidebar.expander("Update Game Artwork")
    with update_artwork_expander:
        st.markdown("**Update artwork using SteamGridDB API**")
        st.info("Fetches high-resolution grid covers, heroes, logos, and icons")
        
        update_artwork_game_id = st.text_input("Game ID to Update Artwork", key="gallery_update_artwork_game_id")
        
        # Show game information when ID is entered
        if update_artwork_game_id and update_artwork_game_id.isdigit():
            try:
                game_info = fetch_game_by_id(update_artwork_game_id)
                if game_info:
                    st.info(f"🎮 **{game_info.get('title', 'Unknown')}** (ID: {update_artwork_game_id})")
                    # Show current artwork status
                    has_grid = bool(game_info.get('high_res_cover_url'))
                    has_hero = bool(game_info.get('hero_image_url'))
                    has_logo = bool(game_info.get('logo_image_url'))
                    has_icon = bool(game_info.get('icon_image_url'))
                    
                    artwork_status = []
                    if has_grid: artwork_status.append("✅ Grid")
                    else: artwork_status.append("❌ Grid")
                    if has_hero: artwork_status.append("✅ Hero")
                    else: artwork_status.append("❌ Hero")
                    if has_logo: artwork_status.append("✅ Logo")
                    else: artwork_status.append("❌ Logo")
                    if has_icon: artwork_status.append("✅ Icon")
                    else: artwork_status.append("❌ Icon")
                    
                    st.caption(f"Current artwork: {' | '.join(artwork_status)}")
                else:
                    st.warning(f"⚠️ Game ID {update_artwork_game_id} not found")
            except Exception:
                st.warning(f"⚠️ Could not fetch game information for ID {update_artwork_game_id}")
        
        mode = st.selectbox(
            "Artwork update mode",
            options=["Automatic (SteamGridDB)", "Manual upload"],
            index=0,
            key="gallery_artwork_update_mode",
        )

        if mode == "Automatic (SteamGridDB)":
            confirm_update_artwork = st.checkbox(
                "I confirm that I want to update this game's artwork",
                key="gallery_update_artwork_confirm",
            )
            if st.button("Update Artwork", key="gallery_update_artwork_button") and confirm_update_artwork:
                if update_artwork_game_id:
                    # Try to fetch game title for more informative spinner text
                    _title = None
                    try:
                        gd = fetch_game_by_id(update_artwork_game_id)
                        if isinstance(gd, dict):
                            _title = gd.get("title")
                    except Exception:
                        pass
                    _spinner_msg = f"Fetching artwork for '{_title}' (ID {update_artwork_game_id})..." if _title else "Fetching artwork from SteamGridDB..."
                    with st.spinner(_spinner_msg):
                        result = update_game_artwork(update_artwork_game_id)
                        if result and "error" not in result:
                            set_flash(f"Artwork updated for Game ID {result.get('game_id', update_artwork_game_id)} • {result.get('game_title','')}", "success")
                            st.session_state["refresh_artwork_stats"] = True
                            st.rerun()
                        elif result and result.get("error") == "api_key_missing":
                            st.error("❌ SteamGridDB API key not configured")
                            st.info("To use this feature:")
                            st.write("1. Get an API key from https://www.steamgriddb.com/profile/preferences/api")
                            st.write("2. Add `steamgriddb_api_key` to your `config.json` file")
                            st.write("3. Restart the backend service")
                        elif result and result.get("error") == "no_artwork_found":
                            st.warning("⚠️ No artwork found for this game")
                            st.write(f"**Game:** {result['details']['game_title']}")
                            st.info("SteamGridDB may not have artwork for this specific game. Try manually adding artwork or check if the game name matches exactly.")
                        else:
                            st.error("Failed to update game artwork. Please check the Game ID and try again.")
        else:
            st.markdown("**Manually upload artwork** (grid/hero/logo/icon)")
            artwork_type = st.selectbox(
                "Artwork type",
                options=["grid", "hero", "logo", "icon"],
                index=0,
                key="gallery_manual_art_type",
                help="Select which artwork slot to fill",
            )
            upload_file = st.file_uploader(
                "Choose an image file (png/jpg/jpeg/webp)",
                type=["png", "jpg", "jpeg", "webp"],
                key="gallery_manual_art_file",
            )
            if st.button("Upload Artwork", key="gallery_manual_art_upload"):
                if not update_artwork_game_id:
                    st.error("Please enter a Game ID")
                elif not upload_file:
                    st.error("Please choose an image file to upload")
                else:
                    with st.spinner("Uploading artwork..."):
                        files = {"file": (upload_file.name, upload_file.getvalue(), upload_file.type or "application/octet-stream")}
                        data = {"artwork_type": artwork_type}
                        resp = requests.post(
                            f"{BACKEND_URL}/upload_game_artwork/{update_artwork_game_id}",
                            files=files,
                            data=data,
                            timeout=30,
                        )
                        if resp.status_code == 200:
                            rj = resp.json()
                            set_flash(f"Artwork uploaded successfully • Game ID {rj.get('game_id')} • Type {rj.get('artwork_type')}", "success")
                            st.rerun()
                        else:
                            try:
                                st.error(resp.json())
                            except Exception:
                                st.error(f"Upload failed: HTTP {resp.status_code}")

        # ---- Bulk: Update All Missing Artwork ----
        st.markdown("---")
        st.markdown("**Bulk: Update All Missing Artwork**")
        
        # Show games that would be processed
        try:
            resp = requests.get(f"{BACKEND_URL}/api/high_res_artwork/status")
            if resp.status_code == 200:
                stats = resp.json()
                if stats.get("success"):
                    missing_games = stats.get("games_without_artwork", [])
                    if missing_games:
                        st.info(f"📋 **{len(missing_games)} games** need artwork updates")
                        
                        # Show expandable list of games to be processed
                        with st.expander(f"View games missing artwork ({len(missing_games)})", expanded=False):
                            for i, game in enumerate(missing_games):
                                st.write(f"• **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
                    else:
                        st.success("✅ All games already have artwork!")
                        st.info("No games need artwork updates at this time.")
        except Exception:
            st.warning("Could not check artwork status")
        
        confirm_bulk_art = st.checkbox(
            "I confirm I want to update all games missing artwork",
            key="gallery_bulk_art_confirm",
        )
        
        # Enhanced bulk processing with real-time current game display
        if st.button("Update All Missing Artwork", key="gallery_bulk_art_button") and confirm_bulk_art:
            # Check if any games actually need updating
            missing_games = []
            try:
                resp = requests.get(f"{BACKEND_URL}/api/high_res_artwork/status")
                if resp.status_code == 200:
                    stats = resp.json()
                    if stats.get("success"):
                        missing_games = stats.get("games_without_artwork", [])
                        if not missing_games:
                            st.warning("No games need artwork updates. All games already have artwork!")
                            st.stop()
                        
                        st.info(f"🚀 Starting bulk artwork update for {len(missing_games)} games...")
            except Exception:
                st.error("Could not check which games need artwork updates")
                st.stop()
            
            # Process games one by one to show current game being processed
            progress_bar = st.progress(0)
            current_game_status = st.empty()
            results_placeholder = st.empty()
            
            successful_updates = []
            failed_updates = []
            
            for i, game in enumerate(missing_games):
                # Update current game display
                current_game_status.info(f"🎮 **Processing:** {game.get('title', 'Unknown')} (ID: {game.get('id', 'N/A')}) • {i+1}/{len(missing_games)}")
                
                # Update progress bar
                progress = (i + 1) / len(missing_games)
                progress_bar.progress(progress)
                
                # Process this individual game
                try:
                    game_id = game.get('id')
                    if game_id:
                        result = update_game_artwork(game_id)
                        if result and "error" not in result:
                            successful_updates.append(game)
                        else:
                            failed_updates.append(game)
                    else:
                        failed_updates.append(game)
                        
                    # Small delay to make progress visible
                    time.sleep(0.1)
                        
                except Exception as e:
                    failed_updates.append(game)
                    continue
            
            # Clear current game status and show final results
            current_game_status.empty()
            
            # Show completion stats
            st.success(f"✅ Bulk artwork update completed!")
            
            # Show detailed results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Games Processed", len(missing_games))
            with col2:
                st.metric("Successful Updates", len(successful_updates))
            with col3:
                st.metric("Errors", len(failed_updates))
            
            # Store results in session state to display outside expander
            st.session_state["bulk_artwork_results"] = {
                "successful_updates": successful_updates,
                "failed_updates": failed_updates
            }
            st.session_state["refresh_artwork_stats"] = True
            
            # Auto-refresh to show updated artwork
            st.rerun()
    
    # Display bulk price results outside of expanders (to avoid nesting)
    if "bulk_price_results" in st.session_state:
        results = st.session_state["bulk_price_results"]
        successful_updates = results.get("successful_updates", [])
        failed_updates = results.get("failed_updates", [])
        
        st.markdown("---")
        st.subheader("💰 Bulk Price Update Results")
        
        # Show list of updated games
        if successful_updates:
            with st.expander(f"✅ Successfully updated ({len(successful_updates)})", expanded=False):
                for game in successful_updates:
                    st.write(f"✅ **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
        
        # Show list of failed games
        if failed_updates:
            with st.expander(f"❌ Failed updates ({len(failed_updates)})", expanded=False):
                for game in failed_updates:
                    st.write(f"❌ **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
        
        # Clear results after displaying
        if st.button("Clear Results", key="clear_bulk_price_results"):
            del st.session_state["bulk_price_results"]
            st.rerun()
    
    # Display bulk artwork results outside of expanders (to avoid nesting)
    if "bulk_artwork_results" in st.session_state:
        results = st.session_state["bulk_artwork_results"]
        successful_updates = results.get("successful_updates", [])
        failed_updates = results.get("failed_updates", [])
        
        st.markdown("---")
        st.subheader("🎨 Bulk Artwork Update Results")
        
        # Show list of updated games
        if successful_updates:
            with st.expander(f"✅ Successfully updated ({len(successful_updates)})", expanded=False):
                for game in successful_updates:
                    st.write(f"✅ **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
        
        # Show list of failed games
        if failed_updates:
            with st.expander(f"❌ Failed updates ({len(failed_updates)})", expanded=False):
                for game in failed_updates:
                    st.write(f"❌ **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
        
        # Clear results after displaying
        if st.button("Clear Results", key="clear_bulk_artwork_results"):
            del st.session_state["bulk_artwork_results"]
            st.rerun()
    
    # Fetch gallery data
    gallery_data = fetch_gallery_games(
        filters=filters,
        page=st.session_state["gallery_page"],
        per_page=per_page
    )
    
    games = gallery_data.get("games", [])
    # Store current page games for actions within forms (e.g., Update Prices in Price History form)
    st.session_state["current_gallery_games"] = games
    pagination = gallery_data.get("pagination", {})
    total_games = pagination.get("total_count", 0)  # Backend uses total_count, not total_games
    total_pages = pagination.get("total_pages", 1)
    
    # Display results summary
    col_summary, col_stats = st.columns([3, 1])
    with col_summary:
        if games:
            # Calculate total value of filtered games
            total_value = sum(
                game.get("average_price", 0) or 0 
                for game in games
            )
            
        if filters:
            active_filters = []
            if title_search:
                active_filters.append(f"Search: '{title_search}'")
            if selected_platform != "All":
                active_filters.append(f"Platform: {selected_platform}")
            if selected_genre != "All":
                active_filters.append(f"Genre: {selected_genre}")
            if selected_region != "All":
                active_filters.append(f"Region: {selected_region}")
            if year_range and year_range != (min_year, max_year):
                active_filters.append(f"Years: {year_range[0]}-{year_range[1]}")
            
            st.markdown(f"**Found {total_games} games** matching: {' | '.join(active_filters)}")
            if games:
                st.markdown(f"### Page Value: £{total_value:.2f}")
        else:
            st.markdown(f"**Showing all {total_games} games** in your collection")
            if games:
                st.markdown(f"### Page Value: £{total_value:.2f}")
    
    with col_stats:
        # This column can be used for other stats or left empty
        pass
    
    # Display games in grid layout
    if games:
        # Create grid layout
        rows = [games[i:i + grid_cols] for i in range(0, len(games), grid_cols)]
        
        for row in rows:
            cols = st.columns(grid_cols)
            for idx, game in enumerate(row):
                if idx < len(cols):
                    display_gallery_tile(cols[idx], game)
        
        # Pagination controls
        if total_pages > 1:
            st.markdown("---")
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            
            with col_prev:
                if st.session_state["gallery_page"] > 1:
                    if st.button("Previous", key="gallery_prev"):
                        st.session_state["gallery_page"] -= 1
                        st.rerun()
            
            with col_info:
                st.markdown(f"**Page {st.session_state['gallery_page']} of {total_pages}**")
                
                # Page jump selector
                page_options = list(range(1, total_pages + 1))
                if len(page_options) <= 10:  # Only show if reasonable number of pages
                    selected_page = st.selectbox(
                        "Jump to page:",
                        page_options,
                        index=st.session_state["gallery_page"] - 1,
                        key="gallery_page_jump"
                    )
                    if selected_page != st.session_state["gallery_page"]:
                        st.session_state["gallery_page"] = selected_page
                        st.rerun()
            
            with col_next:
                if st.session_state["gallery_page"] < total_pages:
                    if st.button("Next", key="gallery_next"):
                        st.session_state["gallery_page"] += 1
                        st.rerun()
    else:
        st.info("No games found matching your filters. Try adjusting the criteria above.")
        
        if filters:
            st.markdown("""
            **Tips for better results:**
            - Try removing some filters
            - Check spelling in the search box
            - Use broader tag selections
            """)

def display_gallery_tile(column, game):
    """Display individual game tile with clickable artwork using HTML/CSS hover effects"""
    with column:
        # Use best available cover image
        cover_url = get_best_cover_image(game)
        
        # Game details - ensure all fields have safe defaults
        game_id = game.get('id', 'unknown')
        game_title = game.get('title', 'Unknown Game') or 'Unknown Game'
        platform = game.get('platforms', ['Unknown Platform'])
        platform_text = ', '.join(platform) if isinstance(platform, list) else str(platform or 'Unknown Platform')
        region = backend_to_frontend_region(game.get('region', 'PAL'))
        platform_region_text = f"{platform_text} ({region})"
        
        # Genre display (limit to 1 genre to save space for price)
        genres = game.get("genres", [])
        genre_html = ""
        
        # Ensure genres is a list and has valid content
        if genres and isinstance(genres, list):
            # Filter out empty/None genres
            valid_genres = [g.strip() for g in genres if g and str(g).strip()]
            if valid_genres:
                display_genres = valid_genres[:1]  # Show only 1 genre to make room for price
                genre_colors = ["#667eea", "#764ba2", "#f093fb", "#f5576c", "#4ecdc4", "#45b7d1"]
                for i, genre in enumerate(display_genres):
                    color = genre_colors[i % len(genre_colors)]
                    genre_html += f'<span style="background: {color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 9px; margin-right: 4px; display: inline-block;">{html.escape(str(genre))}</span>'
                if len(valid_genres) > 1:
                    genre_html += f'<span style="color: #888; font-size: 9px; font-style: italic;">+{len(valid_genres) - 1}</span>'
        
        # Price and year - ensure safe handling of None/empty values
        price = game.get("average_price")
        year = game.get("release_year")
        price_text = f"£{price:.2f}" if price and price != 0 else "No price"
        year_text = f" • {year}" if year else ""
        
        # Create the tile with enhanced styling
        with st.container():
            # Add custom CSS for this specific tile
            st.markdown(f"""
            <style>
            .game-tile-{game_id} {{
                border: 1px solid #ddd;
                border-radius: 15px;
                padding: 0;
                margin-bottom: 20px;
                background: linear-gradient(145deg, #f8f9fa, #ffffff);
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                text-align: center;
                overflow: hidden;
                cursor: pointer;
                position: relative;
                transform-style: preserve-3d;
                perspective: 1000px;
            }}
            .game-tile-{game_id}:hover {{
                transform: translateY(-8px) rotateX(2deg) rotateY(2deg) scale(1.02);
                box-shadow: 0 20px 60px rgba(0,0,0,0.25), 0 8px 20px rgba(102, 126, 234, 0.3);
                border-color: #667eea;
            }}
            .game-tile-{game_id}::before {{
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                background: linear-gradient(45deg, #667eea, #764ba2, #f093fb, #f5576c);
                border-radius: 15px;
                opacity: 0;
                transition: opacity 0.3s ease;
                z-index: -1;
            }}
            .game-tile-{game_id}:hover::before {{
                opacity: 1;
            }}
            .game-tile-{game_id} img {{
                width: 100%;
                height: 220px;
                object-fit: cover;
                border-radius: 15px 15px 0 0;
                margin-bottom: 0;
                transition: all 0.4s ease;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            .game-tile-{game_id}:hover img {{
                transform: scale(1.05);
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            }}
            .game-tile-content-{game_id} {{
                padding: 15px;
                transform-style: preserve-3d;
                transition: transform 0.4s ease;
            }}
            .game-tile-{game_id}:hover .game-tile-content-{game_id} {{
                transform: translateZ(10px);
            }}
            </style>
            """, unsafe_allow_html=True)
            
            # Use a much simpler approach - just create a clickable tile with st.button overlay
            # First, display the visual tile
            st.markdown(f"""
            <div class="visual-tile-{game_id}" style="
                border: 1px solid #ddd;
                border-radius: 15px;
                padding: 0;
                margin-bottom: 20px;
                background: linear-gradient(145deg, #f8f9fa, #ffffff);
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                text-align: center;
                overflow: hidden;
                position: relative;
                transform-style: preserve-3d;
                perspective: 1000px;
                height: 420px;
            ">
                <img src="{cover_url}" alt="{html.escape(str(game_title))}" style="
                    width: 100%;
                    height: 220px;
                    object-fit: cover;
                    border-radius: 15px 15px 0 0;
                    margin-bottom: 0;
                    transition: all 0.4s ease;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                ">
                <div style="padding: 15px;">
                    <h4 style="margin: 5px 0 8px 0; font-size: 14px; color: #333; font-weight: 600; line-height: 1.2;">
                        {html.escape(str(game_title))}
                    </h4>
                    <p style="margin: 0 0 8px 0; font-size: 12px; color: #666;">
                        {html.escape(str(platform_region_text))}
                    </p>
                    <div style="margin-bottom: 8px;">
                        {genre_html}
                    </div>
                    <div style="margin-top: 8px; font-weight: bold; color: #333; font-size: 12px;">
                        {html.escape(str(price_text))}{html.escape(str(year_text))}
                    </div>
                </div>
            </div>
            
            <style>
            .visual-tile-{game_id}:hover {{
                transform: translateY(-8px) rotateX(2deg) rotateY(2deg) scale(1.02) !important;
                box-shadow: 0 20px 60px rgba(0,0,0,0.25), 0 8px 20px rgba(102, 126, 234, 0.3) !important;
                border-color: #667eea !important;
            }}
            .visual-tile-{game_id}:hover img {{
                transform: scale(1.05) !important;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2) !important;
            }}
            </style>
            """, unsafe_allow_html=True)
            
            # Now create a button that spans the entire tile area
            if st.button(
                "View Details", 
                key=f"game_tile_{game_id}",
                help=f"Click to view details for {game_title}",
                use_container_width=True
            ):
                # Store current gallery state before navigating to game detail
                store_gallery_state()
                st.session_state["selected_game_detail"] = game
                st.session_state["page"] = "game_detail"
                st.rerun()

# -------------------------
# Main Application Function
# -------------------------
def main():
    # Only show main title when not on gallery/library page
    if st.session_state.get("page") != "gallery":
        st.title("Video Game Catalogue")

    if "bulk_delete_mode" not in st.session_state:
        st.session_state["bulk_delete_mode"] = False

    # Initialize session state for filter mode and page navigation
    if "filters_active" not in st.session_state:
        st.session_state["filters_active"] = False
    if "page" not in st.session_state:
        st.session_state["page"] = "home"
    
    # Initialize editor pagination
    if "editor_page" not in st.session_state:
        st.session_state["editor_page"] = 1
    if "editor_per_page" not in st.session_state:
        st.session_state["editor_per_page"] = 20

    # -------------------------
    # Sidebar: Navigation Buttons
    # -------------------------
    col_home, col_gallery = st.sidebar.columns(2)
    
    with col_home:
        home_clicked = st.button("Editor", type="primary", use_container_width=True)
    with col_gallery:
        gallery_clicked = st.button("Library", type="secondary", use_container_width=True)
    
    if gallery_clicked:
        # Check if we have stored gallery state to restore
        if st.session_state.get("stored_gallery_state"):
            restore_gallery_state()
        st.session_state["page"] = "gallery"
        st.rerun()
    
    if home_clicked:
        # Switch to home page and preserve the price source selection
        st.session_state["page"] = "home"
        price_source_backup = st.session_state.get("price_source_selection", "eBay")
        
        # Clear all filters and reset to home state
        st.session_state["filters_active"] = False
        st.session_state["search_results"] = None
        st.session_state["selected_game"] = None
        st.session_state["selected_game_by_id"] = None
        st.session_state["editing_game_id"] = None
        st.session_state["bulk_delete_mode"] = False
        # Increment a counter to force new input keys
        st.session_state["home_reset_counter"] = st.session_state.get("home_reset_counter", 0) + 1
        # Clear ALL session state keys that might interfere
        keys_to_delete = []
        for key in st.session_state.keys():
            if key.startswith(("filter_", "search_", "edit_game_data", "confirm_delete_", "add_", "delete_", "edit_", "bulk_delete_", "game_name_", "igdb_id_", "platform_select")):
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del st.session_state[key]
        
        # Restore the price source selection in both session state and URL
        st.session_state["price_source_selection"] = price_source_backup
        st.query_params["price_source"] = price_source_backup
        st.rerun()

    st.sidebar.markdown("---")  # Add a separator line

    # -------------------------
    # Page Routing Logic
    # -------------------------
    if st.session_state.get("page") == "gallery":
        gallery_page()
        return  # Exit main function to show only gallery page
    elif st.session_state.get("page") == "game_detail":
        game_detail_page()
        return  # Exit main function to show only game detail page
    
    # Otherwise, show the home page content below...

    # -------------------------
    # Sidebar: Music Player Section
    # -------------------------
    music_expander = st.sidebar.expander("Video Game Music Player")
    with music_expander:
        st.markdown("### VIPVGM - Video Game Music")
        st.markdown("*Load the embedded player on demand to prevent autoplay.*")
        if not st.session_state.get("vipvgm_home_embedded"):
            if st.button("Load Embedded Player", key="vipvgm_home_load"):
                st.session_state["vipvgm_home_embedded"] = True

        if st.session_state.get("vipvgm_home_embedded"):
            iframe_html = """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; padding: 15px; margin: 10px 0;">
                <iframe 
                    src="https://www.vipvgm.net/" 
                    width="100%" 
                    height="400" 
                    frameborder="0" 
                    scrolling="yes"
                    allow="encrypted-media; fullscreen"
                    title="VIPVGM Video Game Music Player"
                    style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"
                ></iframe>
            </div>
            """
            components.html(iframe_html, height=450)
    st.sidebar.markdown("---")  # Add separator

    # Database Backups (Editor)
    with st.sidebar.expander("Database Backups", expanded=False):
        if st.button("Create Backup", key="editor_create_backup", type="primary", use_container_width=True):
            try:
                r = requests.post(f"{BACKEND_URL}/api/backup_db")
                if r.status_code == 200 and r.json().get("success"):
                    info = r.json()
                    st.success(f"Backup created: {info.get('backup_file')}")
                    if info.get("download_url"):
                        st.link_button("Download", f"{BACKEND_URL}{info['download_url']}", use_container_width=True)
                else:
                    st.error("Failed to create backup")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Show existing backups
        st.markdown("**Available Backups:**")
        try:
            lr = requests.get(f"{BACKEND_URL}/api/backups")
            if lr.status_code == 200 and lr.json().get("success"):
                backups = lr.json().get("backups", [])
                if backups:
                    for f in backups[:5]:  # Show only last 5 backups
                        name = f.get('name', 'Unknown')
                        size_bytes = int(f.get('size_bytes', 0))
                        
                        # Format file size more compactly
                        if size_bytes > 1024 * 1024:  # > 1MB
                            size_str = f"{size_bytes / (1024 * 1024):.1f}MB"
                        elif size_bytes > 1024:  # > 1KB
                            size_str = f"{size_bytes / 1024:.1f}KB"
                        else:
                            size_str = f"{size_bytes}B"
                        
                        # Truncate long filenames for better display
                        display_name = name[:25] + "..." if len(name) > 28 else name
                        
                        if f.get("download_url"):
                            st.markdown(f"📥 [{display_name}]({BACKEND_URL}{f['download_url']})")
                            st.caption(f"Size: {size_str}")
                        else:
                            st.markdown(f"📄 {display_name}")
                            st.caption(f"Size: {size_str}")
                        
                        if f != backups[min(4, len(backups)-1)]:  # Add spacing except for last item
                            st.markdown("")
                            
                    if len(backups) > 5:
                        st.caption(f"...and {len(backups) - 5} more backups")
                else:
                    st.info("No backups found.")
            else:
                st.warning("Could not load backup list.")
        except Exception as e:
            st.error(f"Error loading backups: {e}")
    
    st.sidebar.markdown("---")  # Add separator

    # -------------------------
    # Global Price Source Selector
    # -------------------------
    st.sidebar.markdown("### Price Scraping")
    
    # Get the current price source from URL parameters or session state
    price_options = ["eBay", "Amazon", "CeX", "PriceCharting"]
    
    # Initialize from backend if no local preference exists
    if "price_source_selection" not in st.session_state and "price_source" not in st.query_params:
        try:
            response = requests.get(f"{BACKEND_URL}/price_source")
            if response.status_code == 200:
                backend_price_source = response.json().get("price_source", "eBay")
                st.session_state["price_source_selection"] = backend_price_source
                st.query_params["price_source"] = backend_price_source
        except Exception:
            # Fallback to default if backend is unavailable
            pass
    
    # Check URL parameters first for persistence across page refreshes
    url_params = st.query_params
    url_price_source = url_params.get("price_source")
    
    # Initialize the price source selection with URL parameter priority
    if url_price_source and url_price_source in price_options:
        # Use URL parameter if valid
        current_selection = url_price_source
        st.session_state["price_source_selection"] = current_selection
    elif "price_source_selection" not in st.session_state:
        # Initialize with default if no URL parameter and no session state
        current_selection = "eBay"
        st.session_state["price_source_selection"] = current_selection
        # Set URL parameter to maintain persistence
        st.query_params["price_source"] = current_selection
    else:
        # Use existing session state
        current_selection = st.session_state.get("price_source_selection", "eBay")
        # Ensure URL parameter matches session state
        if current_selection in price_options:
            st.query_params["price_source"] = current_selection
    
    # Ensure the current selection is valid
    if current_selection not in price_options:
        current_selection = "eBay"
        st.session_state["price_source_selection"] = current_selection
        st.query_params["price_source"] = current_selection
    
    # Get the index for the selectbox
    try:
        current_index = price_options.index(current_selection)
    except ValueError:
        current_index = 0  # Default to eBay if there's any issue
        st.session_state["price_source_selection"] = "eBay"
        st.query_params["price_source"] = "eBay"
    
    global_price_source = st.sidebar.selectbox(
        "Default Price Source:", 
        price_options,
        index=current_index,
        key="global_price_source",
        help="This will be used for all price scraping operations (barcode scanning, IGDB lookups, etc.)"
    )
    
    # Region selector for PriceCharting only
    if global_price_source == "PriceCharting":
        region_options = ["PAL", "NTSC", "JP"]
        
        # Get current region from backend if not in session state
        if "pricecharting_region" not in st.session_state:
            try:
                resp = requests.get(f"{BACKEND_URL}/default_region")
                if resp.status_code == 200:
                    backend_region = resp.json().get("default_region", "PAL")
                    # Convert backend region to frontend format
                    if backend_region.upper() in ["PAL", "NTSC"]:
                        current_region = backend_region.upper()
                    elif backend_region.lower() in ["japan", "jp", "jpn"]:
                        current_region = "JP"
                    else:
                        current_region = "PAL"
                else:
                    current_region = "PAL"
            except Exception:
                current_region = "PAL"
        else:
            current_region = st.session_state.get("pricecharting_region", "PAL")
            if current_region not in region_options:
                current_region = "PAL"
            
        try:
            region_index = region_options.index(current_region)
        except ValueError:
            region_index = 0
            current_region = "PAL"
            
        # Placeholder so feedback appears directly under the region selectbox
        region_feedback = st.sidebar.empty()

        # Helper function to convert frontend region format to backend format
        def frontend_to_backend_region(frontend_region):
            if frontend_region == "JP":
                return "Japan"
            return frontend_region
        
        # Ensure backend config is updated immediately when user changes region
        def _on_pricecharting_region_change():
            new_region = st.session_state.get("pricecharting_region", "PAL")
            backend_region = frontend_to_backend_region(new_region)
            try:
                response = requests.post(
                    f"{BACKEND_URL}/default_region",
                    json={"default_region": backend_region}
                )
                if response.status_code == 200:
                    region_feedback.success(f"Region updated to {new_region}", icon="✅")
                else:
                    region_feedback.error("Failed to update backend region", icon="⚠️")
            except Exception as e:
                region_feedback.error(f"Error syncing region: {e}", icon="⚠️")

        # Initialize session state with current region before creating selectbox
        if "pricecharting_region" not in st.session_state:
            st.session_state["pricecharting_region"] = current_region
            
        selected_region = st.sidebar.selectbox(
            "PriceCharting Region:",
            region_options,
            key="pricecharting_region",
            help="Choose the region for PriceCharting pricing:\n• PAL: European market prices\n• NTSC: North American market prices\n• JP: Japanese market prices",
            on_change=_on_pricecharting_region_change
        )
        
        # Boxed toggle for PriceCharting condition selection
        boxed_condition = st.sidebar.checkbox(
            "Boxed (CiB)",
            value=st.session_state.get("pricecharting_boxed", True),
            key="pricecharting_boxed",
            help="• Checked: Complete in Box (CiB) pricing - includes case/box\n• Unchecked: Loose pricing - game only, no case/box\n\nDefault is CiB as most disc games have cases, but cartridge games often come loose"
        )
    
    # Update both session state and URL parameters when selection changes
    if global_price_source != st.session_state.get("price_source_selection"):
        st.session_state["price_source_selection"] = global_price_source
        st.query_params["price_source"] = global_price_source
        
        # Also update the backend's price source preference
        try:
            response = requests.post(
                f"{BACKEND_URL}/price_source", 
                json={"price_source": global_price_source}
            )
            if response.status_code == 200:
                st.sidebar.success(f"Price source updated to {global_price_source}", icon="✅")
            else:
                st.sidebar.error(f"Failed to update backend price source", icon="⚠️")
        except Exception as e:
            st.sidebar.error(f"Error syncing price source: {e}", icon="⚠️")

    # -------------------------
    # Sidebar: Search by Title
    # -------------------------
    st.sidebar.title("Filter Games")
    # Use a dynamic key that changes when home is clicked to force a fresh input
    search_key = f"search_title_{st.session_state.get('home_reset_counter', 0)}"
    search_term = st.sidebar.text_input("Search by Title", key=search_key)
    selected_for_deletion = []  # List to hold IDs for games selected for deletion

    # If a search term is provided, fetch and display matching games with edit/delete options.
    if search_term:
        filters = {"title": search_term}
        games = fetch_games(filters)
        if not isinstance(games, list):
            games = []
        total_cost = calculate_total_cost(games)
        st.markdown(
            f"<h3>Total Cost of Search Results: <strong style='color: red;'>£{float(total_cost):.2f}</strong></h3>",
            unsafe_allow_html=True
        )
        if games:
            if "editing_game_id" not in st.session_state:
                st.session_state.editing_game_id = None
            # Initialize the list to store IDs for bulk deletion.
            selected_for_deletion = []  # Initialize list outside the loop

            for game in games:
                display_game_item(game)
                if st.checkbox("Select for deletion", key=f"bulk_delete_{game['id']}"):
                    selected_for_deletion.append(game["id"])

            # Now, after the loop, if any games were selected, show one button for bulk deletion.
            if selected_for_deletion:
                if st.button("Delete Selected Games", key="bulk_delete_button"):
                    for game_id in selected_for_deletion:
                        if delete_game(game_id):
                            st.success(f"Deleted game with ID: {game_id}")
                        else:
                            st.error(f"Failed to delete game with ID: {game_id}")
                    # Optionally, refresh the game list using the same filters:
                    games = fetch_games(filters)
        else:
            st.warning("No games found matching your search.")
        # Return early so that only search results are displayed
        return

    # -------------------------
    # Sidebar: Add Game Section
    # -------------------------
    add_expander = st.sidebar.expander("Add Game")
    with add_expander:
        title = st.text_input("Title", key="add_title")
        description = st.text_area("Description", key="add_description")
        publisher = st.text_input("Publisher", key="add_publisher")

        raw_platforms = st.text_input("Platforms (comma separated)", key="add_platforms")
        platforms_list = [p.strip() for p in raw_platforms.split(",") if p.strip()]

        raw_genres = st.text_input("Genres (comma separated)", key="add_genres")
        genres_list = [g.strip() for g in raw_genres.split(",") if g.strip()]

        series = st.text_input("Series", key="add_series")
        release_date = st.date_input("Release Date", key="add_release_date")
        average_price = st.number_input("Average Price", value=0.0, step=0.01, format="%.2f", key="add_average_price")

        if st.button("Add Game", key="add_game_button"):
            game_data = {
                "title": title,
                "cover_image": "",  # Cover Image URL field removed - now uses high-res artwork system
                "description": description,
                "publisher": [publisher],
                "platforms": platforms_list,
                "genres": genres_list,
                "series": [series],
                "release_date": (
                    release_date.strftime("%Y-%m-%d") if release_date else "1900-01-01"
                ),
                "average_price": average_price,
            }
            if add_game(game_data):
                st.success("Game added successfully")

    # -------------------------
    # Sidebar: Delete Game Section
    # -------------------------
    delete_expander = st.sidebar.expander("Delete Game")
    with delete_expander:
        game_id = st.text_input("Game ID", key="delete_game_id")
        confirm_delete = st.checkbox("I confirm that I want to delete this game", key="delete_confirm")
        if st.button("Delete Game", key="delete_game_button") and confirm_delete:
            if delete_game(game_id):
                st.success("Game Deleted")
                # Rebuild the filters from your session state (or from your filter controls)
                filters = {}
                if st.session_state.get("filter_publisher"):
                    filters["publisher"] = st.session_state["filter_publisher"]
                if st.session_state.get("filter_platform"):
                    filters["platform"] = st.session_state["filter_platform"]
                if st.session_state.get("filter_genre"):
                    filters["genre"] = st.session_state["filter_genre"]
                if st.session_state.get("filter_year"):
                    filters["year"] = st.session_state["filter_year"]
                # If you have sort options:
                if st.session_state.get("filter_sort_highest_value"):
                    filters["sort"] = "highest"
                elif st.session_state.get("filter_sort_alphabetical"):
                    filters["sort"] = "alphabetical"
                # Re-fetch games using the same filters
                games = fetch_games(filters)
            else:
                st.error("Failed to delete game")

    # -------------------------
    # Sidebar: Edit Game Section (Separate from inline editing)
    # -------------------------
    edit_expander = st.sidebar.expander("Edit Game")
    with edit_expander:
        edit_game_id = st.text_input("Game ID to Edit", key="edit_game_id")
        if st.button("Fetch Game Details", key="fetch_game_details_button"):
            game_details = fetch_game_by_id(edit_game_id)
            if game_details:
                st.session_state["edit_game_data"] = game_details
            else:
                st.error("Game not found.")

        if "edit_game_data" in st.session_state:
            game_details = st.session_state["edit_game_data"]

            # Ensure platforms and genres are in list form
            if isinstance(game_details["platforms"], str):
                game_details["platforms"] = [game_details["platforms"]]
            if isinstance(game_details["genres"], str):
                game_details["genres"] = [game_details["genres"]]

            edit_title = st.text_input("Title", game_details["title"], key="edit_title")
            edit_description = st.text_area("Description", game_details["description"], key="edit_description")

            edit_publisher = st.text_input("Publisher", ", ".join(game_details["publisher"]), key="edit_publisher")
            new_pub_list = [p.strip() for p in edit_publisher.split(",") if p.strip()]

            edit_platforms_str = ", ".join(game_details["platforms"])
            edit_platforms_input = st.text_input("Platforms (comma separated)", edit_platforms_str, key="edit_platforms")
            new_platforms_list = [p.strip() for p in edit_platforms_input.split(",") if p.strip()]

            edit_genres_str = ", ".join(game_details["genres"])
            edit_genres_input = st.text_input("Genres (comma separated)", edit_genres_str, key="edit_genres")
            new_genres_list = [g.strip() for g in edit_genres_input.split(",") if g.strip()]

            edit_series_str = ", ".join(game_details["series"])
            edit_series_input = st.text_input("Series (comma separated)", edit_series_str, key="edit_series")
            new_series_list = [s.strip() for s in edit_series_input.split(",") if s.strip()]

            edit_release_date = st.date_input("Release Date", key="edit_release_date")
            # Region selector for sidebar editor
            region_options = ["PAL", "NTSC", "JP"]
            current_region = backend_to_frontend_region(game_details.get("region") or "PAL")
            if current_region not in region_options:
                current_region = "PAL"
            region_index = region_options.index(current_region)
            edit_region = st.selectbox("Region", region_options, index=region_index, key="edit_region_sidebar")
            default_price = float(game_details.get("average_price") or 0)
            edit_average_price = st.number_input("Average Price", value=default_price, step=0.01, format="%.2f", key="edit_average_price")

            if st.button("Update Game", key="update_game_button"):
                # Convert frontend region format to backend format for storage
                backend_region = "Japan" if edit_region == "JP" else edit_region
                
                updated_game_data = {
                    "title": edit_title,
                    "cover_image": "",  # Cover Image URL field removed - now uses high-res artwork system
                    "description": edit_description,
                    "publisher": new_pub_list,
                    "platforms": new_platforms_list,
                    "genres": new_genres_list,
                    "series": new_series_list,
                    "release_date": (
                        edit_release_date.strftime("%Y-%m-%d") if edit_release_date else "1900-01-01"
                    ),
                    "average_price": edit_average_price,
                    "region": backend_region,
                }
                if update_game(edit_game_id, updated_game_data):
                    st.success("Game updated successfully")
                else:
                    st.error("Failed to update game")

            # Add "Update Price" button to the edit section
            st.markdown("---")
            st.markdown("**Or update just the price:**")
            current_price_source = get_price_source()
            st.info(f"Will use current price source: **{current_price_source}**")
            
            if st.button("Update Price Only", key="update_price_only_button"):
                with st.spinner(f"Updating price using {current_price_source}..."):
                    result = update_game_price(edit_game_id)
                    if result:
                        st.success(f"✅ Price updated successfully!")
                        st.write(f"**Game:** {result['game_title']}")
                        st.write(f"**Old Price:** £{result['old_price']:.2f}" if result['old_price'] else "**Old Price:** Not set")
                        st.write(f"**New Price:** £{result['new_price']:.2f}" if result['new_price'] else "**New Price:** Not found")
                        st.write(f"**Source:** {result['price_source']}")
                        
                        # Update the session state with new price
                        if "edit_game_data" in st.session_state:
                            st.session_state["edit_game_data"]["average_price"] = result['new_price']
                        st.rerun()  # Refresh to show updated data
                    else:
                        st.error("Failed to update game price.")

    # -------------------------
    # Sidebar: Update Game Price Section
    # -------------------------
    update_price_expander = st.sidebar.expander("Update Game Price")
    with update_price_expander:
        st.markdown("**Update price using current price source configuration**")
        
        # Get current price source for display
        current_price_source = get_price_source()
        st.info(f"Current price source: **{current_price_source}**")
        
        # Individual game price update
        st.markdown("**Single Game Price Update**")
        update_price_game_id = st.text_input("Game ID to Update Price", key="editor_update_price_game_id")
        confirm_update_price = st.checkbox("I confirm that I want to update this game's price", key="editor_update_price_confirm")
        
        if st.button("Update Price", key="editor_update_price_button") and confirm_update_price:
            if update_price_game_id:
                with st.spinner(f"Updating price using {current_price_source}..."):
                    result = update_game_price(update_price_game_id)
                    if result:
                        st.success(f"✅ Price updated successfully!")
                        st.write(f"**Game:** {result['game_title']}")
                        st.write(f"**Old Price:** £{result['old_price']:.2f}" if result['old_price'] else "**Old Price:** Not set")
                        st.write(f"**New Price:** £{result['new_price']:.2f}" if result['new_price'] else "**New Price:** Not found")
                        st.write(f"**Source:** {result['price_source']}")
                        
                        # Rebuild the filters and refresh games list
                        filters = {}
                        if st.session_state.get("filter_publisher"):
                            filters["publisher"] = st.session_state["filter_publisher"]
                        if st.session_state.get("filter_platform"):
                            filters["platform"] = st.session_state["filter_platform"]
                        if st.session_state.get("filter_genre"):
                            filters["genre"] = st.session_state["filter_genre"]
                        if st.session_state.get("filter_year"):
                            filters["year"] = st.session_state["filter_year"]
                        # Re-fetch games to show updated price
                        games = fetch_games(filters)
                    else:
                        st.error("Failed to update game price. Please check the Game ID and try again.")
            else:
                st.warning("Please enter a Game ID.")
        
        # ---- Bulk: Update Games Without Prices ----
        st.markdown("---")
        st.markdown("**Bulk: Update Games Without Prices**")
        
        # Show games that would be processed (games without prices)
        try:
            resp = requests.get(f"{BACKEND_URL}/api/games")
            if resp.status_code == 200:
                all_games = resp.json()
                games_without_prices = [game for game in all_games if not game.get('price') or game.get('price') == 0]
                if games_without_prices:
                    st.info(f"📋 **{len(games_without_prices)} games** need price updates")
                    
                    # Show expandable list of games to be processed
                    with st.expander(f"View games without prices ({len(games_without_prices)})", expanded=False):
                        for i, game in enumerate(games_without_prices[:20]):  # Show first 20
                            current_price = f"£{game.get('price', 0):.2f}" if game.get('price') else "No price"
                            st.write(f"• **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')}) - {current_price}")
                        if len(games_without_prices) > 20:
                            st.caption(f"... and {len(games_without_prices) - 20} more games")
                else:
                    st.success("✅ All games already have prices!")
                    st.info("No games need price updates at this time.")
        except Exception:
            st.warning("Could not check price status")
        
        confirm_bulk_price = st.checkbox(
            "I confirm I want to update all games without prices",
            key="editor_bulk_price_confirm",
        )
        
        # Enhanced bulk processing with real-time current game display
        if st.button("Update All Games Without Prices", key="editor_bulk_price_button") and confirm_bulk_price:
            # Check if any games actually need updating
            games_without_prices = []
            try:
                resp = requests.get(f"{BACKEND_URL}/api/games")
                if resp.status_code == 200:
                    all_games = resp.json()
                    games_without_prices = [game for game in all_games if not game.get('price') or game.get('price') == 0]
                    if not games_without_prices:
                        st.warning("No games need price updates. All games already have prices!")
                        st.stop()
                    
                    st.info(f"🚀 Starting bulk price update for {len(games_without_prices)} games...")
            except Exception:
                st.error("Could not check which games need price updates")
                st.stop()
            
            # Process games one by one to show current game being processed
            progress_bar = st.progress(0)
            current_game_status = st.empty()
            
            successful_updates = []
            failed_updates = []
            
            for i, game in enumerate(games_without_prices):
                # Update current game display
                current_game_status.info(f"💰 **Processing:** {game.get('title', 'Unknown')} (ID: {game.get('id', 'N/A')}) • {i+1}/{len(games_without_prices)}")
                
                # Update progress bar
                progress = (i + 1) / len(games_without_prices)
                progress_bar.progress(progress)
                
                # Process this individual game
                try:
                    game_id = game.get('id')
                    if game_id:
                        result = update_game_price(game_id)
                        if result and result.get('new_price'):
                            successful_updates.append(game)
                        else:
                            failed_updates.append(game)
                    else:
                        failed_updates.append(game)
                        
                    # Small delay to make progress visible
                    time.sleep(0.1)
                        
                except Exception as e:
                    failed_updates.append(game)
                    continue
            
            # Clear current game status and show final results
            current_game_status.empty()
            
            # Show completion stats
            st.success(f"✅ Bulk price update completed!")
            
            # Show detailed results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Games Processed", len(games_without_prices))
            with col2:
                st.metric("Successful Updates", len(successful_updates))
            with col3:
                st.metric("Errors", len(failed_updates))
            
            # Store results in session state to display outside expander
            st.session_state["editor_bulk_price_results"] = {
                "successful_updates": successful_updates,
                "failed_updates": failed_updates
            }
            
            # Auto-refresh to show updated prices
            st.rerun()
        
        # ---- Bulk: Update ALL Game Prices ----
        st.markdown("---")
        st.markdown("**⚠️ Bulk: Update ALL Game Prices**")
        st.warning("⚠️ **WARNING:** This will update prices for ALL games in your database. This operation will take a very long time and may hit rate limits.")
        
        # Show total games count
        try:
            resp = requests.get(f"{BACKEND_URL}/api/games")
            if resp.status_code == 200:
                all_games = resp.json()
                st.info(f"📋 **{len(all_games)} total games** would be processed")
                st.caption("⏱️ Estimated time: ~5-10 seconds per game")
        except Exception:
            st.warning("Could not get total games count")
        
        confirm_bulk_all_prices = st.checkbox(
            "⚠️ I understand this will take a very long time and want to update ALL game prices",
            key="editor_bulk_all_price_confirm",
        )
        
        # Enhanced bulk processing for ALL games
        if st.button("⚠️ Update ALL Game Prices", key="editor_bulk_all_price_button") and confirm_bulk_all_prices:
            # Get all games
            all_games = []
            try:
                resp = requests.get(f"{BACKEND_URL}/api/games")
                if resp.status_code == 200:
                    all_games = resp.json()
                    if not all_games:
                        st.warning("No games found in database!")
                        st.stop()
                    
                    st.info(f"🚀 Starting bulk price update for ALL {len(all_games)} games...")
                    st.warning("⏱️ This operation may take several hours. Please be patient and do not close this tab.")
            except Exception:
                st.error("Could not fetch games from database")
                st.stop()
            
            # Process games one by one to show current game being processed
            progress_bar = st.progress(0)
            current_game_status = st.empty()
            
            successful_updates = []
            failed_updates = []
            
            for i, game in enumerate(all_games):
                # Update current game display
                current_game_status.info(f"💰 **Processing:** {game.get('title', 'Unknown')} (ID: {game.get('id', 'N/A')}) • {i+1}/{len(all_games)}")
                
                # Update progress bar
                progress = (i + 1) / len(all_games)
                progress_bar.progress(progress)
                
                # Process this individual game
                try:
                    game_id = game.get('id')
                    if game_id:
                        result = update_game_price(game_id)
                        if result:
                            successful_updates.append(game)
                        else:
                            failed_updates.append(game)
                    else:
                        failed_updates.append(game)
                        
                    # Small delay to make progress visible and avoid rate limits
                    time.sleep(0.2)
                        
                except Exception as e:
                    failed_updates.append(game)
                    continue
            
            # Clear current game status and show final results
            current_game_status.empty()
            
            # Show completion stats
            st.success(f"✅ Bulk price update for ALL games completed!")
            
            # Show detailed results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Games Processed", len(all_games))
            with col2:
                st.metric("Successful Updates", len(successful_updates))
            with col3:
                st.metric("Errors", len(failed_updates))
            
            # Store results in session state to display outside expander
            st.session_state["editor_bulk_price_results"] = {
                "successful_updates": successful_updates,
                "failed_updates": failed_updates
            }
            
            # Auto-refresh to show updated prices
            st.rerun()

    # -------------------------
    # Sidebar: Update Game Artwork Section
    # -------------------------
    update_artwork_expander = st.sidebar.expander("Update Game Artwork")
    with update_artwork_expander:
        st.markdown("**Update artwork using SteamGridDB API**")
        st.info("Fetches high-resolution grid covers, heroes, logos, and icons")
        
        # Individual game artwork update
        st.markdown("**Single Game Artwork Update**")
        update_artwork_game_id = st.text_input("Game ID to Update Artwork", key="editor_update_artwork_game_id")
        
        # Show game information when ID is entered
        if update_artwork_game_id and update_artwork_game_id.isdigit():
            try:
                game_info = fetch_game_by_id(update_artwork_game_id)
                if game_info:
                    st.info(f"🎮 **{game_info.get('title', 'Unknown')}** (ID: {update_artwork_game_id})")
                    # Show current artwork status
                    has_grid = bool(game_info.get('high_res_cover_url'))
                    has_hero = bool(game_info.get('hero_image_url'))
                    has_logo = bool(game_info.get('logo_image_url'))
                    has_icon = bool(game_info.get('icon_image_url'))
                    
                    artwork_status = []
                    if has_grid: artwork_status.append("✅ Grid")
                    else: artwork_status.append("❌ Grid")
                    if has_hero: artwork_status.append("✅ Hero")
                    else: artwork_status.append("❌ Hero")
                    if has_logo: artwork_status.append("✅ Logo")
                    else: artwork_status.append("❌ Logo")
                    if has_icon: artwork_status.append("✅ Icon")
                    else: artwork_status.append("❌ Icon")
                    
                    st.caption(f"Current artwork: {' | '.join(artwork_status)}")
                else:
                    st.warning(f"⚠️ Game ID {update_artwork_game_id} not found")
            except Exception:
                st.warning(f"⚠️ Could not fetch game information for ID {update_artwork_game_id}")
        
        mode = st.selectbox(
            "Artwork update mode",
            options=["Automatic (SteamGridDB)", "Manual upload"],
            index=0,
            key="editor_artwork_update_mode",
        )

        if mode == "Automatic (SteamGridDB)":
            confirm_update_artwork = st.checkbox(
                "I confirm that I want to update this game's artwork",
                key="editor_update_artwork_confirm",
            )
            if st.button("Update Artwork", key="editor_update_artwork_button") and confirm_update_artwork:
                if update_artwork_game_id:
                    # Try to fetch game title for more informative spinner text
                    _title = None
                    try:
                        gd = fetch_game_by_id(update_artwork_game_id)
                        if isinstance(gd, dict):
                            _title = gd.get("title")
                    except Exception:
                        pass
                    _spinner_msg = f"Fetching artwork for '{_title}' (ID {update_artwork_game_id})..." if _title else "Fetching artwork from SteamGridDB..."
                    with st.spinner(_spinner_msg):
                        result = update_game_artwork(update_artwork_game_id)
                        if result and "error" not in result:
                            st.success("✅ Artwork updated successfully!")
                            st.write(f"**Game:** {result['game_title']}")
                            st.write(f"**Game ID:** {result['game_id']}")
                            # Refresh current view to show updated artwork without rerun
                            filters = {}
                            if st.session_state.get("filter_publisher"):
                                filters["publisher"] = st.session_state["filter_publisher"]
                            if st.session_state.get("filter_platform"):
                                filters["platform"] = st.session_state["filter_platform"]
                            if st.session_state.get("filter_genre"):
                                filters["genre"] = st.session_state["filter_genre"]
                            if st.session_state.get("filter_year"):
                                filters["year"] = st.session_state["filter_year"]
                            try:
                                _ = fetch_games(filters)
                            except Exception:
                                pass
                            st.session_state["refresh_artwork_stats"] = True
                        elif result and result.get("error") == "api_key_missing":
                            st.error("❌ SteamGridDB API key not configured")
                            st.info("To use this feature:")
                            st.write("1. Get an API key from https://www.steamgriddb.com/profile/preferences/api")
                            st.write("2. Add `steamgriddb_api_key` to your `config.json` file")
                            st.write("3. Restart the backend service")
                        elif result and result.get("error") == "no_artwork_found":
                            st.warning("⚠️ No artwork found for this game")
                            st.write(f"**Game:** {result['details']['game_title']}")
                            st.info("SteamGridDB may not have artwork for this specific game. Try manually adding artwork or check if the game name matches exactly.")
                        else:
                            st.error("Failed to update game artwork. Please check the Game ID and try again.")
        else:
            st.markdown("**Manually upload artwork** (grid/hero/logo/icon)")
            artwork_type = st.selectbox(
                "Artwork type",
                options=["grid", "hero", "logo", "icon"],
                index=0,
                key="editor_manual_art_type",
                help="Select which artwork slot to fill",
            )
            upload_file = st.file_uploader(
                "Choose an image file (png/jpg/jpeg/webp)",
                type=["png", "jpg", "jpeg", "webp"],
                key="editor_manual_art_file",
            )
            if st.button("Upload Artwork", key="editor_manual_art_upload"):
                if not update_artwork_game_id:
                    st.error("Please enter a Game ID")
                elif not upload_file:
                    st.error("Please choose an image file to upload")
                else:
                    with st.spinner("Uploading artwork..."):
                        files = {"file": (upload_file.name, upload_file.getvalue(), upload_file.type or "application/octet-stream")}
                        data = {"artwork_type": artwork_type}
                        resp = requests.post(
                            f"{BACKEND_URL}/upload_game_artwork/{update_artwork_game_id}",
                            files=files,
                            data=data,
                            timeout=30,
                        )
                        if resp.status_code == 200:
                            rj = resp.json()
                            st.success("✅ Artwork uploaded successfully!")
                            st.write(f"**Game ID:** {rj.get('game_id')}")
                            st.write(f"**Type:** {rj.get('artwork_type')}")
                            if rj.get("url"):
                                st.image(f"{BACKEND_URL}{rj['url']}", caption="Preview")
                        else:
                            try:
                                st.error(resp.json())
                            except Exception:
                                st.error(f"Upload failed: HTTP {resp.status_code}")

        # ---- Bulk: Update All Missing Artwork ----
        st.markdown("---")
        st.markdown("**Bulk: Update All Missing Artwork**")
        
        # Show games that would be processed
        try:
            resp = requests.get(f"{BACKEND_URL}/api/high_res_artwork/status")
            if resp.status_code == 200:
                stats = resp.json()
                if stats.get("success"):
                    missing_games = stats.get("games_without_artwork", [])
                    if missing_games:
                        st.info(f"📋 **{len(missing_games)} games** need artwork updates")
                        
                        # Show expandable list of games to be processed
                        with st.expander(f"View games missing artwork ({len(missing_games)})", expanded=False):
                            for i, game in enumerate(missing_games):
                                st.write(f"• **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
                    else:
                        st.success("✅ All games already have artwork!")
                        st.info("No games need artwork updates at this time.")
        except Exception:
            st.warning("Could not check artwork status")
        
        confirm_bulk_art = st.checkbox(
            "I confirm I want to update all games missing artwork",
            key="editor_bulk_art_confirm",
        )
        
        # Enhanced bulk processing with real-time current game display
        if st.button("Update All Missing Artwork", key="editor_bulk_art_button") and confirm_bulk_art:
            # Check if any games actually need updating
            missing_games = []
            try:
                resp = requests.get(f"{BACKEND_URL}/api/high_res_artwork/status")
                if resp.status_code == 200:
                    stats = resp.json()
                    if stats.get("success"):
                        missing_games = stats.get("games_without_artwork", [])
                        if not missing_games:
                            st.warning("No games need artwork updates. All games already have artwork!")
                            st.stop()
                        
                        st.info(f"🚀 Starting bulk artwork update for {len(missing_games)} games...")
            except Exception:
                st.error("Could not check which games need artwork updates")
                st.stop()
            
            # Process games one by one to show current game being processed
            progress_bar = st.progress(0)
            current_game_status = st.empty()
            
            successful_updates = []
            failed_updates = []
            
            for i, game in enumerate(missing_games):
                # Update current game display
                current_game_status.info(f"🎮 **Processing:** {game.get('title', 'Unknown')} (ID: {game.get('id', 'N/A')}) • {i+1}/{len(missing_games)}")
                
                # Update progress bar
                progress = (i + 1) / len(missing_games)
                progress_bar.progress(progress)
                
                # Process this individual game
                try:
                    game_id = game.get('id')
                    if game_id:
                        result = update_game_artwork(game_id)
                        if result and "error" not in result:
                            successful_updates.append(game)
                        else:
                            failed_updates.append(game)
                    else:
                        failed_updates.append(game)
                        
                    # Small delay to make progress visible
                    time.sleep(0.1)
                        
                except Exception as e:
                    failed_updates.append(game)
                    continue
            
            # Clear current game status and show final results
            current_game_status.empty()
            
            # Show completion stats
            st.success(f"✅ Bulk artwork update completed!")
            
            # Show detailed results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Games Processed", len(missing_games))
            with col2:
                st.metric("Successful Updates", len(successful_updates))
            with col3:
                st.metric("Errors", len(failed_updates))
            
            # Store results in session state to display outside expander
            st.session_state["editor_bulk_artwork_results"] = {
                "successful_updates": successful_updates,
                "failed_updates": failed_updates
            }
            st.session_state["refresh_artwork_stats"] = True
            
            # Auto-refresh to show updated artwork
            st.rerun()

    # The manual upload is now integrated above under the "Manual upload" checkbox.

    # -------------------------
    # Sidebar: Advanced Filters Section with Export, Bulk Delete, and Display of Filtered Games
    # -------------------------
    filter_expander = st.sidebar.expander("Advanced Filters")
    with filter_expander:
        publishers = sorted(fetch_unique_values("publisher"))
        platforms = sorted(fetch_unique_values("platform"))
        genres = sorted(fetch_unique_values("genre"))
        years = sorted(fetch_unique_values("year"))
        regions = ["JP", "PAL", "NTSC"]

        if st.button("Clear Filters", key="clear_filter_button"):
            st.session_state["filter_publisher"] = ""
            st.session_state["filter_platform"] = ""
            st.session_state["filter_genre"] = ""
            st.session_state["filter_year"] = ""
            st.session_state["filter_region"] = "All"
            # Reset price range to full range
            if "filter_price_range" in st.session_state:
                del st.session_state["filter_price_range"]
            st.session_state["filters_active"] = False
            # Don't re-fetch games here, let the filter logic handle it with pagination

        selected_publisher = st.selectbox("Publisher", [""] + publishers, key="filter_publisher")
        selected_platform = st.selectbox("Platform", [""] + platforms, key="filter_platform")
        selected_genre = st.selectbox("Genre", [""] + genres, key="filter_genre")
        selected_year = st.selectbox("Release Year", [""] + years, key="filter_year")
        selected_region = st.selectbox("Region", ["All"] + regions, key="filter_region")
        
        # Price range filter for editor
        try:
            all_editor_games_data = fetch_games(filters={})  # Get all games for accurate price range calculation
            if isinstance(all_editor_games_data, dict) and "games" in all_editor_games_data:
                all_editor_games = all_editor_games_data["games"]
            elif isinstance(all_editor_games_data, list):
                all_editor_games = all_editor_games_data
            else:
                all_editor_games = []
            
            if all_editor_games:
                games_with_prices = [g for g in all_editor_games if g.get("average_price") is not None and g.get("average_price") > 0]
                
                if games_with_prices:
                    prices = [float(g["average_price"]) for g in games_with_prices]
                    min_price, max_price = min(prices), max(prices)
                    
                    if min_price < max_price:
                        selected_price_range = st.slider(
                            "Price Range (£)",
                            min_value=float(min_price),
                            max_value=float(max_price),
                            value=(float(min_price), float(max_price)),
                            step=0.50,
                            format="£%.2f",
                            key="filter_price_range"
                        )
                    else:
                        st.info(f"Only price available: £{min_price:.2f}")
                        selected_price_range = None
                else:
                    selected_price_range = None
            else:
                selected_price_range = None
        except Exception:
            selected_price_range = None

        # Add checkboxes for sorting
        sort_alphabetical = st.checkbox("Sort Alphabetically", key="filter_sort_alphabetical")
        sort_highest_value = st.checkbox("Sort by Highest Value", key="filter_sort_highest_value")

        filters = {}
        if selected_publisher:
            filters["publisher"] = selected_publisher
        if selected_platform:
            filters["platform"] = selected_platform
        if selected_genre:
            filters["genre"] = selected_genre
        if selected_year:
            filters["year"] = selected_year
        if selected_region and selected_region != "All":
            filters["region"] = selected_region
        if selected_price_range:
            # Add price filtering to editor - always apply if selected_price_range is set
            try:
                filters["price_min"] = selected_price_range[0]
                filters["price_max"] = selected_price_range[1]
            except Exception:
                pass

        # Decide which sort to apply. If both are checked, highest takes precedence.
        if sort_highest_value:
            filters["sort"] = "highest"
        elif sort_alphabetical:
            filters["sort"] = "alphabetical"

        # Add pagination controls to Advanced Filters
        st.markdown("### Display Options")
        per_page = st.selectbox(
            "Games per page",
            [10, 20, 50, 100],
            index=1,  # Default to 20
            key="editor_per_page_select"
        )
        st.session_state["editor_per_page"] = per_page

        if st.button("Filter", key="filter_button"):
            st.session_state["filters_active"] = True
            st.session_state["editor_page"] = 1  # Reset to first page
            editor_data = fetch_games(filters, page=st.session_state["editor_page"], per_page=per_page)
        elif st.session_state["filters_active"]:
            editor_data = fetch_games(filters, page=st.session_state["editor_page"], per_page=per_page)
        else:
            editor_data = []

        # Handle both old format (list) and new format (dict with pagination)
        if isinstance(editor_data, dict) and "games" in editor_data:
            games = editor_data["games"]
            pagination_info = editor_data.get("pagination", {})
        else:
            games = editor_data if isinstance(editor_data, list) else []
            pagination_info = {}

        # --- EXPORT CSV BUTTON ---
        filter_params = {}
        if st.session_state.get("filter_publisher"):
            filter_params["publisher"] = st.session_state["filter_publisher"]
        if st.session_state.get("filter_platform"):
            filter_params["platform"] = st.session_state["filter_platform"]
        if st.session_state.get("filter_genre"):
            filter_params["genre"] = st.session_state["filter_genre"]
        if st.session_state.get("filter_year"):
            filter_params["year"] = st.session_state["filter_year"]

        query_string = "&".join([f"{k}={v}" for k, v in filter_params.items()])
        export_url = f"{BACKEND_URL}/export_csv"
        if query_string:
            export_url += "?" + query_string

        st.download_button(
            label="Export Filtered CSV",
            data=requests.get(export_url).text,
            file_name="games_export.csv",
            mime="text/csv"
        )

    # -------------------------
    # Display Editor Bulk Results (outside of expanders to avoid nesting)
    # -------------------------
    # Display bulk price results
    if "editor_bulk_price_results" in st.session_state:
        results = st.session_state["editor_bulk_price_results"]
        successful_updates = results.get("successful_updates", [])
        failed_updates = results.get("failed_updates", [])
        
        st.markdown("---")
        st.subheader("💰 Editor Bulk Price Update Results")
        
        # Show list of updated games
        if successful_updates:
            with st.expander(f"✅ Successfully updated ({len(successful_updates)})", expanded=False):
                for game in successful_updates:
                    st.write(f"✅ **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
        
        # Show list of failed games
        if failed_updates:
            with st.expander(f"❌ Failed updates ({len(failed_updates)})", expanded=False):
                for game in failed_updates:
                    st.write(f"❌ **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
        
        # Clear results after displaying
        if st.button("Clear Results", key="clear_editor_bulk_price_results"):
            del st.session_state["editor_bulk_price_results"]
            st.rerun()

    # Display bulk artwork results
    if "editor_bulk_artwork_results" in st.session_state:
        results = st.session_state["editor_bulk_artwork_results"]
        successful_updates = results.get("successful_updates", [])
        failed_updates = results.get("failed_updates", [])
        
        st.markdown("---")
        st.subheader("🎨 Editor Bulk Artwork Update Results")
        
        # Show list of updated games
        if successful_updates:
            with st.expander(f"✅ Successfully updated ({len(successful_updates)})", expanded=False):
                for game in successful_updates:
                    st.write(f"✅ **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
        
        # Show list of failed games
        if failed_updates:
            with st.expander(f"❌ Failed updates ({len(failed_updates)})", expanded=False):
                for game in failed_updates:
                    st.write(f"❌ **{game.get('title', 'Unknown')}** (ID: {game.get('id', 'N/A')})")
        
        # Clear results after displaying
        if st.button("Clear Results", key="clear_editor_bulk_artwork_results"):
            del st.session_state["editor_bulk_artwork_results"]
            st.rerun()

    # -------------------------
    # Display Filtered Games with Inline Bulk Delete
    # -------------------------
    if st.session_state["filters_active"]:
        total_cost = calculate_total_cost(games)
        st.markdown(
            f"<h3>Total Cost of Displayed Games: <strong style='color: red;'>£{float(total_cost):.2f}</strong></h3>",
            unsafe_allow_html=True
        )
        if games:
            if "editing_game_id" not in st.session_state:
                st.session_state.editing_game_id = None

            # Toggle Bulk Delete Mode: a row with two columns for the toggle and confirm button.
            col_toggle, col_confirm = st.columns([1, 1])
            with col_toggle:
                if st.button("Toggle Bulk Delete Mode", key="toggle_bulk_delete"):
                    st.session_state["bulk_delete_mode"] = not st.session_state.get("bulk_delete_mode", False)
            
            # Initialize an empty list to collect IDs for bulk deletion.
            selected_for_deletion = []

            # Display games.
            for game in games:
                if st.session_state.get("bulk_delete_mode", False):
                    # Condensed layout for bulk delete mode: checkbox to left and condensed info to right.
                    col_checkbox, col_info = st.columns([1, 4])
                    with col_checkbox:
                        if st.checkbox("", key=f"bulk_delete_{game['id']}"):
                            selected_for_deletion.append(game["id"])
                    with col_info:
                        cover_image_url = get_best_cover_image(game)
                        st.image(cover_image_url, width=100)
                        st.markdown(f"**{game.get('title', 'N/A')}**")
                else:
                    # Full display view if not in bulk delete mode.
                    display_game_item(game)

            # In bulk delete mode, display a count and confirm button in col_confirm.
            if st.session_state.get("bulk_delete_mode", False):
                with col_confirm:
                    count_selected = len(selected_for_deletion)
                    st.info(f"{count_selected} game{'s' if count_selected != 1 else ''} selected for deletion.")
                    if count_selected:
                        if st.button("Confirm Bulk Deletion", key="confirm_bulk_delete"):
                            for game_id in selected_for_deletion:
                                if delete_game(game_id):
                                    st.success(f"Deleted game with ID: {game_id}")
                                else:
                                    st.error(f"Failed to delete game with ID: {game_id}")
                            # Refresh the games list using the same filters:
                            games = fetch_games(filters)
                            st.session_state["bulk_delete_mode"] = False
                    else:
                        st.info("No games selected for deletion.")
        else:
            st.warning("No games found for the applied filters.")
        
        # Add pagination controls for filtered games
        if pagination_info and pagination_info.get("total_pages", 1) > 1:
            st.markdown("---")
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            
            with col_prev:
                if st.session_state["editor_page"] > 1:
                    if st.button("Previous", key="editor_prev"):
                        st.session_state["editor_page"] -= 1
                        st.rerun()
            
            with col_info:
                current_page = pagination_info.get("current_page", 1)
                total_pages = pagination_info.get("total_pages", 1)
                total_count = pagination_info.get("total_count", 0)
                st.markdown(f"**Page {current_page} of {total_pages}** ({total_count} games total)")
                
                # Page jump selector for small page counts
                if total_pages <= 10:
                    page_options = list(range(1, total_pages + 1))
                    selected_page = st.selectbox(
                        "Jump to page:",
                        page_options,
                        index=current_page - 1,
                        key="editor_page_jump"
                    )
                    if selected_page != st.session_state["editor_page"]:
                        st.session_state["editor_page"] = selected_page
                        st.rerun()
            
            with col_next:
                if pagination_info.get("has_next", False):
                    if st.button("Next", key="editor_next"):
                        st.session_state["editor_page"] += 1
                        st.rerun()

    export_expander = st.sidebar.expander("Export All Games")
    with export_expander:
        response = requests.get(f"{BACKEND_URL}/export_csv")
        if response.status_code == 200:
            csv_data = response.text
            st.download_button(
                label="Export CSV",
                data=csv_data,
                file_name="games_export.csv",
                mime="text/csv"
            )
        else:
            st.error("Failed to export CSV.")

        bulk_delete_expander = st.sidebar.expander("Bulk Delete Games")
        with bulk_delete_expander:
            # Fetch the list of games with pagination to avoid loading everything
            bulk_games_data = fetch_games(filters={}, page=1, per_page=100)  # Load first 100 for bulk delete selection
            if isinstance(bulk_games_data, dict) and "games" in bulk_games_data:
                all_games = bulk_games_data["games"]
            elif isinstance(bulk_games_data, list):
                all_games = bulk_games_data
            else:
                all_games = []

            # Build a dictionary mapping game titles to IDs.
            # Optionally, you can combine the title and ID in the display string.
            game_options = {f"{game['title']} (ID: {game['id']})": game["id"] for game in all_games}
            
            # Create a multiselect widget so the user can select multiple games.
            selected_titles = st.multiselect("Select games to delete:", list(game_options.keys()))
            
            if st.button("Delete Selected Games"):
                for title in selected_titles:
                    game_id = game_options[title]
                    if delete_game(game_id):
                        st.success(f"Deleted game: {title}")
                    else:
                        st.error(f"Failed to delete game: {title}")
                # Refresh the games list after deletion with pagination
                bulk_games_data = fetch_games(filters={}, page=1, per_page=100)
                if isinstance(bulk_games_data, dict) and "games" in bulk_games_data:
                    all_games = bulk_games_data["games"]
                elif isinstance(bulk_games_data, list):
                    all_games = bulk_games_data
                else:
                    all_games = []

    # -------------------------
    # Rest of the UI (Barcode scanning, local searches, etc.)
    # -------------------------
    st.markdown(f"[Install 'Scan Video Games' Shortcut]({ICLOUD_LINK})")
    st.markdown(f"[Install 'Scan Video Games' Shortcut Alternate]({ICLOUD_LINK_ALT})")

    st.markdown("## IGDB: Search Game by Name")
    game_name = st.text_input("Enter Game Name", key="game_name_input")

    if "search_results" not in st.session_state:
        st.session_state["search_results"] = None
    if "selected_game" not in st.session_state:
        st.session_state["selected_game"] = None

    if st.button("Search Game", key="search_game_button"):
        search_response = search_game_by_name(game_name)
        if search_response:
            # Check if the response contains an error
            if "error" in search_response:
                st.error(f"❌ {search_response['error']}")
                if search_response.get("details"):
                    st.info(f"**Details:** {search_response['details']}")
                if search_response.get("instructions"):
                    st.info(f"**Instructions:** {search_response['instructions']}")
                st.session_state["search_results"] = None
            else:
                st.session_state["search_results"] = search_response
        else:
            st.error("No game found with the provided name.")
            st.session_state["search_results"] = None

    if st.session_state["search_results"]:
        # Get the exact match and alternative matches list
        exact_match = st.session_state["search_results"].get("exact_match")
        alternative_matches = st.session_state["search_results"].get("alternative_matches", [])

        game_options = []
        game_map = {}

        # Add the exact match if available
        if exact_match:
            option_text = f"Exact Match: {exact_match['name']}"
            game_options.append(option_text)
            game_map[option_text] = exact_match

        # Add each alternative match
        for alt in alternative_matches:
            option_text = f"Alternative Match: {alt['name']}"
            game_options.append(option_text)
            game_map[option_text] = alt

        if game_options:
            selected_option = st.radio("Select a game to add:", game_options, key="selected_game_radio")
            if selected_option in game_map:
                st.session_state["selected_game"] = game_map[selected_option]
            else:
                st.error("Please select a valid game option.")
        else:
            st.error("No valid game options available.")

        selected_game_data = st.session_state.get("selected_game")
        if selected_game_data:
            st.markdown("### Game Details")
            st.markdown(f"**Title:** {selected_game_data['name']}")
            st.markdown(f"**Description:** {selected_game_data.get('summary', 'N/A')}")
            st.markdown(f"**Cover URL:** {selected_game_data.get('cover_url', 'N/A')}")
            publishers = selected_game_data.get("involved_companies", [])
            if publishers and all(isinstance(p, str) for p in publishers):
                publisher_text = ", ".join(publishers)
            elif publishers and all(isinstance(p, dict) and "company" in p and "name" in p["company"] for p in publishers):
                publisher_text = ", ".join([p["company"]["name"] for p in publishers])
            else:
                publisher_text = "N/A"
            st.markdown(f"**Publisher:** {publisher_text}")

            # Platform selection
            platforms = selected_game_data.get("platforms", [])
            if platforms and all(isinstance(p, str) for p in platforms):
                platform_options = platforms
            elif platforms and all(isinstance(p, dict) and "name" in p for p in platforms):
                platform_options = [p["name"] for p in platforms]
            else:
                platform_options = []

            if platform_options:
                selected_platform = st.selectbox("Select Platform:", platform_options, key="platform_select")
                st.markdown(f"**Selected Platform:** {selected_platform}")
            else:
                selected_platform = None
                st.markdown("**Platforms:** N/A")

            genres = selected_game_data.get("genres", [])
            if genres and all(isinstance(g, str) for g in genres):
                genre_text = ", ".join(genres)
            elif genres and all(isinstance(g, dict) and "name" in g for g in genres):
                genre_text = ", ".join([g["name"] for g in genres])
            else:
                genre_text = "N/A"
            st.markdown(f"**Genres:** {genre_text}")

            release_date_timestamp = selected_game_data.get("release_date")
            if isinstance(release_date_timestamp, int):
                release_date = time.strftime("%Y-%m-%d", time.gmtime(release_date_timestamp))
            else:
                release_date = "N/A"
            st.markdown(f"**Release Date:** {release_date}")
            
            # Region selection for the game to be added
            region_options = ["PAL", "NTSC", "JP"]
            default_region = st.session_state.get("pricecharting_region", "PAL")
            if default_region not in region_options:
                default_region = "PAL"
            selected_region_for_add = st.selectbox("Region", region_options, index=region_options.index(default_region), key="add_region_select")
        else:
            st.error("No game selected.")

        # Now, when the user clicks "Add Selected Game", build the search query and scrape the price from eBay.
        if st.button("Add Selected Game", key="add_selected_game_button"):
            if selected_game_data:
                # Build the search query by combining the game name and the selected platform.
                search_query = selected_game_data["name"]
                if selected_platform:
                    search_query += " " + selected_platform

                # Call the selected price scraper using the combined query.
                if global_price_source == "eBay":
                    scraped_price = scrape_ebay_prices(search_query)
                elif global_price_source == "Amazon":
                    scraped_price = scrape_amazon_price(search_query)
                elif global_price_source == "PriceCharting":
                    # Get the selected region and boxed preference for PriceCharting
                    selected_region = st.session_state.get("pricecharting_region", "PAL")
                    prefer_boxed = st.session_state.get("pricecharting_boxed", True)
                    pricecharting_data = scrape_pricecharting_price(search_query, selected_platform, selected_region)
                    # Use condition-aware pricing based on user preference
                    scraped_price = get_pricecharting_price_by_condition(pricecharting_data, prefer_boxed)
                    
                    if pricecharting_data:
                        # Show pricing breakdown in UI with selected condition highlighted
                        condition_text = "Boxed (CiB)" if prefer_boxed else "Loose"
                        st.markdown(f"**Selected Condition:** {condition_text}")
                        
                        if pricecharting_data.get('loose_price'):
                            marker = " ← **SELECTED**" if not prefer_boxed and scraped_price == pricecharting_data['loose_price'] else ""
                            st.markdown(f"**PriceCharting Loose Price:** £{pricecharting_data['loose_price']:.2f}{marker}")
                        if pricecharting_data.get('cib_price'):
                            marker = " ← **SELECTED**" if prefer_boxed and scraped_price == pricecharting_data['cib_price'] else ""
                            st.markdown(f"**PriceCharting CIB Price:** £{pricecharting_data['cib_price']:.2f}{marker}")
                        if pricecharting_data.get('new_price'):
                            marker = " ← **SELECTED**" if scraped_price == pricecharting_data['new_price'] else ""
                            st.markdown(f"**PriceCharting New Price:** £{pricecharting_data['new_price']:.2f}{marker}")
                else:  # CeX
                    scraped_price = scrape_cex_price(search_query)
                
                if scraped_price is not None:
                    st.markdown(f"**Scraped Price from {global_price_source} (to add):** £{scraped_price:.2f}")
                else:
                    st.markdown(f"**Scraped Price from {global_price_source} (to add):** N/A")

                game_data = {
                    "title": selected_game_data["name"],
                    "cover_image": selected_game_data.get("cover_url"),
                    "description": selected_game_data.get("summary"),
                    "publisher": selected_game_data.get("involved_companies", []),
                    "platforms": [selected_platform] if selected_platform else selected_game_data.get("platforms", []),
                    "genres": selected_game_data.get("genres", []),
                    "franchise": selected_game_data.get("franchises", []),
                    "series": selected_game_data.get("series", []),
                    "release_date": None,
                    "average_price": scraped_price,
                    "region": selected_region_for_add,
                }
                if selected_game_data.get("release_date"):
                    game_data["release_date"] = time.strftime("%Y-%m-%d", time.gmtime(selected_game_data["release_date"]))
                if add_game(game_data):
                    st.success(f"{selected_game_data['name']} added successfully!")
                else:
                    st.error("Failed to add game.")

    st.markdown("## IGDB: Search Game by ID")
    igdb_id = st.text_input("Enter IGDB ID", key="igdb_id_input")

    if st.button("IGDB: Search Game by ID", key="search_game_by_id_button"):
        search_response = search_game_by_id(igdb_id)
        if search_response:
            # Check if the response contains an error
            if "error" in search_response:
                st.error(f"❌ {search_response['error']}")
                if search_response.get("details"):
                    st.info(f"**Details:** {search_response['details']}")
                if search_response.get("instructions"):
                    st.info(f"**Instructions:** {search_response['instructions']}")
                st.session_state["selected_game_by_id"] = None
            else:
                st.session_state["selected_game_by_id"] = search_response
        else:
            st.error("No game found with the provided IGDB ID.")
            st.session_state["selected_game_by_id"] = None

    if "selected_game_by_id" in st.session_state and st.session_state["selected_game_by_id"]:
        selected_game_data_by_id = st.session_state["selected_game_by_id"]
        st.markdown("### Game Details (By ID)")
        st.markdown(f"**Title:** {selected_game_data_by_id.get('name', 'N/A')}")
        st.markdown(f"**Description:** {selected_game_data_by_id.get('summary', 'N/A')}")
        cover_url = selected_game_data_by_id.get("cover", {}).get("url", "N/A")
        st.markdown(f"**Cover URL:** {cover_url}")

        publishers = []
        if isinstance(selected_game_data_by_id.get("involved_companies"), list):
            for company in selected_game_data_by_id.get("involved_companies", []):
                if isinstance(company, dict) and "company" in company:
                    company_info = company["company"]
                    if isinstance(company_info, dict) and "name" in company_info:
                        publishers.append(company_info["name"])
        st.markdown(f"**Publisher:** {', '.join(publishers) if publishers else 'N/A'}")

        # Platform select box for IGDB ID results.
        platforms = []
        if isinstance(selected_game_data_by_id.get("platforms"), list):
            for platform in selected_game_data_by_id.get("platforms", []):
                if isinstance(platform, dict) and "name" in platform:
                    platforms.append(platform["name"])
        if platforms:
            selected_platform_by_id = st.selectbox("Select Platform:", platforms, key="platform_select_by_id")
            st.markdown(f"**Selected Platform:** {selected_platform_by_id}")
        else:
            selected_platform_by_id = None
            st.markdown("**Platforms:** N/A")

        genres = []
        if isinstance(selected_game_data_by_id.get("genres"), list):
            for genre in selected_game_data_by_id["genres"]:
                if isinstance(genre, dict) and "name" in genre:
                    genres.append(genre["name"])
                elif isinstance(genre, str):
                    genres.append(genre)
        st.markdown(f"**Genres:** {', '.join(genres) if genres else 'N/A'}")

        series = []
        if isinstance(selected_game_data_by_id.get("franchises"), list):
            for franchise in selected_game_data_by_id.get("franchises", []):
                if isinstance(franchise, dict) and "name" in franchise:
                    series.append(franchise["name"])
        st.markdown(f"**Series:** {', '.join(series) if series else 'N/A'}")

        release_date = "N/A"
        if isinstance(selected_game_data_by_id.get("first_release_date"), (int, float)):
            release_date = time.strftime("%Y-%m-%d", time.gmtime(selected_game_data_by_id["first_release_date"]))
        st.markdown(f"**Release Date:** {release_date}")

        # On "Add Game by ID", call the selected price scraper with the combined query.
        if st.button("Add Game by ID", key="add_game_by_id_button"):
            search_query = selected_game_data_by_id.get("name", "")
            if selected_platform_by_id:
                search_query += " " + selected_platform_by_id
            
            # Call the selected price scraper using the combined query.
            if global_price_source == "eBay":
                scraped_price = scrape_ebay_prices(search_query)
            elif global_price_source == "Amazon":
                scraped_price = scrape_amazon_price(search_query)
            elif global_price_source == "PriceCharting":
                # Get the selected region and boxed preference for PriceCharting
                selected_region = st.session_state.get("pricecharting_region", "PAL")
                prefer_boxed = st.session_state.get("pricecharting_boxed", True)
                pricecharting_data = scrape_pricecharting_price(search_query, selected_platform_by_id, selected_region)
                # Use condition-aware pricing based on user preference
                scraped_price = get_pricecharting_price_by_condition(pricecharting_data, prefer_boxed)
                
                if pricecharting_data:
                    # Show pricing breakdown in UI with selected condition highlighted
                    condition_text = "Boxed (CiB)" if prefer_boxed else "Loose"
                    st.markdown(f"**Selected Condition:** {condition_text}")
                    
                    if pricecharting_data.get('loose_price'):
                        marker = " ← **SELECTED**" if not prefer_boxed and scraped_price == pricecharting_data['loose_price'] else ""
                        st.markdown(f"**PriceCharting Loose Price:** £{pricecharting_data['loose_price']:.2f}{marker}")
                    if pricecharting_data.get('cib_price'):
                        marker = " ← **SELECTED**" if prefer_boxed and scraped_price == pricecharting_data['cib_price'] else ""
                        st.markdown(f"**PriceCharting CIB Price:** £{pricecharting_data['cib_price']:.2f}{marker}")
                    if pricecharting_data.get('new_price'):
                        marker = " ← **SELECTED**" if scraped_price == pricecharting_data['new_price'] else ""
                        st.markdown(f"**PriceCharting New Price:** £{pricecharting_data['new_price']:.2f}{marker}")
            else:  # CeX
                scraped_price = scrape_cex_price(search_query)
                
            if scraped_price is not None:
                st.markdown(f"**Scraped Price from {global_price_source} (to add):** £{scraped_price:.2f}")
            else:
                st.markdown(f"**Scraped Price from {global_price_source} (to add):** N/A")
            # Region for add-by-id: mirror the sidebar PriceCharting region selection
            selected_region_for_add_by_id = st.session_state.get("pricecharting_region", "PAL")
            game_data = {
                "title": selected_game_data_by_id["name"],
                "cover_image": selected_game_data_by_id.get("cover", {}).get("url"),
                "description": selected_game_data_by_id.get("summary"),
                "publisher": [
                    company["company"]["name"]
                    for company in selected_game_data_by_id.get("involved_companies", [])
                    if "company" in company and "name" in company["company"]
                ],
                "platforms": [selected_platform_by_id] if selected_platform_by_id else [
                    platform["name"]
                    for platform in selected_game_data_by_id.get("platforms", [])
                    if "name" in platform
                ],
                "genres": [
                    genre["name"]
                    for genre in selected_game_data_by_id.get("genres", [])
                    if isinstance(genre, dict) and "name" in genre
                ],
                "series": [
                    franchise["name"]
                    for franchise in selected_game_data_by_id.get("franchises", [])
                    if "name" in franchise
                ],
                "release_date": None,
                "average_price": scraped_price,
                "region": selected_region_for_add_by_id,
            }
            if selected_game_data_by_id.get("first_release_date"):
                game_data["release_date"] = time.strftime("%Y-%m-%d", time.gmtime(selected_game_data_by_id["first_release_date"]))
            if add_game(game_data):
                st.success(f"{selected_game_data_by_id['name']} added successfully!")
            else:
                st.error("Failed to add game.")

    # -------------------------
    # Overall Totals and Top Games (if no filters are active)
    # -------------------------
    # Get total value from ALL games (no pagination for total calculation)
    all_games_data = fetch_games(filters={})  # No pagination - get all games for accurate total
    if isinstance(all_games_data, dict) and "games" in all_games_data:
        all_games = all_games_data["games"]
    elif isinstance(all_games_data, list):
        all_games = all_games_data
    else:
        all_games = []
        
    overall_total_value = calculate_total_cost(all_games)
    st.markdown(
        f"<h3>Total Value of All Scanned Games: <span style='color: red;'>£{overall_total_value:.2f}</span></h3>",
        unsafe_allow_html=True
    )

    if not st.session_state["filters_active"]:
        st.markdown("## Top 5 Games by Average Price")
        top_games = fetch_top_games()
        if top_games:  # Only display if we have games
            for game in top_games:
                cover_image_url = get_best_cover_image(game)
                price_value = game.get("average_price")
                if price_value is not None:
                    try:
                        average_price = f"£{float(price_value):.2f}"
                    except (ValueError, TypeError):
                        average_price = "N/A"
                else:
                    average_price = "N/A"
                st.markdown(
                    f"""
                    <div class="game-container">
                        <img src="{html.escape(str(cover_image_url))}" class="game-image">
                        <div class="game-details">
                            <div><strong>ID:</strong> {html.escape(str(game['id']))}</div>
                            <div><strong>Title:</strong> {html.escape(str(game['title']))}</div>
                            <div><strong>Description:</strong> {html.escape(str(game['description']))}</div>
                            <div><strong>Publisher:</strong> {html.escape(str(game['publisher']))}</div>
                            <div><strong>Platforms:</strong> {html.escape(str(game['platforms']))}</div>
                            <div><strong>Genres:</strong> {html.escape(str(game['genres']))}</div>
                            <div><strong>Series:</strong> {html.escape(str(game['series']))}</div>
                            <div><strong>Release Date:</strong> {html.escape(str(game['release_date']))}</div>
                            <div><strong>Region:</strong> {html.escape(str(backend_to_frontend_region(game.get('region', 'N/A'))))}</div>
                            <div><strong>Average Price:</strong> {html.escape(str(average_price))}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No games with prices found yet. Add some games to see the top 5!")
        




if __name__ == "__main__":
    main()
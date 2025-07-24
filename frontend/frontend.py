import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import os, sys

# Configure Streamlit page - MUST be the very first Streamlit command!
st.set_page_config(
    page_title="Video Game Catalogue",
    page_icon="🎮"
)

# Calculate the project root as the parent directory of the frontend folder.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print("Project root added to sys.path:", PROJECT_ROOT)


from modules.scrapers import scrape_ebay_prices, scrape_amazon_price, scrape_barcode_lookup, scrape_cex_price

# Retrieve the backend host from environment variables, default to 'localhost' if using Python locally
backend_host = os.getenv("BACKEND_HOST", "localhost")
backend_port = 5001  # Assuming the backend is running on this port

# Backend API base URL
BACKEND_URL = f"http://{backend_host}:{backend_port}"
print(f"Connecting to backend at {BACKEND_URL}")  # Debugging output

# iCloud shortcut link (replace with actual link as needed)
ICLOUD_LINK = "https://www.icloud.com/shortcuts/024bf54a6f584cc78c3ed394bcda8e84"
ICLOUD_LINK_ALT = "https://www.icloud.com/shortcuts/bea9f60437194f0fad2f89b87c9d1fff"

# -------------------------
# Backend API Helper Functions
# -------------------------

def fetch_games(filters=None):
    response = requests.get(f"{BACKEND_URL}/games", params=filters)
    return response.json()

def fetch_consoles():
    response = requests.get(f"{BACKEND_URL}/consoles")
    return response.json()

def fetch_unique_values(value_type):
    response = requests.get(f"{BACKEND_URL}/unique_values", params={"type": value_type})
    return response.json()

def calculate_total_cost(games):
    return sum(
        game.get("average_price", 0)
        for game in games
        if game.get("average_price") is not None
    )

def add_game(game_data):
    response = requests.post(f"{BACKEND_URL}/add_game", json=game_data)
    return response.status_code == 201

def delete_game(game_id):
    response = requests.post(f"{BACKEND_URL}/delete_game", json={"id": int(game_id)})
    return response.status_code == 200

def update_game(game_id, game_data):
    response = requests.put(f"{BACKEND_URL}/update_game/{game_id}", json=game_data)
    return response.status_code == 200

def search_game_by_name(game_name):
    response = requests.post(f"{BACKEND_URL}/search_game_by_name", json={"game_name": game_name})
    if response.status_code == 200:
        return response.json()
    else:
        return None

def search_game_by_id(igdb_id):
    response = requests.post(f"{BACKEND_URL}/search_game_by_id", json={"igdb_id": igdb_id})
    if response.status_code == 200:
        return response.json()
    else:
        return None

def fetch_top_games():
    response = requests.get(f"{BACKEND_URL}/top_games")
    return response.json()

def fetch_game_by_id(game_id):
    response = requests.get(f"{BACKEND_URL}/game/{game_id}")
    if response.status_code == 200:
        return response.json()
    else:
        return None

def scan_game(barcode):
    response = requests.post(f"{BACKEND_URL}/scan", json={"barcode": barcode})
    return response.json()

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
            # Prepare cover image URL
            cover_image_url = (
                f"https:{game.get('cover_image', '')}"
                if game.get("cover_image") and game.get("cover_image", "").startswith("//")
                else game.get("cover_image", "https://via.placeholder.com/150")
            )
            # Format the average price display
            average_price = (
                f"£{game.get('average_price', 0):.2f}"
                if game.get("average_price") is not None
                else "N/A"
            )
            # Display game details using HTML formatting
            st.markdown(
                f"""
                <div class="game-container">
                    <img src="{cover_image_url}" class="game-image">
                    <div class="game-details">
                        <div><strong>ID:</strong> {game.get('id', 'N/A')}</div>
                        <div><strong>Title:</strong> {game.get('title', 'N/A')}</div>
                        <div><strong>Description:</strong> {game.get('description', 'N/A')}</div>
                        <div><strong>Publisher:</strong> {game.get('publisher', 'N/A')}</div>
                        <div><strong>Platforms:</strong> {game.get('platforms', 'N/A')}</div>
                        <div><strong>Genres:</strong> {game.get('genres', 'N/A')}</div>
                        <div><strong>Series:</strong> {game.get('series', 'N/A')}</div>
                        <div><strong>Release Date:</strong> {game.get('release_date', 'N/A')}</div>
                        <div><strong>Average Price:</strong> {average_price}</div>
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

    # Inline edit form (only shown if this game is marked for editing)
    if st.session_state.get("editing_game_id") == game.get("id"):
        st.markdown("#### Edit Game")
        new_title = st.text_input("Title", game.get("title"), key=f"edit_title_{game.get('id')}")
        new_desc = st.text_area("Description", game.get("description"), key=f"edit_desc_{game.get('id')}")
        new_cover = st.text_input("Cover Image URL", game.get("cover_image"), key=f"edit_cover_{game.get('id')}")
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
        new_price = st.number_input("Average Price", value=game.get("average_price") or 0.0, step=0.01, format="%.2f", key=f"edit_price_{game.get('id')}")
        
        if st.button("Save", key=f"save_{game.get('id')}"):
            updated_game_data = {
                "title": new_title,
                "cover_image": new_cover,
                "description": new_desc,
                "publisher": [new_pub],
                "platforms": new_platforms_list,
                "genres": new_genres_list,
                "series": [new_series],
                "release_date": new_release,
                "average_price": new_price,
            }
            if update_game(game.get("id"), updated_game_data):
                st.success("Game updated successfully!")
                st.session_state.editing_game_id = None  # Exit edit mode
            else:
                st.error("Failed to update game")

# -------------------------
# Main Application Function
# -------------------------
def main():
    st.title("Video Game Catalogue")

    if "bulk_delete_mode" not in st.session_state:
        st.session_state["bulk_delete_mode"] = False

    # Initialize session state for filter mode
    if "filters_active" not in st.session_state:
        st.session_state["filters_active"] = False

    # -------------------------
    # Sidebar: Home Button
    # -------------------------
    home_clicked = st.sidebar.button("🏠 Home", type="primary", use_container_width=True)
    if home_clicked:
        # Preserve the price source selection
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
    # Sidebar: Music Player Section
    # -------------------------
    music_expander = st.sidebar.expander("🎵 Video Game Music Player")
    with music_expander:
        st.markdown("### 🎮 VIPVGM - Video Game Music")
        st.markdown("*Listen to video game music while browsing your collection!*")
        
        # Create a container for the iframe with a simpler approach
        iframe_html = """
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; padding: 15px; margin: 10px 0;">
            <iframe 
                src="https://www.vipvgm.net/" 
                width="100%" 
                height="400" 
                frameborder="0" 
                scrolling="yes"
                allow="autoplay; encrypted-media; fullscreen"
                title="VIPVGM Video Game Music Player"
                style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"
            ></iframe>
        </div>
        """
        
        # Try to embed the iframe
        try:
            components.html(iframe_html, height=450)
        except Exception as e:
            st.warning("Iframe embedding not working. Click the button below to open VIPVGM in a new tab.")
            if st.button("🎵 Open VIPVGM Music Player", type="primary", key="music_player_fallback"):
                st.link_button("🎵 Open VIPVGM Music Player", "https://www.vipvgm.net/")

    # -------------------------
    # Global Price Source Selector
    # -------------------------
    st.sidebar.markdown("### 💰 Price Scraping Settings")
    
    # Get the current price source from URL parameters or session state
    price_options = ["eBay", "Amazon", "CeX"]
    
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
    
    # Update both session state and URL parameters when selection changes
    if global_price_source != st.session_state.get("price_source_selection"):
        st.session_state["price_source_selection"] = global_price_source
        st.query_params["price_source"] = global_price_source

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
            f"<h3>Total Cost of Search Results: <strong style='color: red;'>£{total_cost:.2f}</strong></h3>",
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
        cover_image = st.text_input("Cover Image URL", key="add_cover_image")
        description = st.text_area("Description", key="add_description")
        publisher = st.text_input("Publisher", key="add_publisher")

        raw_platforms = st.text_input("Platforms (comma separated)", key="add_platforms")
        platforms_list = [p.strip() for p in raw_platforms.split(",") if p.strip()]

        raw_genres = st.text_input("Genres (comma separated)", key="add_genres")
        genres_list = [g.strip() for g in raw_genres.split(",") if g.strip()]

        series = st.text_input("Series", key="add_series")
        release_date = st.date_input("Release Date", key="add_release_date")

        if st.button("Add Game", key="add_game_button"):
            game_data = {
                "title": title,
                "cover_image": cover_image,
                "description": description,
                "publisher": [publisher],
                "platforms": platforms_list,
                "genres": genres_list,
                "series": [series],
                "release_date": (
                    release_date.strftime("%Y-%m-%d") if release_date else "1900-01-01"
                ),
                "average_price": None,
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
            edit_cover_image = st.text_input("Cover Image URL", game_details["cover_image"], key="edit_cover_image")
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
            edit_series_input = st.text_input("Series", edit_series_str, key="edit_series")
            new_series_list = [s.strip() for s in edit_series_input.split(",") if s.strip()]

            edit_release_date = st.date_input("Release Date", key="edit_release_date")
            default_price = float(game_details.get("average_price") or 0)
            edit_average_price = st.number_input("Average Price", value=default_price, step=0.01, format="%.2f", key="edit_average_price")

            if st.button("Update Game", key="update_game_button"):
                updated_game_data = {
                    "title": edit_title,
                    "cover_image": edit_cover_image,
                    "description": edit_description,
                    "publisher": new_pub_list,
                    "platforms": new_platforms_list,
                    "genres": new_genres_list,
                    "series": new_series_list,
                    "release_date": (
                        edit_release_date.strftime("%Y-%m-%d") if edit_release_date else "1900-01-01"
                    ),
                    "average_price": edit_average_price,
                }
                if update_game(edit_game_id, updated_game_data):
                    st.success("Game updated successfully")
                else:
                    st.error("Failed to update game")

    # -------------------------
    # Sidebar: Advanced Filters Section with Export, Bulk Delete, and Display of Filtered Games
    # -------------------------
    filter_expander = st.sidebar.expander("Advanced Filters")
    with filter_expander:
        publishers = sorted(fetch_unique_values("publisher"))
        platforms = sorted(fetch_unique_values("platform"))
        genres = sorted(fetch_unique_values("genre"))
        years = sorted(fetch_unique_values("year"))

        if st.button("Clear Filters", key="clear_filter_button"):
            st.session_state["filter_publisher"] = ""
            st.session_state["filter_platform"] = ""
            st.session_state["filter_genre"] = ""
            st.session_state["filter_year"] = ""
            st.session_state["filters_active"] = False
            games = fetch_games()  # Re-fetch all games

        selected_publisher = st.selectbox("Publisher", [""] + publishers, key="filter_publisher")
        selected_platform = st.selectbox("Platform", [""] + platforms, key="filter_platform")
        selected_genre = st.selectbox("Genre", [""] + genres, key="filter_genre")
        selected_year = st.selectbox("Release Year", [""] + years, key="filter_year")

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

        # Decide which sort to apply. If both are checked, highest takes precedence.
        if sort_highest_value:
            filters["sort"] = "highest"
        elif sort_alphabetical:
            filters["sort"] = "alphabetical"

        if st.button("Filter", key="filter_button"):
            st.session_state["filters_active"] = True
            games = fetch_games(filters)
        elif st.session_state["filters_active"]:
            games = fetch_games(filters)
        else:
            games = []

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
    # Display Filtered Games with Inline Bulk Delete
    # -------------------------
    if st.session_state["filters_active"]:
        total_cost = calculate_total_cost(games)
        st.markdown(
            f"<h3>Total Cost of Displayed Games: <strong style='color: red;'>£{total_cost:.2f}</strong></h3>",
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
                        cover_image_url = (
                            f"https:{game.get('cover_image', '')}"
                            if game.get("cover_image") and game.get("cover_image", "").startswith("//")
                            else game.get("cover_image", "https://via.placeholder.com/100")
                        )
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
            # Fetch the list of games that are currently displayed
            # (You could use fetch_games() to get all games or the currently filtered games)
            all_games = fetch_games()  # or use your current filtered list if desired

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
                # Optionally, refresh the games list after deletion:
                # e.g., st.session_state["filters_active"] = False or update the games variable
                all_games = fetch_games()

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
            else:  # CeX
                scraped_price = scrape_cex_price(search_query)
                
            if scraped_price is not None:
                st.markdown(f"**Scraped Price from {global_price_source} (to add):** £{scraped_price:.2f}")
            else:
                st.markdown(f"**Scraped Price from {global_price_source} (to add):** N/A")
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
    all_games = fetch_games()
    overall_total_value = calculate_total_cost(all_games)
    st.markdown(
        f"<h3>Total Value of All Scanned Games: <span style='color: red;'>£{overall_total_value:.2f}</span></h3>",
        unsafe_allow_html=True
    )

    if not st.session_state["filters_active"]:
        st.markdown("## Top 5 Games by Average Price")
        top_games = fetch_top_games()
        for game in top_games:
            cover_image_url = (
                f"https:{game['cover_image']}"
                if game.get("cover_image") and game["cover_image"].startswith("//")
                else game.get("cover_image")
            )
            average_price = (
                f"£{game['average_price']:.2f}"
                if game.get("average_price") is not None
                else "N/A"
            )
            st.markdown(
                f"""
                <div class="game-container">
                    <img src="{cover_image_url}" class="game-image">
                    <div class="game-details">
                        <div><strong>ID:</strong> {game['id']}</div>
                        <div><strong>Title:</strong> {game['title']}</div>
                        <div><strong>Description:</strong> {game['description']}</div>
                        <div><strong>Publisher:</strong> {game['publisher']}</div>
                        <div><strong>Platforms:</strong> {game['platforms']}</div>
                        <div><strong>Genres:</strong> {game['genres']}</div>
                        <div><strong>Series:</strong> {game['series']}</div>
                        <div><strong>Release Date:</strong> {game['release_date']}</div>
                        <div><strong>Average Price:</strong> {average_price}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            

if __name__ == "__main__":
    main()
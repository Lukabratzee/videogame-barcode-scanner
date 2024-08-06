import streamlit as st
import requests
import time
import os

# Retrieve the backend host from environment variables, default to 'localhost' if not set
backend_host = os.getenv('BACKEND_HOST', 'backend')
backend_port = 5001  # Assuming the backend is running on this port

# Backend API base URL
BACKEND_URL = f"http://{backend_host}:{backend_port}"
print(f"Connecting to backend at {BACKEND_URL}")  # Debugging output

# Assuming the iCloud link to the shortcut is provided
ICLOUD_LINK = "https://www.icloud.com/shortcuts/dcfe6771a20a4613b182cd4ca4d22d9d"  # Replace with actual iCloud link

# Function to fetch games from the backend, optionally using filters
def fetch_games(filters=None):
    response = requests.get(f"{BACKEND_URL}/games", params=filters)
    return response.json()

# Function to fetch available consoles from the backend
def fetch_consoles():
    response = requests.get(f"{BACKEND_URL}/consoles")
    return response.json()

# Function to fetch unique values for a given type (e.g., publisher, platform)
def fetch_unique_values(value_type):
    response = requests.get(f"{BACKEND_URL}/unique_values", params={"type": value_type})
    return response.json()

# Function to calculate the total cost of displayed games
def calculate_total_cost(games):
    return sum(game.get("average_price", 0) for game in games if game.get("average_price") is not None)

# Function to add a new game to the backend
def add_game(game_data):
    response = requests.post(f"{BACKEND_URL}/add_game", json=game_data)
    return response.status_code == 201

# Function to delete a game by ID from the backend
def delete_game(game_id):
    response = requests.post(
        f"{BACKEND_URL}/delete_game", json={"id": int(game_id)}
    )  # Ensure game_id is an integer
    return response.status_code == 200

# Function to update an existing game in the backend
def update_game(game_id, game_data):
    response = requests.put(f"{BACKEND_URL}/update_game/{game_id}", json=game_data)
    return response.status_code == 200

# Function to search for games by name using the backend
def search_game_by_name(game_name):
    response = requests.post(f"{BACKEND_URL}/search_game_by_name", json={"game_name": game_name})
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Function to fetch game details by ID from the backend
def fetch_game_by_id(game_id):
    response = requests.get(f"{BACKEND_URL}/game/{game_id}")
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Function to scan a game by barcode
def scan_game(barcode):
    response = requests.post(f"{BACKEND_URL}/scan", json={"barcode": barcode})
    return response.json()

# CSS styling for better layout
st.markdown(
    """
    <style>
    .game-container {
        display: flex;
        align-items: flex-start;  /* Align items to the top */
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
    </style>
""",
    unsafe_allow_html=True,
)

# Main function to run the Streamlit app
def main():
    st.title("Video Game Catalogue")

    # Sidebar for filtering and managing games
    st.sidebar.title("Filter Games")
    search_term = st.sidebar.text_input("Search by Title", key="search_title")

    # Section to add a new game
    add_expander = st.sidebar.expander("Add Game")
    with add_expander:
        title = st.text_input("Title", key="add_title")
        cover_image = st.text_input("Cover Image URL", key="add_cover_image")
        description = st.text_area("Description", key="add_description")
        publisher = st.text_input("Publisher", key="add_publisher")
        platforms = st.text_input("Platforms (comma separated)", key="add_platforms")
        genres = st.text_input("Genres (comma separated)", key="add_genres")
        series = st.text_input("Series", key="add_series")
        release_date = st.date_input("Release Date", key="add_release_date")

        if st.button("Add Game", key="add_game_button"):
            game_data = {
                "title": title,
                "cover_image": cover_image,
                "description": description,
                "publisher": [publisher],
                "platforms": platforms.split(", "),
                "genres": genres.split(", "),
                "series": [series],
                "release_date": release_date.strftime("%Y-%m-%d"),
                "average_price": None,  # Add a field for average price if needed
            }
            if add_game(game_data):
                st.success("Game added successfully")

    # Section to delete an existing game
    delete_expander = st.sidebar.expander("Delete Game")
    with delete_expander:
        game_id = st.text_input("Game ID", key="delete_game_id")
        confirm_delete = st.checkbox(
            "I confirm that I want to delete this game", key="delete_confirm"
        )
        if st.button("Delete Game", key="delete_game_button") and confirm_delete:
            if delete_game(game_id):
                st.success("Game Deleted")
            else:
                st.error("Failed to delete game")

    # Section to edit an existing game
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
            edit_title = st.text_input("Title", game_details["title"], key="edit_title")
            edit_cover_image = st.text_input("Cover Image URL", game_details["cover_image"], key="edit_cover_image")
            edit_description = st.text_area("Description", game_details["description"], key="edit_description")
            edit_publisher = st.text_input("Publisher", ", ".join(game_details["publisher"]), key="edit_publisher")
            edit_platforms = st.text_input("Platforms (comma separated)", ", ".join(game_details["platforms"]), key="edit_platforms")
            edit_genres = st.text_input("Genres (comma separated)", ", ".join(game_details["genres"]), key="edit_genres")
            edit_series = st.text_input("Series", ", ".join(game_details["series"]), key="edit_series")
            edit_release_date = st.date_input("Release Date", key="edit_release_date")

            if st.button("Update Game", key="update_game_button"):
                updated_game_data = {
                    "title": edit_title,
                    "cover_image": edit_cover_image,
                    "description": edit_description,
                    "publisher": edit_publisher.split(", "),
                    "platforms": edit_platforms.split(", "),
                    "genres": edit_genres.split(", "),
                    "series": edit_series.split(", "),
                    "release_date": edit_release_date.strftime("%Y-%m-%d"),
                }
                if update_game(edit_game_id, updated_game_data):
                    st.success("Game updated successfully")
                else:
                    st.error("Failed to update game")

    # Advanced filtering options
    filter_expander = st.sidebar.expander("Advanced Filters")
    with filter_expander:
        publishers = fetch_unique_values("publisher")
        platforms = fetch_unique_values("platform")
        genres = fetch_unique_values("genre")
        years = fetch_unique_values("year")

        if st.button("Clear Filters", key="clear_filter_button"):
            st.session_state["filter_publisher"] = ""
            st.session_state["filter_platform"] = ""
            st.session_state["filter_genre"] = ""
            st.session_state["filter_year"] = ""

        selected_publisher = st.selectbox(
            "Publisher", [""] + publishers, key="filter_publisher"
        )
        selected_platform = st.selectbox(
            "Platform", [""] + platforms, key="filter_platform"
        )
        selected_genre = st.selectbox("Genre", [""] + genres, key="filter_genre")
        selected_year = st.selectbox("Release Year", [""] + years, key="filter_year")

        filters = {}
        if selected_publisher:
            filters["publisher"] = selected_publisher
        if selected_platform:
            filters["platform"] = selected_platform
        if selected_genre:
            filters["genre"] = selected_genre
        if selected_year:
            filters["year"] = selected_year

        if st.button("Filter", key="filter_button"):
            games = fetch_games(filters)
        else:
            games = fetch_games()
            
    # Calculate total cost of the displayed games
    total_cost = calculate_total_cost(games)

    # Display the total cost
    st.markdown(f"### Total Cost of Displayed Games: £{total_cost:.2f}")

    # Link to trigger barcode scanning via iPhone
    st.markdown("[Scan Barcode with iPhone](shortcuts://run-shortcut?name=Scan%20Video%20Games)")

    # Add a link to install the shortcut if not already installed
    st.markdown(f"[Install 'Scan Video Games' Shortcut]({ICLOUD_LINK})")

    # Game search functionality
    st.markdown("## Search Game by Name")
    game_name = st.text_input("Enter Game Name", key="game_name_input")

    # Initialize state to store search results and selected game
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

    # Display search results if available
    if st.session_state["search_results"]:
        exact_match = st.session_state["search_results"].get("exact_match")
        alternative_match = st.session_state["search_results"].get("alternative_match")

        game_options = []
        game_map = {}

        if exact_match:
            game_title = f"Exact Match: {exact_match['name']}"
            game_options.append(game_title)
            game_map[game_title] = exact_match

        if alternative_match:
            alt_title = f"Alternative Match: {alternative_match['name']}"
            game_options.append(alt_title)
            game_map[alt_title] = alternative_match

        selected_option = st.radio("Select a game to add:", game_options, key="selected_game_radio")
        st.session_state["selected_game"] = game_map[selected_option]

        if st.button("Add Selected Game", key="add_selected_game_button"):
            selected_game_data = st.session_state["selected_game"]
            if selected_game_data:
                game_data = {
                    "title": selected_game_data["name"],
                    "cover_image": selected_game_data.get("cover", {}).get("url"),
                    "description": selected_game_data.get("summary"),
                    "publisher": [
                        company["company"]["name"]
                        for company in selected_game_data.get("involved_companies", [])
                    ],
                    "platforms": [
                        platform["name"] for platform in selected_game_data.get("platforms", [])
                    ],
                    "genres": [genre["name"] for genre in selected_game_data.get("genres", [])],
                    "series": [
                        franchise["name"] for franchise in selected_game_data.get("franchises", [])
                    ],
                    "release_date": None,
                    "average_price": None,  # Add field for average price if needed
                }

                # Optionally, convert release date if available
                if selected_game_data.get("first_release_date"):
                    game_data["release_date"] = time.strftime(
                        "%Y-%m-%d", time.gmtime(selected_game_data["first_release_date"])
                    )

                # Call the add_game function
                if add_game(game_data):
                    st.success(f"{selected_game_data['name']} added successfully!")
                else:
                    st.error("Failed to add game.")


    # Display the list of games
    for game in games:
        if search_term.lower() in game["title"].lower():
            # Ensure full image URL
            cover_image_url = (
                f"https:{game['cover_image']}"
                if game["cover_image"] and game["cover_image"].startswith("//")
                else game["cover_image"]
            )
            average_price = (
                f"£{game['average_price']:.2f}"
                if game["average_price"] is not None
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

# Entry point of the script
if __name__ == "__main__":
    main()

import streamlit as st
import requests
import time
import os

# Retrieve the backend host from environment variables, default to 'localhost' if using Python locally
backend_host = os.getenv("BACKEND_HOST", "localhost")

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
    return sum(
        game.get("average_price", 0)
        for game in games
        if game.get("average_price") is not None
    )


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
    response = requests.post(
        f"{BACKEND_URL}/search_game_by_name", json={"game_name": game_name}
    )
    if response.status_code == 200:
        return response.json()
    else:
        return None


# Function to search for games by IGDB ID using the backend
def search_game_by_id(igdb_id):
    response = requests.post(
        f"{BACKEND_URL}/search_game_by_id", json={"igdb_id": igdb_id}
    )
    if response.status_code == 200:
        return response.json()
    else:
        return None


# Function to fetch the top 5 games with the highest average price
def fetch_top_games():
    response = requests.get(f"{BACKEND_URL}/top_games")
    return response.json()


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

    # Initialize state to track filter status
    if "filters_active" not in st.session_state:
        st.session_state["filters_active"] = False

    # Sidebar for filtering and managing games
    st.sidebar.title("Filter Games")
    search_term = st.sidebar.text_input("Search by Title", key="search_title")
    
    # Only fetch games if a search term is provided
    games = []
    if search_term:
        filters = {"title": search_term}  # Pass search term to backend
        games = fetch_games(filters)

    # Ensure 'games' is always a list to prevent errors
    if not isinstance(games, list):
        games = []

    # Debugging: Check what we get from backend
    # st.write("Fetched games:", games)

    # Display search results if there are games
    if games:
        for game in games:
            cover_image_url = (
                f"https:{game.get('cover_image', '')}"
                if game.get("cover_image") and game["cover_image"].startswith("//")
                else game.get("cover_image", "https://via.placeholder.com/150")
            )

            average_price = (
                f"£{game.get('average_price', 0):.2f}"
                if game.get("average_price") is not None
                else "N/A"
            )

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
    else:
        if search_term:
            st.warning("No games found matching your search.")

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
                "release_date": (
                    release_date.strftime("%Y-%m-%d") if release_date else "1900-01-01"
                ),
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
            edit_cover_image = st.text_input(
                "Cover Image URL", game_details["cover_image"], key="edit_cover_image"
            )
            edit_description = st.text_area(
                "Description", game_details["description"], key="edit_description"
            )
            edit_publisher = st.text_input(
                "Publisher", ", ".join(game_details["publisher"]), key="edit_publisher"
            )
            edit_platforms = st.text_input(
                "Platforms (comma separated)",
                ", ".join(game_details["platforms"]),
                key="edit_platforms",
            )
            edit_genres = st.text_input(
                "Genres (comma separated)",
                ", ".join(game_details["genres"]),
                key="edit_genres",
            )
            edit_series = st.text_input(
                "Series", ", ".join(game_details["series"]), key="edit_series"
            )
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
                    "release_date": (
                        edit_release_date.strftime("%Y-%m-%d")
                        if edit_release_date
                        else "1900-01-01"
                    ),
                }
                if update_game(edit_game_id, updated_game_data):
                    st.success("Game updated successfully")
                else:
                    st.error("Failed to update game")

    # Advanced filtering options
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
            st.session_state["filters_active"] = True
            games = fetch_games(filters)
        else:
            games = []

    # Calculate total cost of the displayed games
    total_cost = calculate_total_cost(games)

    # Display the total cost
    if st.session_state["filters_active"]:
        st.markdown(f"### Total Cost of Displayed Games: £{total_cost:.2f}")

    # Link to trigger barcode scanning via iPhone
    st.markdown(
        "[Scan Barcode with iPhone](shortcuts://run-shortcut?name=Scan%20Video%20Games)"
    )

    # Add a link to install the shortcut if not already installed
    st.markdown(f"[Install 'Scan Video Games' Shortcut]({ICLOUD_LINK})")

    # Local game search functionality
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

        selected_option = st.radio(
            "Select a game to add:", game_options, key="selected_game_radio"
        )
        st.session_state["selected_game"] = game_map[selected_option]

        # Display preview information for the selected game
        selected_game_data = st.session_state["selected_game"]
        if selected_game_data:
            st.markdown("### Game Details")
            st.markdown(f"**Title:** {selected_game_data['name']}")
            st.markdown(f"**Description:** {selected_game_data.get('summary', 'N/A')}")
            st.markdown(
            f"**Cover URL:** {selected_game_data.get('cover_url', 'N/A')}"
        )

            publishers = selected_game_data.get("involved_companies", [])

            # If publishers are already a list of strings, join them directly
            if publishers and all(isinstance(publisher, str) for publisher in publishers):
                publisher_text = ", ".join(publishers)

            # If publishers are a list of dictionaries, extract names
            elif publishers and all(isinstance(publisher, dict) and "company" in publisher and "name" in publisher["company"] for publisher in publishers):
                publisher_text = ", ".join([publisher["company"]["name"] for publisher in publishers])

            else:
                publisher_text = "N/A"

            st.markdown(f"**Publisher:** {publisher_text}")
                
            platforms = selected_game_data.get("platforms", [])

            # If platforms are already a list of strings, join them directly
            if platforms and all(isinstance(platform, str) for platform in platforms):
                platform_text = ", ".join(platforms)

            # If platforms are a list of dictionaries, extract names
            elif platforms and all(isinstance(platform, dict) and "name" in platform for platform in platforms):
                platform_text = ", ".join([platform["name"] for platform in platforms])

            else:
                platform_text = "N/A"

            st.markdown(f"**Platforms:** {platform_text}")

            # st.write("Debugging: Full Game Data:", selected_game_data)  # Check full response
            # st.write("Debugging: Genres Field:", selected_game_data.get("genres", "MISSING"))  # Check genres field
            genres = selected_game_data.get("genres", [])

            # Handle case where genres is a list of strings (like in your response)
            if genres and all(isinstance(genre, str) for genre in genres):
                genre_text = ", ".join(genres)

            # Handle case where genres is a list of dictionaries (older structure)
            elif genres and all(isinstance(genre, dict) and "name" in genre for genre in genres):
                genre_text = ", ".join([genre["name"] for genre in genres])

            else:
                genre_text = "N/A"

            st.markdown(f"**Genres:** {genre_text}")

            release_date_timestamp = selected_game_data.get("release_date")

            if isinstance(release_date_timestamp, int):  # Ensure it's a valid timestamp
                release_date = time.strftime("%Y-%m-%d", time.gmtime(release_date_timestamp))
            else:
                release_date = "N/A"

            st.markdown(f"**Release Date:** {release_date}")

        if st.button("Add Selected Game", key="add_selected_game_button"):
            if selected_game_data:
                game_data = {
                    "title": selected_game_data["name"],
                    "cover_image": selected_game_data.get("cover_url"),
                    "description": selected_game_data.get("summary"),
                    "publisher": selected_game_data.get("involved_companies", []),
                    "platforms": selected_game_data.get("platforms", []),
                    "genres": selected_game_data.get("genres", []),
                    "franchise": selected_game_data.get("franchises", []),
                    "series": selected_game_data.get("series", []),
                    "release_date": None,
                    "average_price": None,  # Add field for average price if needed
                }

                # Optionally, convert release date if available
                if selected_game_data.get("release_date"):
                    game_data["release_date"] = time.strftime(
                        "%Y-%m-%d",
                        time.gmtime(selected_game_data["release_date"]),
                    )

                # Call the add_game function
                if add_game(game_data):
                    st.success(f"{selected_game_data['name']} added successfully!")
                else:
                    st.error("Failed to add game.")

    # IGDB ID search functionality
    st.markdown("## Search Game by IGDB ID")
    igdb_id = st.text_input("Enter IGDB ID", key="igdb_id_input")

    if st.button("Search Game by ID", key="search_game_by_id_button"):
        search_response = search_game_by_id(igdb_id)
        if search_response:
            st.session_state["selected_game_by_id"] = search_response
        else:
            st.error("No game found with the provided IGDB ID.")
            st.session_state["selected_game_by_id"] = None

    # Display game details if IGDB ID search result is available
    if "selected_game_by_id" in st.session_state and st.session_state["selected_game_by_id"]:
        selected_game_data_by_id = st.session_state["selected_game_by_id"]
        st.markdown("### Game Details (By ID)")

        # Title & Description
        st.markdown(f"**Title:** {selected_game_data_by_id.get('name', 'N/A')}")
        st.markdown(f"**Description:** {selected_game_data_by_id.get('summary', 'N/A')}")

        # Cover Image
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

        platforms = []
        if isinstance(selected_game_data_by_id.get("platforms"), list):
            for platform in selected_game_data_by_id.get("platforms", []):
                if isinstance(platform, dict) and "name" in platform:
                    platforms.append(platform["name"])
        st.markdown(f"**Platforms:** {', '.join(platforms) if platforms else 'N/A'}")

        genres = []
        if isinstance(selected_game_data_by_id.get("genres"), list):
            for genre in selected_game_data_by_id["genres"]:
                if isinstance(genre, dict) and "name" in genre:
                    genres.append(genre["name"])
                elif isinstance(genre, str):  # Handle if IGDB returns a string
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

        if st.button("Add Game by ID", key="add_game_by_id_button"):
            if selected_game_data_by_id:
                game_data = {
                    "title": selected_game_data_by_id["name"],
                    "cover_image": selected_game_data_by_id.get("cover", {}).get("url"),
                    "description": selected_game_data_by_id.get("summary"),
                    "publisher": [
                        company["company"]["name"]
                        for company in selected_game_data_by_id.get(
                            "involved_companies", []
                        )
                    ],
                    "platforms": [
                        platform["name"]
                        for platform in selected_game_data_by_id.get("platforms", [])
                    ],
                    "genres": [
                        genre["name"]
                        for genre in selected_game_data_by_id.get("genres", [])
                    ],
                    "series": [
                        franchise["name"]
                        for franchise in selected_game_data_by_id.get("franchises", [])
                    ],
                    "release_date": None,
                    "average_price": None,  # Add field for average price if needed
                }

                # Optionally, convert release date if available
                if selected_game_data_by_id.get("first_release_date"):
                    game_data["release_date"] = time.strftime(
                        "%Y-%m-%d",
                        time.gmtime(selected_game_data_by_id["first_release_date"]),
                    )

                # Call the add_game function
                if add_game(game_data):
                    st.success(
                        f"{selected_game_data_by_id['name']} added successfully!"
                    )
                else:
                    st.error("Failed to add game.")

    # Display the list of games
    for game in games:
        if search_term.lower() in game["title"].lower():
            # Ensure full image URL with a fallback placeholder
            cover_image_url = (
                f"https:{game.get('cover_image', '')}"
                if game.get("cover_image") and game["cover_image"].startswith("//")
                else game.get("cover_image", "https://via.placeholder.com/150")
            )

            # Ensure price is displayed properly
            average_price = (
                f"£{game.get('average_price', 0):.2f}"
                if game.get("average_price") is not None
                else "N/A"
            )

            # Handle potential missing or incorrectly formatted data
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

    # Fetch and display the top 5 games with the highest average price
    if not st.session_state["filters_active"]:
        st.markdown("## Top 5 Games by Average Price")
        top_games = fetch_top_games()
        for game in top_games:
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

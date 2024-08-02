import streamlit as st
import requests

# Backend API URLs
BACKEND_URL = "http://localhost:5001"


def fetch_games(filters=None):
    response = requests.get(f"{BACKEND_URL}/games", params=filters)
    return response.json()


def fetch_consoles():
    response = requests.get(f"{BACKEND_URL}/consoles")
    return response.json()


def fetch_unique_values(value_type):
    response = requests.get(f"{BACKEND_URL}/unique_values", params={"type": value_type})
    return response.json()


def add_game(game_data):
    response = requests.post(f"{BACKEND_URL}/add_game", json=game_data)
    return response.status_code == 201


def delete_game(game_id):
    response = requests.post(
        f"{BACKEND_URL}/delete_game", json={"id": int(game_id)}
    )  # Ensure game_id is an integer
    return response.status_code == 200

def update_game(game_id, game_data):
    response = requests.put(f"{BACKEND_URL}/update_game/{game_id}", json=game_data)
    return response.status_code == 200

def fetch_game_by_id(game_id):
    response = requests.get(f"{BACKEND_URL}/game/{game_id}")
    if response.status_code == 200:
        return response.json()
    else:
        return None

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


def main():
    st.title("Video Game Catalogue")

    st.sidebar.title("Filter Games")
    search_term = st.sidebar.text_input("Search by Title", key="search_title")

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
                "average_price": None,  # Add a field for average price in the frontend (if needed)
            }
            if add_game(game_data):
                st.success("Game added successfully")

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

        # Edit Game section
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


    # Add barcode scan functionality
    st.markdown("## Barcode Scanner")
    barcode = st.text_input("Enter Barcode", key="barcode_input")

     # Add a link to trigger the shortcut
    st.markdown("[Scan Barcode with iPhone](shortcuts://run-shortcut?name=Scan Video Games)")

    if st.button("Scan Barcode", key="scan_barcode_button"):
        scan_response = scan_game(barcode)
        if "exact_match" in scan_response or "alternative_match" in scan_response:
            selected_game = scan_response.get("exact_match") or scan_response.get(
                "alternative_match"
            )
            game_data = {
                "title": selected_game["name"],
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
                "average_price": None,  # Add field for average price if needed
            }
            st.write(game_data)
            # Optionally save the selected game to the database here
        elif "error" in scan_response:
            st.error(scan_response["error"])
        else:
            game_data = scan_response
            st.write("Game found:")
            st.write(game_data)
            # Optionally save the game to the database here

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

if __name__ == "__main__":
    main()

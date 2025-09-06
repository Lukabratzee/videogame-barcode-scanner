import os
import sqlite3

# Use DATABASE_PATH environment variable if set, otherwise use local directory
if 'DATABASE_PATH' in os.environ:
    db_path = os.environ['DATABASE_PATH']
    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, 'games.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create table
cursor.execute('''
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    title TEXT,
    description TEXT,
    publisher TEXT,
    platforms TEXT,
    genres TEXT,
    series TEXT,
    release_date TEXT,
    average_price REAL,
    youtube_trailer_url TEXT
)
''')

conn.commit()

# Check if database is empty and add placeholder if needed
cursor.execute("SELECT COUNT(*) FROM games")
count = cursor.fetchone()[0]
print(f"DEBUG: Current game count in database: {count}")

if count == 0:
    print("DEBUG: Database is empty, adding placeholder...")
    # Add a placeholder entry to prevent empty database issues
    placeholder_game = (
        -1,  # id (will be filtered out)
        "__PLACEHOLDER__",  # title
        "Placeholder entry - do not display",  # description
        "__PLACEHOLDER__",  # publisher
        "__PLACEHOLDER__",  # platforms
        "__PLACEHOLDER__",  # genres
        "__PLACEHOLDER__",  # series
        "1900-01-01",  # release_date
        0.0,  # average_price
        None  # youtube_trailer_url
    )

    cursor.execute('''
    INSERT INTO games (id, title, description, publisher, platforms, genres, series, release_date, average_price, youtube_trailer_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', placeholder_game)
    
    conn.commit()
    print("✅ Added placeholder entry to prevent empty database issues")
    
    # Verify the placeholder was added
    cursor.execute("SELECT COUNT(*) FROM games")
    new_count = cursor.fetchone()[0]
    print(f"DEBUG: Game count after placeholder insertion: {new_count}")
else:
    print(f"DEBUG: Database not empty (count: {count}), skipping placeholder")

# Verify table creation
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games';")
table_exists = cursor.fetchone()
print("Table 'games' exists:", bool(table_exists))

conn.close()

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'games.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create table
cursor.execute('''
CREATE TABLE IF NOT EXISTS games (
    "id" INTEGER PRIMARY KEY,
    "title" TEXT,
    "cover_image" TEXT,
    "description" TEXT,
    "publisher" TEXT,
    "platforms" TEXT,
    "genres" TEXT,
    "series" TEXT,
    "release_date" TEXT,
    "average_price" REAL
)
''')

conn.commit()

# Verify table creation
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games';")
table_exists = cursor.fetchone()
print("Table 'games' exists:", bool(table_exists))

conn.close()

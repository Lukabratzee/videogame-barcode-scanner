import sqlite3

conn = sqlite3.connect('games.db')
cursor = conn.cursor()

# Add the average_price column to the games table
cursor.execute('ALTER TABLE games ADD COLUMN average_price REAL')

conn.commit()
conn.close()

import sqlite3

conn = sqlite3.connect('games.db')
cursor = conn.cursor()

# Drop the column 'series'
cursor.execute('ALTER TABLE games DROP COLUMN series')

conn.commit()
conn.close()

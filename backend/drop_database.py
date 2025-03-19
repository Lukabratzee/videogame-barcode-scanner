import sqlite3

conn = sqlite3.connect('games.db')
cursor = conn.cursor()

# Erase DB
cursor.execute('DROP TABLE IF EXISTS games')

conn.commit()
conn.close()

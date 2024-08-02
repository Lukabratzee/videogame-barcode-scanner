import sqlite3

conn = sqlite3.connect('games.db')
cursor = conn.cursor()

cursor.execute("SELECT average_price FROM games")
prices = cursor.fetchall()
for price in prices:
    print(price)

conn.close()

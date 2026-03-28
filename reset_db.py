import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS payments")

conn.commit()
conn.close()

print("✅ payments table deleted successfully")
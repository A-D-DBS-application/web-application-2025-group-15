import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

try:
    c.execute("ALTER TABLE progress ADD COLUMN updated_at TEXT DEFAULT (datetime('now','localtime'))")
    print("✅ Kolom 'updated_at' toegevoegd!")
except sqlite3.OperationalError:
    print("Kolom 'updated_at' bestaat al, geen actie nodig.")

conn.commit()
conn.close()

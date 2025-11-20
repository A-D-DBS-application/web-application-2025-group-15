import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

sample_players = [
    ('speler1', 'speler1@mail.com', '0499000001', 'player', 'padel', 'test123'),
    ('speler2', 'speler2@mail.com', '0499000002', 'player', 'padel', 'test123'),
    ('speler3', 'speler3@mail.com', '0499000003', 'player', 'padel', 'test123'),
    ('speler4', 'speler4@mail.com', '0499000004', 'player', 'padel', 'test123'),
    ('speler5', 'speler5@mail.com', '0499000005', 'player', 'padel', 'test123'),
    ('speler6', 'speler6@mail.com', '0499000006', 'player', 'padel', 'test123'),
    ('speler7', 'speler7@mail.com', '0499000007', 'player', 'padel', 'test123'),
    ('speler8', 'speler8@mail.com', '0499000008', 'player', 'padel', 'test123'),
    ('speler9', 'speler9@mail.com', '0499000009', 'player', 'padel', 'test123'),
    ('speler10', 'speler10@mail.com', '0499000010', 'player', 'padel', 'test123')
]

c.executemany("""
INSERT INTO users (username, email, phone, role, sport, password)
VALUES (?, ?, ?, ?, ?, ?)
""", sample_players)

conn.commit()
conn.close()
print("✅ 10 spelers toegevoegd!")

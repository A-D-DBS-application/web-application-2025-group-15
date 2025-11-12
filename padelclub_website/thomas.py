from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import date
from config import Config
from dotenv import load_dotenv

app = Flask(__name__)
app.config.from_object(Config)






# -----------------------------
# DATABASE SETUP
# -----------------------------

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Gebruikers
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        role TEXT CHECK(role IN ('player','coach','admin')) NOT NULL,
        sport TEXT CHECK(sport IN ('padel','badminton','tennis')),
        password TEXT NOT NULL
    )
    """)

    # Lessen
    c.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        coach_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY(player_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(coach_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Lesboekingen
    c.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        coach_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        status TEXT DEFAULT 'geboekt',
        FOREIGN KEY(player_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(coach_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Afgelopen lessen
    c.execute("""
    CREATE TABLE IF NOT EXISTS completed_lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        coach_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        swot_strengths TEXT,
        swot_weaknesses TEXT,
        swot_opportunities TEXT,
        swot_threats TEXT,
        notes TEXT,
        rating INTEGER,
        FOREIGN KEY(player_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(coach_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Progressie (met datum)
    c.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        coach_id INTEGER NOT NULL,
        p_score INTEGER DEFAULT 0,
        hand TEXT CHECK(hand IN ('links','rechts','beide')),
        strengths TEXT,
        weaknesses TEXT,
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(player_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(coach_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Voeg 1 administrator toe als die nog niet bestaat
    c.execute("SELECT * FROM users WHERE username='administrator'")
    if not c.fetchone():
        c.execute("""
        INSERT INTO users (username, email, phone, role, sport, password)
        VALUES ('administrator', 'admin@club.be', '0000', 'admin', 'padel', 'admin123')
        """)
        print("✅ Administrator aangemaakt: username='administrator', wachtwoord='admin123'")

    conn.commit()
    conn.close()

init_db()
def fix_progress_table():
    """Voegt kolom 'updated_at' toe aan progress als die nog niet bestaat."""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    try:
        # Controleer of de kolom al bestaat
        c.execute("PRAGMA table_info(progress)")
        columns = [row[1] for row in c.fetchall()]
        if "updated_at" not in columns:
            c.execute("ALTER TABLE progress ADD COLUMN updated_at TEXT DEFAULT (datetime('now','localtime'))")
            conn.commit()
            print("✅ Kolom 'updated_at' toegevoegd aan 'progress'.")
        else:
            print("ℹ️ Kolom 'updated_at' bestaat al, geen aanpassing nodig.")
    except Exception as e:
        print("⚠️ Fout bij het controleren/toevoegen van kolom:", e)
    finally:
        conn.close()

# Voeg dit toe na init_db() zodat het automatisch wordt uitgevoerd
init_db()
fix_progress_table()

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[4]
            if user[4] == "player":
                return redirect(url_for("player_dashboard"))
            elif user[4] == "coach":
                return redirect(url_for("coach_dashboard"))
            elif user[4] == "admin":
                return redirect(url_for("admin_dashboard"))
        else:
            return render_template("login.html", error="❌ Onjuiste gebruikersnaam of wachtwoord!")
    return render_template("login.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        phone = request.form["phone"]
        role = request.form["role"]
        sport = request.form["sport"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO users (username, email, phone, role, sport, password)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, email, phone, role, sport, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Gebruikersnaam bestaat al!")
        finally:
            conn.close()

        return redirect(url_for("login"))
    return render_template("register.html")

# ---------- PLAYER DASHBOARD ----------
@app.route("/player")
def player_dashboard():
    if session.get("role") != "player":
        return redirect(url_for("home"))
    return render_template("player_dashboard.html")

# ---------- LES AANVRAGEN ----------
@app.route("/player/book_lesson", methods=["GET", "POST"])
def book_lesson():
    if session.get("role") != "player":
        return redirect(url_for("home"))

    player_id = session.get("user_id")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Haal coaches op
    c.execute("SELECT id, username, sport FROM users WHERE role='coach'")
    coaches = c.fetchall()

    if request.method == "POST":
        coach_id = request.form["coach_id"]
        date = request.form["date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]

        # Controleer of coach al bezet is
        c.execute("""
            SELECT * FROM bookings 
            WHERE coach_id=? AND date=? 
              AND ((start_time <= ? AND end_time > ?) OR (start_time < ? AND end_time >= ?))
        """, (coach_id, date, start_time, start_time, end_time, end_time))
        overlap = c.fetchone()

        if overlap:
            conn.close()
            return render_template("book_lesson.html", coaches=coaches, error="❌ Coach is al geboekt op dat moment!")

        # Voeg boeking toe
        c.execute("""
            INSERT INTO bookings (player_id, coach_id, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (player_id, coach_id, date, start_time, end_time))
        conn.commit()
        conn.close()
        return redirect(url_for("player_dashboard"))

    conn.close()
    return render_template("book_lesson.html", coaches=coaches)

# ---------- COACH ----------
# ---------- COACH DASHBOARD ----------
@app.route("/coach")
def coach_dashboard():
    if session.get("role") != "coach":
        return redirect(url_for("home"))

    coach_id = session.get("user_id")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # 🔹 Stap 1: Haal spelers op die gekoppeld zijn aan deze coach
    c.execute("""
        SELECT u.id, u.username, u.email, u.phone, u.sport,
               p.p_score, p.hand, p.strengths, p.weaknesses
        FROM users u
        JOIN lessons l ON u.id = l.player_id
        LEFT JOIN progress p ON u.id = p.player_id AND p.coach_id = ?
        WHERE l.coach_id = ?
        GROUP BY u.id
    """, (coach_id, coach_id))
    spelers = c.fetchall()

    # 🔹 Stap 2: Controleer op afgelopen lessen
    today = date.today().isoformat()

    # Selecteer alle lessen die in het verleden liggen
    c.execute("""
        SELECT id, player_id, coach_id, date, start_time, end_time
        FROM bookings
        WHERE coach_id = ? AND date < ?
    """, (coach_id, today))
    past_lessons = c.fetchall()

    # 🔹 Stap 3: Verplaats ze naar completed_lessons
    for les in past_lessons:
        c.execute("""
            INSERT INTO completed_lessons (player_id, coach_id, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (les[1], les[2], les[3], les[4], les[5]))
        c.execute("DELETE FROM bookings WHERE id = ?", (les[0],))
    conn.commit()

    # 🔹 Stap 4: Haal opnieuw geplande lessen op (enkel toekomstige!)
    c.execute("""
        SELECT id, player_id, date, start_time, end_time, status
        FROM bookings
        WHERE coach_id = ? AND date >= ?
        ORDER BY date ASC
    """, (coach_id, today))
    geplande_lessen = c.fetchall()

    # 🔹 Stap 5: Haal de afgelopen lessen op uit completed_lessons
    c.execute("""
        SELECT id, player_id, date
        FROM completed_lessons
        WHERE coach_id = ?
        ORDER BY date DESC
    """, (coach_id,))
    afgelopen_lessen = c.fetchall()

    conn.close()

    # 🔹 Stap 6: Render de pagina
    return render_template(
        "coach_dashboard.html",
        spelers=spelers,
        lessen=geplande_lessen,
        completed=afgelopen_lessen
    )

# ---------- COACH: Speler toevoegen ----------
@app.route("/coach/add_player", methods=["GET", "POST"])
def add_player():
    if session.get("role") != "coach":
        return redirect(url_for("home"))

    coach_id = session.get("user_id")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

   # 🔹 Haal spelers op die nog NIET gekoppeld zijn aan deze coach
   # 🔹 Haal spelers op die nog NIET gekoppeld zijn aan deze coach
    c.execute("""
    SELECT u.id, u.username
    FROM users u
    WHERE u.role = 'player'
    AND u.id NOT IN (
        SELECT player_id FROM lessons WHERE coach_id = ?
    )
""", (coach_id,))
    all_players = c.fetchall()


 

    

    if request.method == "POST":
        player_id = request.form["player_id"]
        p_score = request.form.get("p_score")
        hand = request.form.get("hand")
        strengths = request.form.get("strengths")
        weaknesses = request.form.get("weaknesses")

        # Controleer of speler al aan coach gekoppeld is
        c.execute("SELECT * FROM lessons WHERE player_id=? AND coach_id=?", (player_id, coach_id))
        if c.fetchone():
            conn.close()
            return render_template("add_player.html", error="Deze speler is al gekoppeld aan jou!", spelers=all_players)

        # Voeg les toe (koppeling coach–speler)
        c.execute("INSERT INTO lessons (player_id, coach_id, date) VALUES (?, ?, DATE('now'))", (player_id, coach_id))

        # Voeg progressie toe
        c.execute("""
            INSERT INTO progress (player_id, coach_id, p_score, hand, strengths, weaknesses)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (player_id, coach_id, p_score, hand, strengths, weaknesses))

        conn.commit()
        conn.close()
        return redirect(url_for("coach_dashboard"))

    conn.close()
    return render_template("add_player.html", spelers=all_players)

    if request.method == "POST":
        player_username = request.form["player_username"]
        p_score = request.form.get("p_score")
        hand = request.form.get("hand")
        strengths = request.form.get("strengths")
        weaknesses = request.form.get("weaknesses")

        c.execute("SELECT id FROM users WHERE username=? AND role='player'", (player_username,))
        player = c.fetchone()

        if not player:
            conn.close()
            return render_template("add_player.html", error="Speler niet gevonden!")

        player_id = player[0]
        c.execute("SELECT * FROM lessons WHERE player_id=? AND coach_id=?", (player_id, coach_id))
        if not c.fetchone():
            c.execute("INSERT INTO lessons (player_id, coach_id, date) VALUES (?, ?, DATE('now'))", (player_id, coach_id))

        c.execute("""
            INSERT INTO progress (player_id, coach_id, p_score, hand, strengths, weaknesses)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (player_id, coach_id, p_score, hand, strengths, weaknesses))

        conn.commit()
        conn.close()
        return redirect(url_for("coach_dashboard"))

    conn.close()
    return render_template("add_player.html")

# ---------- COACH: Les inplannen (keuzepagina) ----------
@app.route("/coach/schedule_lesson")
def schedule_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("home"))
    return render_template("schedule_lesson_choice.html")

# ---------- COACH: Groepsles ----------
@app.route("/coach/schedule_group_lesson", methods=["GET", "POST"])
def schedule_group_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("home"))

    coach_id = session.get("user_id")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.username 
        FROM users u
        JOIN lessons l ON u.id = l.player_id
        WHERE l.coach_id = ?
        GROUP BY u.id
    """, (coach_id,))
    spelers = c.fetchall()

    if request.method == "POST":
        selected_players = request.form.getlist("player_ids")
        if len(selected_players) < 2:
            return render_template("schedule_group_lesson.html", spelers=spelers, error="❌ Selecteer minstens 2 spelers (max. 5).")
        if len(selected_players) > 5:
            return render_template("schedule_group_lesson.html", spelers=spelers, error="❌ Je mag maximaal 5 spelers selecteren.")

        date = request.form["date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        lesson_type = request.form["lesson_type"]
        notes = request.form.get("notes")

        for player_id in selected_players:
            c.execute("""
                INSERT INTO bookings (player_id, coach_id, date, start_time, end_time, status)
                VALUES (?, ?, ?, ?, ?, 'geboekt')
            """, (player_id, coach_id, date, start_time, end_time))
        conn.commit()
        conn.close()
        return redirect(url_for("coach_dashboard"))

    conn.close()
    return render_template("schedule_group_lesson.html", spelers=spelers)

# ---------- COACH: Individuele les ----------
@app.route("/coach/schedule_individual_lesson", methods=["GET", "POST"])
def schedule_individual_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("home"))

    coach_id = session.get("user_id")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.username 
        FROM users u
        JOIN lessons l ON u.id = l.player_id
        WHERE l.coach_id = ?
        GROUP BY u.id
    """, (coach_id,))
    spelers = c.fetchall()

    if request.method == "POST":
        player_id = request.form["player_id"]
        date = request.form["date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        lesson_type = request.form["lesson_type"]
        notes = request.form.get("notes")

        c.execute("""
            INSERT INTO bookings (player_id, coach_id, date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, 'geboekt')
        """, (player_id, coach_id, date, start_time, end_time))
        conn.commit()
        conn.close()
        return redirect(url_for("coach_dashboard"))

    conn.close()
    return render_template("schedule_individual_lesson.html", spelers=spelers)
    
# ---------- COACH: Speler detailpagina ----------
@app.route("/coach/player/<int:player_id>")
def view_player(player_id):
    if session.get("role") != "coach":
        return redirect(url_for("home"))

    coach_id = session.get("user_id")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Basisinfo van de speler ophalen
    c.execute("SELECT username, email, phone, sport FROM users WHERE id=?", (player_id,))
    speler = c.fetchone()

    # Alle progressie-updates ophalen
    c.execute("""
        SELECT p_score, hand, strengths, weaknesses, updated_at
        FROM progress
        WHERE player_id=? AND coach_id=?
        ORDER BY datetime(updated_at) DESC
    """, (player_id, coach_id))
    progressies = c.fetchall()
    conn.close()

    return render_template("player_detail.html", speler=speler, progressies=progressies)

# ---------- COACH: Speler verwijderen ----------
@app.route("/coach/remove_player/<int:player_id>")
def remove_player(player_id):
    if session.get("role") != "coach":
        return redirect(url_for("home"))

    coach_id = session.get("user_id")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Verwijder koppeling tussen coach en speler
    c.execute("DELETE FROM lessons WHERE player_id=? AND coach_id=?", (player_id, coach_id))
    c.execute("DELETE FROM progress WHERE player_id=? AND coach_id=?", (player_id, coach_id))
    conn.commit()
    conn.close()

    return redirect(url_for("coach_dashboard"))

# ---------- ADMIN ----------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, username, role, sport FROM users")
    users = c.fetchall()
    conn.close()
    return render_template("admin_dashboard.html", users=users)

@app.route("/admin/delete/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))
    
# ---------- ADMIN: Speler detail ----------
@app.route("/admin/player/<int:player_id>")
def admin_view_player(player_id):
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Basisgegevens speler
    c.execute("""
        SELECT id, username, email, phone, sport, role
        FROM users
        WHERE id=?
    """, (player_id,))
    speler = c.fetchone()

    if not speler:
        conn.close()
        return render_template("admin_dashboard.html", error="Speler niet gevonden!")

    # Voortgangsgegevens
    c.execute("""
        SELECT p_score, hand, strengths, weaknesses, updated_at
        FROM progress
        WHERE player_id=?
        ORDER BY datetime(updated_at) DESC
    """, (player_id,))
    progress = c.fetchall()

    # Lessen
    c.execute("""
        SELECT date, coach_id
        FROM lessons
        WHERE player_id=?
        ORDER BY date DESC
    """, (player_id,))
    lessen = c.fetchall()

    # Coachnamen toevoegen aan lessen
    coachen = []
    for les in lessen:
        c.execute("SELECT username FROM users WHERE id=?", (les[1],))
        coach = c.fetchone()
        coachen.append(coach[0] if coach else "Onbekend")

    conn.close()

    return render_template(
        "admin_player_detail.html",
        speler=speler,
        progress=progress,
        lessen=zip(lessen, coachen)
    )

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ---------- COACH: Les evalueren ----------
@app.route("/coach/evaluate_lesson/<int:lesson_id>", methods=["GET", "POST"])
def evaluate_lesson(lesson_id):
    if session.get("role") != "coach":
        return redirect(url_for("home"))

    coach_id = session.get("user_id")
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Controleer of de les bestaat in completed_lessons
    c.execute("""
        SELECT id, player_id, date, start_time, end_time
        FROM completed_lessons
        WHERE id=? AND coach_id=?
    """, (lesson_id, coach_id))
    lesson = c.fetchone()

    if not lesson:
        conn.close()
        return redirect(url_for("coach_dashboard"))

    # Haal spelerinformatie op
    c.execute("SELECT username FROM users WHERE id=?", (lesson[1],))
    speler = c.fetchone()

    if request.method == "POST":
        swot_strengths = request.form["swot_strengths"]
        swot_weaknesses = request.form["swot_weaknesses"]
        swot_opportunities = request.form["swot_opportunities"]
        swot_threats = request.form["swot_threats"]
        notes = request.form["notes"]
        rating = request.form["rating"]

        # Sla de evaluatie op in completed_lessons
        c.execute("""
            UPDATE completed_lessons
            SET swot_strengths=?, swot_weaknesses=?, swot_opportunities=?, swot_threats=?, notes=?, rating=?
            WHERE id=?
        """, (swot_strengths, swot_weaknesses, swot_opportunities, swot_threats, notes, rating, lesson_id))

        # Update progress van speler
        c.execute("""
            UPDATE progress
            SET strengths=?, weaknesses=?, p_score=?
            WHERE player_id=? AND coach_id=?
        """, (swot_strengths, swot_weaknesses, rating, lesson[1], coach_id))

        conn.commit()
        conn.close()
        return redirect(url_for("coach_dashboard"))

    conn.close()
    return render_template("evaluate_lesson.html", lesson=lesson, speler=speler)


# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(debug=True)











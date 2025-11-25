from flask import Flask, render_template, request, redirect, url_for, session
from datetime import date
from config import Config
from dotenv import load_dotenv
from supabase_client import supabase

app = Flask(__name__)
app.config.from_object(Config)

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

        email_input = request.form.get("email") 
        wachtwoord_input = request.form.get("password")

        print(f"Inlogpoging voor: {email_input}")

        try:
            resp_player = supabase.table("players").select("*").eq("email", email_input).eq("wachtwoord", wachtwoord_input).execute()
            
            if resp_player.data:
                user = resp_player.data[0]

                session["user_id"] = user["player_id"]
                session["role"] = "player"
                session["name"] = user["first_name"]
                session["assigned_coach"] = user.get("assigned_coach_id") 
                return redirect(url_for("player_dashboard"))

            resp_coach = supabase.table("coaches").select("*").eq("email", email_input).eq("wachtwoord", wachtwoord_input).execute()
            
            if resp_coach.data:
                user = resp_coach.data[0]

                session["user_id"] = user["coach_id"]
                session["role"] = "coach"
                session["name"] = user["first_name"]
                return redirect(url_for("coach_dashboard"))
            
            return render_template("login.html", error="E-mail of wachtwoord onjuist.")

        except Exception as e:
            print(f"Login error: {e}")
            return render_template("login.html", error="Er ging iets mis bij het inloggen.")

    return render_template("login.html")

# ---------- PLAYER DASHBOARD ----------
@app.route("/player")
def player_dashboard():
    # Alleen spelers mogen hier komen
    if session.get("role") != "player":
        return redirect(url_for("login"))

    player_id = session.get("user_id")

    # -----------------------------
    # Geplande lessen van deze speler
    # -----------------------------
    geplande = []
    try:
        resp_bookings = (
            supabase.table("bookings")
            .select("date, start_time, end_time, coach_id")
            .eq("player_id", player_id)
            .order("date", desc=False)
            .execute()
        )
        bookings = resp_bookings.data or []
        print("DEBUG /player bookings:", bookings)

        # unieke coach_ids verzamelen
        coach_ids = {b.get("coach_id") for b in bookings if b.get("coach_id") is not None}
        coach_name_by_id = {}

        if coach_ids:
            resp_coaches = (
                supabase.table("coaches")
                .select("coach_id, first_name, last_name")
                .in_("coach_id", list(coach_ids))
                .execute()
            )
            coach_rows = resp_coaches.data or []
            print("DEBUG /player coaches rows:", coach_rows)

            for c in coach_rows:
                cid = c.get("coach_id")
                naam = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                coach_name_by_id[cid] = naam or "Onbekend"

        # bookings + coachnamen samenvoegen in dicts voor de template
        for b in bookings:
            geplande.append({
                "date": b.get("date"),
                # '12:30:00' -> '12:30'
                "start_time": (b.get("start_time") or "")[:5],
                "end_time": (b.get("end_time") or "")[:5],
                "coach_name": coach_name_by_id.get(b.get("coach_id"), "Onbekend"),
            })

        print("DEBUG /player geplande:", geplande)

    except Exception as e:
        print(f"Fout bij ophalen geplande lessen speler: {e}")
        geplande = []

    # -----------------------------
    # Voortgang uit de tabel 'progress'
    # (laatste record voor deze speler)
    # -----------------------------
    progress = None
    try:
        resp_progress = (
            supabase.table("progress")
            .select("*")                    # alles ophalen, ongeacht kolomnamen
            .eq("player_id", player_id)
            .order("created_at", desc=True)  # of 'updated_at' als jij die gebruikt
            .limit(1)
            .execute()
        )
        rows = resp_progress.data or []
        print("DEBUG /player raw progress rows:", rows)

        if rows:
            r = rows[0]
            # Normaliseer naar vaste keys voor de template
            progress = {
                # probeer verschillende mogelijke kolomnamen voor P-score
                "p_score": r.get("p_ranking") or r.get("p_score") or r.get("ranking") or "",
                "hand": r.get("hand"),
                "strengths": r.get("strengths"),
                "weaknesses": r.get("weaknesses"),
            }
            print("DEBUG /player normalized progress:", progress)

    except Exception as e:
        print(f"Fout bij ophalen progress speler: {e}")
        progress = None

    return render_template(
        "player_dashboard.html",
        geplande=geplande,
        progress=progress,
    )

# ---------- REGISTER ----------
@app.route("/register")
def register():
    return render_template("register_choice.html")

@app.route("/register/player", methods=["GET", "POST"])
def register_player():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email_input = request.form.get("email")
        phone_input = request.form.get("phone")
        password_input = request.form.get("wachtwoord")

        if not email_input or not password_input or not first_name or not last_name:
            return render_template("register_player.html", error="Vul alle verplichte velden in.")
        
        user_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email_input,
            "phone": phone_input,
            "wachtwoord": password_input  
        }
        try:
            supabase.table("players").insert(user_data).execute()
            return redirect(url_for("login"))
        except Exception as e:
            print(f"Registratiefout: {e}. Probeer opnieuw.")
            return render_template("register_player.html", error="Er ging iets mis. Bestaat dit e-mailadres al?")
    return render_template("register_player.html")

@app.route("/register/coach", methods=["GET", "POST"])
def register_coach(): 
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email_input = request.form.get("email")
        phone_input = request.form.get("phone")
        password_input = request.form.get("wachtwoord")

        if not email_input or not password_input or not first_name or not last_name:
            return render_template("register_coach.html", error="Vul alle verplichte velden in.")
        
        user_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email_input,
            "phone": phone_input,
            "wachtwoord": password_input  
        }
        try:
            supabase.table("coaches").insert(user_data).execute()
            return redirect(url_for("login"))
        except Exception as e:
            print(f"Registratiefout: {e}. Probeer opnieuw.")
            return render_template("register_coach.html", error="Er ging iets mis. Bestaat dit e-mailadres al?")
    return render_template("register_coach.html")




# ---------- LES AANVRAGEN ----------
@app.route("/player/book_lesson", methods=["GET", "POST"])
def book_lesson():
    # Alleen spelers mogen hier binnen
    if session.get("role") != "player":
        return redirect(url_for("home"))

    player_id = session.get("user_id")

    # --- Coaches ophalen ---
    coaches = []
    try:
        resp_coaches = (
            supabase.table("coaches")
            .select("coach_id, first_name, last_name, email")
            .execute()
        )
        coaches = resp_coaches.data or []
    except Exception as e:
        print(f"Fout bij ophalen coaches: {e}")
        coaches = []

    # Waarden die we eventueel terug doorgeven aan de template
    selected_coach_id = None
    selected_date = None
    available_slots = []
    error = None

    if request.method == "POST":
        step = request.form.get("step")

        # -------------------------
        # STAP 1: coach + datum kiezen
        # -------------------------
        if step == "choose":
            selected_coach_id = request.form.get("coach_id")
            selected_date = request.form.get("date")

            if not selected_coach_id or not selected_date:
                error = "Kies een coach en datum."
            else:
                try:
                    # Haal bestaande bookings op voor die coach en datum
                    resp_bookings = (
                        supabase.table("bookings")
                        .select("start_time, end_time")
                        .eq("coach_id", selected_coach_id)
                        .eq("date", selected_date)
                        .execute()
                    )
                    existing_bookings = resp_bookings.data or []
                    print("DEBUG bestaande bookings:", existing_bookings)

                    # Mogelijke slots (pas aan naar wens)
                    possible_slots = [
                        {"start": "09:00", "end": "10:00"},
                        {"start": "10:00", "end": "11:00"},
                        {"start": "11:00", "end": "12:00"},
                        {"start": "12:00", "end": "13:00"},
                        {"start": "13:00", "end": "14:00"},
                        {"start": "14:00", "end": "15:00"},
                        {"start": "15:00", "end": "16:00"},
                        {"start": "16:00", "end": "17:00"},
                        {"start": "17:00", "end": "18:00"},
                        {"start": "18:00", "end": "19:00"},
                        {"start": "19:00", "end": "20:00"},
                        {"start": "20:00", "end": "21:00"},
                    ]

                    def is_free(slot_start, slot_end):
                        for b in existing_bookings:
                            b_start = (b.get("start_time") or "")[:5]  # '12:30:00' -> '12:30'
                            b_end = (b.get("end_time") or "")[:5]
                            # overlap als NIET (nieuw eind <= bestaand begin of nieuw begin >= bestaand eind)
                            if not (slot_end <= b_start or slot_start >= b_end):
                                return False
                        return True

                    available_slots = [
                        s for s in possible_slots
                        if is_free(s["start"], s["end"])
                    ]
                    print("DEBUG vrije slots:", available_slots)

                    if not available_slots:
                        error = "Er zijn geen vrije timeslots voor deze coach op deze datum."

                except Exception as e:
                    print(f"Fout bij bepalen slots: {e}")
                    error = "Er ging iets mis bij het ophalen van de tijden."

        # -------------------------
        # STAP 2: effectief boeken
        # -------------------------
        elif step == "book":
            selected_coach_id = request.form.get("coach_id")
            selected_date = request.form.get("date")
            chosen_slot = request.form.get("time_slot")  # bv "12:00-13:00"

            if not selected_coach_id or not selected_date or not chosen_slot:
                error = "Kies een coach, datum en tijdslot."
            else:
                try:
                    start_time, end_time = chosen_slot.split("-")
                    start_time = start_time.strip()
                    end_time = end_time.strip()

                    # Veiligheid: check nog eens op overlap
                    resp_bookings = (
                        supabase.table("bookings")
                        .select("start_time, end_time")
                        .eq("coach_id", selected_coach_id)
                        .eq("date", selected_date)
                        .execute()
                    )
                    existing_bookings = resp_bookings.data or []

                    overlap = False
                    for b in existing_bookings:
                        b_start = (b.get("start_time") or "")[:5]
                        b_end = (b.get("end_time") or "")[:5]
                        if not (end_time <= b_start or start_time >= b_end):
                            overlap = True
                            break

                    if overlap:
                        error = "❌ Iemand heeft net dit timeslot geboekt. Kies een ander slot."
                    else:
                        booking_data = {
                            "player_id": player_id,
                            "coach_id": int(selected_coach_id),
                            "date": selected_date,
                            "start_time": start_time,
                            "end_time": end_time,
                            "status": "geboekt",
                        }

                        resp_insert = supabase.table("bookings").insert(booking_data).execute()
                        print("DEBUG insert booking:", resp_insert.data)
                        return redirect(url_for("player_dashboard"))

                except Exception as e:
                    print(f"Fout bij boeken les: {e}")
                    error = "Er ging iets mis bij het boeken. Probeer later opnieuw."

    # GET of na fout: render pagina
    return render_template(
        "book_lesson.html",
        coaches=coaches,
        error=error,
        selected_coach_id=selected_coach_id,
        selected_date=selected_date,
        available_slots=available_slots,
    )

# ---------- COACH ----------
# ---------- COACH DASHBOARD ----------
@app.route("/coach")
def coach_dashboard():
    # Alleen coaches mogen hier binnen
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")
    today = date.today().isoformat()

    # -----------------------------
    # Stap 1: spelers van deze coach + hun progressie
    # -----------------------------
    spelers = []

    try:
        # Haal alle spelers op aan wie deze coach is toegewezen
        resp_players = (
            supabase.table("players")
            .select("*")
            .eq("assigned_coach_id", coach_id)
            .execute()
        )
        players = resp_players.data or []

        # Verzamel alle player_ids
        player_ids = [p.get("player_id") for p in players if p.get("player_id") is not None]

        progress_by_player = {}
        if player_ids:
            # Haal alle progress records voor deze coach en deze spelers
            resp_progress = (
                supabase.table("progress")
                .select("*")
                .eq("coach_id", coach_id)
                .in_("player_id", player_ids)
                .execute()
            )
            progress_rows = resp_progress.data or []

            # Map per player_id
            for row in progress_rows:
                pid = row.get("player_id")
                if pid is not None:
                    progress_by_player[pid] = row

        # Merge player-info + progress-info
        for p in players:
            pid = p.get("player_id")
            merged = dict(p)  # kopie van player-row
            prog = progress_by_player.get(pid)
            if prog:
                merged["p_score"] = prog.get("p_score")
                merged["hand"] = prog.get("hand")
                merged["strengths"] = prog.get("strengths")
                merged["weaknesses"] = prog.get("weaknesses")
            else:
                merged["p_score"] = None
                merged["hand"] = None
                merged["strengths"] = None
                merged["weaknesses"] = None

            spelers.append(merged)

    except Exception as e:
        print(f"Fout bij ophalen spelers/progress: {e}")
        spelers = []

    # -----------------------------
    # Stap 2: verplaats oude bookings naar completed_lessons
    # -----------------------------
    try:
        resp_past = (
            supabase.table("bookings")
            .select("*")
            .eq("coach_id", coach_id)
            .lt("date", today)
            .execute()
        )
        past_lessons = resp_past.data or []

        for les in past_lessons:
            comp_data = {
                "player_id": les.get("player_id"),
                "coach_id": coach_id,
                "date": les.get("date"),
                "start_time": les.get("start_time"),
                "end_time": les.get("end_time"),
                # extra velden (notes, rating, ...) kun je later nog toevoegen
            }

            # Voeg toe aan completed_lessons
            supabase.table("completed_lessons").insert(comp_data).execute()

            # Verwijder uit bookings
            les_id = les.get("id")
            if les_id is not None:
                supabase.table("bookings").delete().eq("id", les_id).execute()

    except Exception as e:
        print(f"Fout bij verplaatsen van bookings naar completed_lessons: {e}")

    # -----------------------------
    # Stap 3: geplande (toekomstige) lessen ophalen
    # -----------------------------
    geplande_lessen = []
    try:
        resp_future = (
            supabase.table("bookings")
            .select("*")
            .eq("coach_id", coach_id)
            .gte("date", today)
            .order("date", desc=False)
            .execute()
        )
        geplande_lessen = resp_future.data or []
    except Exception as e:
        print(f"Fout bij ophalen geplande lessen: {e}")
        geplande_lessen = []

    # -----------------------------
    # Stap 4: afgelopen lessen ophalen
    # -----------------------------
    afgelopen_lessen = []
    try:
        resp_completed = (
            supabase.table("completed_lessons")
            .select("*")
            .eq("coach_id", coach_id)
            .order("date", desc=True)
            .execute()
        )
        afgelopen_lessen = resp_completed.data or []
    except Exception as e:
        print(f"Fout bij ophalen completed_lessons: {e}")
        afgelopen_lessen = []

    # -----------------------------
    # Stap 5: render de pagina
    # -----------------------------
    return render_template(
        "coach_dashboard.html",
        spelers=spelers,
        lessen=geplande_lessen,
        completed=afgelopen_lessen,
    )

# ---------- COACH: Speler toevoegen ----------
@app.route("/coach/add_player", methods=["GET", "POST"])
def add_player():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    # 🔹 Haal spelers op die nog GEEN coach hebben
    spelers = []
    try:
        resp_players = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email, phone")
            .is_("assigned_coach_id", None)   # alleen spelers zonder toegewezen coach
            .execute()
        )
        spelers = resp_players.data or []
    except Exception as e:
        print(f"Fout bij ophalen beschikbare spelers: {e}")
        spelers = []

    if request.method == "POST":
        player_id = request.form.get("player_id")
        p_score = request.form.get("p_score")
        hand = request.form.get("hand")
        strengths = request.form.get("strengths")
        weaknesses = request.form.get("weaknesses")

        if not player_id:
            return render_template(
                "add_player.html",
                spelers=spelers,
                error="Kies eerst een speler."
            )

        try:
            # 🔹 Controleer of speler al een coach heeft
            resp_player = (
                supabase.table("players")
                .select("assigned_coach_id")
                .eq("player_id", player_id)
                .single()
                .execute()
            )

            assigned = resp_player.data.get("assigned_coach_id") if resp_player.data else None
            if assigned is not None:
                return render_template(
                    "add_player.html",
                    spelers=spelers,
                    error="Deze speler is al gekoppeld aan een coach!"
                )

            # 🔹 Koppel speler aan deze coach
            supabase.table("players").update(
                {"assigned_coach_id": coach_id}
            ).eq("player_id", player_id).execute()

            # 🔹 Voeg een progress-record toe voor deze speler bij deze coach
            progress_data = {
                "player_id": player_id,
                "coach_id": coach_id,
                "p_score": p_score if p_score else None,
                "hand": hand,
                "strengths": strengths,
                "weaknesses": weaknesses,
            }
            supabase.table("progress").insert(progress_data).execute()

            return redirect(url_for("coach_dashboard"))

        except Exception as e:
            print(f"Fout bij koppelen speler aan coach: {e}")
            return render_template(
                "add_player.html",
                spelers=spelers,
                error="Er ging iets mis bij het toevoegen. Probeer later opnieuw."
            )

    # GET: toon formulier
    return render_template("add_player.html", spelers=spelers)

# ---------- COACH: Les inplannen (keuzepagina) ----------
@app.route("/coach/schedule_lesson")
def schedule_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("login"))
    return render_template("schedule_lesson_choice.html")

# ---------- COACH: Groepsles ----------
@app.route("/coach/schedule_group_lesson", methods=["GET", "POST"])
def schedule_group_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    # Spelers ophalen die gekoppeld zijn aan deze coach
    spelers = []
    try:
        resp_spelers = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email")
            .eq("assigned_coach_id", coach_id)
            .execute()
        )
        spelers = resp_spelers.data or []
    except Exception as e:
        print(f"Fout bij ophalen spelers voor groepsles: {e}")
        spelers = []

    if request.method == "POST":
        selected_players = request.form.getlist("player_ids")

        # Minstens 2 en max 5 spelers
        if len(selected_players) < 2:
            return render_template(
                "schedule_group_lesson.html",
                spelers=spelers,
                error="❌ Selecteer minstens 2 spelers (max. 5)."
            )
        if len(selected_players) > 5:
            return render_template(
                "schedule_group_lesson.html",
                spelers=spelers,
                error="❌ Je mag maximaal 5 spelers selecteren."
            )

        date = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        lesson_type = request.form.get("lesson_type")  # momenteel niet opgeslagen
        notes = request.form.get("notes")              # momenteel niet opgeslagen

        if not date or not start_time or not end_time:
            return render_template(
                "schedule_group_lesson.html",
                spelers=spelers,
                error="Vul alle velden (datum en uren) in."
            )

        try:
            # Per speler een booking aanmaken in Supabase
            bookings = []
            for player_id in selected_players:
                bookings.append(
                    {
                        "player_id": player_id,
                        "coach_id": coach_id,
                        "date": date,
                        "start_time": start_time,
                        "end_time": end_time,
                        "status": "geboekt",
                        # Als jullie later kolommen toevoegen zoals 'lesson_type' of 'notes',
                        # kunnen die hier ook toegevoegd worden.
                    }
                )

            # In één keer meerdere bookings inserten
            supabase.table("bookings").insert(bookings).execute()

            return redirect(url_for("coach_dashboard"))

        except Exception as e:
            print(f"Fout bij inplannen groepsles: {e}")
            return render_template(
                "schedule_group_lesson.html",
                spelers=spelers,
                error="Er ging iets mis bij het inplannen. Probeer later opnieuw."
            )

    # GET: toon formulier met spelerslijst
    return render_template("schedule_group_lesson.html", spelers=spelers)

# ---------- COACH: Individuele les ----------
@app.route("/coach/schedule_individual_lesson", methods=["GET", "POST"])
def schedule_individual_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    # Spelers ophalen die gekoppeld zijn aan deze coach
    spelers = []
    try:
        resp_spelers = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email")
            .eq("assigned_coach_id", coach_id)
            .execute()
        )
        spelers = resp_spelers.data or []
    except Exception as e:
        print(f"Fout bij ophalen spelers voor individuele les: {e}")
        spelers = []

    if request.method == "POST":
        player_id = request.form.get("player_id")
        date = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        lesson_type = request.form.get("lesson_type")  # nog niet gebruikt
        notes = request.form.get("notes")              # nog niet gebruikt

        if not player_id or not date or not start_time or not end_time:
            return render_template(
                "schedule_individual_lesson.html",
                spelers=spelers,
                error="Vul alle velden in."
            )

        try:
            booking_data = {
                "player_id": player_id,
                "coach_id": coach_id,
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "status": "geboekt",
                # Als jullie later kolommen zoals 'lesson_type' of 'notes' toevoegen
                # aan de bookings-tabel, kunnen die hier ook worden opgeslagen.
            }

            supabase.table("bookings").insert(booking_data).execute()

            return redirect(url_for("coach_dashboard"))

        except Exception as e:
            print(f"Fout bij inplannen individuele les: {e}")
            return render_template(
                "schedule_individual_lesson.html",
                spelers=spelers,
                error="Er ging iets mis bij het inplannen. Probeer later opnieuw."
            )

    # GET: toon formulier met spelerslijst
    return render_template("schedule_individual_lesson.html", spelers=spelers)

# ---------- COACH: Speler detailpagina ----------
@app.route("/coach/player/<int:player_id>")
def view_player(player_id):
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    # Basisinfo van de speler ophalen uit Supabase
    speler = None
    try:
        resp_speler = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email, phone, sport")
            .eq("player_id", player_id)
            .single()
            .execute()
        )
        speler = resp_speler.data
    except Exception as e:
        print(f"Fout bij ophalen speler {player_id}: {e}")
        speler = None

    # Alle progressie-updates ophalen uit Supabase
    progressies = []
    try:
        resp_progress = (
            supabase.table("progress")
            .select("p_score, hand, strengths, weaknesses, updated_at")
            .eq("player_id", player_id)
            .eq("coach_id", coach_id)
            .order("updated_at", desc=True)
            .execute()
        )
        progressies = resp_progress.data or []
    except Exception as e:
        print(f"Fout bij ophalen progress voor speler {player_id}: {e}")
        progressies = []

    return render_template(
        "player_detail.html",
        speler=speler,
        progressies=progressies
    )

# ---------- COACH: Speler verwijderen ----------
@app.route("/coach/remove_player/<int:player_id>")
def remove_player(player_id):
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    try:
        # 1. Verwijder koppeling tussen coach en speler
        supabase.table("players").update(
            {"assigned_coach_id": None}
        ).eq("player_id", player_id).execute()

        # 2. Verwijder progress van deze speler bij deze coach
        supabase.table("progress").delete().eq("player_id", player_id).eq("coach_id", coach_id).execute()

    except Exception as e:
        print(f"Fout bij verwijderen speler: {e}")

    return redirect(url_for("coach_dashboard"))

# ---------- ADMIN ----------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    users = []

    try:
        # 🔹 Alle spelers ophalen
        resp_players = (
            supabase.table("players")
            .select("player_id, first_name, last_name, sport")
            .execute()
        )
        players = resp_players.data or []

        for p in players:
            users.append({
                "id": p.get("player_id"),
                "username": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                "role": "player",
                "sport": p.get("sport"),
            })

        # 🔹 Alle coaches ophalen
        resp_coaches = (
            supabase.table("coaches")
            .select("coach_id, first_name, last_name, sport")
            .execute()
        )
        coaches = resp_coaches.data or []

        for c in coaches:
            users.append({
                "id": c.get("coach_id"),
                "username": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                "role": "coach",
                "sport": c.get("sport"),
            })

    except Exception as e:
        print(f"Fout bij ophalen users in admin_dashboard: {e}")
        users = []

    return render_template("admin_dashboard.html", users=users)


@app.route("/admin/delete/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    try:
        # Probeer speler te verwijderen
        supabase.table("players").delete().eq("player_id", user_id).execute()
        # Probeer coach te verwijderen
        supabase.table("coaches").delete().eq("coach_id", user_id).execute()
    except Exception as e:
        print(f"Fout bij delete_user({user_id}): {e}")

    return redirect(url_for("admin_dashboard"))


# ---------- ADMIN: Speler detail ----------
@app.route("/admin/player/<int:player_id>")
def admin_view_player(player_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    # -----------------------------
    # Basisgegevens speler
    # -----------------------------
    speler = None
    try:
        resp_speler = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email, phone, sport")
            .eq("player_id", player_id)
            .single()
            .execute()
        )
        speler = resp_speler.data
    except Exception as e:
        print(f"Fout bij ophalen speler {player_id}: {e}")
        speler = None

    if not speler:
        # Admin-dashboard tonen met foutmelding als speler niet bestaat
        return render_template(
            "admin_dashboard.html",
            error="Speler niet gevonden!",
            users=[]
        )

    # Voeg 'role' toe zodat template iets gelijkaardigs heeft als vroeger
    speler["role"] = "player"

    # -----------------------------
    # Voortgangsgegevens
    # -----------------------------
    progress = []
    try:
        resp_progress = (
            supabase.table("progress")
            .select("p_score, hand, strengths, weaknesses, updated_at, coach_id")
            .eq("player_id", player_id)
            .order("updated_at", desc=True)
            .execute()
        )
        progress = resp_progress.data or []
    except Exception as e:
        print(f"Fout bij ophalen progress voor speler {player_id}: {e}")
        progress = []

    # -----------------------------
    # Lessen (gepland + afgelopen)
    # -----------------------------
    lessen = []   # lijst van (date, coach_id)
    try:
        # Geplande lessen (bookings)
        resp_bookings = (
            supabase.table("bookings")
            .select("date, coach_id")
            .eq("player_id", player_id)
            .execute()
        )
        bookings = resp_bookings.data or []
        for b in bookings:
            lessen.append((b.get("date"), b.get("coach_id")))

        # Afgelopen lessen (completed_lessons)
        resp_completed = (
            supabase.table("completed_lessons")
            .select("date, coach_id")
            .eq("player_id", player_id)
            .execute()
        )
        completed = resp_completed.data or []
        for c in completed:
            lessen.append((c.get("date"), c.get("coach_id")))

        # Sorteer alles op datum (nieuwste eerst, als je dat wil)
        lessen.sort(key=lambda x: x[0], reverse=True)

    except Exception as e:
        print(f"Fout bij ophalen lessen voor speler {player_id}: {e}")
        lessen = []

    # -----------------------------
    # Coachnamen ophalen
    # -----------------------------
    coachen = []
    try:
        coach_ids = {coach_id for _, coach_id in lessen if coach_id is not None}
        coach_name_by_id = {}

        if coach_ids:
            resp_coaches = (
                supabase.table("coaches")
                .select("coach_id, first_name, last_name")
                .in_("coach_id", list(coach_ids))
                .execute()
            )
            coaches_rows = resp_coaches.data or []
            for row in coaches_rows:
                cid = row.get("coach_id")
                naam = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
                coach_name_by_id[cid] = naam or "Onbekend"

        # Maak de coachen-lijst in dezelfde volgorde als lessen
        for _, coach_id in lessen:
            coachen.append(coach_name_by_id.get(coach_id, "Onbekend"))

    except Exception as e:
        print(f"Fout bij ophalen coachnamen voor speler {player_id}: {e}")
        coachen = ["Onbekend" for _ in lessen]

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
    return redirect(url_for("login"))

# ---------- COACH: Les evalueren ----------
@app.route("/coach/evaluate_lesson/<int:lesson_id>", methods=["GET", "POST"])
def evaluate_lesson(lesson_id):
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    # -----------------------------
    # Les ophalen uit completed_lessons
    # -----------------------------
    try:
        resp_lesson = (
            supabase.table("completed_lessons")
            .select("id, player_id, date, start_time, end_time, swot_strengths, swot_weaknesses, swot_opportunities, swot_threats, notes, rating")
            .eq("id", lesson_id)
            .eq("coach_id", coach_id)
            .single()
            .execute()
        )
        lesson = resp_lesson.data
    except Exception as e:
        print(f"Fout bij ophalen les {lesson_id}: {e}")
        lesson = None

    if not lesson:
        return redirect(url_for("coach_dashboard"))

    player_id = lesson.get("player_id")

    # -----------------------------
    # Spelerinformatie ophalen
    # -----------------------------
    speler = None
    try:
        resp_speler = (
            supabase.table("players")
            .select("first_name, last_name")
            .eq("player_id", player_id)
            .single()
            .execute()
        )
        if resp_speler.data:
            speler = f"{resp_speler.data.get('first_name', '')} {resp_speler.data.get('last_name', '')}".strip()
        else:
            speler = "Onbekende speler"
    except Exception as e:
        print(f"Fout bij ophalen speler {player_id}: {e}")
        speler = "Onbekende speler"

    if request.method == "POST":
        swot_strengths = request.form.get("swot_strengths")
        swot_weaknesses = request.form.get("swot_weaknesses")
        swot_opportunities = request.form.get("swot_opportunities")
        swot_threats = request.form.get("swot_threats")
        notes = request.form.get("notes")
        rating = request.form.get("rating")

        try:
            # -----------------------------
            # Evaluatie opslaan in completed_lessons
            # -----------------------------
            supabase.table("completed_lessons").update({
                "swot_strengths": swot_strengths,
                "swot_weaknesses": swot_weaknesses,
                "swot_opportunities": swot_opportunities,
                "swot_threats": swot_threats,
                "notes": notes,
                "rating": rating,
            }).eq("id", lesson_id).execute()

            # -----------------------------
            # Progress van speler updaten
            # -----------------------------
            supabase.table("progress").update({
                "strengths": swot_strengths,
                "weaknesses": swot_weaknesses,
                "p_score": rating,
            }).eq("player_id", player_id).eq("coach_id", coach_id).execute()

            return redirect(url_for("coach_dashboard"))

        except Exception as e:
            print(f"Fout bij evalueren les {lesson_id}: {e}")
            return render_template(
                "evaluate_lesson.html",
                lesson=lesson,
                speler=speler,
                error="Er ging iets mis bij het opslaan van de evaluatie. Probeer later opnieuw."
            )

    # GET: toon evaluatieformulier
    return render_template("evaluate_lesson.html", lesson=lesson, speler=speler)

# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(debug=True)














        


















    


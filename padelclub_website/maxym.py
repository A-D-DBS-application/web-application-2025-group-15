from dotenv import load_dotenv
load_dotenv()  # <-- verplicht .env laden vóór supabase_client

from config import Config
from supabase_client import supabase
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

 # ---------- LOGIN ZONDER WACHTWOORD ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email_input = request.form.get("email", "").strip()
        print(f"Inlogpoging voor: {email_input}")

        if not email_input:
            return render_template("login.html", error="Vul je e-mailadres in.")

        try:
            # 1) PROBEER ALS SPELER
            resp_player = (
                supabase
                .table("players")
                .select("*")
                .eq("email", email_input)
                .execute()
            )
            print("DEBUG resp_player.data =", resp_player.data)

            players = resp_player.data or []
            if len(players) > 0:
                player = players[0]   # eerste match
                session["user_id"] = player["player_id"]
                session["role"] = "player"
                session["name"] = player.get("first_name") or ""
                session["assigned_coach"] = player.get("assigned_coach_id")
                print("✅ Ingelogd als SPELER:", session)
                return redirect(url_for("player_dashboard"))

            # 2) ZO NIET: PROBEER ALS COACH
            resp_coach = (
                supabase
                .table("coaches")
                .select("*")
                .eq("email", email_input)
                .execute()
            )
            print("DEBUG resp_coach.data =", resp_coach.data)

            coaches = resp_coach.data or []
            if len(coaches) > 0:
                coach = coaches[0]
                session["user_id"] = coach["coach_id"]
                session["role"] = "coach"
                session["name"] = coach.get("first_name") or ""
                print("✅ Ingelogd als COACH:", session)
                return redirect(url_for("coach_dashboard"))

            # 3) GEEN MATCH
            return render_template(
                "login.html",
                error="Geen account gevonden met dit e-mailadres."
            )

        except Exception as e:
            print("❌ Login error:", repr(e))
            return render_template(
                "login.html",
                error="Er ging iets mis bij het inloggen. Probeer later opnieuw."
            )

    # GET: toon loginpagina
    return render_template("login.html")


# ---------- PLAYER DASHBOARD ----------
@app.route("/player")
def player_dashboard():
    if session.get("role") != "player":
        return redirect(url_for("login"))

    player_id = session.get("user_id")

    geplande = []
    progress = None  # voorlopig geen voortgangstabel meer

    try:
        # 1) alle lesson_ids ophalen voor deze speler
        resp_lp = (
            supabase.table("lesson_players")
            .select("lesson_id")
            .eq("player_id", player_id)
            .execute()
        )
        lp_rows = resp_lp.data or []
        lesson_ids = [r.get("lesson_id") for r in lp_rows if r.get("lesson_id") is not None]
        print("DEBUG /player lesson_ids:", lesson_ids)

        if lesson_ids:
            # 2) bijhorende lessen ophalen
            resp_lessons = (
                supabase.table("lessons")
                .select("lesson_id, date, start_time, end_time, coach_id")
                .in_("lesson_id", lesson_ids)
                .order("date", desc=False)
                .execute()
            )
            lesson_rows = resp_lessons.data or []
            print("DEBUG /player lessons:", lesson_rows)

            # 3) coach-namen ophalen
            coach_ids = {l.get("coach_id") for l in lesson_rows if l.get("coach_id") is not None}
            coach_name_by_id = {}
            if coach_ids:
                resp_coaches = (
                    supabase.table("coaches")
                    .select("coach_id, first_name, last_name")
                    .in_("coach_id", list(coach_ids))
                    .execute()
                )
                for c in (resp_coaches.data or []):
                    cid = c.get("coach_id")
                    naam = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                    coach_name_by_id[cid] = naam or "Onbekend"

            # 4) alles samenvoegen voor de template
            for les in lesson_rows:
                geplande.append({
                    "date": les.get("date"),
                    "start_time": (les.get("start_time") or "")[:5],
                    "end_time": (les.get("end_time") or "")[:5],
                    "coach_name": coach_name_by_id.get(les.get("coach_id"), "Onbekend"),
                })

        print("DEBUG /player geplande:", geplande)

    except Exception as e:
        print("Fout bij ophalen geplande lessen speler:", e)
        geplande = []

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
def register_player_step1():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")

        if not email or not first_name or not last_name:
            return render_template("register_player_step1.html", error="Vul alle verplichte velden in.")

        # Check duplicaten
        try:
            if supabase.table("players").select("player_id").eq("email", email).execute().data:
                return render_template("login.html", error="Dit e-mailadres bestaat al. Log hier in.")
            if supabase.table("coaches").select("coach_id").eq("email", email).execute().data:
                return render_template("login.html", error="Dit e-mailadres is al geregistreerd als coach.")
        except: pass

        session["player_data"] = {
            "first_name": first_name, "last_name": last_name, "email": email, "phone": phone
        }
        return redirect(url_for("register_player_step2"))

    return render_template("register_player_step1.html")

@app.route("/register/player/step2", methods=["GET", "POST"])
def register_player_step2():
    if "player_data" not in session: 
        return redirect(url_for("register_player_step1"))

    if request.method == "POST":
        data = session["player_data"]
        data["ranking"] = request.form.get("ranking")
        data["hand_preference"] = request.form.get("hand_preference")
        data["gender"] = request.form.get("gender")

        try:
            supabase.table("players").insert(data).execute()
            session.pop("player_data", None)
            return render_template("login.html", error="Account aangemaakt! Je kunt nu inloggen.")
        except Exception as e:
            print(f"Reg error: {e}")
            return render_template("register_player_step2.html", error="Er ging iets mis bij het opslaan.")

    return render_template("register_player_step2.html")

@app.route("/register/coach", methods=["GET", "POST"])
def register_coach():
    if request.method == "POST":
        data = {
            "first_name": request.form.get("first_name"),
            "last_name": request.form.get("last_name"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone")
        }
        
        try:
            if supabase.table("coaches").select("coach_id").eq("email", data["email"]).execute().data:
                return render_template("login.html", error="Coach bestaat al. Log hier in.")
        except: pass

        try:
            supabase.table("coaches").insert(data).execute()
            return render_template("login.html", error="Coach account aangemaakt!")
        except Exception as e:
            return render_template("register_coach.html", error=f"Fout: {e}")

    return render_template("register_coach.html")





# ---------- LES AANVRAGEN ----------
@app.route("/player/book_lesson", methods=["GET", "POST"])
def book_lesson():
    # Alleen spelers mogen hier binnen
    if session.get("role") != "player":
        return redirect(url_for("home"))

    player_id = session.get("user_id")

    # Coaches ophalen (voor dropdown)
    coaches = []
    try:
        resp_coaches = (
            supabase.table("coaches")
            .select("coach_id, first_name, last_name, email")
            .execute()
        )
        coaches = resp_coaches.data or []
        print("DEBUG coaches:", coaches)
    except Exception as e:
        print("Fout bij ophalen coaches:", repr(e))
        coaches = []

    available_slots = None
    selected_coach_id = None
    selected_date = None
    error = None

    # Basis lijst van mogelijke tijdsloten (1 uur)
    ALL_SLOTS = [
        ("09:00", "10:00"),
        ("10:00", "11:00"),
        ("11:00", "12:00"),
        ("12:00", "13:00"),
        ("13:00", "14:00"),
        ("14:00", "15:00"),
        ("15:00", "16:00"),
        ("16:00", "17:00"),
        ("17:00", "18:00"),
        ("18:00", "19:00"),
        ("19:00", "20:00"),
    ]

    if request.method == "POST":
        action = request.form.get("action")  # 'show_slots' of 'book'
        selected_coach_id = request.form.get("coach_id") or None
        selected_date = request.form.get("date") or None

        # ---- STAP 1: tijdsloten tonen ----
        if action == "show_slots":
            if not selected_coach_id or not selected_date:
                error = "Kies eerst een coach en een datum."
            else:
                try:
                    coach_id_int = int(selected_coach_id)

                    # Alle bestaande lessen voor deze coach + datum
                    resp_lessons = (
                        supabase.table("lessons")
                        .select("start_time, end_time")
                        .eq("coach_id", coach_id_int)
                        .eq("date", selected_date)
                        .execute()
                    )
                    existing = resp_lessons.data or []
                    print("DEBUG bestaande lessen:", existing)

                    taken = set()
                    for row in existing:
                        s = (row.get("start_time") or "")[:5]  # '09:00'
                        e = (row.get("end_time") or "")[:5]    # '10:00'
                        if s and e:
                            taken.add(f"{s}-{e}")

                    # Vrije slots = alle slots die niet in taken zitten
                    available_slots = []
                    for s, e in ALL_SLOTS:
                        slot_id = f"{s}-{e}"
                        if slot_id not in taken:
                            available_slots.append({
                                "id": slot_id,
                                "label": f"{s} – {e}",
                                "start": s,
                                "end": e,
                            })

                    if not available_slots:
                        error = "Geen vrije tijdsloten voor deze datum."

                except Exception as e:
                    print("Fout bij ophalen tijdsloten:", repr(e))
                    error = "Er ging iets mis bij het ophalen van de tijdsloten."

                # ---- STAP 2: geselecteerd slot boeken ----
        elif action == "book":
            slot_id = request.form.get("slot")  # bv. '09:00-10:00'

            if not selected_coach_id or not selected_date or not slot_id:
                error = "Kies een coach, datum én tijdslot."
            else:
                try:
                    coach_id_int = int(selected_coach_id)
                    player_id_int = int(player_id)
                    start_str, end_str = slot_id.split("-")  # "09:00", "10:00"

                    # 1) les zelf in lessons
                    booking_data = {
                        "coach_id": coach_id_int,
                        "date": selected_date,
                        "start_time": start_str,  # Supabase maakt hier een time van
                        "end_time": end_str,
                    }

                    print("DEBUG nieuwe les:", booking_data)
                    resp_insert = supabase.table("lessons").insert(booking_data).execute()
                    print("DEBUG insert response:", resp_insert)

                    if getattr(resp_insert, "error", None):
                        raise Exception(resp_insert.error)

                    # 2) de net aangemaakte lesson_id ophalen
                    inserted_rows = resp_insert.data or []
                    if not inserted_rows:
                        raise Exception("Geen data terug van lessons-insert")

                    lesson_id = inserted_rows[0].get("lesson_id")
                    if not lesson_id:
                        raise Exception("lesson_id ontbreekt in insert-respons")

                    # 3) koppeling speler ↔ les in lesson_players
                    lp_data = {
                        "lesson_id": lesson_id,
                        "player_id": player_id_int,
                    }
                    print("DEBUG lesson_players insert:", lp_data)
                    resp_lp = supabase.table("lesson_players").insert(lp_data).execute()
                    print("DEBUG lesson_players response:", resp_lp)

                    if getattr(resp_lp, "error", None):
                        raise Exception(resp_lp.error)

                    return redirect(url_for("player_dashboard"))

                except Exception as e:
                    print("Fout bij boeken les:", repr(e))
                    error = "Er ging iets mis bij het boeken. Probeer later opnieuw."

    # GET of POST met fouten → pagina tonen
    return render_template(
        "book_lesson.html",
        coaches=coaches,
        available_slots=available_slots,
        selected_coach_id=selected_coach_id,
        selected_date=selected_date,
        error=error,
    )

# ---------- COACH ----------
# ---------- COACH DASHBOARD ----------
@app.route("/coach")
def coach_dashboard():
    # Alleen coaches mogen hier binnen
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    # -----------------------------
    # 1. Spelers van deze coach
    # -----------------------------
    spelers = []
    try:
        resp_players = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email, phone")
            .eq("assigned_coach_id", coach_id)
            .execute()
        )
        spelers = resp_players.data or []
        print("DEBUG coach spelers:", spelers)
    except Exception as e:
        print("Fout bij ophalen spelers:", e)
        spelers = []

    # -----------------------------
    # 2. Lessen van deze coach
    # lessons + lesson_players + players
    # -----------------------------
    lessen = []
    try:
        # Alle lessen waar deze coach lesgeeft
        resp_lessons = (
            supabase.table("lessons")
            .select("lesson_id, date, start_time, end_time, coach_id")
            .eq("coach_id", coach_id)
            .order("date", desc=False)
            .execute()
        )
        lesson_rows = resp_lessons.data or []
        print("DEBUG coach lessons:", lesson_rows)

        lesson_ids = [l.get("lesson_id") for l in lesson_rows if l.get("lesson_id") is not None]

        # Koppeltabel lesson_player: welke spelers zitten in welke les?
        lp_by_lesson = {}
        if lesson_ids:
            resp_lp = (
                supabase.table("lesson_players")
                .select("lesson_id, player_id")
                .in_("lesson_id", lesson_ids)
                .execute()
            )
            lp_rows = resp_lp.data or []
            print("DEBUG coach lesson_player:", lp_rows)

            for row in lp_rows:
                lid = row.get("lesson_id")
                pid = row.get("player_id")
                if lid is None or pid is None:
                    continue
                lp_by_lesson.setdefault(lid, []).append(pid)

        # Alle player_ids die in één van die lessen zitten
        all_player_ids = sorted({pid for pids in lp_by_lesson.values() for pid in pids})
        name_by_player = {}

        if all_player_ids:
            resp_pnames = (
                supabase.table("players")
                .select("player_id, first_name, last_name")
                .in_("player_id", all_player_ids)
                .execute()
            )
            p_rows = resp_pnames.data or []
            print("DEBUG coach players_for_lessons:", p_rows)

            for r in p_rows:
                pid = r.get("player_id")
                if pid is None:
                    continue
                naam = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                name_by_player[pid] = naam or f"Speler {pid}"

        # Bouw nette lessen-lijst voor de template
        for les in lesson_rows:
            lid = les.get("lesson_id")
            pids = lp_by_lesson.get(lid, [])
            namen = [name_by_player.get(pid, f"Speler {pid}") for pid in pids]

            lessen.append({
                "date": les.get("date"),
                "start_time": (les.get("start_time") or "")[:5],  # '09:00:00' -> '09:00'
                "end_time": (les.get("end_time") or "")[:5],
                "players": ", ".join(namen) if namen else "Geen spelers gekoppeld",
            })

    except Exception as e:
        print("Fout bij ophalen lessen coach:", e)
        lessen = []

    # -----------------------------
    # 3. Render dashboard
    # -----------------------------
    return render_template(
        "coach_dashboard.html",
        spelers=spelers,
        lessen=lessen,
    )

# ---------- COACH: Speler toevoegen ----------
@app.route("/coach/add_player", methods=["GET", "POST"])
def add_player():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")
    error = None
    spelers = []



    # ---------- POST: speler koppelen ----------
    if request.method == "POST":
        player_id = request.form.get("player_id")

        if not player_id:
            error = "Geen speler geselecteerd."
        else:
            try:
                # Check of speler al een coach heeft
                resp_player = (
                    supabase.table("players")
                    .select("assigned_coach_id")
                    .eq("player_id", player_id)
                    .maybe_single()
                    .execute()
                )
                assigned = None
                if resp_player.data:
                    assigned = resp_player.data.get("assigned_coach_id")

                if assigned is not None:
                    error = "Deze speler is al gekoppeld aan een coach."
                else:
                    # Koppel speler aan deze coach
                    supabase.table("players").update(
                        {"assigned_coach_id": coach_id}
                    ).eq("player_id", player_id).execute()

                    return redirect(url_for("coach_dashboard"))

            except Exception as e:
                print(f"Fout bij koppelen speler aan coach: {e}")
                error = "Er ging iets mis bij het koppelen. Probeer later opnieuw."

    # ---------- GET (en ook als er een fout was): lijst met spelers tonen ----------
    q = request.args.get("q", "").strip()

    try:
        query = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email, phone")
            .is_("assigned_coach_id", None)  # alleen spelers zonder coach
        )

        # Heel simpel: filter op voornaam (kan later uitgebreid worden)
        if q:
            query = query.ilike("first_name", f"%{q}%")

        resp_spelers = query.execute()
        spelers = resp_spelers.data or []

    except Exception as e:
        print(f"Fout bij ophalen/zoeken spelers: {e}")
        spelers = []
        if not error:
            error = "Er ging iets mis bij het ophalen van spelers."

    return render_template(
        "add_player.html",
        spelers=spelers,
        q=q,
        error=error,
    )

# ---------- COACH: Speler verwijderen ----------
@app.route("/coach/remove_player/<int:player_id>")
def remove_player(player_id):
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    try:
        supabase.table("players").update(
            {"assigned_coach_id": None}
        ).eq("player_id", player_id).execute()

    except Exception as e:
        print(f"Fout bij verwijderen speler: {e}")

    return redirect(url_for("coach_dashboard"))

# ---------- COACH: Les inplannen (keuzepagina) ---------- #werkt niet
@app.route("/coach/schedule_lesson")
def schedule_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("login"))
    return render_template("schedule_lesson_choice.html")

# ---------- COACH: Groepsles ----------            #werkt niet
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

# ---------- COACH: Individuele les ----------   #werkt niet
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

# ---------- COACH: Speler detailpagina ----------   #werkt niet omdat er geen progress tabel meer is in supabase (html ook niet in orde denkik)
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




# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(debug=True)














        


















    


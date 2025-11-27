from dotenv import load_dotenv
load_dotenv() 

from config import Config
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import date
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
        email_input = request.form.get("email", "").strip()
        
        if not email_input:
            return render_template("login.html", error="Vul je e-mailadres in.")

        try:
            # 1. Check Players
            resp_player = supabase.table("players").select("*").eq("email", email_input).execute()
            players = resp_player.data or []
            if players:
                player = players[0]
                session["user_id"] = player["player_id"]
                session["role"] = "player"
                session["name"] = player.get("first_name", "")
                session["assigned_coach"] = player.get("assigned_coach_id")
                return redirect(url_for("player_dashboard"))

            # 2. Check Coaches
            resp_coach = supabase.table("coaches").select("*").eq("email", email_input).execute()
            coaches = resp_coach.data or []
            if coaches:
                coach = coaches[0]
                session["user_id"] = coach["coach_id"]
                session["role"] = "coach"
                session["name"] = coach.get("first_name", "")
                return redirect(url_for("coach_dashboard"))

            return render_template("login.html", error="Geen account gevonden.")

        except Exception as e:
            print(f"Login error: {e}")
            return render_template("login.html", error="Er ging iets mis.")

    return render_template("login.html")


# ---------- LOGOUT (HIER IS HIJ!) ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- PLAYER DASHBOARD ----------
@app.route("/player")
def player_dashboard():
    if session.get("role") != "player": 
        return redirect(url_for("login"))
    
    player_id = session.get("user_id")
    geplande = []

    try:
        # 1. Haal les IDs op via lesson_players
        resp_lp = supabase.table("lesson_players").select("lesson_id").eq("player_id", player_id).execute()
        lesson_ids = [r['lesson_id'] for r in (resp_lp.data or [])]

        if lesson_ids:
            # 2. Haal de les details op
            resp_lessons = supabase.table("lessons").select("*").in_("lesson_id", lesson_ids).order("date").execute()
            
            # 3. Haal coach namen op
            coach_ids = list({l['coach_id'] for l in (resp_lessons.data or []) if l['coach_id']})
            coach_map = {}
            if coach_ids:
                c_data = supabase.table("coaches").select("coach_id, first_name, last_name").in_("coach_id", coach_ids).execute()
                for c in (c_data.data or []):
                    coach_map[c['coach_id']] = f"{c['first_name']} {c['last_name']}"

            # 4. Samenvoegen
            for l in (resp_lessons.data or []):
                geplande.append({
                    "date": l.get("date"),
                    "start_time": str(l.get("start_time"))[:5],
                    "end_time": str(l.get("end_time"))[:5],
                    "coach_name": coach_map.get(l.get("coach_id"), "Onbekend")
                })
    except Exception as e:
        print(f"Dashboard error: {e}")

    return render_template("player_dashboard.html", geplande=geplande)


# ---------- REGISTRATIE ----------
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


# ---------- COACH DASHBOARD ----------
@app.route("/coach")
def coach_dashboard():
    if session.get("role") != "coach": return redirect(url_for("login"))
    coach_id = session.get("user_id")
    
    spelers = []
    lessen = []

    try:
        # 1. Eigen spelers
        spelers = supabase.table("players").select("*").eq("assigned_coach_id", coach_id).execute().data or []

        # 2. Eigen lessen
        raw_lessen = supabase.table("lessons").select("*").eq("coach_id", coach_id).order("date").execute().data or []
        
        # 3. Spelers bij lessen zoeken
        lesson_ids = [l['lesson_id'] for l in raw_lessen]
        lp_map = {}
        if lesson_ids:
            lp_data = supabase.table("lesson_players").select("lesson_id, player_id").in_("lesson_id", lesson_ids).execute().data or []
            
            # Namen ophalen
            p_ids = list({x['player_id'] for x in lp_data})
            p_map = {}
            if p_ids:
                p_data = supabase.table("players").select("player_id, first_name, last_name").in_("player_id", p_ids).execute().data or []
                for p in p_data:
                    p_map[p['player_id']] = f"{p['first_name']} {p['last_name']}"
            
            for row in lp_data:
                lp_map.setdefault(row['lesson_id'], []).append(p_map.get(row['player_id'], "Onbekend"))

        for l in raw_lessen:
            lessen.append({
                "date": l['date'],
                "start_time": str(l['start_time'])[:5],
                "end_time": str(l['end_time'])[:5],
                "players": ", ".join(lp_map.get(l['lesson_id'], ["Geen spelers"]))
            })

    except Exception as e:
        print(f"Coach dash error: {e}")

    return render_template("coach_dashboard.html", spelers=spelers, lessen=lessen)


# ---------- COACH: SPELER TOEVOEGEN (GEFIXT) ----------
@app.route("/coach/add_player", methods=["GET", "POST"])
def add_player():
    if session.get("role") != "coach": return redirect(url_for("login"))
    coach_id = session.get("user_id")
    
    vrije_spelers = []
    try:
        vrije_spelers = supabase.table("players").select("*").is_("assigned_coach_id", None).execute().data or []
    except: pass

    if request.method == "POST":
        player_id = request.form.get("player_id")
        if not player_id:
            return render_template("add_player.html", spelers=vrije_spelers, error="Kies een speler.")
        
        try:
            # Update speler met coach ID (Progress insert verwijderd!)
            supabase.table("players").update({"assigned_coach_id": coach_id}).eq("player_id", player_id).execute()
            return redirect(url_for("coach_dashboard"))
        except Exception as e:
            return render_template("add_player.html", spelers=vrije_spelers, error=f"Fout: {e}")

    return render_template("add_player.html", spelers=vrije_spelers)


# ---------- COACH: GROEPSLES PLANNEN (GEFIXT - GEBRUIKT 'lessons') ----------
@app.route("/coach/schedule_group_lesson", methods=["GET", "POST"])
def schedule_group_lesson():
    if session.get("role") != "coach": return redirect(url_for("login"))
    coach_id = session.get("user_id")
    eigen_spelers = supabase.table("players").select("*").eq("assigned_coach_id", coach_id).execute().data or []

    if request.method == "POST":
        player_ids = request.form.getlist("player_ids")
        date_in = request.form.get("date")
        start = request.form.get("start_time")
        end = request.form.get("end_time")

        if len(player_ids) < 2:
            return render_template("schedule_group_lesson.html", spelers=eigen_spelers, error="Selecteer minstens 2 spelers.")
        
        try:
            # 1. Maak de les aan in 'lessons' (ipv bookings)
            les_data = {
                "coach_id": coach_id, "date": date_in, "start_time": start, "end_time": end, "lesson_type": "Groepsles"
            }
            resp = supabase.table("lessons").insert(les_data).execute()
            if not resp.data: raise Exception("Les aanmaken mislukt")
            
            lesson_id = resp.data[0]['lesson_id']

            # 2. Koppel spelers in 'lesson_players'
            lp_insert = [{"lesson_id": lesson_id, "player_id": pid} for pid in player_ids]
            supabase.table("lesson_players").insert(lp_insert).execute()

            return redirect(url_for("coach_dashboard"))
        except Exception as e:
            print(f"Group lesson error: {e}")
            return render_template("schedule_group_lesson.html", spelers=eigen_spelers, error="Fout bij inplannen.")

    return render_template("schedule_group_lesson.html", spelers=eigen_spelers)


# ---------- COACH: INDIVIDUELE LES (GEFIXT - GEBRUIKT 'lessons') ----------
@app.route("/coach/schedule_individual_lesson", methods=["GET", "POST"])
def schedule_individual_lesson():
    if session.get("role") != "coach": return redirect(url_for("login"))
    coach_id = session.get("user_id")
    eigen_spelers = supabase.table("players").select("*").eq("assigned_coach_id", coach_id).execute().data or []

    if request.method == "POST":
        pid = request.form.get("player_id")
        date_in = request.form.get("date")
        start = request.form.get("start_time")
        end = request.form.get("end_time")

        try:
            # 1. Maak les in 'lessons'
            les_data = {
                "coach_id": coach_id, "date": date_in, "start_time": start, "end_time": end, "lesson_type": "Individueel"
            }
            resp = supabase.table("lessons").insert(les_data).execute()
            lesson_id = resp.data[0]['lesson_id']

            # 2. Koppel speler in 'lesson_players'
            supabase.table("lesson_players").insert({"lesson_id": lesson_id, "player_id": pid}).execute()
            return redirect(url_for("coach_dashboard"))
        except Exception as e:
            return render_template("schedule_individual_lesson.html", spelers=eigen_spelers, error=f"Fout: {e}")

    return render_template("schedule_individual_lesson.html", spelers=eigen_spelers)


# ---------- COACH: DETAILS & DELETE (GEFIXT - Progress verwijderd) ----------
@app.route("/coach/player/<int:player_id>")
def view_player(player_id):
    if session.get("role") != "coach": return redirect(url_for("login"))
    
    speler = None
    try:
        speler = supabase.table("players").select("*").eq("player_id", player_id).single().execute().data
    except: pass

    return render_template("player_detail.html", speler=speler, progressies=[])

@app.route("/coach/remove_player/<int:player_id>")
def remove_player(player_id):
    if session.get("role") != "coach": return redirect(url_for("login"))
    try:
        # Alleen ontkoppelen
        supabase.table("players").update({"assigned_coach_id": None}).eq("player_id", player_id).execute()
    except: pass
    return redirect(url_for("coach_dashboard"))


# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(debug=True)
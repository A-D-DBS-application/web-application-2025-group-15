from flask import Flask, render_template, request, redirect, url_for, session, make_response, flash
from config import Config
from extensions import db
from sqlalchemy import or_, and_
from datetime import datetime, date, timedelta
from icalendar import Calendar, Event
from supabase import create_client, Client
from models import GroupLessonRequest, Lesson
import json
import os
import datetime
from services import recommend_coaches_for_lesson
from werkzeug.utils import secure_filename
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

from models import (
    Player,
    Coach,
    Club,
    Lesson,
    CompletedLesson,
    CoachAvailability,
    GroupLessonRequest   
)


app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'static'

db.init_app(app)

# =========================================================
#  HULPFUNCTIES (BEST PRACTICES)
# =========================================================

# --- tijdsloten ---
def get_daily_time_slots():
    # Genereert uren van 09:00 tot 22:00
    slots = []
    for hour in range(9, 22):
        start = f"{hour:02d}:00"
        end = f"{hour+1:02d}:00"
        slots.append((start, end))
    return slots

# --- profielfoto's ---
def upload_profile_image(file_obj, email, folder="profile_pictures"):
    if not file_obj or not file_obj.filename:
        return None

    ext = os.path.splitext(file_obj.filename)[1].lower()
    # Maak bestandsnaam veilig
    safe_email = email.replace("@", "_").replace(".", "_")
    filename = f"{folder}/{safe_email}_{int(datetime.now().timestamp())}{ext}"
    
    file_bytes = file_obj.read()

    try:
        supabase.storage.from_("profile_pictures").upload(filename, file_bytes)
        return f"{Config.SUPABASE_URL}/storage/v1/object/public/profile_pictures/{filename}"
    except Exception as e:
        print(f"Fout bij uploaden ({folder}):", repr(e))
        return None

# --- agenda conflicten controleren ---
def check_scheduling_conflict(date_obj, start_time, end_time, coach_id, player_id=None):
    """
    Controleert of er een conflict is in de agenda.
    Geeft een foutmelding (string) terug als er overlap is, anders None.
    """
    
    # 1. Check: Heeft de COACH al een les?
    # Logica: Een les overlapt als (Start < Einde_Nieuw) EN (Einde > Start_Nieuw)
    conflict_coach = Lesson.query.filter(
        Lesson.coach_id == coach_id,
        Lesson.date == date_obj,
        Lesson.start_time < end_time,
        Lesson.end_time > start_time
    ).first()

    if conflict_coach:
        return "De coach heeft al een les op dit tijdstip."

    # 2. Check: Heeft de SPELER al een les? (Alleen als player_id is meegegeven)
    if player_id:
        conflict_player = Lesson.query.filter(
            Lesson.date == date_obj,
            Lesson.start_time < end_time,
            Lesson.end_time > start_time,
            Lesson.players.any(Player.player_id == player_id)
        ).first()

        if conflict_player:
            return "De speler heeft al een les op dit tijdstip."

    return None # Geen conflicten gevonden

#om lessen te verzetten naar completed lessons als ze in het verleden liggen
def cleanup_past_lessons():
    try:
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()

        past_lessons = Lesson.query.filter(
            or_(
                Lesson.date < current_date,
                and_(Lesson.date == current_date, Lesson.end_time < current_time)
            )
        ).all()

        if not past_lessons:
            return
        
        count = 0
        for lesson in past_lessons:
            for player in lesson.players:
                completed = CompletedLesson(
                    lesson_id=lesson.lesson_id,
                    player_id=player.player_id,
                    coach_id=lesson.coach_id,
                    date=lesson.date,
                    start_time=lesson.start_time,
                    end_time=lesson.end_time,
                    coach_feedback=None,
                    rating=None
                )
                db.session.add(completed)
                count += 1
            db.session.delete(lesson)
        db.session.commit()
        print(f"{count} lessen verplaatst naar het archief.")
    except Exception as e:
        db.session.rollback()
        print("Fout bij cleanup van verlopen lessen:", repr(e))

# --- HOME & LOGIN ---

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_input = request.form.get("email", "").strip()
        print(f"Inlogpoging voor: {email_input}")

        if not email_input:
            return render_template("login.html", error="Vul je e-mailadres in.")

        try:
            player = Player.query.filter_by(email=email_input).first()
            if player:
                session["user_id"] = player.player_id
                session["role"] = "player"
                session["name"] = player.first_name
                return redirect(url_for("player_dashboard"))
            
            coach = Coach.query.filter_by(email=email_input).first()
            if coach:
                session["user_id"] = coach.coach_id
                session["role"] = "coach"
                session["name"] = coach.first_name
                return redirect(url_for("coach_dashboard"))
            
            return render_template("login.html", error="Geen account gevonden.")

        except Exception as e:
            print("❌ Login error:", repr(e))
            return render_template("login.html", error="Er ging iets mis.")
                                   
    return render_template("login.html")

# ============================================================
#  PLAYER DASHBOARD
# ============================================================
@app.route("/player")
def player_dashboard():
    if session.get("role") != "player":
        return redirect(url_for("login"))

    cleanup_past_lessons()

    player_id = session.get("user_id")
    user = Player.query.get(player_id)
    if not user:
        return redirect(url_for("logout"))

    upcoming_lessons = []

    today = date.today()
    now = datetime.now().time()

    # ------------------------------
    # UPCOMING LESSONS
    # ------------------------------
    for lesson in user.lessons:

        # Alleen toekomstige lessen
        if lesson.date > today or (lesson.date == today and lesson.start_time >= now):

            # Coachnaam ophalen
            if lesson.coach:
                coach_name = f"{lesson.coach.first_name} {lesson.coach.last_name}"
            else:
                coach_name = "Onbekend"

            # Type bepalen
            if len(lesson.players) > 1:
                lesson_type = "Groepsles"
            else:
                lesson_type = "Individueel"

            # Alles opslaan
            upcoming_lessons.append({
                "lesson_id": lesson.lesson_id,
                "date": lesson.date,
                "start_time": lesson.start_time,
                "end_time": lesson.end_time,
                "coach_name": coach_name,
                "lesson_type": lesson_type,
            })

    # ------------------------------
# ------------------------------
    # PAST LESSONS (GEOPTIMALISEERD)
    # ------------------------------
    past_lessons = []
    
    # We gebruiken een JOIN om de Les én de Coach in één keer op te halen
    results = (db.session.query(CompletedLesson, Coach)
               .outerjoin(Coach, CompletedLesson.coach_id == Coach.coach_id)
               .filter(CompletedLesson.player_id == player_id)
               .order_by(CompletedLesson.date.desc())
               .limit(10)
               .all())

    for row, coach in results:
        # Nu hebben we het coach-object al direct (of None als hij niet bestaat)
        coach_name = f"{coach.first_name} {coach.last_name}" if coach else "Onbekend"
        has_evaluation = bool(row.coach_feedback)

        past_lessons.append({
            "lesson_id": row.lesson_id,
            "id": row.id,
            "date": row.date,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "coach_name": coach_name,
            "has_evaluation": has_evaluation,
        })

    return render_template(
        "player_dashboard.html",
        user=user,
        upcoming_lessons=upcoming_lessons,
        past_lessons=past_lessons
    )
# ============================================================
#  REGISTER ROUTES (SPELER & COACH)
# ============================================================

@app.route("/register")
def register():
    return render_template("register_choice.html")

# --- speler registratie ---
@app.route("/register/player", methods=["GET", "POST"])
def register_player_step1():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")

        if not email or not first_name or not last_name:
            return render_template("register_player_step1.html",
                                   error="Vul alle verplichte velden in.")

        try:
            if Player.query.filter_by(email=email).first():
                return render_template("login.html", error="Dit e-mailadres bestaat al. Log hier in.")
            if Coach.query.filter_by(email=email).first():
                return render_template("login.html", error="Dit e-mailadres is al geregistreerd als coach.")
            
        except Exception as e:
            print("Fout bij controleren bestaande accounts:", repr(e))
            pass

        session["player_data"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone
        }
        return redirect(url_for("register_player_step2"))
    return render_template("register_player_step1.html")

from datetime import datetime

@app.route("/register/player/step2", methods=["GET", "POST"])
def register_player_step2():
    if "player_data" not in session:
        return redirect(url_for("register_player_step1"))

    if request.method == "POST":
        data = session["player_data"]

        ranking = request.form.get("ranking")
        hand_preference = request.form.get("hand_preference")
        gender = request.form.get("gender")
        dob_str = request.form.get("dob")

        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                return render_template(
                    "register_player_step2.html",
                    error="Ongeldige geboortedatum."
                )
                
        lesson_type_preference = request.form.get("lesson_type_preference")
        playing_intensity = request.form.get("playing_intensity")

        # -------------------------
        # PROFIELFOTO UPLOAD (SPELER)
        # -------------------------
        file = request.files.get("image")
        profile_url = upload_profile_image(file, data["email"], folder="players")

        # -------------------------
        # NIEUWE SPELER MAKEN
        # -------------------------
        new_player = Player(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data["phone"],
            ranking=ranking,
            hand_preference=hand_preference,
            gender=gender,
            date_of_birth=dob,
            profile_image=profile_url,   # <--- URL opgeslagen in DB
            lesson_type_preference=lesson_type_preference,
            playing_intensity=playing_intensity,
        )

        try:
            db.session.add(new_player)
            db.session.commit()
            session.pop("player_data", None)
            return render_template(
                "login.html",
                error="Account aangemaakt! Je kunt nu inloggen."
            )
        except Exception as e:
            db.session.rollback()
            print("Fout bij opslaan nieuwe speler:", repr(e))
            return render_template(
                "register_player_step2.html",
                error="Er ging iets mis bij het opslaan. Probeer opnieuw."
            )

    return render_template("register_player_step2.html")




# Registratie van de coach
@app.route("/register/coach", methods=["GET", "POST"])
def register_coach():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")

        if not email or not first_name or not last_name:
            return render_template("register_coach_step1.html", error="Vul zeker e-mail, voornaam en achternaam in.")
        

        try:
            if Player.query.filter_by(email=email).first():
                return render_template("login.html", error="Dit e-mailadres is al geregistreerd als speler. Log hier in.")
            if Coach.query.filter_by(email=email).first():
                return render_template("login.html", error="Dit e-mailadres bestaat al. Log hier in.")
        except:
            print("Fout bij controleren bestaande accounts:")
            pass

        session["coach_data"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone
        }
        return redirect(url_for("register_coach_step2"))

    return render_template("register_coach_step1.html")

from datetime import datetime

@app.route("/register/coach/step2", methods=["GET", "POST"])
def register_coach_step2():
    if "coach_data" not in session:
        return redirect(url_for("register_coach_step1"))

    if request.method == "POST":
        data = session["coach_data"]

        ranking = request.form.get("ranking")
        hand_preference = request.form.get("hand_preference")
        gender = request.form.get("gender")
        dob_str = request.form.get("dob")
        lesson_type_preference = request.form.get("lesson_type_preference")
        playing_intensity = request.form.get("playing_intensity")



        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                return render_template(
                    "register_coach_step2.html",
                    error="Ongeldige geboortedatum."
                )

        # -------------------------
        # PROFIELFOTO UPLOAD (COACH)
        # -------------------------
        file = request.files.get("image")
        profile_url = upload_profile_image(file, data["email"], folder="coaches")

        # -------------------------
        # NIEUWE COACH MAKEN
        # -------------------------
        new_coach = Coach(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data["phone"],
            gender=gender,
            ranking=ranking,
            hand_preference=hand_preference,
            date_of_birth=dob,
            profile_image=profile_url,
            lesson_type_preference=lesson_type_preference,
            playing_intensity=playing_intensity,
        )

        try:
            db.session.add(new_coach)
            db.session.commit()
            session.pop("coach_data", None)
            return render_template(
                "login.html",
                error="Account aangemaakt! Je kunt nu inloggen."
            )
        except Exception as e:
            db.session.rollback()
            print("Fout bij opslaan nieuwe coach:", repr(e))
            return render_template(
                "register_coach_step2.html",
                error="Er ging iets mis bij het opslaan."
            )

    return render_template("register_coach_step2.html")




# ============================================================
#  LES AANVRAGEN (PLAYER)
# ============================================================
@app.route("/request_lesson_type")
def request_lesson_type():
    if session.get("role") != "player":
        return redirect(url_for("login"))

    return render_template("request_lesson_type.html")

@app.route("/request_group_lesson", methods=["GET", "POST"])
def request_group_lesson():
    if session.get("role") != "player":
        return redirect(url_for("login"))

    coaches = Coach.query.all()
    available_slots = None
    selected_coach_id = None
    selected_date = None
    error = None

    ALL_SLOTS = get_daily_time_slots()

    if request.method == "POST":
        action = request.form.get("action")
        selected_coach_id = request.form.get("coach_id")
        selected_date = request.form.get("date")

        # -----------------------
        #   TIJDSLOTEN OPHALEN
        # -----------------------
        if action == "show_slots":
            if not selected_coach_id or not selected_date:
                error = "Kies een coach en datum."
            else:
                existing = Lesson.query.filter_by(
                    coach_id=selected_coach_id,
                    date=selected_date
                ).all()

                taken = {
                    f"{l.start_time.strftime('%H:%M')}-{l.end_time.strftime('%H:%M')}"
                    for l in existing
                }

                avail = CoachAvailability.query.filter_by(
                    coach_id=selected_coach_id,
                    date=datetime.strptime(selected_date, "%Y-%m-%d").date()
                ).all()

                defined = {
                    f"{a.start_time.strftime('%H:%M')}-{a.end_time.strftime('%H:%M')}"
                    for a in avail
                }

                available_slots = []
                for s, e in ALL_SLOTS:
                    slot_id = f"{s}-{e}"
                    if slot_id in defined and slot_id not in taken:
                        available_slots.append({
                            "id": slot_id,
                            "label": f"{s} – {e}",
                            "start": s,
                            "end": e
                        })

                if not available_slots:
                    error = "Geen tijdsloten beschikbaar."

        # -----------------------
        #   REVIEWPAGINA
        # -----------------------
        if action == "review":
            slot = request.form.get("slot")
            focus = request.form.get("focus")

            if not (selected_coach_id and selected_date and slot and focus):
                error = "Selecteer coach, datum, tijdslot en onderwerp."
            else:
                start, end = slot.split("-")
                coach_obj = Coach.query.get(selected_coach_id)

                return render_template(
                    "confirm_group_lesson.html",
                    coach=coach_obj,
                    coach_id=selected_coach_id,
                    date=selected_date,
                    time=start,
                    start=start,
                    end=end,
                    focus=focus
                )

    return render_template(
        "request_group_lesson.html",
        coaches=coaches,
        available_slots=available_slots,
        selected_coach_id=selected_coach_id,
        selected_date=selected_date,
        error=error
    )






@app.route("/review_group_lesson_request")
def review_group_lesson_request():
    date = request.args.get("date")
    time = request.args.get("time")
    skill = request.args.get("skill")

    return render_template(
        "review_group_lesson_request.html",
        date=date, time=time, skill=skill
    )

@app.route("/finalize_group_lesson_request")
def finalize_group_lesson_request():
    # speler moet ingelogd zijn
    player_id = session.get("user_id")
    if not player_id:
        return redirect(url_for("login"))

    player = Player.query.get(player_id)

    # data ophalen uit URL-parameters (vanuit confirm_group_lesson.html)
    chosen_coach_id = request.args.get("coach_id", type=int)
    date_str = request.args.get("date")
    start_str = request.args.get("start")
    focus = request.args.get("focus")

    if not (chosen_coach_id and date_str and start_str and focus):
        return render_template("error.html", message="Onvolledige groepsles-data.")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_obj = datetime.strptime(start_str, "%H:%M").time()
        end_obj = (datetime.combine(date_obj, start_obj) + timedelta(hours=1)).time()
    except ValueError:
        return render_template("error.html", message="Ongeldige datum of tijd.")

    # -----------------------------
    # 1) Aanbevelingsalgoritme voor groepsles
    # -----------------------------
    intensity = getattr(player, "playing_intensity", None)

    recs = recommend_coaches_for_lesson(
        players=[player],
        subject=focus,
        intensity=intensity,
        lesson_date=date_obj,
        start_time=start_obj,
        end_time=end_obj,
        return_details=True,
    )

    print("🔍 Group recommendations:", recs)

    best_rec = None
    chosen_score = None

    if recs:
        best_rec = recs[0]

        # score van de coach die speler koos
        for rec in recs:
            if rec["coach"].coach_id == chosen_coach_id:
                chosen_score = rec["score"]
                break

    # -----------------------------
    # 2) Popup tonen als andere coach duidelijk beter is
    # -----------------------------
    if best_rec and best_rec["coach"].coach_id != chosen_coach_id:
        if chosen_score is None or best_rec["score"] >= (chosen_score + 5):
            end_str = end_obj.strftime("%H:%M") 

            # Toon keuzescherm
            return render_template(
                "group_recommendation_choice.html",
                chosen_coach=Coach.query.get(chosen_coach_id),
                recommended_coach=best_rec["coach"],
                reasons=best_rec["reasons"],
                date_str=date_str,
                start_str=start_str,
                end_str=end_str,   
                focus=focus,
            )

    # -----------------------------
    # 3) Geen popup → gewoon request voor gekozen coach opslaan
    # -----------------------------
    new_request = GroupLessonRequest(
        player_id=player_id,
        coach_id=chosen_coach_id,
        date=date_obj,
        time=start_obj,
        lesson_focus=focus
    )

    db.session.add(new_request)
    db.session.commit()

    # Matcher starten voor deze coach+slot
    return redirect(url_for(
        "check_group_match",
        coach_id=chosen_coach_id,
        date=date_str,
        time=start_str,
        focus=focus
    ))

@app.route("/player/confirm_group_choice", methods=["POST"])
def player_confirm_group_choice():
    if session.get("role") != "player":
        return redirect(url_for("login"))

    player_id = session.get("user_id")
    player = Player.query.get(player_id)

    decision = request.form.get("decision")  # "recommended" of "chosen"
    chosen_coach_id = int(request.form.get("chosen_coach_id"))
    recommended_coach_id = int(request.form.get("recommended_coach_id"))
    date_str = request.form.get("date")
    start_str = request.form.get("start")
    focus = request.form.get("focus")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_obj = datetime.strptime(start_str, "%H:%M").time()
    except Exception:
        return render_template("error.html", message="Ongeldige groepsles-data.")

    # uiteindelijke coach
    final_coach_id = recommended_coach_id if decision == "recommended" else chosen_coach_id

    # Groepsles-aanvraag opslaan (net zoals vroeger)
    new_request = GroupLessonRequest(
        player_id=player_id,
        coach_id=final_coach_id,
        date=date_obj,
        time=start_obj,
        lesson_focus=focus
    )

    try:
        db.session.add(new_request)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Fout bij opslaan groepsles-aanvraag:", e)
        return render_template("error.html", message="Er ging iets mis bij het aanvragen van de groepsles.")

    # Daarna werkt het systeem EXACT zoals ervoor:
    # check_group_match kijkt of er ≥3 requests zijn voor deze coach + datum + tijd + focus
    return redirect(url_for(
        "check_group_match",
        coach_id=final_coach_id,
        date=date_str,
        time=start_str,
        focus=focus
    ))







from datetime import datetime, timedelta

def parse_rank(value):
    if not value:
        return None
    s = str(value)
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


@app.route("/check_group_match")
def check_group_match():
    date_str  = request.args.get("date")
    time_str  = request.args.get("time")
    coach_id  = request.args.get("coach_id", type=int)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    time_obj = datetime.strptime(time_str, "%H:%M").time()

    # Alleen aanvragen voor deze coach + datum + tijd
    all_requests = GroupLessonRequest.query.filter_by(
        date=date_obj,
        time=time_obj,
        coach_id=coach_id
    ).all()

    if not all_requests:
        return "Geen groepsles-aanvragen gevonden."

    MIN_GROUP = 3
    MAX_GROUP = 4
    MAX_P_DIFF = 200

    # Referentiespeler
    ref_req      = all_requests[0]
    ref_player   = ref_req.player
    ref_focus    = ref_req.lesson_focus
    ref_intensity = ref_player.playing_intensity
    ref_score    = parse_rank(ref_player.ranking)

    if ref_score is None:
        remaining = MIN_GROUP
        return render_template(
            "group_lesson_wait.html",
            date=date_str,
            time=time_str,
            remaining=remaining,
            focus=ref_focus
        )

    # 1) Zelfde onderwerp
    focus_matches = [r for r in all_requests if r.lesson_focus == ref_focus]
    if len(focus_matches) < MIN_GROUP:
        remaining = MIN_GROUP - len(focus_matches)
        return render_template("group_lesson_wait.html",
                               date=date_str, time=time_str,
                               remaining=remaining, focus=ref_focus)

    # 2) Zelfde intensiteit
    intensity_matches = [
        r for r in focus_matches
        if r.player.playing_intensity == ref_intensity
    ]
    if len(intensity_matches) < MIN_GROUP:
        remaining = MIN_GROUP - len(intensity_matches)
        return render_template("group_lesson_wait.html",
                               date=date_str, time=time_str,
                               remaining=remaining, focus=ref_focus)

    # 3) P-score max ±200
    pscore_matches = []
    for r in intensity_matches:
        score = parse_rank(r.player.ranking)
        if score is None:
            continue
        if abs(score - ref_score) <= MAX_P_DIFF:
            pscore_matches.append(r)

    if len(pscore_matches) < MIN_GROUP:
        remaining = MIN_GROUP - len(pscore_matches)
        return render_template("group_lesson_wait.html",
                               date=date_str, time=time_str,
                               remaining=remaining, focus=ref_focus)

    chosen_group = pscore_matches[:MAX_GROUP]

    # --- LES AANMAKEN ---
    end_time_obj = (datetime.combine(date_obj, time_obj) + timedelta(hours=1)).time()

    lesson = Lesson(
        coach_id=coach_id,
        date=date_obj,
        start_time=time_obj,
        end_time=end_time_obj,
        lesson_type="Groepsles",
        lesson_focus=ref_focus
    )
    db.session.add(lesson)
    db.session.commit()

    # --- FIX: TIME SLOT UIT COACH AVAILABILITY VERWIJDEREN ---
    slot = CoachAvailability.query.filter(
        CoachAvailability.coach_id == coach_id,
        CoachAvailability.date == date_obj,
        CoachAvailability.start_time <= time_obj,
        CoachAvailability.end_time >= end_time_obj
    ).first()

    if slot:
        db.session.delete(slot)
        db.session.commit()

    # --- SPELERS TOEVOEGEN + REQUESTS VERWIJDEREN ---
    for req in chosen_group:
        if req.player not in lesson.players:
            lesson.players.append(req.player)
        db.session.delete(req)

    db.session.commit()

    return render_template("group_lesson_confirmed.html", lesson=lesson)




@app.route("/player/book_lesson", methods=["GET", "POST"])
def book_lesson():
    if session.get("role") != "player":
        return redirect(url_for("login"))

    player_id = session.get("user_id")
    player = Player.query.get(player_id) # Dit is jouw huidige gebruiker

    # Coaches ophalen
    try:
        coaches = Coach.query.all()
    except Exception:
        coaches = []

    available_slots = None
    selected_coach_id = None
    selected_date = None
    error = None

    ALL_SLOTS = get_daily_time_slots()

    # Data ophalen uit request (zowel bij show_slots als book acties)
    selected_coach_id_str = request.form.get("coach_id")
    if selected_coach_id_str:
        selected_coach_id = int(selected_coach_id_str)
    
    selected_date = request.form.get("date")

    if request.method == "POST":
        action = request.form.get("action")

        # =============================
        # 1) TIJDSLOTEN TONEN
        # =============================
        if action == "show_slots":
            if not selected_coach_id or not selected_date:
                error = "Kies eerst een coach en een datum."
            else:
                try:
                    selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()

                    # Bestaande lessen ophalen
                    existing_lessons = Lesson.query.filter(
                        Lesson.coach_id == selected_coach_id,
                        Lesson.date == selected_date_obj
                    ).all()

                    taken = {
                        f"{les.start_time.strftime('%H:%M')}-{les.end_time.strftime('%H:%M')}"
                        for les in existing_lessons
                    }

                    # Beschikbaarheid ophalen
                    availability = CoachAvailability.query.filter_by(
                        coach_id=selected_coach_id,
                        date=selected_date_obj
                    ).all()

                    available_defined = {
                        f"{av.start_time.strftime('%H:%M')}-{av.end_time.strftime('%H:%M')}"
                        for av in availability
                    }

                    available_slots = []
                    if not available_defined:
                        error = "Deze coach heeft geen beschikbaarheid ingesteld voor deze datum."
                    else:
                        for s, e in ALL_SLOTS:
                            slot_id = f"{s}-{e}"
                            if slot_id in available_defined and slot_id not in taken:
                                available_slots.append({
                                    "id": slot_id,
                                    "label": f"{s} – {e}",
                                    "start": s,
                                    "end": e,
                                })

                        if not available_slots:
                            error = "Geen vrije tijdsloten meer op deze datum."

                except Exception as e:
                    print("Fout bij ophalen tijdsloten:", e)
                    error = "Er ging iets mis bij het ophalen van de tijdsloten."

        # =============================
        # 2) LES BOEKEN
        # =============================
        elif action == "book":
            slot_id = request.form.get("slot")
            focus = request.form.get("focus") or None
            intensity = getattr(player, "playing_intensity", None)

            if not selected_coach_id or not selected_date or not slot_id:
                error = "Kies een coach, datum én tijdslot."
            else:
                try:
                    lesson_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
                    start_str, end_str = slot_id.split("-")
                    start_time_obj = datetime.strptime(start_str, "%H:%M").time()
                    end_time_obj = datetime.strptime(end_str, "%H:%M").time()

                    # A) Conflict Check
                    conflict_error = check_scheduling_conflict(
                        lesson_date, 
                        start_time_obj, 
                        end_time_obj, 
                        selected_coach_id, 
                        player_id 
                    )

                    if conflict_error:
                        return render_template(
                            "book_lesson.html",
                            coaches=coaches,
                            error=conflict_error,
                            selected_date=selected_date,
                            selected_coach_id=selected_coach_id,
                            available_slots=[] 
                        )

                    # B) Recommendation Check
                    recs = recommend_coaches_for_lesson(
                        players=[player],
                        subject=focus,
                        intensity=intensity,
                        lesson_date=lesson_date,
                        start_time=start_time_obj,
                        end_time=end_time_obj,
                        return_details=True,
                    )

                    best_rec = None
                    chosen_score = None # Start op None

                    if recs:
                        best_rec = recs[0]
                        # Zoek de score van de coach die de speler heeft aangeklikt
                        for rec in recs:
                            if rec["coach"].coach_id == selected_coach_id:
                                chosen_score = rec["score"]
                                break
                    
                    # FIX 1: Voorkom crash als chosen_score None is (gebeurt als coach niet in recs staat)
                    if chosen_score is None:
                        chosen_score = 0.0

                    # C) Popup Logic: Is er een betere coach?
                    if best_rec and best_rec["coach"].coach_id != selected_coach_id:
                        # Drempel van 5 punten verschil
                        if best_rec["score"] >= (chosen_score + 5):
                            
                            # FIX 2: We geven 'current_user=player' mee, want jouw HTML gebruikt {{ current_user }}
                            return render_template(
                                "recommendation_choice.html",
                                selected_coach=Coach.query.get(selected_coach_id),
                                recommended_coach=best_rec["coach"],
                                reasons=best_rec["reasons"],
                                date=lesson_date,
                                slot_id=slot_id,
                                start_time=start_time_obj,
                                end_time=end_time_obj,
                                current_user=player  # <--- ESSENTIEEL VOOR JOUW HTML
                            )

                    # D) Definitief Boeken (Geen betere match of popup genegeerd)
                    new_lesson = Lesson(
                        coach_id=selected_coach_id,
                        date=lesson_date,
                        start_time=start_time_obj,
                        end_time=end_time_obj,
                        lesson_type="Individueel"
                    )

                    new_lesson.players.append(player)
                    
                    # Auto-link coach aan speler als relatie nog niet bestaat
                    coach_obj = Coach.query.get(selected_coach_id)
                    if coach_obj and coach_obj not in player.coaches:
                        player.coaches.append(coach_obj)

                    db.session.add(new_lesson)

                    # E) Beschikbaarheid verwijderen (Exacte match)
                    slot_to_remove = CoachAvailability.query.filter_by(
                        coach_id=selected_coach_id,
                        date=lesson_date,
                        start_time=start_time_obj,
                        end_time=end_time_obj
                    ).first()

                    if slot_to_remove:
                        db.session.delete(slot_to_remove)

                    db.session.commit()
                    return redirect(url_for("player_dashboard"))

                except Exception as e:
                    db.session.rollback()
                    print("Fout bij boeken les:", e) # Kijk in je terminal naar deze fout als het misgaat
                    error = "Er ging iets mis bij het boeken."

    return render_template(
        "book_lesson.html",
        coaches=coaches,
        available_slots=available_slots,
        selected_coach_id=selected_coach_id,
        selected_date=selected_date,
        error=error,
    )


def _create_individual_lesson_and_redirect(player_id, coach_id, selected_date_obj, start_time_obj, end_time_obj):
    """Hulpfunctie die effectief de les aanmaakt + beschikbaarheid updatet."""
    try:
        # Conflicten checken (coach)
        conflict_coach = Lesson.query.filter(
            Lesson.coach_id == coach_id,
            Lesson.date == selected_date_obj,
            Lesson.start_time < end_time_obj,
            Lesson.end_time > start_time_obj
        ).first()

        if conflict_coach:
            return render_template(
                "book_lesson.html",
                error="Deze coach heeft al een les op dit tijdstip.",
                coaches=Coach.query.all(),
                available_slots=[],
                selected_coach_id=coach_id,
                selected_date=selected_date_obj.strftime("%Y-%m-%d"),
            )

        # Conflicten checken (speler)
        conflict_player = Lesson.query.filter(
            Lesson.date == selected_date_obj,
            Lesson.start_time < end_time_obj,
            Lesson.end_time > start_time_obj,
            Lesson.players.any(Player.player_id == player_id)
        ).first()

        if conflict_player:
            return render_template(
                "book_lesson.html",
                error="Je hebt zelf al een les op dit moment.",
                coaches=Coach.query.all(),
                available_slots=[],
                selected_coach_id=coach_id,
                selected_date=selected_date_obj.strftime("%Y-%m-%d"),
            )

        # Les aanmaken
        new_lesson = Lesson(
            coach_id=coach_id,
            date=selected_date_obj,
            start_time=start_time_obj,
            end_time=end_time_obj,
            lesson_type="Individueel"
        )

        player = Player.query.get(player_id)
        new_lesson.players.append(player)
        db.session.add(new_lesson)

        # Beschikbaarheid-slot verwijderen
        slot_to_remove = CoachAvailability.query.filter_by(
            coach_id=coach_id,
            date=selected_date_obj,
            start_time=start_time_obj,
            end_time=end_time_obj
        ).first()

        if slot_to_remove:
            db.session.delete(slot_to_remove)

        db.session.commit()
        return redirect(url_for("player_dashboard"))

    except Exception as e:
        db.session.rollback()
        print("Fout bij definitief boeken:", e)
        return render_template(
            "book_lesson.html",
            error="Er ging iets mis bij het definitief boeken.",
            coaches=Coach.query.all(),
            available_slots=[],
            selected_coach_id=coach_id,
            selected_date=selected_date_obj.strftime("%Y-%m-%d"),
        )
    
@app.route("/player/confirm_lesson_choice", methods=["POST"])
def player_confirm_lesson_choice():
    if session.get("role") != "player":
        return redirect(url_for("login"))

    player_id = session.get("user_id")
    player = Player.query.get(player_id)

    choice = request.form.get("choice")  # "recommended" of "original"
    recommended_id = int(request.form.get("recommended_coach_id"))
    original_id = int(request.form.get("original_coach_id"))
    date_str = request.form.get("date")
    slot_id = request.form.get("slot_id")

    try:
        lesson_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_str, end_str = slot_id.split("-")
        start_time_obj = datetime.strptime(start_str, "%H:%M").time()
        end_time_obj = datetime.strptime(end_str, "%H:%M").time()
    except Exception:
        return render_template("error.html", message="Ongeldige data voor les.")

    # Welke coach uiteindelijk gebruiken?
    coach_id = recommended_id if choice == "recommended" else original_id

    try:
        new_lesson = Lesson(
            coach_id=coach_id,
            date=lesson_date,
            start_time=start_time_obj,
            end_time=end_time_obj,
            lesson_type="Individueel"
        )
        new_lesson.players.append(player)
        db.session.add(new_lesson)

        # Beschikbaarheid-slot weghalen voor de coach die de les geeft
        slot_to_remove = CoachAvailability.query.filter_by(
            coach_id=coach_id,
            date=lesson_date,
            start_time=start_time_obj,
            end_time=end_time_obj
        ).first()

        if slot_to_remove:
            db.session.delete(slot_to_remove)

        db.session.commit()
        return redirect(url_for("player_dashboard"))

    except Exception as e:
        db.session.rollback()
        print("Fout bij bevestigen leskeuze:", e)
        return render_template("error.html", message="Er ging iets mis bij het bevestigen van de les.")


# ============================================================
#LES ANNULEREN (PLAYER):
# ============================================================
#  CONFIRM CANCEL LESSON (PLAYER)
# ============================================================

# 1. DE TUSSENPAGINA (Bevestiging vragen)
@app.route("/confirm_cancel_lesson/<int:lesson_id>")
def confirm_cancel_lesson(lesson_id):
    if session.get("role") != "player":
        return redirect(url_for("login"))
    
    # We sturen de gebruiker naar de aparte HTML pagina
    return render_template("confirm_cancel_lesson.html", lesson_id=lesson_id)


# 2. DE ACTIE (Daadwerkelijk verwijderen)
# Deze wordt aangeroepen als je OP de bevestigingspagina op "JA" klikt
@app.route("/cancel_lesson/<int:lesson_id>", methods=["POST"])
def cancel_lesson(lesson_id):
    if "user_id" not in session or session.get("role") != "player":
        return redirect(url_for("login"))

    player_id = session.get("user_id")
    lesson = Lesson.query.get_or_404(lesson_id)
    player = Player.query.get(player_id)

    if player not in lesson.players:
        flash("Je kunt alleen je eigen lessen annuleren.", "error")
        return redirect(url_for("player_dashboard"))

    try:
        # Tijdslot herstellen
        restored_slot = CoachAvailability(
            coach_id=lesson.coach_id,
            date=lesson.date,
            start_time=lesson.start_time,
            end_time=lesson.end_time
        )
        db.session.add(restored_slot)

        # Les verwijderen
        db.session.delete(lesson)
        db.session.commit()
        flash("Les geannuleerd en tijdslot vrijgegeven.", "success")

    except Exception as e:
        db.session.rollback()
        print("Fout:", e)
        flash("Kon de les niet annuleren.", "error")

    return redirect(url_for("player_dashboard"))
# ============================================================
#  COACH DASHBOARD
# ============================================================

@app.route("/coach")
def coach_dashboard():

    if session.get("role") != "coach":
        return redirect(url_for("login"))

    cleanup_past_lessons()

    coach_id = session.get("user_id")
    coach = Coach.query.get(coach_id)

    if not coach:
        return redirect(url_for("logout"))

    students = coach.students.all()

    # UPCOMING LESSONS
    upcoming_lessons = []
    if coach.lessons:
        today = date.today()
        now = datetime.now().time()
        
        for lesson in coach.lessons:
            if lesson.date > today or (lesson.date == today and lesson.start_time >= now):

                player_names = [f"{p.first_name} {p.last_name}" for p in lesson.players]
                players_str = ", ".join(player_names) if player_names else "No players assigned"

                upcoming_lessons.append({
                    "lesson_id": lesson.lesson_id,
                    "date": lesson.date,
                    "start_time": lesson.start_time,
                    "end_time": lesson.end_time,
                    "players": players_str,
                    "lesson_type": lesson.lesson_type
                })

        upcoming_lessons.sort(key=lambda x: (x["date"], x["start_time"]))

    # PAST LESSONS
    past_lessons = []
    completed_rows = (
        CompletedLesson.query
        .filter_by(coach_id=coach_id)
        .order_by(CompletedLesson.date.desc())
        .limit(15)
        .all()
    )

    for row in completed_rows:
        player_name = "Unknown"
        if row.player_id:
            player_obj = Player.query.get(row.player_id)
            if player_obj:
                player_name = f"{player_obj.first_name} {player_obj.last_name}"

        has_evaluation = bool(row.coach_feedback)

        past_lessons.append({
            "lesson_id": row.lesson_id,
            "id": row.id,
            "date": row.date,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "player_name": player_name,
            "has_evaluation": has_evaluation
        })

    return render_template(
        "coach_dashboard.html",
        user=coach,                     # <-- BELANGRIJK!
        coach=coach,
        students=students,
        upcoming_lessons=upcoming_lessons,
        past_lessons=past_lessons
    )
     
    


# ============================================================
#  COACH BESCHIKBAARHEID INSTELLEN
# ============================================================

@app.route("/coach_availability", methods=["GET", "POST"])
def coach_availability():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")
    coach = Coach.query.get_or_404(coach_id)

    # 1. Datum bepalen
    date_str = request.values.get("date")
    
    selected_date = None
    all_slots = []
    selected_slot_ids = set()
    message = None
    error = None

    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # 2. POST: Opslaan
            if request.method == "POST":
                chosen_slots = request.form.getlist("slots") 

                try:
                    # VERVANGEN: Availability -> CoachAvailability
                    # Eerst alles wissen van die dag
                    CoachAvailability.query.filter_by(coach_id=coach_id, date=selected_date).delete()

                    # Nieuwe toevoegen
                    for slot_id in chosen_slots:
                        start_str, end_str = slot_id.split("-")
                        start_t = datetime.strptime(start_str, "%H:%M").time()
                        end_t = datetime.strptime(end_str, "%H:%M").time()

                        # VERVANGEN: Availability -> CoachAvailability
                        new_slot = CoachAvailability(
                            coach_id=coach_id,
                            date=selected_date,
                            start_time=start_t,
                            end_time=end_t
                        )
                        db.session.add(new_slot)

                    db.session.commit()
                    message = "Beschikbaarheid succesvol bijgewerkt!"
                
                except Exception as e:
                    db.session.rollback()
                    print("Fout:", e)
                    error = "Kon niet opslaan."

            # 3. GET: Weergave voorbereiden
            raw_slots = get_daily_time_slots()
            
            all_slots = []
            for s, e in raw_slots:
                all_slots.append({
                    "id": f"{s}-{e}",
                    "label": f"{s} – {e}"
                })

            # VERVANGEN: Availability -> CoachAvailability
            existing = CoachAvailability.query.filter_by(coach_id=coach_id, date=selected_date).all()
            
            selected_slot_ids = {
                f"{av.start_time.strftime('%H:%M')}-{av.end_time.strftime('%H:%M')}"
                for av in existing
            }

        except ValueError:
            error = "Ongeldige datum."

    return render_template(
        "coach_availability.html",
        coach=coach,
        date_str=date_str,
        selected_date=selected_date,
        all_slots=all_slots,
        selected_slot_ids=selected_slot_ids,
        message=message,
        error=error
    )
# ============================================================
#  EVALUATIE LES (COACH)
# ============================================================
# In app.py - vervang de start van evaluate_lesson hiermee:

@app.route("/evaluate_lesson/<int:record_id>/<int:step>", methods=["GET", "POST"])
def evaluate_lesson(record_id, step):
    # 1. Authenticatie
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    # Haal de CompletedLesson op basis van het unieke ID (record_id)
    completed_lesson = CompletedLesson.query.get(record_id)
    
    if not completed_lesson:
        return render_template("error.html", message="Les niet gevonden of nog niet afgerond.")

    player = Player.query.get(completed_lesson.player_id)

    # We slaan de data tijdelijk op in de sessie op basis van record_id
    session_key = f"eval_data_{record_id}"
    if session_key not in session:
        session[session_key] = {}
    
    data = session[session_key]

    # --- STAP 1: TECHNIEK ---
    if step == 1:
        if request.method == "POST":
            data['techniek'] = {
                "forehand": request.form.get("forehand"),
                "backhand": request.form.get("backhand"),
                "volley": request.form.get("volley"),
                "smash": request.form.get("smash"),
                "bandeja": request.form.get("bandeja"),
                "service": request.form.get("service"),
                "opmerking": request.form.get("opmerking")
            }
            session[session_key] = data
            # AANGEPAST: record_id ipv lesson_id
            return redirect(url_for("evaluate_lesson", record_id=record_id, step=2))
        
        return render_template("evaluate_steps/step1.html", lesson=completed_lesson, player=player, evaluation=data)

    # --- STAP 2: TACTIEK ---
    elif step == 2:
        if request.method == "POST":
            data['tactiek'] = {
                "positiespel": request.form.get("positie"),
                "keuze_slagen": request.form.get("keuzes"),
                "samenwerking": request.form.get("samenwerking"),
                "netspel": request.form.get("netspel"),
                "verdediging": request.form.get("verdediging"),
                "opmerking": request.form.get("opmerking")
            }
            session[session_key] = data
            # AANGEPAST: record_id ipv lesson_id
            return redirect(url_for("evaluate_lesson", record_id=record_id, step=3))
        
        return render_template("evaluate_steps/step2.html", lesson=completed_lesson, player=player, evaluation=data)

    # --- STAP 3: FYSIEK ---
    elif step == 3:
        if request.method == "POST":
            data['fysiek'] = {
                "snelheid": request.form.get("snelheid"),
                "uithouding": request.form.get("uithouding"),
                "kracht": request.form.get("kracht"),
                "mobiliteit": request.form.get("mobiliteit"),
                "opmerking": request.form.get("opmerking")
            }
            session[session_key] = data
            # AANGEPAST: record_id ipv lesson_id
            return redirect(url_for("evaluate_lesson", record_id=record_id, step=4))
        
        return render_template("evaluate_steps/step3.html", lesson=completed_lesson, player=player, evaluation=data)

    # --- STAP 4: MENTAAL ---
    elif step == 4:
        if request.method == "POST":
            data['mentaal'] = {
                "focus": request.form.get("focus"),
                "inzet": request.form.get("inzet"),
                "sportiviteit": request.form.get("sportiviteit"),
                "veerkracht": request.form.get("veerkracht"),
                "opmerking": request.form.get("opmerking")
            }
            session[session_key] = data
            # AANGEPAST: record_id ipv lesson_id
            return redirect(url_for("evaluate_lesson", record_id=record_id, step=5))
        
        return render_template("evaluate_steps/step4.html", lesson=completed_lesson, player=player, evaluation=data)

    # --- STAP 5: OPSLAAN ---
    elif step == 5:
        if request.method == "POST":
            try:
                # Opslaan in database
                completed_lesson.coach_feedback = json.dumps(data)
                db.session.commit()
                
                # Sessie opruimen
                session.pop(session_key, None)
                
                return redirect(url_for("coach_dashboard"))
            
            except Exception as e:
                db.session.rollback()
                print("Fout bij opslaan:", e)
                return render_template("evaluate_steps/step5.html", lesson=completed_lesson, player=player, evaluation=data, error="Er ging iets mis.")

        return render_template("evaluate_steps/step5.html", lesson=completed_lesson, player=player, evaluation=data)

    # Fallback (start opnieuw bij stap 1 als step ongeldig is)
    return redirect(url_for("evaluate_lesson", record_id=record_id, step=1))

# In app.py - vervang de hele view_evaluation functie hiermee:

@app.route("/view_evaluation/<int:record_id>")  # <--- Naam gewijzigd naar record_id
def view_evaluation(record_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Gebruik .get() om de SPECIFIEKE evaluatie van deze speler te pakken
    completed_lesson = CompletedLesson.query.get(record_id)
    
    if not completed_lesson:
        return render_template("error.html", message="Evaluatie niet gevonden.")

    try:
        evaluation_data = json.loads(completed_lesson.coach_feedback) if completed_lesson.coach_feedback else {}
    except:
        evaluation_data = {}

    player = Player.query.get(completed_lesson.player_id)
    coach = Coach.query.get(completed_lesson.coach_id)

    return render_template("view_evaluation.html", 
                           lesson=completed_lesson, 
                           evaluation=evaluation_data, 
                           player=player, 
                           coach=coach)
# ============================================================
#  COACH – SPELER TOEVOEGEN
# ============================================================
@app.route("/add_player", methods=["GET"])
def add_player():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    search_query = request.args.get("q", "").strip()

    # qery voor spelers die nog geen student zijn van deze coach
    coach_id = session.get("user_id")
    query = Player.query.filter(~Player.coaches.any(Coach.coach_id == coach_id))

    # Als er een zoekterm is → extra filter
    if search_query:
        query = query.filter(
            or_(
                Player.first_name.ilike(f"%{search_query}%"),
                Player.last_name.ilike(f"%{search_query}%"),
                Player.email.ilike(f"%{search_query}%")
            )
        )

    spelers = query.order_by(Player.first_name).all()

    return render_template("add_player.html", spelers=spelers, q=search_query)



@app.route("/assign_coach/<int:player_id>", methods=["POST"])
def assign_coach(player_id):
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    coach = Coach.query.get_or_404(coach_id)
    player = Player.query.get_or_404(player_id)

    if player not in coach.students:
        coach.students.append(player)
        try:
            db.session.commit()
            print(f"{player.first_name} {player.last_name} succesvol toegevoegd aan coach {coach.first_name} {coach.last_name}.")
        except Exception as e:
            db.session.rollback()
            print("Fout bij toewijzen coach:", e)
    else:
        print(f"{player.first_name} {player.last_name} is al student van coach {coach.first_name} {coach.last_name}.")

    return redirect(url_for("add_player"))

# ============================================================
#  LES INPLANNEN (INDIVIDUEEL)
# ============================================================

@app.route("/schedule_individual_lesson", methods=["GET", "POST"])
def schedule_individual_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")
    coach = Coach.query.get(coach_id)

    if request.method == "POST":
        player_id = request.form.get("player_id")
        date_str = request.form.get("date")
        start_time_str = request.form.get("start_time")
        duration = int(request.form.get("duration", 60))

        if not player_id or not date_str or not start_time_str:
            return render_template("schedule_individual_lesson.html", 
                                   students=coach.students, 
                                   error="Vul alle velden in.")

        try:
            lesson_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            
            start_dt = datetime.combine(lesson_date, start_time)
            end_dt = start_dt + timedelta(minutes=duration)
            end_time = end_dt.time()

            # Check voor conflicten bij de coach
            conflict_error = check_scheduling_conflict(lesson_date, start_time, end_time, coach_id, player_id)
            
            if conflict_error:
                return render_template("schedule_individual_lesson.html", 
                                       students=coach.students, 
                                       error=conflict_error)

            # Les aanmaken
            new_lesson = Lesson(
                coach_id=coach_id,
                date=lesson_date,
                start_time=start_time,
                end_time=end_time,
                lesson_type="Individueel"
            )
            
            player = Player.query.get(player_id)
            new_lesson.players.append(player)

            #als eerste keer bij coach is relatie toevoegen aan database
            if coach not in player.coaches:
                player.coaches.append(coach)
                print(f"Nieuwe connectie gemaakt: {player.first_name} is nu gekoppeld aan {coach.first_name}")
            # ---------------------------------------------------------

            db.session.add(new_lesson)
            db.session.commit()

            return redirect(url_for("coach_dashboard"))

        except Exception as e:
            db.session.rollback()
            print("Fout bij inplannen:", e)
            return render_template("schedule_individual_lesson.html", 
                                   students=coach.students, 
                                   error="Er ging iets mis. Controleer de datum/tijd.")

    # Let op: Als je lessen wilt inplannen met spelers die NOG GEEN student zijn,
    # moet je hieronder 'students=coach.students' veranderen naar 'students=Player.query.all()'
    return render_template("schedule_individual_lesson.html", students=coach.students)
# ============================================================
#  ICAL EXPORT (Download voor Outlook/Google)
# ============================================================
@app.route("/download_ics/<int:lesson_id>")
def download_ics(lesson_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    lesson = Lesson.query.get_or_404(lesson_id)

    cal = Calendar()
    cal.add('prodid', '-//Fit Out Padel//App//NL')
    cal.add('version', '2.0')

    event = Event()
    # Check of lesson_type bestaat, anders fallback
    summary_text = f"Padel Les ({lesson.lesson_type})" if hasattr(lesson, 'lesson_type') else "Padel Les"
    event.add('summary', summary_text)
    
    start_dt = datetime.combine(lesson.date, lesson.start_time)
    
    # Check of end_time bestaat
    if lesson.end_time:
        end_dt = datetime.combine(lesson.date, lesson.end_time)
    else:
        end_dt = start_dt # Fallback als er geen eindtijd is

    event.add('dtstart', start_dt)
    event.add('dtend', end_dt)
    event.add('dtstamp', datetime.now())
    
    # Coach check
    if lesson.coach:
        coach_name = f"{lesson.coach.first_name} {lesson.coach.last_name}"
    else:
        coach_name = "Onbekend"

    event.add('description', f"Training gegeven door {coach_name}. Zorg dat je 10 min op voorhand bent!")
    event.add('location', "Fit Out Padel Destelbergen")

    cal.add_component(event)

    response = make_response(cal.to_ical())
    response.headers["Content-Disposition"] = f"attachment; filename=les_{lesson_id}.ics"
    response.headers["Content-Type"] = "text/calendar; charset=utf-8"
    
    return response

# ============================================================
#  COACH – SPELER DETAILS & HISTORIE
# ============================================================

@app.route("/coach/player/<int:player_id>", methods=["GET", "POST"])
def coach_player_detail(player_id):
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    # 1. Haal de ingelogde coach op
    current_coach_id = session.get("user_id")
    current_coach = Coach.query.get(current_coach_id) 

    student = Player.query.get(player_id)
    if not student:
        return redirect(url_for("coach_dashboard"))

    if request.method == "POST":
        student.strengths = request.form.get("strengths")
        student.weaknesses = request.form.get("weaknesses")
        try:
            db.session.commit()
            return redirect(url_for("coach_player_detail", player_id=player_id))
        except Exception as e:
            db.session.rollback()
            print("Fout bij updaten profiel:", e)

    past_lessons = (CompletedLesson.query
                    .filter_by(player_id=player_id)
                    .order_by(CompletedLesson.date.desc())
                    .all())
    
    history = []
    for row in past_lessons:
        coach = Coach.query.get(row.coach_id)
        history.append({
            "id": row.id,
            "date": row.date,
            "has_evaluation": bool(row.coach_feedback),
            "lesson_id": row.lesson_id,
            "coach_name": f"{coach.first_name} {coach.last_name}" if coach else "Onbekend",
            "coach_id": row.coach_id
        })

    # 2. Geef 'user' (current_coach) mee aan de template
    return render_template(
        "coach_player_detail.html", 
        student=student, 
        history=history, 
        user=current_coach 
    )
    return render_template("coach_player_detail.html", student=student, history=history)
# ============================================================
#  LOGOUT
# ============================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/unlink_player/<int:player_id>', methods=['POST'])
def unlink_player(player_id):
    current_coach_id = session.get('user_id')
    user_role = session.get('role')

    if not current_coach_id or user_role != 'coach':
        print("FOUT: Geen geldige coach-sessie gevonden.")
        return redirect(url_for('login'))
    
    player_to_remove = Player.query.get(player_id)
    current_coach = Coach.query.get(current_coach_id)
    
    if player_to_remove and current_coach:

        if current_coach in player_to_remove.coaches:
            player_to_remove.coaches.remove(current_coach)
            db.session.commit()
            print(f"Speler {player_to_remove.first_name} {player_to_remove.last_name} succesvol verwijderd uit je lijst met spelers.")
        else:
            print(f"FOUT: Speler {player_to_remove.first_name} {player_to_remove.last_name} is geen speler van jou.")
    else:
        print("FOUT: Speler of coach niet gevonden in database.")
    
    return redirect(url_for('coach_dashboard'))

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    # 1. Check of gebruiker is ingelogd
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    role = session.get("role")

    # 2. Haal het juiste profiel op (Coach of Speler)
    if role == "coach":
        profile = Coach.query.get(user_id)
    else:
        profile = Player.query.get(user_id)

    # 3. Als er op OPSLAAN is gedrukt (POST)
    if request.method == "POST":
        # A. Basisgegevens
        profile.first_name = request.form.get("first_name")
        profile.last_name = request.form.get("last_name")
        profile.email = request.form.get("email")
        profile.phone = request.form.get("phone")

        # B. Sportieve gegevens (DIT ZORGT DAT HET OPGESLAGEN WORDT)
        # We wijzen de waarde direct toe. Als het formulier leeg is, wordt de DB ook leeg.
        profile.ranking = request.form.get("ranking")
        profile.playing_intensity = request.form.get("playing_intensity")
        profile.lesson_type_preference = request.form.get("lesson_type_preference")

        # C. Foto upload
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                # Zorg dat je 'import os' bovenaan hebt staan!
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                profile.profile_image = url_for("static", filename=filename)

        # D. Opslaan in Database (Commit)
        try:
            db.session.commit()
            flash("Profiel succesvol bijgewerkt!", "success")
        except Exception as e:
            db.session.rollback()
            print("Fout bij opslaan profiel:", e)
            flash("Er ging iets mis bij het opslaan.", "error")
        
        return redirect(url_for("edit_profile"))

    # 4. Pagina tonen (GET)
    return render_template("edit_profile.html", profile=profile)

# ============================================================
#  MAIN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
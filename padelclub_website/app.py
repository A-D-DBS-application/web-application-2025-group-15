from flask import Flask, render_template, request, redirect, url_for, session, make_response
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

db.init_app(app)

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
    # PAST LESSONS
    # ------------------------------
    past_lessons = []
    completed_rows = (CompletedLesson.query
                      .filter_by(player_id=player_id)
                      .order_by(CompletedLesson.date.desc())
                      .limit(10)
                      .all())

    for row in completed_rows:
        has_evaluation = True if row.coach_feedback else False

        coach_name = "Onbekend"
        if row.coach_id:
            c_obj = Coach.query.get(row.coach_id)
            if c_obj:
                coach_name = f"{c_obj.first_name} {c_obj.last_name}"

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
        profile_url = None

        if file and file.filename:
            # veilige unieke bestandsnaam
            ext = os.path.splitext(file.filename)[1].lower()  # .jpg / .png ...
            safe_email = data["email"].replace("@", "_").replace(".", "_")
            filename = f"players/{safe_email}_{int(datetime.now().timestamp())}{ext}"

            file_bytes = file.read()

            try:
                # upload naar Supabase bucket "profile_pictures"
                supabase.storage.from_("profile_pictures").upload(
                    filename,
                    file_bytes
                )

                # publieke URL opbouwen
                profile_url = (
                    f"{Config.SUPABASE_URL}"
                    f"/storage/v1/object/public/profile_pictures/{filename}"
                )
            except Exception as e:
                print("Fout bij uploaden profielfoto speler:", repr(e))
                # eventueel: toch doorgaan zonder foto
                profile_url = None

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
        profile_url = None

        if file and file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            safe_email = data["email"].replace("@", "_").replace(".", "_")
            filename = f"coaches/{safe_email}_{int(datetime.now().timestamp())}{ext}"

            file_bytes = file.read()

            try:
                supabase.storage.from_("profile_pictures").upload(
                    filename,
                    file_bytes
                )

                profile_url = (
                    f"{Config.SUPABASE_URL}"
                    f"/storage/v1/object/public/profile_pictures/{filename}"
                )
            except Exception as e:
                print("Fout bij uploaden profielfoto coach:", repr(e))
                profile_url = None

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

    ALL_SLOTS = []
    OPENING = 9
    CLOSING = 22
    DURATION = 60

    t = datetime.strptime(f"{OPENING}:00", "%H:%M")
    end_limit = datetime.strptime(f"{CLOSING}:00", "%H:%M")

    while t + timedelta(minutes=DURATION) <= end_limit:
        start_str = t.strftime("%H:%M")
        end_str = (t + timedelta(minutes=DURATION)).strftime("%H:%M")
        ALL_SLOTS.append((start_str, end_str))
        t += timedelta(minutes=DURATION)

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
    player = Player.query.get(player_id)

    # Alle coaches tonen in dropdown
    try:
        coaches = Coach.query.all()
    except Exception:
        coaches = []

    available_slots = None
    selected_coach_id = None
    selected_date = None
    error = None

    # ---- ALGEMENE TIJDSLOTEN GENEREREN ----
    ALL_SLOTS = []
    OPENING_HOUR = 9
    CLOSING_HOUR = 22
    DURATION_MINUTES = 60

    current_time = datetime.strptime(f"{OPENING_HOUR}:00", "%H:%M")
    end_time_limit = datetime.strptime(f"{CLOSING_HOUR}:00", "%H:%M")

    while current_time + timedelta(minutes=DURATION_MINUTES) <= end_time_limit:
        start_str = current_time.strftime("%H:%M")
        slot_end = current_time + timedelta(minutes=DURATION_MINUTES)
        end_str = slot_end.strftime("%H:%M")

        ALL_SLOTS.append((start_str, end_str))
        current_time = slot_end

    # ---- POST ACTIES ----
    if request.method == "POST":
        action = request.form.get("action")
        selected_coach_id = request.form.get("coach_id")
        selected_date = request.form.get("date")

        if selected_coach_id:
            selected_coach_id = int(selected_coach_id)

        # =============================
        # 1) TIJDSLOTEN TONEN
        # =============================
        if action == "show_slots":
            if not selected_coach_id or not selected_date:
                error = "Kies eerst een coach en een datum."
            else:
                try:
                    selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()

                    # Bestaande lessen → ingenomen slots
                    existing_lessons = Lesson.query.filter(
                        Lesson.coach_id == selected_coach_id,
                        Lesson.date == selected_date_obj
                    ).all()

                    taken = {
                        f"{les.start_time.strftime('%H:%M')}-{les.end_time.strftime('%H:%M')}"
                        for les in existing_lessons
                    }

                    # Beschikbaarheid coach
                    availability = CoachAvailability.query.filter_by(
                        coach_id=selected_coach_id,
                        date=selected_date_obj
                    ).all()

                    available_defined = {
                        f"{av.start_time.strftime('%H:%M')}-{av.end_time.strftime('%H:%M')}"
                        for av in availability
                    }

                    if not available_defined:
                        error = "Deze coach heeft nog geen beschikbaarheid ingesteld voor deze datum."
                        available_slots = []
                    else:
                        available_slots = []
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
        # 2) LES BOEKEN (MET RECOMMENDER)
        # =============================
        if action == "book":
            slot_id = request.form.get("slot")
            # optioneel: les-focus (bv. uit extra veld in je formulier)
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

                    # ---------------------------
                    # A) RECOMMENDATION ALGORTIME
                    # ---------------------------
                    recs = recommend_coaches_for_lesson(
                        players=[player],
                        subject=focus,
                        intensity=intensity,
                        lesson_date=lesson_date,
                        start_time=start_time_obj,
                        end_time=end_time_obj,
                        return_details=True,
                    )

                    print("🔍 Recommendations:", recs)

                    best_rec = None
                    chosen_score = None

                    if recs:
                        best_rec = recs[0]

                        # score van de door speler gekozen coach zoeken
                        for rec in recs:
                            if rec["coach"].coach_id == selected_coach_id:
                                chosen_score = rec["score"]
                                break

                    # Debug prints in console
                    if best_rec:
                        print(f"Beste coach: {best_rec['coach'].first_name} (score={best_rec['score']})")
                        print(f"Gekozen coach id: {selected_coach_id}, gekozen score: {chosen_score}")

                    # ---------------------------
                    # B) POPUP TONEN ALS ANDERE COACH BETER IS
                    # ---------------------------
                    if best_rec and best_rec["coach"].coach_id != selected_coach_id:
                        # threshold: minimaal 5 punten beter
                        if chosen_score is None or best_rec["score"] >= (chosen_score + 5):
                            # we tonen een keuze-scherm
                            return render_template(
                                "recommendation_choice.html",
                                selected_coach=Coach.query.get(selected_coach_id),
                                recommended_coach=best_rec["coach"],
                                reasons=best_rec["reasons"],
                                date=lesson_date,
                                slot_id=slot_id,
                                start_time=start_time_obj,
                                end_time=end_time_obj,
                            )

                    # ---------------------------
                    # C) GEEN POPUP → GEWOON LES BOEKEN
                    # ---------------------------
                    new_lesson = Lesson(
                        coach_id=selected_coach_id,
                        date=lesson_date,
                        start_time=start_time_obj,
                        end_time=end_time_obj,
                        lesson_type="Individueel"
                    )

                    new_lesson.players.append(player)
                    db.session.add(new_lesson)

                    # Beschikbaar tijdslot verwijderen
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
                    print("Fout bij boeken les:", e)
                    error = "Er ging iets mis bij het boeken. Probeer later opnieuw."

    # ---- TEMPLATE RENDEREN (GET of errors) ----
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

@app.route("/confirm_cancel_lesson/<int:lesson_id>")
def confirm_cancel_lesson(lesson_id):
    if session.get("role") != "player":
        return redirect(url_for("login"))

    return render_template("confirm_cancel_lesson.html", lesson_id=lesson_id)

# ============================================================
#  LES ANNULEREN (PLAYER)
# ============================================================

@app.route("/cancel_lesson/<int:lesson_id>")
def cancel_lesson(lesson_id):
    if session.get("role") != "player":
        return redirect(url_for("login"))

    player_id = session.get("user_id")

    # Les en speler ophalen
    lesson = Lesson.query.get(lesson_id)
    player = Player.query.get(player_id)

    if not lesson:
        return render_template("error.html", message="Les niet gevonden.")

    if player not in lesson.players:
        return render_template("error.html", message="Je mag deze les niet annuleren.")

    try:
        # 1️⃣ Tijdslot terug vrijgeven in CoachAvailability
        restored_slot = CoachAvailability(
            coach_id=lesson.coach_id,
            date=lesson.date,
            start_time=lesson.start_time,
            end_time=lesson.end_time
        )
        db.session.add(restored_slot)

        # 2️⃣ Les verwijderen
        db.session.delete(lesson)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("Fout bij annuleren (ORM):", e)
        return render_template("error.html", message="Er ging iets mis bij het annuleren.")

    # 3️⃣ Alleen als alles goed is gegaan → succespagina
    return redirect(url_for("cancel_success"))


@app.route("/cancel_success")
def cancel_success():
    if session.get("role") != "player":
        return redirect(url_for("login"))
    return render_template("cancel_success.html")

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

@app.route("/coach/availability", methods=["GET", "POST"])
def coach_availability():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")
    coach = Coach.query.get_or_404(coach_id)

    # Basis parameters
    OPENING_HOUR = 9
    CLOSING_HOUR = 22
    DURATION_MINUTES = 60

    # Datum ophalen
    date_str = request.values.get("date")
    selected_date = None
    all_slots = []
    selected_slot_ids = set()
    message = None
    error = None

    # Als er een datum is
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Slots genereren
            current_time = datetime.strptime(f"{OPENING_HOUR}:00", "%H:%M")
            end_time_limit = datetime.strptime(f"{CLOSING_HOUR}:00", "%H:%M")

            while current_time + timedelta(minutes=DURATION_MINUTES) <= end_time_limit:
                start_str = current_time.strftime("%H:%M")
                slot_end = current_time + timedelta(minutes=DURATION_MINUTES)
                end_str = slot_end.strftime("%H:%M")

                all_slots.append({
                    "id": f"{start_str}-{end_str}",
                    "label": f"{start_str} – {end_str}"
                })

                current_time = slot_end

            # Bestaande beschikbaarheid ophalen
            existing = CoachAvailability.query.filter_by(
                coach_id=coach_id,
                date=selected_date
            ).all()

            selected_slot_ids = {
                f"{av.start_time.strftime('%H:%M')}-{av.end_time.strftime('%H:%M')}"
                for av in existing
            }

            # POST: opslaan
            if request.method == "POST":
                chosen_slots = request.form.getlist("slots")

                # Oude verwijderen
                CoachAvailability.query.filter_by(
                    coach_id=coach_id,
                    date=selected_date
                ).delete()

                # Nieuwe opslaan
                for slot_id in chosen_slots:
                    start_str, end_str = slot_id.split("-")
                    start_t = datetime.strptime(start_str, "%H:%M").time()
                    end_t = datetime.strptime(end_str, "%H:%M").time()

                    av = CoachAvailability(
                        coach_id=coach_id,
                        date=selected_date,
                        start_time=start_t,
                        end_time=end_t
                    )
                    db.session.add(av)

                db.session.commit()
                message = "Beschikbaarheid opgeslagen!"
                selected_slot_ids = set(chosen_slots)

        except Exception as e:
            db.session.rollback()
            print("Fout bij instellen beschikbaarheid:", e)
            error = "Er ging iets mis bij het opslaan van je beschikbaarheid."

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
@app.route("/evaluate_lesson/<int:lesson_id>/<int:step>", methods=["GET", "POST"])
def evaluate_lesson(lesson_id, step):
    # 1. Authenticatie
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    completed_lesson = CompletedLesson.query.filter_by(lesson_id=lesson_id).first()
    
    if not completed_lesson:
        return render_template("error.html", message="Les niet gevonden of nog niet afgerond.")

    player = Player.query.get(completed_lesson.player_id)

    session_key = f"eval_data_{lesson_id}"
    if session_key not in session:
        session[session_key] = {}
    
    data = session[session_key]

    # --- STAP 1: TECHNIEK ---
    if step == 1:
        if request.method == "POST":
            data['techniek'] = {
                "forehand": request.form.get("forehand_score"),
                "backhand": request.form.get("backhand_score"),
                "volley": request.form.get("volley_score"),
                "smash": request.form.get("smash_score"),
                "opmerking": request.form.get("opmerking")
            }
            session[session_key] = data
            return redirect(url_for("evaluate_lesson", lesson_id=lesson_id, step=2))
        
        return render_template("evaluate_steps/step1.html", lesson=completed_lesson, player=player, evaluation=data)

    # --- STAP 2: TACTIEK ---
    elif step == 2:
        if request.method == "POST":
            data['tactiek'] = {
                "positiespel": request.form.get("positiespel_score"),
                "keuze_slagen": request.form.get("keuze_slagen_score"),
                "samenwerking": request.form.get("samenwerking_score"),
                "speelstrategie": request.form.get("speelstrategie_score"),
                "opmerking": request.form.get("opmerking")
            }
            session[session_key] = data
            return redirect(url_for("evaluate_lesson", lesson_id=lesson_id, step=3))
        
        return render_template("evaluate_steps/step2.html", lesson=completed_lesson, player=player, evaluation=data)

    # --- STAP 3: FYSIEK ---
    elif step == 3:
        if request.method == "POST":
            data['fysiek'] = {
                "conditie": request.form.get("conditie_score"),
                "reactiesnelheid": request.form.get("reactiesnelheid_score"),
                "explosiviteit": request.form.get("explosiviteit_score"),
                "opmerking": request.form.get("opmerking")
            }
            session[session_key] = data
            return redirect(url_for("evaluate_lesson", lesson_id=lesson_id, step=4))
        
        return render_template("evaluate_steps/step3.html", lesson=completed_lesson, player=player, evaluation=data)

    # --- STAP 4: MENTAAL ---
    elif step == 4:
        if request.method == "POST":
            data['mentaal'] = {
                "focus": request.form.get("focus_score"),
                "doorzettingsvermogen": request.form.get("doorzet_score"),
                "opmerking": request.form.get("opmerking")
            }
            session[session_key] = data
            return redirect(url_for("evaluate_lesson", lesson_id=lesson_id, step=5))
        
        return render_template("evaluate_steps/step4.html", lesson=completed_lesson, player=player, evaluation=data)

    # --- STAP 5: OPSLAAN & RANKING ---
    elif step == 5:
        if request.method == "POST":
            try:
                completed_lesson.coach_feedback = json.dumps(data)

                db.session.commit()
                session.pop(session_key, None)
                
                return redirect(url_for("coach_dashboard"))
            
            except Exception as e:
                db.session.rollback()
                print("Fout bij opslaan:", e)
                return render_template("evaluate_steps/step5.html", lesson=completed_lesson, player=player, evaluation=data, error="Er ging iets mis.")

        return render_template("evaluate_steps/step5.html", lesson=completed_lesson, player=player, evaluation=data)

    return redirect(url_for("evaluate_lesson", lesson_id=lesson_id, step=1))

@app.route("/view_evaluation/<int:lesson_id>")
def view_evaluation(lesson_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    completed_lesson = CompletedLesson.query.filter_by(lesson_id=lesson_id).first()
    if not completed_lesson:
        return render_template("error.html", message="Evaluatie nog niet beschikbaar.")

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

    if not coach.students.filter_by(player_id=player_id).count() > 0:
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
            conflict_coach = Lesson.query.filter(
                Lesson.coach_id == coach_id,
                Lesson.date == lesson_date,
                Lesson.start_time < end_time,
                Lesson.end_time > start_time
            ).first()

            if conflict_coach:
                return render_template("schedule_individual_lesson.html", 
                                       students=coach.students, 
                                       error="Je hebt zelf al een les op dit tijdstip!")

            # Check voor conflicten bij de speler
            conflict_player = Lesson.query.filter(
                Lesson.date == lesson_date,
                Lesson.start_time < end_time,
                Lesson.end_time > start_time,
                Lesson.players.any(player_id=player_id) 
            ).first()

            if conflict_player:
                return render_template("schedule_individual_lesson.html", 
                                       students=coach.students, 
                                       error="Deze speler heeft al les op dit moment.")

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

@app.route("/export_lesson/<int:lesson_id>")
def export_lesson(lesson_id):
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        return "Les niet gevonden", 404

    cal = Calendar()
    cal.add('prodid', '-//Fit Out Padel//maxym-app//NL')
    cal.add('version', '2.0')

    event = Event()
    event.add('summary', f"Padel Les ({lesson.lesson_type})")
    
    start_dt = datetime.combine(lesson.date, lesson.start_time)
    end_dt = datetime.combine(lesson.date, lesson.end_time)
    
    event.add('dtstart', start_dt)
    event.add('dtend', end_dt)
    event.add('dtstamp', datetime.now())
    
    coach_name = f"{lesson.coach.first_name} {lesson.coach.last_name}"
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
        history.append({
            "date": row.date,
            "has_evaluation": bool(row.coach_feedback),
            "lesson_id": row.lesson_id
        })

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
    user_id = session.get("user_id")
    role = session.get("role")

    if not user_id:
        return redirect(url_for("login"))

    # Juiste model ophalen
    profile = Coach.query.get(user_id) if role == "coach" else Player.query.get(user_id)

    if request.method == "POST":

        # -----------------------
        # 1. NORMALE VELDEN
        # -----------------------
        profile.first_name = request.form.get("first_name")
        profile.last_name = request.form.get("last_name")
        profile.email = request.form.get("email")
        profile.phone = request.form.get("phone")
        profile.gender = request.form.get("gender")
        profile.ranking = request.form.get("ranking")
        profile.lesson_type_preference = request.form.get("lesson_type_preference")
        profile.playing_intensity = request.form.get("playing_intensity")


        if role == "player":
            dob = request.form.get("dob")
            if dob:
                profile.date_of_birth = dob

        # -----------------------
        # 2. FOTO UPLOAD BLOK
        # -----------------------
        file = request.files.get("image")

        if file and file.filename != "":
            ext = file.filename.split(".")[-1]
            filename = f"profile_{user_id}_{int(datetime.now().timestamp())}.{ext}"

            file_bytes = file.read()  # <-- Supabase verwacht BYTES

            # Upload naar Supabase Storage
            supabase.storage.from_("profile_pictures").upload(filename, file_bytes)

            # Publieke URL ophalen
            public_url = supabase.storage.from_("profile_pictures").get_public_url(filename)

            # Opslaan in database
            profile.profile_image = public_url

        # -----------------------
            # 3. OPSLAAN
        # -----------------------
        db.session.commit()

        return redirect(url_for("coach_dashboard" if role == "coach" else "player_dashboard"))

    return render_template("edit_profile.html", profile=profile)

# ============================================================
#  MAIN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)


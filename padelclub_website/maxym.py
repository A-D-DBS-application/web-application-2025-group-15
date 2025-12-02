# ============================================================
#  INITIALISATIE & IMPORTS
# ============================================================

from dotenv import load_dotenv
load_dotenv()  # <-- verplicht .env laden vóór supabase_client

from config import Config
from supabase_client import supabase
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import date, datetime, time
from config import Config
from dotenv import load_dotenv

app = Flask(__name__)


# ============================================================
#  CLEANUP: VERPLAATS AFGELOPEN LESSEN
# ============================================================

def cleanup_past_lessons():
    """
    Verplaats afgelopen lessen uit 'lessons' naar 'completed_lessons'
    en verwijder ze uit 'lessons' (lesson_players via ON DELETE CASCADE).
    """
    try:
        today = date.today()
        now_time = datetime.now().time()

        resp = (
            supabase.table("lessons")
            .select("lesson_id, date, start_time, end_time, coach_id")
            .lte("date", today.isoformat())
            .execute()
        )
        lessons = resp.data or []
        if not lessons:
            return

        lessons_by_id = {}
        past_ids = []

        for les in lessons:
            lid = les.get("lesson_id")
            if not lid:
                continue

            raw_date = les.get("date")
            if not raw_date:
                continue

            if isinstance(raw_date, str):
                try:
                    lesson_date = date.fromisoformat(raw_date)
                except Exception:
                    continue
            else:
                lesson_date = raw_date

            end_str = (les.get("end_time") or "")[:8]

            is_past = False
            if lesson_date < today:
                is_past = True
            elif lesson_date == today and end_str:
                try:
                    h, m, s = map(int, end_str.split(":"))
                    end_t = time(h, m, s)
                    if end_t <= now_time:
                        is_past = True
                except Exception:
                    pass

            if not is_past:
                continue

            lessons_by_id[lid] = {
                "date": lesson_date.isoformat(),
                "start_time": (les.get("start_time") or "")[:8],
                "end_time": end_str,
                "coach_id": les.get("coach_id"),
            }
            past_ids.append(lid)

        if not past_ids:
            return

        resp_lp = (
            supabase.table("lesson_players")
            .select("lesson_id, player_id")
            .in_("lesson_id", past_ids)
            .execute()
        )
        lp_rows = resp_lp.data or []

        completed_rows = []
        for row in lp_rows:
            lid = row.get("lesson_id")
            pid = row.get("player_id")
            if not lid or not pid:
                continue

            info = lessons_by_id.get(lid)
            if not info:
                continue

            completed_rows.append({
                "lesson_id": lid,
                "player_id": pid,
                "coach_id": info.get("coach_id"),
                "date": info.get("date"),
                "start_time": info.get("start_time"),
                "end_time": info.get("end_time"),
            })

        if completed_rows:
            supabase.table("completed_lessons").insert(completed_rows).execute()

        supabase.table("lessons").delete().in_("lesson_id", past_ids).execute()
        print("cleanup_past_lessons: verplaatst", len(completed_rows), "rows")

    except Exception as e:
        print("Fout bij cleanup_past_lessons:", e)


app.config.from_object(Config)


# ============================================================
#  HOME ROUTE
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
#  LOGIN - SYSTEEM ZONDER WACHTWOORD
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_input = request.form.get("email", "").strip()
        print(f"Inlogpoging voor: {email_input}")

        if not email_input:
            return render_template("login.html", error="Vul je e-mailadres in.")

        try:
            # --- probeer als speler ---
            resp_player = (
                supabase.table("players")
                .select("*")
                .eq("email", email_input)
                .execute()
            )
            players = resp_player.data or []
            if players:
                player = players[0]
                session["user_id"] = player["player_id"]
                session["role"] = "player"
                session["name"] = player.get("first_name") or ""
                session["assigned_coach"] = player.get("assigned_coach_id")
                return redirect(url_for("player_dashboard"))

            # --- probeer als coach ---
            resp_coach = (
                supabase.table("coaches")
                .select("*")
                .eq("email", email_input)
                .execute()
            )
            coaches = resp_coach.data or []
            if coaches:
                coach = coaches[0]
                session["user_id"] = coach["coach_id"]
                session["role"] = "coach"
                session["name"] = coach.get("first_name") or ""
                return redirect(url_for("coach_dashboard"))

            return render_template("login.html",
                                   error="Geen account gevonden met dit e-mailadres.")

        except Exception as e:
            print("❌ Login error:", repr(e))
            return render_template("login.html",
                                   error="Er ging iets mis bij het inloggen. Probeer later opnieuw.")

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

    geplande = []
    progress = None

    # -----------------------------
    # Geplande lessen
    # -----------------------------
    try:
        resp_lp = (
            supabase.table("lesson_players")
            .select("lesson_id")
            .eq("player_id", player_id)
            .execute()
        )
        lp_rows = resp_lp.data or []
        lesson_ids = [r.get("lesson_id") for r in lp_rows if r.get("lesson_id")]

        if lesson_ids:
            resp_lessons = (
                supabase.table("lessons")
                .select("lesson_id, date, start_time, end_time, coach_id")
                .in_("lesson_id", lesson_ids)
                .order("date", desc=False)
                .execute()
            )

            lesson_rows = resp_lessons.data or []

            coach_ids = {l.get("coach_id") for l in lesson_rows if l.get("coach_id")}
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
                    naam = f"{c.get('first_name','')} {c.get('last_name','')}".strip()
                    coach_name_by_id[cid] = naam or "Onbekend"

            for les in lesson_rows:
                geplande.append({
                    "lesson_id": les.get("lesson_id"),
                    "date": les.get("date"),
                    "start_time": (les.get("start_time") or "")[:5],
                    "end_time": (les.get("end_time") or "")[:5],
                    "coach_name": coach_name_by_id.get(les.get("coach_id"), "Onbekend"),
                })

    except Exception as e:
        print("Fout bij ophalen geplande lessen speler:", e)
        geplande = []

    # -----------------------------
    # Voortgang
    # -----------------------------
    try:
        resp_player = (
            supabase.table("players")
            .select("ranking, hand_preference, strengths, weaknesses")
            .eq("player_id", player_id)
            .maybe_single()
            .execute()
        )
        pdata = resp_player.data or {}

        if pdata:
            progress = {
                "p_score": pdata.get("ranking"),
                "hand": pdata.get("hand_preference"),
                "strengths": pdata.get("strengths"),
                "weaknesses": pdata.get("weaknesses"),
            }

    except Exception as e:
        print("Fout bij ophalen voortgang speler:", e)
        progress = None

    # -----------------------------
    # Recente evaluaties
    # -----------------------------
    evaluations = []
    try:
        resp_eval = (
            supabase.table("completed_lessons")
            .select("date, start_time, end_time, coach_id, coach_feedback, rating")
            .eq("player_id", player_id)
            .order("date", desc=True)
            .limit(5)
            .execute()
        )

        eval_rows = resp_eval.data or []
        coach_ids_eval = {r.get("coach_id") for r in eval_rows if r.get("coach_id")}
        coach_name_by_id_eval = {}

        if coach_ids_eval:
            resp_coaches_eval = (
                supabase.table("coaches")
                .select("coach_id, first_name, last_name")
                .in_("coach_id", list(coach_ids_eval))
                .execute()
            )
            for c in (resp_coaches_eval.data or []):
                cid = c["coach_id"]
                naam = f"{c['first_name']} {c['last_name']}".strip()
                coach_name_by_id_eval[cid] = naam or "Onbekend"

        for r in eval_rows:
            evaluations.append({
                "date": r.get("date"),
                "time": f"{(r.get('start_time') or '')[:5]} – {(r.get('end_time') or '')[:5]}",
                "coach_name": coach_name_by_id_eval.get(r.get("coach_id"), "Onbekend"),
                "feedback": r.get("coach_feedback"),
                "rating": r.get("rating"),
            })

    except Exception as e:
        print("Fout bij ophalen evaluaties speler:", e)
        evaluations = []

    return render_template(
        "player_dashboard.html",
        geplande=geplande,
        progress=progress,
        evaluations=evaluations,
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
            if supabase.table("players").select("player_id").eq("email", email).execute().data:
                return render_template("login.html",
                                       error="Dit e-mailadres bestaat al. Log hier in.")
            if supabase.table("coaches").select("coach_id").eq("email", email).execute().data:
                return render_template("login.html",
                                       error="Dit e-mailadres is al geregistreerd als coach.")
        except:
            pass

        session["player_data"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone
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
            return render_template("login.html",
                                   error="Account aangemaakt! Je kunt nu inloggen.")
        except Exception:
            return render_template("register_player_step2.html",
                                   error="Er ging iets mis bij het opslaan.")

    return render_template("register_player_step2.html")

# --- coach registratie ---
@app.route("/register/coach", methods=["GET", "POST"])
def register_coach():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")

        if not email or not first_name or not last_name:
            return render_template("register_coach_step1.html",
                                   error="Vul zeker e-mail, voornaam en achternaam in.")

        try:
            if supabase.table("coaches").select("coach_id").eq("email", email).execute().data:
                return render_template("login.html",
                                       error="Dit e-mailadres bestaat al. Log hier in.")
            if supabase.table("players").select("player_id").eq("email", email).execute().data:
                return render_template("login.html",
                                       error="Dit e-mailadres is al geregistreerd als speler.")
        except:
            pass

        session["coach_data"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone
        }
        return redirect(url_for("register_coach_step2"))

    return render_template("register_coach_step1.html")


@app.route("/register/coach/step2", methods=["GET", "POST"])
def register_coach_step2():
    if "coach_data" not in session:
        return redirect(url_for("register_coach_step1"))

    if request.method == "POST":
        data = session["coach_data"]
        data["is_active"] = True
        data["gender"] = request.form.get("gender")
        data["ranking"] = request.form.get("ranking")

        try:
            supabase.table("coaches").insert(data).execute()
            session.pop("coach_data", None)
            return render_template("login.html",
                                   error="Account aangemaakt! Je kunt nu inloggen.")
        except Exception:
            return render_template("register_coach_step2.html",
                                   error="Er ging iets mis bij het opslaan.")

    return render_template("register_coach_step2.html")


# ============================================================
#  LES AANVRAGEN (PLAYER)
# ============================================================

@app.route("/player/book_lesson", methods=["GET", "POST"])
def book_lesson():
    if session.get("role") != "player":
        return redirect(url_for("home"))

    player_id = session.get("user_id")

    # coaches ophalen
    try:
        resp_coaches = (
            supabase.table("coaches")
            .select("coach_id, first_name, last_name, email")
            .execute()
        )
        coaches = resp_coaches.data or []
    except Exception:
        coaches = []

    available_slots = None
    selected_coach_id = None
    selected_date = None
    error = None

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
        action = request.form.get("action")
        selected_coach_id = request.form.get("coach_id")
        selected_date = request.form.get("date")

        # -----------------------------
        #  TIJDSLOTEN TONEN
        # -----------------------------
        if action == "show_slots":
            if not selected_coach_id or not selected_date:
                error = "Kies eerst een coach en een datum."
            else:
                try:
                    coach_id_int = int(selected_coach_id)

                    resp_lessons = (
                        supabase.table("lessons")
                        .select("start_time, end_time")
                        .eq("coach_id", coach_id_int)
                        .eq("date", selected_date)
                        .execute()
                    )
                    existing = resp_lessons.data or []

                    taken = set()
                    for row in existing:
                        s = (row.get("start_time") or "")[:5]
                        e = (row.get("end_time") or "")[:5]
                        if s and e:
                            taken.add(f"{s}-{e}")

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

        # -----------------------------
        #  LES BOEKEN
        # -----------------------------
        elif action == "book":
            slot_id = request.form.get("slot")

            if not selected_coach_id or not selected_date or not slot_id:
                error = "Kies een coach, datum én tijdslot."
            else:
                try:
                    coach_id_int = int(selected_coach_id)
                    player_id_int = int(player_id)
                    start_str, end_str = slot_id.split("-")

                    booking_data = {
                        "coach_id": coach_id_int,
                        "date": selected_date,
                        "start_time": start_str,
                        "end_time": end_str,
                    }

                    resp_insert = (
                        supabase.table("lessons")
                        .insert(booking_data)
                        .execute()
                    )

                    inserted_rows = resp_insert.data or []
                    if not inserted_rows:
                        raise Exception("Geen data terug van lessons-insert")

                    lesson_id = inserted_rows[0].get("lesson_id")
                    if not lesson_id:
                        raise Exception("lesson_id ontbreekt in insert-respons")

                    lp_data = {"lesson_id": lesson_id, "player_id": player_id_int}
                    resp_lp = supabase.table("lesson_players").insert(lp_data).execute()

                    return redirect(url_for("player_dashboard"))

                except Exception as e:
                    print("Fout bij boeken les:", repr(e))
                    error = "Er ging iets mis bij het boeken. Probeer later opnieuw."

    return render_template(
        "book_lesson.html",
        coaches=coaches,
        available_slots=available_slots,
        selected_coach_id=selected_coach_id,
        selected_date=selected_date,
        error=error,
    )


# ============================================================
#  LES ANNULEREN (PLAYER)
# ============================================================

@app.route("/confirm_cancel_lesson/<int:lesson_id>")
def confirm_cancel_lesson(lesson_id):
    if session.get("role") != "player":
        return redirect(url_for("login"))
    return render_template("confirm_cancel_lesson.html", lesson_id=lesson_id)


@app.route("/cancel_lesson/<int:lesson_id>")
def cancel_lesson(lesson_id):
    if session.get("role") != "player":
        return redirect(url_for("login"))

    player_id = session.get("user_id")

    try:
        check = (
            supabase.table("lesson_players")
            .select("*")
            .eq("lesson_id", lesson_id)
            .eq("player_id", player_id)
            .maybe_single()
            .execute()
        )

        if not check.data:
            return render_template("error.html",
                                   message="Je mag deze les niet annuleren.")

        supabase.table("lessons").delete().eq("lesson_id", lesson_id).execute()
        return redirect(url_for("cancel_success"))

    except Exception as e:
        print("Fout bij annuleren:", e)
        return render_template("error.html",
                               message="Er ging iets mis bij het annuleren.")


@app.route("/cancel_success")
def cancel_success():
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

    # -----------------------------
    # Spelers ophalen
    # -----------------------------
    try:
        resp_players = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email, phone")
            .eq("assigned_coach_id", coach_id)
            .execute()
        )
        spelers = resp_players.data or []
    except Exception:
        spelers = []

    # -----------------------------
    # Aankomende lessen
    # -----------------------------
    lessen = []
    try:
        resp_lessons = (
            supabase.table("lessons")
            .select("lesson_id, date, start_time, end_time, coach_id")
            .eq("coach_id", coach_id)
            .order("date", desc=False)
            .execute()
        )
        lesson_rows = resp_lessons.data or []
        lesson_ids = [l.get("lesson_id") for l in lesson_rows if l.get("lesson_id")]

        lp_by_lesson = {}
        if lesson_ids:
            resp_lp = (
                supabase.table("lesson_players")
                .select("lesson_id, player_id")
                .in_("lesson_id", lesson_ids)
                .execute()
            )
            for row in (resp_lp.data or []):
                lid = row.get("lesson_id")
                pid = row.get("player_id")
                if lid and pid:
                    lp_by_lesson.setdefault(lid, []).append(pid)

        all_player_ids = sorted({pid for pids in lp_by_lesson.values() for pid in pids})
        name_by_player = {}

        if all_player_ids:
            resp_pnames = (
                supabase.table("players")
                .select("player_id, first_name, last_name")
                .in_("player_id", all_player_ids)
                .execute()
            )
            for r in (resp_pnames.data or []):
                pid = r.get("player_id")
                naam = f"{r.get('first_name','')} {r.get('last_name','')}".strip()
                name_by_player[pid] = naam or f"Speler {pid}"

        for les in lesson_rows:
            lid = les["lesson_id"]
            pids = lp_by_lesson.get(lid, [])
            namen = [name_by_player.get(pid, f"Speler {pid}") for pid in pids]

            lessen.append({
                "date": les["date"],
                "start_time": (les["start_time"] or "")[:5],
                "end_time": (les["end_time"] or "")[:5],
                "players": ", ".join(namen) if namen else "Geen spelers gekoppeld",
            })

    except Exception:
        lessen = []

    # -----------------------------
    # Afgelopen lessen
    # -----------------------------
    afgelopen_lessen = []
    try:
        resp_completed = (
            supabase.table("completed_lessons")
            .select("id, lesson_id, player_id, date, start_time, end_time, coach_id, evaluation, coach_feedback, rating")
            .eq("coach_id", coach_id)
            .order("date", desc=False)
            .execute()
        )

        comp_rows = resp_completed.data or []
        by_lesson = {}
        all_completed_ids = set()

        # groepeer per les
        for r in comp_rows:
            lid = r["lesson_id"]
            pid = r["player_id"]
            all_completed_ids.add(pid)

            if lid not in by_lesson:
                by_lesson[lid] = {
                    "lesson_id": lid,
                    "date": r["date"],
                    "start_time": (r["start_time"] or "")[:5],
                    "end_time": (r["end_time"] or "")[:5],
                    "player_ids": [],
                    "has_feedback": bool(r["coach_feedback"]),
                }

            by_lesson[lid]["player_ids"].append(pid)

            if r.get("coach_feedback"):
                by_lesson[lid]["has_feedback"] = True

        # speler-namen ophalen
        name_completed = {}
        if all_completed_ids:
            resp_names = (
                supabase.table("players")
                .select("player_id, first_name, last_name")
                .in_("player_id", list(all_completed_ids))
                .execute()
            )
            for r in (resp_names.data or []):
                pid = r["player_id"]
                naam = f"{r['first_name']} {r['last_name']}".strip()
                name_completed[pid] = naam

        # evaluatiestatus toevoegen
        for info in by_lesson.values():
            has_eval = False
            for r in comp_rows:
                if r["lesson_id"] == info["lesson_id"] and r.get("evaluation"):
                    has_eval = True
                    break

            pnames = [name_completed.get(pid, f"Speler {pid}") for pid in info["player_ids"]]

            afgelopen_lessen.append({
                "lesson_id": info["lesson_id"],
                "date": info["date"],
                "start_time": info["start_time"],
                "end_time": info["end_time"],
                "players": ", ".join(pnames),
                "has_evaluation": has_eval
            })

    except Exception as e:
        print("Fout bij ophalen afgelopen lessen coach:", e)
        afgelopen_lessen = []

    return render_template(
        "coach_dashboard.html",
        spelers=spelers,
        lessen=lessen,
        afgelopen_lessen=afgelopen_lessen,
    )


# ============================================================
#  COACH – LES EVALUEREN
# ============================================================

@app.route("/coach/evaluate_lesson/<int:lesson_id>/step/<int:step>", methods=["GET", "POST"])
def evaluate_lesson(lesson_id, step):

    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    resp = (
        supabase.table("completed_lessons")
        .select("*")
        .eq("lesson_id", lesson_id)
        .eq("coach_id", coach_id)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return redirect(url_for("coach_dashboard"))

    base = rows[0]
    evaluation = base.get("evaluation") or {}

    # -----------------------------
    # POST
    # -----------------------------
    if request.method == "POST":

        if step == 1:
            evaluation["techniek"] = {
                "forehand": request.form.get("forehand_score"),
                "backhand": request.form.get("backhand_score"),
                "volley": request.form.get("volley_score"),
                "smash": request.form.get("smash_score"),
                "opmerking": request.form.get("opmerking")
            }

        if step == 2:
            evaluation["tactiek"] = {
                "positiespel": request.form.get("positiespel_score"),
                "keuze_slagen": request.form.get("keuze_slagen_score"),
                "samenwerking": request.form.get("samenwerking_score"),
                "speelstrategie": request.form.get("speelstrategie_score"),
                "opmerking": request.form.get("opmerking")
            }

        if step == 3:
            evaluation["fysiek"] = {
                "conditie": request.form.get("conditie_score"),
                "reactiesnelheid": request.form.get("reactiesnelheid_score"),
                "explosiviteit": request.form.get("explosiviteit_score"),
                "opmerking": request.form.get("opmerking")
            }

        if step == 4:
            evaluation["mentaal"] = {
                "focus": request.form.get("focus_score"),
                "doorzettingsvermogen": request.form.get("doorzet_score"),
                "opmerking": request.form.get("opmerking")
            }

        supabase.table("completed_lessons").update({
            "evaluation": evaluation
        }).eq("lesson_id", lesson_id).eq("coach_id", coach_id).execute()

        if step < 5:
            return redirect(url_for("evaluate_lesson", lesson_id=lesson_id, step=step + 1))
        else:
            return redirect(url_for("coach_dashboard"))

    # GET
    if step == 5:
        return render_template(
            "evaluate_steps/step5.html",
            lesson=base,
            evaluation=evaluation
        )

    return render_template(
        f"evaluate_steps/step{step}.html",
        lesson=base,
        evaluation=evaluation
    )


# ============================================================
#  EVALUATIE BEKIJKEN (COACH)
# ============================================================

@app.route("/coach/evaluation/<int:lesson_id>")
def view_evaluation(lesson_id):

    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    resp = (
        supabase.table("completed_lessons")
        .select("*")
        .eq("lesson_id", lesson_id)
        .eq("coach_id", coach_id)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return redirect(url_for("coach_dashboard"))

    lesson = rows[0]
    evaluation = lesson.get("evaluation") or {}

    return render_template("evaluate_steps/view_evaluation.html",
                           lesson=lesson, evaluation=evaluation)


# ============================================================
#  COACH – SPELER TOEVOEGEN
# ============================================================

@app.route("/coach/add_player", methods=["GET", "POST"])
def add_player():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")
    error = None

    # POST
    if request.method == "POST":
        player_id = request.form.get("player_id")

        if not player_id:
            error = "Geen speler geselecteerd."
        else:
            try:
                resp_player = (
                    supabase.table("players")
                    .select("assigned_coach_id")
                    .eq("player_id", player_id)
                    .maybe_single()
                    .execute()
                )

                assigned = resp_player.data.get("assigned_coach_id") if resp_player.data else None

                if assigned is not None:
                    error = "Deze speler is al gekoppeld aan een coach."
                else:
                    supabase.table("players").update(
                        {"assigned_coach_id": coach_id}
                    ).eq("player_id", player_id).execute()

                    return redirect(url_for("coach_dashboard"))

            except Exception as e:
                print("Fout bij koppelen speler:", e)
                error = "Er ging iets mis bij het koppelen. Probeer later opnieuw."

    # GET (en fallback)
    q = request.args.get("q", "").strip()

    try:
        query = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email, phone")
            .is_("assigned_coach_id", None)
        )

        if q:
            query = query.ilike("first_name", f"%{q}%")

        resp_spelers = query.execute()
        spelers = resp_spelers.data or []

    except Exception as e:
        print("Fout bij zoeken spelers:", e)
        spelers = []
        if not error:
            error = "Er ging iets mis bij het ophalen van spelers."

    return render_template("add_player.html", spelers=spelers, q=q, error=error)


# ============================================================
#  COACH – SPELER VERWIJDEREN
# ============================================================

@app.route("/coach/remove_player/<int:player_id>")
def remove_player(player_id):
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    try:
        supabase.table("players").update(
            {"assigned_coach_id": None}
        ).eq("player_id", player_id).execute()

    except Exception as e:
        print("Fout bij verwijderen speler:", e)

    return redirect(url_for("coach_dashboard"))


# ============================================================
#  COACH – LES INPLANNEN (KEUZE)
# ============================================================

@app.route("/coach/schedule_lesson")
def schedule_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("login"))
    return render_template("schedule_lesson_choice.html")


# ============================================================
#  COACH – GROEPSLES INPLANNEN
# ============================================================

@app.route("/coach/schedule_group_lesson", methods=["GET", "POST"])
def schedule_group_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    try:
        resp_spelers = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email")
            .eq("assigned_coach_id", coach_id)
            .execute()
        )
        spelers = resp_spelers.data or []
    except Exception:
        spelers = []

    if request.method == "POST":
        selected_players = request.form.getlist("player_ids")

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
        lesson_type = request.form.get("lesson_type")
        notes = request.form.get("notes")

        if not date or not start_time or not end_time:
            return render_template(
                "schedule_group_lesson.html",
                spelers=spelers,
                error="Vul alle velden (datum en uren) in."
            )

        try:
            bookings = []
            for pid in selected_players:
                bookings.append({
                    "player_id": pid,
                    "coach_id": coach_id,
                    "date": date,
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": "geboekt",
                })

            supabase.table("bookings").insert(bookings).execute()
            return redirect(url_for("coach_dashboard"))

        except Exception as e:
            print("Fout bij groepsles plannen:", e)
            return render_template(
                "schedule_group_lesson.html",
                spelers=spelers,
                error="Er ging iets mis bij het inplannen. Probeer later opnieuw."
            )

    return render_template("schedule_group_lesson.html", spelers=spelers)


# ============================================================
#  COACH – INDIVIDUELE LES INPLANNEN
# ============================================================

@app.route("/coach/schedule_individual_lesson", methods=["GET", "POST"])
def schedule_individual_lesson():
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    try:
        resp_spelers = (
            supabase.table("players")
            .select("player_id, first_name, last_name, email")
            .eq("assigned_coach_id", coach_id)
            .execute()
        )
        spelers = resp_spelers.data or []
    except Exception:
        spelers = []

    if request.method == "POST":
        player_id = request.form.get("player_id")
        date = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        lesson_type = request.form.get("lesson_type")
        notes = request.form.get("notes")

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
            }

            supabase.table("bookings").insert(booking_data).execute()
            return redirect(url_for("coach_dashboard"))

        except Exception as e:
            print("Fout bij individuele les:", e)
            return render_template(
                "schedule_individual_lesson.html",
                spelers=spelers,
                error="Er ging iets mis bij het inplannen. Probeer later opnieuw."
            )

    return render_template("schedule_individual_lesson.html", spelers=spelers)


# ============================================================
#  COACH – SPELER DETAILS / STERKTES / ZWAKTES
# ============================================================

@app.route("/coach/player/<int:player_id>", methods=["GET", "POST"])
def coach_player_detail(player_id):
    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")

    try:
        resp_check = (
            supabase.table("players")
            .select("assigned_coach_id")
            .eq("player_id", player_id)
            .maybe_single()
            .execute()
        )
        data_check = resp_check.data or {}
        if data_check.get("assigned_coach_id") not in (None, coach_id):
            return redirect(url_for("coach_dashboard"))
    except Exception:
        pass

    if request.method == "POST":
        strengths = request.form.get("strengths") or None
        weaknesses = request.form.get("weaknesses") or None

        try:
            supabase.table("players").update({
                "strengths": strengths,
                "weaknesses": weaknesses,
            }).eq("player_id", player_id).execute()
        except Exception as e:
            print("Fout bij updaten sterktes/zwaktes:", e)

    try:
        resp_speler = (
            supabase.table("players")
            .select(
                "player_id, first_name, last_name, email, phone, gender, ranking,"
                "hand_preference, strengths, weaknesses"
            )
            .eq("player_id", player_id)
            .single()
            .execute()
        )
        speler = resp_speler.data
    except Exception:
        speler = None

    if not speler:
        return redirect(url_for("coach_dashboard"))

    return render_template("player_detail.html", speler=speler)


# ============================================================
#  LOGOUT
# ============================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
#  MAIN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)

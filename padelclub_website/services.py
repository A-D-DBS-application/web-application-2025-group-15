from sqlalchemy import func
from datetime import datetime
from extensions import db
from models import Coach, Player, Lesson, CoachAvailability, CompletedLesson

# ---------------------------------------------------------
# 1. Hulpfuncties voor P-score en meerderheid
# ---------------------------------------------------------


def _parse_p(value):
    """Zet een rankingveld om naar een integer P-score (bv. 'P1000' -> 1000)."""
    if value is None:
        return None
    s = str(value)
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _compute_avg_p(players):
    """Gemiddelde P-score van de betrokken spelers."""
    p_values = []
    for p in players:
        p_int = _parse_p(p.ranking)
        if p_int is not None:
            p_values.append(p_int)

    if not p_values:
        return None
    return sum(p_values) / len(p_values)


def _majority(values):
    """Meest voorkomende waarde in een lijst (simple majority)."""
    values = [v for v in values if v]
    if not values:
        return None
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return max(counts.items(), key=lambda x: x[1])[0]


# ---------------------------------------------------------
# 2. Gewichten voor de “ML-achtige” coachscore
# ---------------------------------------------------------

COACH_WEIGHTS = {
    # Lesvorm match (individueel/groeps)
    "lesson_type_match": 0.18,
    # Intensiteit (recreatief/competitief/…)
    "intensity_match": 0.22,
    # Niveau-match (P-score)
    "p_similarity": 0.25,
    # Aantal eerdere lessen met deze speler(s)
    "prior_relationship": 0.12,
    # Ervaring van coach (aantal completed lessons)
    "experience": 0.08,
    # Workload / planning (niet té vol)
    "workload": 0.10,
    # Inhoudelijke expertise (focus/onderwerp)
    "subject_match": 0.05,
}


# ---------------------------------------------------------
# 3. Feature-vector voor een coach
# ---------------------------------------------------------


def _build_coach_features(
    coach,
    players,
    subject,
    intensity,
    lesson_date,
    start_time,
    end_time,
    avg_p,
):
    """
    Bouwt een feature-vector (dict met waarden tussen 0 en 1) voor een coach.
    Dit is de 'ML-achtige' stap: we zetten alle relevante info om naar
    genormaliseerde features.
    """

    features = {
        "lesson_type_match": 0.5,    # neutrale start
        "intensity_match": 0.5,
        "p_similarity": 0.5,
        "prior_relationship": 0.0,
        "experience": 0.0,
        "workload": 0.5,
        "subject_match": 0.5,
    }

    # 1) Lesvorm: speler(s) vs coach
    player_lesson_prefs = [getattr(p, "lesson_type_preference", None) for p in players]
    group_lesson_pref = _majority(player_lesson_prefs)
    coach_lesson_pref = getattr(coach, "lesson_type_preference", None)

    if group_lesson_pref and coach_lesson_pref:
        if coach_lesson_pref == group_lesson_pref:
            features["lesson_type_match"] = 1.0
        else:
            features["lesson_type_match"] = 0.2
    elif group_lesson_pref or coach_lesson_pref:
        # slechts één van de twee gekend → half vertrouwen
        features["lesson_type_match"] = 0.6

    # 2) Intensiteit: recreatief / competitief / …
    coach_intensity = getattr(coach, "playing_intensity", None)
    if coach_intensity and intensity:
        if coach_intensity == intensity:
            features["intensity_match"] = 1.0
        else:
            # verschillend maar niet totaal onbekend
            features["intensity_match"] = 0.3
    elif coach_intensity or intensity:
        features["intensity_match"] = 0.6

    # 3) P-score similarity (continu in plaats van harde if-else)
    coach_p = _parse_p(getattr(coach, "ranking", None))
    if avg_p is not None and coach_p is not None:
        diff = abs(coach_p - avg_p)

        # we mappen de diff naar een similarity ∈ [0,1]
        # diff = 0  → 1.0
        # diff = 800 → 0.0  (vanaf daar beschouwen we het als heel slecht)
        MAX_DIFF = 800
        similarity = max(0.0, 1.0 - (diff / MAX_DIFF))
        features["p_similarity"] = similarity
    else:
        # geen info → neutraal laten (0.5)
        pass

    # 4) Relatiecoach: hoeveel eerdere lessen met deze speler(s)?
    player_ids = [p.player_id for p in players]
    previous_with_you = (
        db.session.query(func.count(CompletedLesson.id))
        .filter(
            CompletedLesson.coach_id == coach.coach_id,
            CompletedLesson.player_id.in_(player_ids),
        )
        .scalar()
    )

    if previous_with_you:
        # cap op 5 lessen → daarna >= 1.0
        capped = min(previous_with_you, 5)
        features["prior_relationship"] = capped / 5.0  # schaal 0–1

    # 5) Ervaring: totaal aantal completed lessons
    total_completed = (
        db.session.query(func.count(CompletedLesson.id))
        .filter(CompletedLesson.coach_id == coach.coach_id)
        .scalar()
    )
    if total_completed:
        capped_exp = min(total_completed, 20)  # max effect bij 20+ lessen
        features["experience"] = capped_exp / 20.0

    # 6) Workload: aantal toekomstige lessen vanaf deze datum
    upcoming = (
        db.session.query(func.count(Lesson.lesson_id))
        .filter(
            Lesson.coach_id == coach.coach_id,
            Lesson.date >= lesson_date,
        )
        .scalar()
    )

    # Minder is beter → we mappen naar een score:
    # 0 lessen → 1.0
    # 1–5 → 0.8
    # 6–10 → 0.5
    # >10 → 0.2
    if upcoming == 0:
        features["workload"] = 1.0
    elif upcoming <= 5:
        features["workload"] = 0.8
    elif upcoming <= 10:
        features["workload"] = 0.5
    else:
        features["workload"] = 0.2

    # 7) Onderwerp / focus: expertise van coach
    expertise = getattr(coach, "expertise_topics", "") or ""
    topics = [t.strip().lower() for t in expertise.split(",") if t.strip()]
    if subject:
        subj = subject.lower()
        if subj in topics:
            features["subject_match"] = 1.0
        elif topics:
            features["subject_match"] = 0.2  # andere topics, maar wel expertise
        else:
            features["subject_match"] = 0.5  # geen data
    else:
        # geen subject gekozen → neutraal
        features["subject_match"] = 0.5

    return features


# ---------------------------------------------------------
# 4. Scoren + uitleg genereren
# ---------------------------------------------------------


def _score_and_explain(
    coach,
    players,
    subject,
    intensity,
    lesson_date,
    start_time,
    end_time,
    avg_p,
):
    """
    Geeft (score, reasons) terug voor één coach.
    Score is gebaseerd op een gewogen som van genormaliseerde features.
    Alle uitleg is bewust positief of neutraal geformuleerd.
    """

    # Feature-vector bouwen
    features = _build_coach_features(
        coach=coach,
        players=players,
        subject=subject,
        intensity=intensity,
        lesson_date=lesson_date,
        start_time=start_time,
        end_time=end_time,
        avg_p=avg_p,
    )

    # Lineaire combinatie (zoals een simpel ML-model)
    raw_score = 0.0
    for name, value in features.items():
        weight = COACH_WEIGHTS.get(name, 0.0)
        raw_score += weight * value

    # Naar 0–100 schaal
    score = round(raw_score * 100, 1)

    # ------------------------
    # Uitleg op basis van features (altijd positief / neutraal)
    # ------------------------
    reasons = []

    # Lesvorm
    if features["lesson_type_match"] >= 0.9:
        reasons.append(
            "Deze coach geeft graag dezelfde soort lessen (individueel/groeps) als jouw voorkeur."
        )
    elif features["lesson_type_match"] <= 0.3:
        reasons.append(
            "Deze coach brengt wat variatie in lesvorm ten opzichte van wat je gewoon bent."
        )

    # Intensiteit
    if features["intensity_match"] >= 0.9:
        reasons.append(
            "De speelintensiteit van deze coach sluit perfect aan bij jouw voorkeur."
        )
    elif features["intensity_match"] <= 0.4:
        reasons.append(
            "Deze coach biedt een andere speelintensiteit, wat voor extra uitdaging kan zorgen."
        )

    # P-score / niveau
    coach_p = _parse_p(getattr(coach, "ranking", None))
    if avg_p is not None and coach_p is not None:
        diff = abs(coach_p - avg_p)
        if diff == 0:
            reasons.append(
                f"De P-score van deze coach is exact gelijk aan jouw niveau (verschil = {diff} punten)."
            )
        elif diff <= 100:
            reasons.append(
                f"De P-score van deze coach ligt bijna exact op jouw niveau (verschil = {diff} punten)."
            )
        elif diff <= 300:
            reasons.append(
                f"De P-score van deze coach ligt dicht bij jouw niveau (verschil = {diff} punten)."
            )
        elif diff <= 600:
            reasons.append(
                f"Er is een klein niveauverschil (verschil = {diff} punten), wat extra leermomenten kan creëren."
            )
        else:
            reasons.append(
                f"Je speelt met een duidelijk ander niveau (verschil = {diff} punten), wat een sterke leercurve kan geven."
            )
    else:
        reasons.append(
            "We combineren je profiel met planning en ervaring van coaches om een passende match te maken."
        )

    # Relatie / eerdere lessen met jou
    player_ids = [p.player_id for p in players]
    previous_with_you = (
        db.session.query(func.count(CompletedLesson.id))
        .filter(
            CompletedLesson.coach_id == coach.coach_id,
            CompletedLesson.player_id.in_(player_ids),
        )
        .scalar()
    )

    if previous_with_you:
        reasons.append(
            f"Je hebt al {previous_with_you} eerdere les(sen) met deze coach gehad, wat continuïteit geeft."
        )
    else:
        reasons.append(
            "Je krijgt de kans om met een nieuwe coach samen te werken."
        )

    # Ervaring (totaal)
    total_completed = (
        db.session.query(func.count(CompletedLesson.id))
        .filter(CompletedLesson.coach_id == coach.coach_id)
        .scalar()
    )
    if total_completed >= 10:
        reasons.append(
            "Deze coach heeft uitgebreide ervaring met verschillende spelers."
        )
    elif total_completed >= 3:
        reasons.append(
            "Deze coach heeft al een mooie basis aan ervaring met verschillende spelers."
        )
    else:
        reasons.append(
            "Deze coach heeft ruimte om samen met jou ervaring op te bouwen."
        )

    # Workload / planning (toekomstige lessen)
    upcoming = (
        db.session.query(func.count(Lesson.lesson_id))
        .filter(
            Lesson.coach_id == coach.coach_id,
            Lesson.date >= lesson_date,
        )
        .scalar()
    )
    if upcoming == 0:
        reasons.append("Deze coach heeft momenteel veel ruimte in de planning.")
    elif upcoming <= 5:
        reasons.append("Deze coach heeft een actieve maar goed beheersbare planning.")
    else:
        reasons.append(
            "Deze coach is populair en heeft een goed gevulde agenda."
        )

    # Subject / focus
    expertise = getattr(coach, "expertise_topics", "") or ""
    topics = [t.strip().lower() for t in expertise.split(",") if t.strip()]
    if subject:
        subj = subject.lower()
        if subj in topics:
            reasons.append("Deze coach heeft expliciete expertise in het gekozen thema.")
        elif topics:
            reasons.append(
                "Deze coach heeft expertise in andere thema’s die ook tijdens deze les kunnen terugkomen."
            )
        else:
            reasons.append(
                "Het profiel van deze coach is nog in opbouw; we focussen hier vooral op niveau, intensiteit en planning."
            )
    else:
        reasons.append(
            "Deze les is flexibel qua inhoud; we matchen vooral op niveau, intensiteit en beschikbaarheid."
        )

    return score, reasons


# ---------------------------------------------------------
# 5. Hoofdfunctie: coaches aanbevelen
# ---------------------------------------------------------


def recommend_coaches_for_lesson(
    players,
    subject,
    intensity,
    lesson_date,
    start_time,
    end_time,
    return_details=False,
):
    """
    Geeft een lijst van aanbevelingen, gesorteerd op score (hoog → laag).

    - als return_details = False → [(coach, score), ...]
    - als return_details = True  → [{"coach": coach, "score": score, "reasons": [...]} , ...]
    """

    avg_p = _compute_avg_p(players)

    # Alle coaches die in dit tijdslot beschikbaar zijn
    free_coaches_q = (
        Coach.query
        .join(CoachAvailability, Coach.coach_id == CoachAvailability.coach_id)
        .filter(
            CoachAvailability.date == lesson_date,
            CoachAvailability.start_time <= start_time,
            CoachAvailability.end_time >= end_time,
        )
        .distinct()
    )
    free_coaches = free_coaches_q.all()

    recommendations = []

    for coach in free_coaches:
        score, reasons = _score_and_explain(
            coach=coach,
            players=players,
            subject=subject,
            intensity=intensity,
            lesson_date=lesson_date,
            start_time=start_time,
            end_time=end_time,
            avg_p=avg_p,
        )

        if return_details:
            recommendations.append(
                {
                    "coach": coach,
                    "score": score,
                    "reasons": reasons,
                }
            )
        else:
            recommendations.append((coach, score))

    recommendations.sort(
        key=lambda item: item["score"] if return_details else item[1],
        reverse=True,
    )
    return recommendations
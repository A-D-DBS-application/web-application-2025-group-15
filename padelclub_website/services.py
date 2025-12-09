from sqlalchemy import func
from datetime import datetime
from extensions import db
from models import Coach, Player, Lesson, CoachAvailability, CompletedLesson


def _compute_avg_p(players):
    """Gemiddelde P-score van de betrokken spelers."""
    p_values = []
    for p in players:
        if p.ranking is None:
            continue
        s = str(p.ranking)
        digits = "".join(ch for ch in s if ch.isdigit())
        if not digits:
            continue
        try:
            p_values.append(int(digits))
        except ValueError:
            continue

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
    Score ~ 0–100, higher = beter.
    """

    score = 0
    reasons = []

    # Voor gebruiksgemak: 1 speler bij individuele les
    main_player = players[0] if players else None

    # 1️⃣ Lesvorm (individueel / groeps) – match speler vs coach
    player_lesson_prefs = [
        getattr(p, "lesson_type_preference", None) for p in players
    ]
    group_lesson_pref = _majority(player_lesson_prefs)
    coach_lesson_pref = getattr(coach, "lesson_type_preference", None)

    if group_lesson_pref and coach_lesson_pref:
        if coach_lesson_pref == group_lesson_pref:
            score += 20
            reasons.append(
                "Coach geeft graag dezelfde soort lessen (individueel/groeps) als jouw voorkeur."
            )
        else:
            score += 2
            reasons.append(
                "Coach geeft een andere lesvorm dan jouw voorkeur, dit kan afwisselend zijn maar is minder ideaal."
            )

    # 2️⃣ Intensiteit (recreatief/competitief/…) – speler vs coach
    coach_intensity = getattr(coach, "playing_intensity", None)
    if coach_intensity and intensity:
        if coach_intensity == intensity:
            score += 25
            reasons.append(
                "Speelintensiteit van coach sluit perfect aan bij jouw voorkeur."
            )
        else:
            score += 5
            reasons.append(
                "Speelintensiteit is anders dan jouw voorkeur, maar we denken dat dit nog werkbaar is."
            )

        # 3️⃣ P-score compatibiliteit (niveau)
    coach_center = getattr(coach, "ranking", None)
    coach_p = None
    if coach_center:
        digits = "".join(ch for ch in str(coach_center) if ch.isdigit())
        if digits:
            try:
                coach_p = int(digits)
            except ValueError:
                coach_p = None

    if avg_p is not None and coach_p is not None:
        diff = abs(coach_p - avg_p)

        if diff == 0:
            score += 25
            reasons.append(
                f"P-score van coach is exact gelijk aan jouw niveau (verschil = {diff} punten)."
            )
        elif diff <= 100:
            score += 22
            reasons.append(
                f"P-score van coach ligt bijna exact op jouw niveau (verschil = {diff} punten)."
            )
        elif diff <= 300:
            score += 15
            reasons.append(
                f"P-score van coach ligt redelijk dicht bij jouw niveau (verschil = {diff} punten)."
            )
        elif diff <= 600:
            score += 5
            reasons.append(
                f"Niveau van coach is speelbaar maar niet ideaal (verschil = {diff} punten)."
            )
        else:
            reasons.append(
                f"Niveau van coach ligt vrij ver van jouw P-score (verschil = {diff} punten); dit is een minder ideale match."
            )
    else:
        reasons.append(
            "Er is onvoldoende P-score informatie om niveau perfect te matchen."
        )

    # 4️⃣ Relatie coach–speler: hoeveel eerdere lessen samen?
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
        bonus = min(previous_with_you * 3, 15)
        score += bonus
        reasons.append(
            f"Coach heeft al {previous_with_you} eerdere les(sen) met jou/jullie gegeven, wat continuïteit geeft."
        )
    else:
        reasons.append("Coach heeft nog geen voorgeschiedenis met jou in het systeem.")

    # 5️⃣ Ervaring in totaal (alle spelers)
    total_completed = (
        db.session.query(func.count(CompletedLesson.id))
        .filter(CompletedLesson.coach_id == coach.coach_id)
        .scalar()
    )
    if total_completed >= 10:
        score += 5
        reasons.append(
            "Coach heeft al veel lessen gegeven en heeft ervaring met verschillende spelers."
        )
    elif total_completed >= 3:
        score += 3
        reasons.append(
            "Coach heeft al wat ervaring met lessen in dit systeem."
        )
    else:
        reasons.append("Coach bouwt nog ervaring op in het systeem.")

    # 6️⃣ Workload / planning – lichte voorkeur voor niet té drukke coaches
    upcoming = (
        db.session.query(func.count(Lesson.lesson_id))
        .filter(Lesson.coach_id == coach.coach_id, Lesson.date >= lesson_date)
        .scalar()
    )

    if upcoming == 0:
        score += 7
        reasons.append("Coach heeft momenteel veel ruimte in de planning.")
    elif upcoming <= 5:
        score += 4
        reasons.append(
            "Coach heeft een goed gevulde maar beheersbare planning."
        )
    else:
        score -= 3
        reasons.append(
            "Coach heeft al veel toekomstige lessen; we vermijden overbelasting lichtjes."
        )

    return score, reasons


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

    free_coaches_q = (
        Coach.query
        .join(CoachAvailability, Coach.coach_id == CoachAvailability.coach_id)
        .filter(
            CoachAvailability.date == lesson_date,
            CoachAvailability.start_time <= start_time,
            CoachAvailability.end_time >= end_time
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
            recommendations.append({
                "coach": coach,
                "score": score,
                "reasons": reasons,
            })
        else:
            recommendations.append((coach, score))

    recommendations.sort(
        key=lambda item: item["score"] if return_details else item[1],
        reverse=True
    )
    return recommendations
from extensions import db
from sqlalchemy.dialects.postgresql import JSONB


# ============================================
#  ASSOCIATION TABLE (PLAYERS <-> LESSONS)
# ============================================

lesson_players = db.Table(
    "lesson_players",
    db.Column("lesson_id", db.Integer, db.ForeignKey("lessons.lesson_id"), primary_key=True),
    db.Column("player_id", db.BigInteger, db.ForeignKey("players.player_id"), primary_key=True),
    db.Column("attendance", db.Boolean),
    db.Column("feedback", db.Text)
)

# ============================================
#  ASSOCIATION TABLE (COACHES <-> PLAYERS)
# ============================================
coach_players = db.Table(
    "coach_players",
    db.Column("coach_id", db.BigInteger, db.ForeignKey("coaches.coach_id"), primary_key=True),
    db.Column("player_id", db.BigInteger, db.ForeignKey("players.player_id"), primary_key=True),
    db.Column("created_at", db.DateTime, server_default=db.func.now())
)

# ============================================
#  CLUB MODEL
# ============================================

class Club(db.Model):
    __tablename__ = "clubs"

    club_id = db.Column(db.Integer, primary_key=True)
    club_name = db.Column(db.String, nullable=False)
    location = db.Column(db.String)
    contact_info = db.Column(JSONB)
    sports_supported = db.Column(JSONB)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now())

    


# ============================================
#  COACH MODEL
# ============================================

class Coach(db.Model):
    __tablename__ = "coaches"

    coach_id = db.Column(db.BigInteger, primary_key=True)
    first_name = db.Column(db.Text, nullable=False)
    last_name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    phone = db.Column(db.Text)
    bio = db.Column(db.Text)
    hand_preference = db.Column(db.Text)
    gender = db.Column(db.String)
    date_of_birth = db.Column(db.Date, nullable=True)
    profile_image = db.Column(db.String, nullable=True)
    ranking = db.Column(db.String)
    lesson_type_preference = db.Column(db.String, nullable=True)
    playing_intensity = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    


    # Relationships
    lessons = db.relationship("Lesson", backref="coach", lazy=True)
    students = db.relationship("Player", secondary=coach_players, back_populates="coaches", lazy="dynamic")
    availability_slots = db.relationship(
        "CoachAvailability",
        backref="coach",
        cascade="all, delete-orphan",
        lazy=True
    )


# ============================================
#  PLAYER MODEL
# ============================================

class Player(db.Model):
    __tablename__ = "players"

    player_id = db.Column(db.BigInteger, primary_key=True)
    first_name = db.Column(db.Text, nullable=False)
    last_name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    phone = db.Column(db.Text)
    hand_preference = db.Column(db.Text)
    ranking = db.Column(db.String)
    gender = db.Column(db.String)
    date_of_birth = db.Column(db.Date, nullable=True)
    profile_image = db.Column(db.String, nullable=True)
    strengths = db.Column(db.Text)
    weaknesses = db.Column(db.Text)
    lesson_type_preference = db.Column(db.String(50))
    playing_intensity = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    # Relationships
    coaches = db.relationship("Coach", secondary=coach_players, back_populates="students")
    lessons = db.relationship(
        "Lesson",
        secondary=lesson_players
    )



# ============================================
#  LESSON MODEL
# ============================================

class Lesson(db.Model):
    __tablename__ = "lessons"

    lesson_id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("coaches.coach_id"))
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    lesson_type = db.Column(db.String, nullable=True)
    lesson_focus = db.Column(db.String, nullable=True)

    
    players = db.relationship("Player", secondary="lesson_players")





# ============================================
#  COACH AVAILABILITY MODEL
# ============================================

class CoachAvailability(db.Model):
    __tablename__ = "coach_availability"

    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.BigInteger, db.ForeignKey("coaches.coach_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)


# ============================================
#  COMPLETED LESSON MODEL
# ============================================

class CompletedLesson(db.Model):
    __tablename__ = "completed_lessons"

    id = db.Column(db.BigInteger, primary_key=True)
    lesson_id = db.Column(db.BigInteger)
    player_id = db.Column(db.BigInteger, nullable=False)
    coach_id = db.Column(db.BigInteger)
    date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    rating = db.Column(db.Numeric)
    coach_feedback = db.Column(db.Text)
    evaluation = db.Column(JSONB)
    created_at = db.Column(db.DateTime(timezone=True))


# ============================================
#  RECOMMENDATION MODEL
# ============================================

class Recommendation(db.Model):
    __tablename__ = "recommendations"

    recommendation_id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer)
    coach_id = db.Column(db.Integer)
    recommended_lesson_type = db.Column(db.String)
    confidence_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# ============================================
#  GROUP LESSON REQUEST MODEL
# ============================================

from datetime import datetime, timezone
class GroupLessonRequest(db.Model):
    __tablename__ = "group_lesson_requests"

    request_id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.player_id"), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey("coaches.coach_id"), nullable=False)

    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)

    lesson_focus = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    player = db.relationship("Player", backref="group_requests")
    coach = db.relationship("Coach", backref="group_requests")
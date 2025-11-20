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

    if session.get("role") != "player":
        return redirect(url_for("login"))
    
    return render_template("player_dashboard.html")

# ---------- COACH DASHBOARD ----------
@app.route("/coach")
def coach_dashboard():

    if session.get("role") != "coach":
        return redirect(url_for("login"))

    coach_id = session.get("user_id")
    
 
    my_players = []
    try:

        response = supabase.table("players").select("*").eq("assigned_coach_id", coach_id).execute()
        my_players = response.data
    except Exception as e:
        print(f"Fout bij ophalen spelers: {e}")

    return render_template("coach_dashboard.html", spelers=my_players, lessen=[], completed=[])

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

if __name__ == "__main__":
    app.run(debug=True)
        


















    


import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,      # controleer of DB-verbinding nog leeft
    "pool_recycle": 280,        # verbreek oude verbindingen voor Supabase dat doet
    "pool_size": 5,             # houd een kleine pool open
    "max_overflow": 10
}

    

   
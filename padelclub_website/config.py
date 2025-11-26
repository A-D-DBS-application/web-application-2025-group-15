import os
from pathlib import Path
from dotenv import load_dotenv

# Bepaal de map waar dit bestand (config.py) staat
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'

# Laad de .env alleen als hij bestaat
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    SECRET_KEY = os.getenv('SECRET_KEY')
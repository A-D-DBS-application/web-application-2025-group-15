from config import Config
from supabase import create_client

supabase=create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

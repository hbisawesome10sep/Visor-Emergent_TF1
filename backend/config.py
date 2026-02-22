from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
JWT_SECRET = os.environ['JWT_SECRET']
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY', '')
GOLDAPI_KEY = os.environ.get("GOLDAPI_KEY", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GMAIL_REDIRECT_URI = os.environ.get("GMAIL_REDIRECT_URI", "")
ENCRYPTION_MASTER_KEY = os.environ.get("ENCRYPTION_MASTER_KEY", "")

# Sensitive fields that need encryption
USER_SENSITIVE_FIELDS = ["pan", "aadhaar", "dob", "full_name"]
LOAN_SENSITIVE_FIELDS = ["account_number"]
GMAIL_TOKEN_SENSITIVE_FIELDS = ["access_token", "refresh_token", "client_secret"]

# Market data constants
REFRESH_TIMES_IST = ["09:25", "11:30", "12:30", "15:15"]
TROY_OZ_TO_GRAMS = 31.1035
GOLD_DOMESTIC_PREMIUM = 1.075
SILVER_DOMESTIC_PREMIUM = 1.155

# Gmail OAuth scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Auto-detect redirect URI from frontend URL
if not GMAIL_REDIRECT_URI:
    _fe_url = os.environ.get("FRONTEND_URL", "https://bankstatement-hub.preview.emergentagent.com")
    GMAIL_REDIRECT_URI = f"{_fe_url}/api/gmail/callback"

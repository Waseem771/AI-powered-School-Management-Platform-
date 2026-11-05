import hashlib
import os
import secrets
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# School Information
SCHOOL_NAME = os.getenv("SCHOOL_NAME", "Al-Noor Academy")
SCHOOL_TAGLINE = os.getenv("SCHOOL_TAGLINE", "Excellence in Education & Character")
SCHOOL_ADDRESS = os.getenv("SCHOOL_ADDRESS", "Plot 42, Sector F-8/4, Islamabad, Pakistan")
SCHOOL_PHONE = os.getenv("SCHOOL_PHONE", "+92 (51) 285-4321")
SCHOOL_EMAIL = os.getenv("SCHOOL_EMAIL", "info@alnoor-academy.edu.pk")
CURRENCY = os.getenv("CURRENCY", "Rs.")

# Environment. Anything other than an explicit "development" gets production safeguards.
APP_ENV = os.getenv("APP_ENV", "production").strip().lower()
IS_PRODUCTION = APP_ENV != "development"
# Labels the app as a demonstration holding made-up records.
DEMO_MODE = os.getenv("DEMO_MODE", "").strip().lower() == "true"

# Auth & Security
MIN_SECRET_KEY_LENGTH = 32
# SHA-256 of signing keys that were published in this project's public repository.
_PUBLISHED_SECRET_KEY_HASHES = {
    "c0da420d31e019b29f35bae6a68339e9459c2d20aeb7b42b55604a30eedc4a34",
    "01bbdba3b0d09cda35650c27342992ff670e84585bb1a36ab208bab1668eb700",
}
LOCAL_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def resolve_secret_key(raw_key: str, is_production: bool) -> str:
    """Production refuses an unsafe key. Development swaps it for a random one per process."""
    key = (raw_key or "").strip()
    is_published = hashlib.sha256(key.encode()).hexdigest() in _PUBLISHED_SECRET_KEY_HASHES
    if len(key) >= MIN_SECRET_KEY_LENGTH and not is_published:
        return key
    if is_production:
        raise RuntimeError(
            f"SECRET_KEY must be a private random value of at least {MIN_SECRET_KEY_LENGTH} characters. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    return secrets.token_urlsafe(48)


def allowed_cors_origins(is_production: bool, frontend_url: str) -> List[str]:
    """Exact origins only: FRONTEND_URL (comma-separated), plus local ports in development."""
    configured = [origin.strip().rstrip("/") for origin in (frontend_url or "").split(",") if origin.strip()]
    return configured if is_production else [*LOCAL_DEV_ORIGINS, *configured]


SECRET_KEY = resolve_secret_key(os.getenv("SECRET_KEY", ""), IS_PRODUCTION)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # One school working day.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_PASSWORD_RESET = os.getenv("ADMIN_PASSWORD_RESET", "").strip().lower() == "true"
CORS_ORIGINS = allowed_cors_origins(IS_PRODUCTION, os.getenv("FRONTEND_URL", ""))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/school.db")

# Groq API for RAG
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Default School Structure
GRADES = ["Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"]
SECTIONS = ["A", "B"]
SUBJECTS = ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Pakistan Studies"]

TUITION_FEE_MONTHLY = 3500
EXAM_FEE_SEMESTER = 500

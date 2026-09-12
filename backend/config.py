import os
from pathlib import Path
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

# Auth & Security
SECRET_KEY = os.getenv("SECRET_KEY", "educore_super_secret_jwt_key_2026_al_noor")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session, select

from config import SCHOOL_NAME
from database import create_db_and_tables, engine
from models.user import User, hash_password
from services.ai_service import ai_service

# Routers
from routers.auth import router as auth_router
from routers.students import router as students_router
from routers.fees import router as fees_router
from routers.results import router as results_router
from routers.dashboard import router as dashboard_router
from routers.ai import router as ai_router
from routers.chatbot import router as chatbot_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== [EduCore AI] Initializing System ===")
    # 1. Ensure database tables exist
    create_db_and_tables()

    # 2. Ensure default admin user exists
    with Session(engine) as session:
        admin_user = session.exec(select(User).where(User.username == "admin")).first()
        if not admin_user:
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin"
            )
            session.add(admin)
            session.commit()
            print("[Auth] Created default admin account (admin / admin123)")

    # 3. Keep startup responsive. The embedding model is initialized on the
    # first policy-assistant request instead of blocking every API endpoint.
    print("[RAG] Policy assistant model will initialize on first use.")

    print("=== [EduCore AI] System Ready on http://localhost:8000 ===")
    yield
    print("=== [EduCore AI] Shutting down ===")

app = FastAPI(
    title=f"EduCore AI - {SCHOOL_NAME} Management API",
    description="Full-stack AI-powered School Administration Platform featuring JWT Auth, Student CRUD, ReportLab PDF generators, scikit-learn + SHAP At-Risk detection, and FAISS + Groq RAG policy chatbot.",
    version="1.0.0",
    lifespan=lifespan
)

import os

cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
frontend_url = os.getenv("FRONTEND_URL", "").strip()
if frontend_url:
    cors_origins.append(frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(fees_router)
app.include_router(results_router)
app.include_router(dashboard_router)
app.include_router(ai_router)
app.include_router(chatbot_router)

@app.get("/")
def root():
    return {
        "system": "EduCore AI",
        "school": SCHOOL_NAME,
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

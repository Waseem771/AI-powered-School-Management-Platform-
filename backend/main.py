from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from config import ADMIN_PASSWORD, ADMIN_PASSWORD_RESET, CORS_ORIGINS, IS_PRODUCTION, SCHOOL_NAME
from database import create_db_and_tables, engine
from services.admin_setup import ensure_admin_account
from services.ai_service import ai_service

# Routers
from routers.auth import router as auth_router
from routers.students import router as students_router
from routers.fees import router as fees_router
from routers.results import router as results_router
from routers.dashboard import router as dashboard_router
from routers.ai import router as ai_router
from routers.chatbot import router as chatbot_router
from routers.admissions_crew import router as admissions_crew_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== [EduCore AI] Initializing System ===")
    create_db_and_tables()

    with Session(engine) as session:
        ensure_admin_account(session, IS_PRODUCTION, ADMIN_PASSWORD, force_reset=ADMIN_PASSWORD_RESET)

    if IS_PRODUCTION and not CORS_ORIGINS:
        print("[Security] FRONTEND_URL is not set, so browsers cannot reach this API.")

    # Keep startup responsive. The embedding model is initialized on the
    # first policy-assistant request instead of blocking every API endpoint.
    print("[RAG] Policy assistant model will initialize on first use.")

    print("=== [EduCore AI] System Ready ===")
    yield
    print("=== [EduCore AI] Shutting down ===")


app = FastAPI(
    title=f"EduCore AI - {SCHOOL_NAME} Management API",
    description="School administration platform: students, fees, exam results, analytics, and AI assistance.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Student records and PDFs must not linger in shared-computer browser caches.
    response.headers["Cache-Control"] = "no-store"
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


# Sign-in uses a bearer token, not cookies, so credentials stay off.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Register routers
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(fees_router)
app.include_router(results_router)
app.include_router(dashboard_router)
app.include_router(ai_router)
app.include_router(chatbot_router)
app.include_router(admissions_crew_router)


@app.get("/")
def root():
    status = {
        "system": "EduCore AI",
        "school": SCHOOL_NAME,
        "status": "online",
        "version": "1.0.0",
    }
    return status if IS_PRODUCTION else {**status, "docs_url": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

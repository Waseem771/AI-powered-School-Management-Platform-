@echo off
rem Starts the fictional demo school. Uses backend\demo.db only, and never opens school.db.
rem Build it first with: cd backend ^&^& python seed_demo.py
if not exist backend\demo.db (
  echo backend\demo.db does not exist yet. Build it first:
  echo     cd backend
  echo     python seed_demo.py
  exit /b 1
)
start "EduCore AI Demo Backend" cmd /k "cd backend && set APP_ENV=development&& set DEMO_MODE=true&& set DATABASE_URL=sqlite:///demo.db&& set SCHOOL_NAME=Roshan Demo Academy&& set SCHOOL_TAGLINE=A fictional school for demonstration&& set SCHOOL_ADDRESS=Demo Road, Khairpur, Sindh&& set SCHOOL_PHONE=0999-0000000&& set SCHOOL_EMAIL=office@demo.invalid&& python -m uvicorn main:app --port 8000"
start "EduCore AI Demo Frontend" cmd /k "cd frontend && npm run dev"
echo Open http://localhost:5173 and sign in as admin.

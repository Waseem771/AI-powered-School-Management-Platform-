@echo off
rem Starts the backend on the LOCAL development database (backend\local_dev.db) at http://localhost:8000.
rem It never uses school.db. If local_dev.db is missing it stops instead of creating or choosing another file.
cd /d "%~dp0"
if not exist "local_dev.db" (
  echo local_dev.db was not found in %cd%. Nothing was started.
  exit /b 1
)
set "DATABASE_URL=sqlite:///local_dev.db"
python -m uvicorn main:app --host 127.0.0.1 --port 8000

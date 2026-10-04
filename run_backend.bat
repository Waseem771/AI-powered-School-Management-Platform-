@echo off
echo ==============================================
echo  Starting EduCore AI - Backend Server (:8000)
echo ==============================================
cd backend
venv_312\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause

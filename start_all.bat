@echo off
echo ========================================================
echo  Launching EduCore AI Full-Stack Platform (Al-Noor)
echo ========================================================
start "EduCore AI Backend" cmd /k "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
start "EduCore AI Frontend" cmd /k "cd frontend && npm run dev"
echo Backend running on: http://localhost:8000 (API docs: http://localhost:8000/docs)
echo Frontend running on: http://localhost:5173

@echo off
echo ====================================
echo  Starting EduCore AI Frontend
echo ====================================
cd /d "%~dp0frontend"
node_modules\.bin\vite.cmd
pause

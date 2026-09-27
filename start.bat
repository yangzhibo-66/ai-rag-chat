@echo off
cd /d "%~dp0"
echo Starting AI RAG System...
echo.
echo   Backend  : http://localhost:8000
echo   Frontend : http://localhost:5173
echo.
python start.py
pause

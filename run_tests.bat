@echo off
echo ========================================================
echo        Running SilkCocoon AI Test Suite (Pytest)
echo ========================================================
echo.
call .\venv\Scripts\activate.bat
pytest -v
pause

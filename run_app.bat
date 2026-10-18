@echo off
echo ========================================================
echo        Starting SilkCocoon AI Application...
echo ========================================================
echo.
call .\venv\Scripts\activate.bat
streamlit run app.py
pause

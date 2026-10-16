@echo off
title Taminot Vazifalar Boti
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "C:\Users\iMaster\.gemini\antigravity-ide\scratch\taminot_task_bot"

echo ====================================================
echo        TA'MINOT VAZIFALAR BOTI ISHGA TUSHMOQDA...
echo ====================================================
echo.

if not exist .venv (
    echo [!] Virtual muhit (.venv) topilmadi. Yaratilmoqda...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)

.venv\Scripts\python.exe bot.py
pause

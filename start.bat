@echo off
title Taminot Vazifalar Boti
chcp 65001 > nul
echo ====================================================
echo        TA'MINOT VAZIFALAR BOTI ISHGA TUSHMOQDA...
echo ====================================================
echo.

if not exist .venv (
    echo [!] Virtual muhit topilmadi. Yaratilmoqda...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)

.venv\Scripts\python.exe bot.py
pause

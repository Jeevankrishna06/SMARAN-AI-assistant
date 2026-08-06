@echo off
title Smaran AI Assistant
echo ⚡ [SMARAN RUNTIME] Starting Assistant in virtual environment...
set PYTHONIOENCODING=utf-8
.venv\Scripts\python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ The assistant stopped with an error code: %ERRORLEVEL%
    echo ℹ️ Please ensure the virtual environment is intact and .venv\Scripts\python.exe exists.
    pause
)

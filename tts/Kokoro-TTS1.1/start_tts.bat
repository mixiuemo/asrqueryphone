@echo off
setlocal

:: ===== 配置区域 =====
set "PYTHONW=D:\anaconda3\envs\ai114\pythonw.exe"
set "SCRIPT=runMain.py"
set "WORKDIR=D:\AI114\code\tts\Kokoro-TTS"
set "LOG_FILE=%WORKDIR%\tts.log"
:: 唯一 ID 标识
set "W_ID=tts-solo"
:: ===================

if not exist "%WORKDIR%" (
    echo [ERROR] Directory not found: %WORKDIR%
    pause
    exit /b
)

cd /d "%WORKDIR%"

echo [SYS] Starting Kokoro-TTS worker in background...
echo [INFO] Log file: %LOG_FILE%

:: 使用 >> 追加日志，不删除老日志
:: 传入 --id=%W_ID% 方便精准关闭
start /B "" "%PYTHONW%" "%SCRIPT%" "--id=%W_ID%" >> "%LOG_FILE%" 2>&1

echo [OK] TTS Started.
timeout /t 3 > nul
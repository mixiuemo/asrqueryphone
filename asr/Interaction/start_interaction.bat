@echo off
setlocal

:: ===== 配置区域 =====
set "PYTHONW=D:\anaconda3\envs\ai114\pythonw.exe"
set "SCRIPT=runMain.py"
set "WORKDIR=D:\AI114\code\asr\Interaction"
set "LOG_FILE=%WORKDIR%\interaction.log"
:: 给这个单实例起个唯一的 ID 方便精准关闭
set "W_ID=interaction-solo"
:: ===================

if not exist "%WORKDIR%" (
    echo [ERROR] Directory not found: %WORKDIR%
    pause
    exit /b
)

cd /d "%WORKDIR%"

echo [SYS] Starting Interaction ASR worker in background...
echo [INFO] Log file: %LOG_FILE%

:: 使用 >> 实现追加写入，不会覆盖之前的日志
:: 传入 --id=%W_ID% 以后关闭时就靠它找进程
start /B "" "%PYTHONW%" "%SCRIPT%" --id=%W_ID% >> "%LOG_FILE%" 2>&1

echo [OK] Started.
timeout /t 3 > nul
@echo off
setlocal

:: ===== 配置区域 =====
set "PYW=D:\anaconda3\envs\ai114\pythonw.exe"
set "B_DIR=D:\AI114\code\admin\python-server\src"
set "W_ID=admin-server-backend"
:: 获取脚本当前所在目录
set "LOG_DIR=%~dp0"
:: ==================

echo [SYS] Starting Admin Backend (Python) only...

if exist "%B_DIR%" (
    cd /d "%B_DIR%"
    :: 启动后端，日志追加到脚本同级目录的 admin_backend.log
    start /B "" "%PYW%" app.py --id=%W_ID% >> "%LOG_DIR%admin_backend.log" 2>&1
    echo [OK] Backend triggered.
) else (
    echo [ERROR] Directory not found: %B_DIR%
    pause
    exit /b
)

echo [SYS] This window will close in 2 seconds...
timeout /t 2 /nobreak > nul
exit
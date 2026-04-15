@echo off
setlocal enabledelayedexpansion

:: ===== 配置区域 (根据实际情况修改) =====
set "PYTHONW=D:\anaconda3\envs\ai114\pythonw.exe"
set "SCRIPT=runMain.py"
set "COUNT=3"
:: =====================================

echo [SYS] Starting %COUNT% ASR workers in background...

for /L %%i in (1,1,%COUNT%) do (
    set "W_ID=asr-worker-%%i"
    set "LOG_FILE=log_%%i.log"
    set /a "PORT=8110 + %%i"
    
    :: 只有第一个进程开启 HTTP 健康检查
    set "ENABLE_HTTP=0"
    if "%%i"=="1" set "ENABLE_HTTP=1"

    echo [INFO] Launching !W_ID! on Port !PORT!...
    
    :: 核心：通过 --id 注入唯一标识，并使用 pythonw 实现无窗口后台运行
    start /B "" "%PYTHONW%" "%SCRIPT%" --id=!W_ID! >> "!LOG_FILE!" 2>&1
    
    :: 留出显存加载时间，避免多个 Paraformer 实例瞬间挤爆 GPU
    timeout /t 5 /nobreak > nul
)

echo [OK] All workers started.
pause
@echo off
setlocal
echo [SYS] Stopping Kokoro-TTS worker...

:: 1. 精准匹配并结束带 tts-solo 标签的进程 [cite: 3]
powershell -Command "Get-CimInstance Win32_Process -Filter \"name = 'pythonw.exe'\" | Where-Object { $_.CommandLine -like '*tts-solo*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Stopped TTS PID:' $_.ProcessId }"

:: 2. 等待进程彻底退出并释放文件锁
echo [INFO] Waiting for process to release tts.log...
timeout /t 3 /nobreak > nul

:: 3. 强制循环删除日志（解决“文件正在使用”报错）
set "LOG_FILE=tts.log"
set "RETRY_COUNT=0"

:RETRY_DEL
if exist "%LOG_FILE%" (
    del /f /q "%LOG_FILE%" >nul 2>&1
    if exist "%LOG_FILE%" (
        set /a RETRY_COUNT+=1
        if !RETRY_COUNT! LSS 5 (
            echo [WARN] Log file still locked, retrying !RETRY_COUNT!/5...
            timeout /t 1 /nobreak > nul
            goto RETRY_DEL
        ) else (
            echo [ERROR] Could not delete %LOG_FILE% after 5 attempts.
        )
    ) else (
        echo [OK] Local log file cleaned.
    )
)

echo [OK] Done.
timeout /t 2 > nul
exit
@echo off
setlocal
echo [SYS] Stopping Interaction ASR worker...

:: 1. 精准匹配并结束进程
powershell -Command "Get-CimInstance Win32_Process -Filter \"name = 'pythonw.exe'\" | Where-Object { $_.CommandLine -like '*interaction-solo*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Stopped Interaction PID:' $_.ProcessId }"

:: 2. 关键补丁：强制等待 3 秒，确保 Python 彻底释放文件锁
echo [INFO] Waiting for file handles to release...
timeout /t 3 /nobreak > nul

:: 3. 尝试删除日志
if exist "interaction.log" (
    :: 使用循环尝试删除，防止偶尔的延迟
    del /f /q "interaction.log" >nul 2>&1
    if exist "interaction.log" (
        echo [WARN] File still locked, retrying in 2s...
        timeout /t 2 /nobreak > nul
        del /f /q "interaction.log" >nul 2>&1
    )
)

echo [OK] Process stopped and log cleaned.
timeout /t 2 > nul
exit
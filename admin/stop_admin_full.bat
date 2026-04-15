@echo off
setlocal
echo [SYS] Stopping Admin Backend only...

:: 1. 精准杀掉带 ID 的 Python 进程
powershell -Command "Get-CimInstance Win32_Process -Filter \"name = 'pythonw.exe'\" | Where-Object { $_.CommandLine -like '*admin-server-backend*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Stopped Backend PID:' $_.ProcessId }"

:: 2. (可选) 如果你希望顺便清理掉所有 Node 进程，可以保留下面这一行。
:: 如果你想手动关前端窗口，就用 :: 把下面这行注释掉。
:: taskkill /F /IM node.exe /T >nul 2>&1

echo [OK] Backend Cleanup finished.
echo [SYS] This window will close in 2 seconds...
timeout /t 2 /nobreak > nul
exit
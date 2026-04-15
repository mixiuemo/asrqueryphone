@echo off
echo [SYS] Cleaning up ASR processes by ID tag...

:: 使用 PowerShell 查找命令行包含 asr-worker 的 pythonw 进程并强制停止
powershell -Command "Get-CimInstance Win32_Process -Filter \"name = 'pythonw.exe'\" | Where-Object { $_.CommandLine -like '*asr-worker*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Stopped PID:' $_.ProcessId }"

:: 强制清理可能被锁定的日志文件
del /f /q log_*.log 2>nul

echo [OK] All targeted processes stopped.
pause
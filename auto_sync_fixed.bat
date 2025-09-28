@echo off
cd /d H:\Code
echo [%date% %time%] Starting auto-sync... >> windows_sync_log.txt

git pull origin main >> windows_sync_log.txt 2>&1
git add . >> windows_sync_log.txt 2>&1
git commit -m "Auto sync from Windows: %date% %time%" >> windows_sync_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] No changes to commit >> windows_sync_log.txt
) else (
    echo [%date% %time%] Changes committed >> windows_sync_log.txt
)
git push origin main >> windows_sync_log.txt 2>&1
if %errorlevel% equ 0 (
    echo [%date% %time%] Sync completed successfully >> windows_sync_log.txt
) else (
    echo [%date% %time%] Sync failed >> windows_sync_log.txt
)
echo ======================================== >> windows_sync_log.txt
type windows_sync_log.txt
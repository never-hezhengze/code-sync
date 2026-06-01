@echo off
cd /d H:\Code || exit /b 1

echo [%date% %time%] Starting auto-sync... >> windows_sync_log.txt

git checkout main >> windows_sync_log.txt 2>&1
if errorlevel 1 goto fail

git pull origin main >> windows_sync_log.txt 2>&1
if errorlevel 1 goto fail

git add . >> windows_sync_log.txt 2>&1
if errorlevel 1 goto fail

git commit -m "Auto sync from Windows: %date% %time%" >> windows_sync_log.txt 2>&1
if errorlevel 1 (
    echo [%date% %time%] No changes to commit >> windows_sync_log.txt
) else (
    echo [%date% %time%] Changes committed >> windows_sync_log.txt
)

git push origin main >> windows_sync_log.txt 2>&1
if errorlevel 1 goto fail

echo [%date% %time%] Sync completed successfully >> windows_sync_log.txt
echo ======================================== >> windows_sync_log.txt
type windows_sync_log.txt
exit /b 0

:fail
echo [%date% %time%] Sync failed >> windows_sync_log.txt
echo ======================================== >> windows_sync_log.txt
type windows_sync_log.txt
exit /b 1
@echo off
cd /d H:\Code
echo [%date% %time%] Starting auto-sync... >> sync_log.txt

:: 添加所有更改的文件
git add .

:: 尝试提交，如果没有更改则跳过
git commit -m "Auto sync: %date% %time%" >> sync_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] No changes to commit >> sync_log.txt
) else (
    echo [%date% %time%] Changes committed >> sync_log.txt
)

:: 推送到 GitHub
git push origin main >> sync_log.txt 2>&1
if %errorlevel% equ 0 (
    echo [%date% %time%] Sync completed successfully >> sync_log.txt
) else (
    echo [%date% %time%] Sync failed >> sync_log.txt
)

echo ======================================== >> sync_log.txt
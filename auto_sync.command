#!/bin/bash
cd ~/Code
echo "[$(date)] Starting auto-sync..." >> mac_sync_log.txt

# 1. 先备份可能冲突的文件
if [ -f sync_log.txt ]; then
    cp sync_log.txt sync_log_backup.txt
fi

# 2. 拉取最新更改（接受远程版本）
git fetch origin
git merge -X theirs origin/main --no-edit

# 3. 恢复备份（如果需要）
if [ -f sync_log_backup.txt ]; then
    cat sync_log_backup.txt >> mac_sync_log.txt
    rm sync_log_backup.txt
fi

# 4. 添加更改（使用 Mac 特定的日志文件）
git add .

# 5. 提交
git commit -m "Auto sync from Mac: $(date)" >> mac_sync_log.txt 2>&1 || echo "[$(date)] No changes or commit failed" >> mac_sync_log.txt

# 6. 推送
git push origin main >> mac_sync_log.txt 2>&1 && echo "[$(date)] Sync successful" >> mac_sync_log.txt || echo "[$(date)] Push failed" >> mac_sync_log.txt

echo "========================================" >> mac_sync_log.txt

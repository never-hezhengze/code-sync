#!/bin/bash
cd ~/Code
echo "[$(date)] Starting auto-sync..." >> sync_log.txt

# 先拉取最新更改（避免冲突）
git pull origin main >> sync_log.txt 2>&1

# 添加所有更改的文件
git add .

# 尝试提交，如果没有更改则跳过
git commit -m "Auto sync: $(date)" >> sync_log.txt 2>&1
if [ $? -ne 0 ]; then
    echo "[$(date)] No changes to commit" >> sync_log.txt
else
    echo "[$(date)] Changes committed" >> sync_log.txt
fi

# 推送到 GitHub
git push origin main >> sync_log.txt 2>&1
if [ $? -eq 0 ]; then
    echo "[$(date)] Sync completed successfully" >> sync_log.txt
else
    echo "[$(date)] Sync failed" >> sync_log.txt
fi

echo "========================================" >> sync_log.txt

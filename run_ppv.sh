#!/bin/bash

# --- KONFIGURASI ---
REPO_DIR="/root/perfect"
LOG_FILE="/var/log/ppv_cron.log"
PYTHON_SCRIPT="ppv.py"
PLAYLIST_FILE="PPVLand.m3u8"

# --- LOG ---
echo "==========================================================" >> "$LOG_FILE"
echo "INFO: Mulai scraping. $(date)" >> "$LOG_FILE"

# --- CHECKOUT REPO ---
cd "$REPO_DIR" || { echo "ERROR: Direktori repo tidak ditemukan." >> "$LOG_FILE"; exit 1; }

# PENTING: Pull untuk mengambil ppv.py yang sudah diperbaiki
echo "INFO: Melakukan Git Pull..." >> "$LOG_FILE"
git pull origin main >> "$LOG_FILE" 2>&1

# --- RUN PYTHON SCRIPT ---
echo "INFO: Menjalankan skrip Python $PYTHON_SCRIPT..." >> "$LOG_FILE"
# Kita tambahkan timeout 40 menit (2400 detik) untuk mengamankan proses
timeout 2400 /usr/bin/time -f "INFO: Python execution time: %E" /usr/bin/python3 "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1
PYTHON_EXIT_CODE=$?

if [ $PYTHON_EXIT_CODE -ne 0 ]; then
    echo "❌ ERROR: Python script (ppv.py) gagal atau timeout." >> "$LOG_FILE"
    echo "INFO: Selesai. $(date)" >> "$LOG_FILE"
    exit 1
fi

# --- GIT COMMIT DAN PUSH ---
echo "INFO: Memeriksa perubahan di $PLAYLIST_FILE..." >> "$LOG_FILE"

# CATATAN PERBAIKAN: Karena file sekarang ada di REPO_DIR, git diff akan bekerja.
if git diff --exit-code "$PLAYLIST_FILE" > /dev/null 2>&1; then
    echo "INFO: Tidak ada perubahan di playlist. Commit dilewati." >> "$LOG_FILE"
else
    # Ada perubahan, lakukan commit dan push
    git add "$PLAYLIST_FILE" >> "$LOG_FILE" 2>&1
    COMMIT_MSG="Update: Auto-playlist for $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1
    
    echo "INFO: Melakukan Git Push..." >> "$LOG_FILE"
    git push origin main >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ SUCCESS: Commit dan Push berhasil." >> "$LOG_FILE"
    else
        echo "❌ ERROR: Git Push gagal (Meskipun SSH harusnya sudah bekerja)." >> "$LOG_FILE"
    fi
fi

# --- JEDA (5 menit) ---
echo "INFO: Menunggu 5 menit sebelum selesai (Jeda antar jalan)." >> "$LOG_FILE"
/bin/sleep 300

# --- SELESAI ---
echo "INFO: Selesai. $(date)" >> "$LOG_FILE"

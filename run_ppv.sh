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

# Pastikan branch benar
git checkout main >> "$LOG_FILE" 2>&1
git pull origin main >> "$LOG_FILE" 2>&1

# --- RUN PYTHON SCRIPT ---
echo "INFO: Menjalankan skrip Python $PYTHON_SCRIPT..." >> "$LOG_FILE"
# Menggunakan time untuk mencatat waktu eksekusi skrip Python
/usr/bin/time -f "INFO: Python execution time: %E" /usr/bin/python3 "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1

# --- GIT COMMIT DAN PUSH (SEGERA setelah hasil keluar) ---
echo "INFO: Memeriksa perubahan di $PLAYLIST_FILE..." >> "$LOG_FILE"
if git diff --exit-code "$PLAYLIST_FILE" > /dev/null; then
    echo "INFO: Tidak ada perubahan di $PLAYLIST_FILE. Commit dilewati." >> "$LOG_FILE"
else
    # Ada perubahan, lakukan commit dan push
    git add "$PLAYLIST_FILE" >> "$LOG_FILE" 2>&1
    COMMIT_MSG="Update: Auto-playlist for $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1
    
    echo "INFO: Melakukan Git Push SEGERA..." >> "$LOG_FILE"
    git push origin main >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ SUCCESS: Commit dan Push berhasil." >> "$LOG_FILE"
    else
        echo "❌ ERROR: Git Push gagal. Periksa kredensial atau koneksi." >> "$LOG_FILE"
    fi
fi

# --- JEDA (5 menit) ---
# Jeda ini dilakukan setelah semua pekerjaan penting (Scraping dan Git Push) selesai.
echo "INFO: Menunggu 5 menit sebelum selesai (Permintaan User: Jeda antar jalan)." >> "$LOG_FILE"
/bin/sleep 300

# --- SELESAI ---
echo "INFO: Selesai. $(date)" >> "$LOG_FILE"

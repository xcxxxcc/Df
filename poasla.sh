#!/data/data/com.termux/files/usr/bin/bash
set -e
set -o pipefail

############################
# ====== KONFIGURASI ===== #
############################

REPO_DIR="$HOME/Df"
FILE="$REPO_DIR/Poasla"
LOG_DIR="$REPO_DIR/log"
LOCK_FILE="$REPO_DIR/.poasla.lock"

mkdir -p "$LOG_DIR"

############################
# ====== LOCK / SAFETY ====#
############################

# Cek kalau script lain lagi jalan
if [ -f "$LOCK_FILE" ] && kill -0 "$(cat $LOCK_FILE)" 2>/dev/null; then
  echo "❌ Script Poasla sudah jalan, exit."
  exit 1
fi

# Buat lock
echo $$ > "$LOCK_FILE"

# Hapus lock saat exit
trap "rm -f $LOCK_FILE" EXIT

############################
# ====== GIT SAFETY ====== #
############################

cd "$REPO_DIR"

# Stop kalau sedang rebase / merge
if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ] || [ -f .git/MERGE_HEAD ]; then
  echo "❌ Repo sedang rebase / merge. Hentikan script."
  exit 1
fi

# Pastikan di branch main
if [ "$(git branch --show-current)" != "main" ]; then
  echo "❌ Tidak di branch main"
  exit 1
fi

# Sinkron aman
git pull --rebase --autostash origin main || { echo "❌ Gagal sinkronisasi!"; exit 1; }

############################
# ====== PERSIAPAN ====== #
############################

[ -f "$FILE" ] || touch "$FILE"
grep -q '^#EXTM3U' "$FILE" || sed -i '1i #EXTM3U' "$FILE"

############################
# ========= SONY ========= #
############################


SONY_URL="https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"
SONY_TMP="sony.tmp"

sed -i '/#--- SONY START ---/,/#--- SONY END ---/d' "$FILE"

curl -fsSL "$SONY_URL" | awk '
{ 
  gsub(/\xEF\xBB\xBF/, ""); 
  gsub(/\r/, "");
  
  # WAJIB MTM: Mengganti domain agar ON di Indonesia
  if ($0 ~ /sonydaimenew\.akamaized\.net/) {
    gsub(/sonydaimenew\.akamaized\.net/, "sonymtmnew.akamaized.net")
  }
}

/^#EXTM3U/ || /^#DATE:/ || /D O C T O R - S T R A N G E/ { next }

/^#EXTINF/ {
  sub(/^#EXTINF:[0-9-]+/, "#EXTINF:1")
  # Mengikuti format grup Anda "SONY"
  gsub(/group-title="[^"]*"/, "group-title=\"SONY\"")
  print
  next
}

NF { print }
' > "$SONY_TMP" || true

if [ -s "$SONY_TMP" ]; then
{
  echo ""
  echo "#--- SONY START ---"
  cat "$SONY_TMP"
  echo "#--- SONY END ---"
} >> "$FILE"
fi

############################
# ========= ZEE5 ========= #
############################

ZEE_URL="https://raw.githubusercontent.com/doctor-8trange/quarnex/refs/heads/main/data/zee5.m3u"
ZEE_TMP="zee5.tmp"

sed -i '/#--- ZEE5 START ---/,/#--- ZEE5 END ---/d' "$FILE"

curl -fsSL "$ZEE_URL" | awk '
function urldecode(s, r) {
  gsub(/\+/, " ", s)
  while (match(s, /%[0-9A-Fa-f]{2}/)) {
    r = substr(s, RSTART+1, 2)
    s = substr(s, 1, RSTART-1) sprintf("%c", strtonum("0x" r)) substr(s, RSTART+3)
  }
  return s
}
{ gsub(/\xEF\xBB\xBF/, ""); gsub(/\r/, "") }
/^#EXTM3U/ || /^#DATE:/ || /^#Written and Directed by/ { next }
/^#EXTINF/ {
  sub(/^#EXTINF:[0-9-]+/, "#EXTINF:1")
  gsub(/group-title="[^"]*"/, "group-title=\"ZEE 5\"")
  print
  next
}
/^https?:\/\// {
  split($0, a, "|")
  url = a[1]
  ua=""; ref=""; org=""
  if (length(a[2])) {
    n = split(a[2], h, "&")
    for (i = 1; i <= n; i++) {
      split(h[i], kv, "=")
      key = tolower(kv[1])
      val = urldecode(substr(h[i], length(kv[1]) + 2))
      if (key == "user-agent") ua = val
      else if (key == "referer") ref = val
      else if (key == "origin") org = val
    }
  }
  if (ua  != "") print "#EXTVLCOPT:http-user-agent=" ua
  if (ref != "") print "#EXTVLCOPT:http-referrer=" ref
  if (org != "") print "#EXTVLCOPT:http-origin=" org
  print url
  next
}
NF { print }
' > "$ZEE_TMP" || true

if [ -s "$ZEE_TMP" ]; then
{
  echo ""
  echo "#--- ZEE5 START ---"
  cat "$ZEE_TMP"
  echo "#--- ZEE5 END ---"
} >> "$FILE"
fi

############################
# ======== PPVLAND ======= #
############################

PPV_URL="https://ppv.168.us.kg/ppvland.m3u"
PPV_TMP="ppvland.tmp"

sed -i '/#--- PPVLAND START ---/,/#--- PPVLAND END ---/d' "$FILE"

curl -fsSL "$PPV_URL" | awk '
{ gsub(/\xEF\xBB\xBF/, ""); gsub(/\r/, "") }
/^#EXTM3U/ { next }
/^#EXTINF/ {
  sub(/^#EXTINF:[0-9-]+/, "#EXTINF:1")
  gsub(/group-title="[^"]*"/, "group-title=\"PPV-LIVE\"")
  print
  next
}
/^#EXTVLCOPT/ || /^https?:\/\// { print }
' > "$PPV_TMP" || true

if [ -s "$PPV_TMP" ]; then
{
  echo ""
  echo "#--- PPVLAND START ---"
  cat "$PPV_TMP"
  echo "#--- PPVLAND END ---"
} >> "$FILE"
fi

############################
# ========= RANDOM 1 =========#
############################
# Source: Bongda 1 & 2 (SEMUA)

BONGDA1_URL="https://raw.githubusercontent.com/t23-02/bongda/refs/heads/main/bongda.m3u"
BONGDA2_URL="https://raw.githubusercontent.com/t23-02/bongda/refs/heads/main/bongda2.m3u"
R1_TMP="random1.tmp"

sed -i '/#--- RANDOM 1 START ---/,/#--- RANDOM 1 END ---/d' "$FILE"

{
  curl -fsSL "$BONGDA1_URL" || true
  echo ""
  curl -fsSL "$BONGDA2_URL" || true
} | awk '
{ gsub(/\xEF\xBB\xBF/, ""); gsub(/\r/, "") }
/^#EXTM3U/ { next }
/^#EXTINF/ {
  sub(/^#EXTINF:[0-9-]+/, "#EXTINF:1")
  gsub(/group-title="[^"]*"/, "group-title=\"RANDOM 1\"")
  gsub(/ngày/, "WIB")
  print
  next
}
/^#EXTVLCOPT/ || /^https?:\/\// { print }
' > "$R1_TMP" || true

if [ -s "$R1_TMP" ]; then
{
  echo ""
  echo "#--- RANDOM 1 START ---"
  cat "$R1_TMP"
  echo "#--- RANDOM 1 END ---"
} >> "$FILE"
fi

############################
# ========= RANDOM 2 ======#
############################
# Source: Bongda 1 & 2 (Filter: Chuối Chiên & 10 Cam)

R2_TMP="random2.tmp"
sed -i '/#--- RANDOM 2 START ---/,/#--- RANDOM 2 END ---/d' "$FILE"

{
  curl -fsSL "$BONGDA1_URL" || true
  echo ""
  curl -fsSL "$BONGDA2_URL" || true
} | awk '
{ gsub(/\xEF\xBB\xBF/, ""); gsub(/\r/, "") }
/^#EXTM3U/ { next }
/^#EXTINF/ {
  # Filter regex untuk mencakup Chuối Chiên (Chu) dan 10 Cam
  keep = ($0 ~ /10[ ]?Cam/ || $0 ~ /Chu/ || $0 ~ /Chiên/)
  if (keep) {
    sub(/^#EXTINF:[0-9-]+/, "#EXTINF:1")
    gsub(/group-title="[^"]*"/, "group-title=\"RANDOM 2\"")
    print
  }
  next
}
keep && (/^#EXTVLCOPT/ || /^https?:\/\//) {
  print
  if (/^https?:\/\//) keep=0
}
' > "$R2_TMP" || true

if [ -s "$R2_TMP" ]; then
{
  echo ""
  echo "#--- RANDOM 2 START ---"
  cat "$R2_TMP"
  echo "#--- RANDOM 2 END ---"
} >> "$FILE"
fi

############################
# ========= RANDOM 3 ======#
############################
# Source: Doms9 events

RANDOM3_URL="https://raw.githubusercontent.com/doms9/iptv/refs/heads/default/M3U8/events.m3u8"
R3_TMP="random3.tmp"

sed -i '/#--- RANDOM 3 START ---/,/#--- RANDOM 3 END ---/d' "$FILE"

curl -fsSL "$RANDOM3_URL" | awk '
{ gsub(/\xEF\xBB\xBF/, ""); gsub(/\r/, "") }
/^#EXTM3U/ { next }
/^#EXTINF/ {
  keep = ($0 ~ /(FAWA|ROXIE|STRMCNTR|STRMHUB|CDNTV)/)
  if (keep) {
    sub(/^#EXTINF:[0-9-]+/, "#EXTINF:1")
    gsub(/group-title="[^"]*"/, "group-title=\"RANDOM 3\"")
    print
  }
  next
}
keep && (/^#EXTVLCOPT/ || /^https?:\/\//) {
  print
  if (/^https?:\/\//) keep=0
}
' > "$R3_TMP" || true

if [ -s "$R3_TMP" ]; then
{
  echo ""
  echo "#--- RANDOM 3 START ---"
  cat "$R3_TMP"
  echo "#--- RANDOM 3 END ---"
} >> "$FILE"
fi

############################
# ========= COMMIT ======= #
############################

# Cek perubahan di file Poasla DAN script poasla.sh sendiri
if [[ -n $(git status -s) ]]; then
  git config user.name "poasla-bot"
  git config user.email "poasla-bot@users.noreply.github.com"
  git add .
  git commit -m "Auto-sync Poasla (SONY, ZEE5, PPV, R1, R2, R3) - $(date +'%Y-%m-%d %H:%M')"
  git push origin main
else
  echo "Tidak ada perubahan"
fi

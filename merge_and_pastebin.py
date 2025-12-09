import requests
import os
import json

# 1. Konfigurasi Sumber
PLAYLIST_URLS = [
    "https://sp.networkerror404.top/playlist/sliv.php",
    "https://raw.githubusercontent.com/t23-02/bongda/refs/heads/main/bongda.m3u",
    "https://raw.githubusercontent.com/t23-02/bongda/refs/heads/main/bongda2.m3u",
    "https://raw.githubusercontent.com/felixiptv/FelixLive/refs/heads/main/PPVLand.m3u8" 
]
HEADER = "#EXTM3U\n"
CUSTOM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Variabel Global untuk menyimpan Gist ID (untuk pembaruan di masa depan)
# Jika ini pertama kali, biarkan kosong. Skrip akan membuat Gist baru.
GIST_ID = os.environ.get('GIST_ID') 
GIST_FILE_NAME = "BL.m3u" # Nama file Gist Anda

# 2. Fungsi Pengambilan Data (Sama seperti sebelumnya)
def fetch_and_clean_playlist(url):
    print(f"Mengambil konten dari: {url}")
    try:
        response = requests.get(url, headers=CUSTOM_HEADERS, timeout=15)
        response.raise_for_status() 

        content = response.text.strip()
        
        if content.startswith(HEADER.strip()):
            content = content[len(HEADER.strip()):].lstrip('\n').lstrip('\r\n')
            
        print(f"Berhasil mengambil {len(content.splitlines())} baris.")
        return content

    except requests.RequestException as e:
        print(f"Gagal mengambil {url}: {e}")
        return ""

# 3. FUNGSI UNGGAHAN BARU KE GITHUB GIST
def upload_to_gist(token, content):
    """Mengunggah atau memperbarui konten ke GitHub Gist."""
    
    GIST_URL = f"https://api.github.com/gists/{GIST_ID}" if GIST_ID else "https://api.github.com/gists"
    
    auth_headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    payload = {
        "description": "Merged M3U Playlist (Auto Updated via GitHub Action)",
        "public": True,
        "files": {
            GIST_FILE_NAME: {
                "content": content
            }
        }
    }

    print(f"\n{'Memperbarui' if GIST_ID else 'Membuat'} Gist...")
    
    try:
        if GIST_ID:
            # Jika GIST_ID sudah ada, kita PATCH (Update)
            response = requests.patch(GIST_URL, headers=auth_headers, json=payload, timeout=15)
        else:
            # Jika GIST_ID belum ada, kita POST (Create)
            response = requests.post(GIST_URL, headers=auth_headers, json=payload, timeout=15)
            
        response.raise_for_status()
        
        data = response.json()
        gist_id_new = data['id']
        raw_url = data['files'][GIST_FILE_NAME]['raw_url']

        print(f"✅ Berhasil! Gist ID: {gist_id_new}")
        print(f"✅ URL Mentah (Playlist): {raw_url}")
        
        # Jika GIST_ID belum disetel, cetak instruksi
        if not GIST_ID:
            print("\n🚨 PERHATIAN: Skrip membuat Gist baru.")
            print("Untuk eksekusi berikutnya (agar skrip meng-update, bukan membuat baru),")
            print(f"tambahkan GIST_ID = '{gist_id_new}' ke file Python Anda ATAU")
            print(f"tambahkan SECRET baru bernama GIST_ID = {gist_id_new} di GitHub.")

        return raw_url

    except requests.RequestException as e:
        print(f"❌ Kesalahan saat mengunggah ke Gist: {e}")
        print("Pastikan GIST_TOKEN memiliki izin 'gist' yang benar.")
        return None

def main():
    token = os.environ.get('GIST_TOKEN')
    if not token:
        print("❌ Error: GIST_TOKEN tidak ditemukan. Silakan tambahkan SECRET baru di GitHub.")
        return

    # 1. Gabungkan Konten
    all_content = []
    for url in PLAYLIST_URLS:
        content = fetch_and_clean_playlist(url)
        if content:
            all_content.append(content)
    
    final_content = HEADER + "\n".join(all_content)
    
    # 2. Unggah ke Gist
    upload_to_gist(token, final_content)

if __name__ == "__main__":
    main()

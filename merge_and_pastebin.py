import requests
import os

# 1. Konfigurasi Sumber - PERUBAHAN ADA DI BAGIAN INI
PLAYLIST_URLS = [
    "https://sp.networkerror404.top/playlist/sliv.php",
    "https://raw.githubusercontent.com/t23-02/bongda/refs/heads/main/bongda.m3u",
    "https://raw.githubusercontent.com/t23-02/bongda/refs/heads/main/bongda2.m3u",
    "https://raw.githubusercontent.com/felixiptv/FelixLive/refs/heads/main/PPVLand.m3u8" # <--- SUMBER BARU
]
HEADER = "#EXTM3U\n"

# 2. Fungsi Pengambilan Data
def fetch_and_clean_playlist(url):
    """Mengunduh konten dari URL dan membersihkan header M3U/M3U8."""
    print(f"Mengambil konten dari: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status() 

        content = response.text.strip()
        
        # Hapus header '#EXTM3U' jika ada, karena kita hanya perlu satu header di awal
        if content.startswith(HEADER.strip()):
            content = content[len(HEADER.strip()):].lstrip('\n').lstrip('\r\n')
            
        print(f"Berhasil mengambil {len(content.splitlines())} baris.")
        return content

    except requests.RequestException as e:
        print(f"Gagal mengambil {url}: {e}")
        return ""

# 3. Fungsi Pengunggahan ke Pastebin
def upload_to_pastebin(api_key, content):
    """Mengunggah konten gabungan ke Pastebin."""
    
    PASTEBIN_URL = "https://pastebin.com/api/api_post.php"
    
    data = {
        'api_dev_key': api_key,
        'api_option': 'paste',
        'api_paste_code': content,
        'api_paste_name': 'BL (Auto Updated)',
        'api_paste_format': 'm3u',
        'api_paste_private': '0',
        'api_paste_expire_date': 'N',
    }
    
    print("\nSedang mengunggah ke Pastebin...")
    try:
        response = requests.post(PASTEBIN_URL, data=data)
        response.raise_for_status()
        
        if response.text.startswith("Bad API request"):
            print(f"❌ Gagal mengunggah ke Pastebin: {response.text}")
            return None
        
        print(f"✅ Berhasil diunggah. URL Pastebin: {response.text}")
        return response.text

    except requests.RequestException as e:
        print(f"❌ Kesalahan saat mengirim ke Pastebin: {e}")
        return None

def main():
    api_key = os.environ.get('PASTEBIN_API_KEY')
    if not api_key:
        print("❌ Error: PASTEBIN_API_KEY tidak ditemukan.")
        return

    # 1. Gabungkan Konten
    all_content = []
    for url in PLAYLIST_URLS:
        content = fetch_and_clean_playlist(url)
        if content:
            all_content.append(content)
    
    # Tambahkan header M3U tunggal
    final_content = HEADER + "\n".join(all_content)
    
    # 2. Unggah ke Pastebin
    upload_to_pastebin(api_key, final_content)

if __name__ == "__main__":
    main()
    

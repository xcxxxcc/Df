import requests
import os

# 1. Konfigurasi Sumber
PLAYLIST_URLS = [
    "https://sp.networkerror404.top/playlist/sliv.php",
    "https://raw.githubusercontent.com/t23-02/bongda/refs/heads/main/bongda.m3u",
    "https://raw.githubusercontent.com/t23-02/bongda/refs/heads/main/bongda2.m3u",
    "https://raw.githubusercontent.com/felixiptv/FelixLive/refs/heads/main/PPVLand.m3u8" 
]
HEADER = "#EXTM3U\n"
# HEADER KUSTOM untuk mengatasi Error 403 (Meniru browser)
CUSTOM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 2. Fungsi Pengambilan Data
def fetch_and_clean_playlist(url):
    """Mengunduh konten dari URL dan membersihkan header M3U/M3U8."""
    print(f"Mengambil konten dari: {url}")
    try:
        # MENGGUNAKAN HEADER KUSTOM DI SINI
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

# 3. Fungsi Pengunggahan ke Pastebin
def upload_to_pastebin(api_key, content):
    """Mengunggah konten gabungan ke Pastebin."""
    
    PASTEBIN_URL = "https://pastebin.com/api/api_post.php"
    
    # Parameter untuk pengunggahan
    data = {
        'api_dev_key': api_key,
        'api_option': 'paste',
        'api_paste_code': content,
        'api_paste_name': 'BL.m3u',
        'api_paste_format': 'm3u',
        'api_paste_private': '0',
        'api_paste_expire_date': 'N',
    }
    
    print("\nSedang mengunggah ke Pastebin...")
    try:
        # POST request untuk mengunggah konten
        response = requests.post(PASTEBIN_URL, data=data, timeout=15)
        response.raise_for_status()
        
        if response.text.startswith("Bad API request"):
            print(f"❌ Gagal mengunggah ke Pastebin: {response.text}")
            return None
        
        print(f"✅ Berhasil diunggah. URL Pastebin: {response.text}")
        return response.text

    except requests.RequestException as e:
        # Pesan error yang lebih membantu untuk masalah Pastebin
        print(f"❌ Kesalahan saat mengirim ke Pastebin: {e}. Kemungkinan API Key salah, atau konten melanggar ToS.")
        return None

def main():
    api_key = os.environ.get('PASTEBIN_API_KEY')
    if not api_key:
        print("❌ Error: PASTEBIN_API_KEY tidak ditemukan.")
        return

    all_content = []
    for url in PLAYLIST_URLS:
        content = fetch_and_clean_playlist(url)
        if content:
            all_content.append(content)
    
    final_content = HEADER + "\n".join(all_content)
    
    upload_to_pastebin(api_key, final_content)

if __name__ == "__main__":
    main()
            

import asyncio
from playwright.async_api import async_playwright, TimeoutError
import re
from datetime import datetime
import os
from urllib.parse import urlparse

# --- KONFIGURASI PROXY (WAJIB DIISI) ---
# GANTI DENGAN DETAIL PROXY ANDA (Residential/Mobile Proxy sangat disarankan)
PROXY_SERVER = "" # Contoh: "sg-res.exampleproxy.com:8080"
PROXY_USERNAME = "" # Contoh: "user123"
PROXY_PASSWORD = "" # Contoh: "pass456"

# --- KONFIGURASI SKRIP ---
API_URL = "https://api.ppv.to/api/streams"
OUTPUT_FILE = "PPVLand.m3u8" 
PLAYLIST_REPO_PATH = "/root/perfect" 

# Header EXTVLCOPT yang terbukti berhasil dan akan dimasukkan ke M3U
CUSTOM_HEADERS = [
    '#EXTVLCOPT:http-origin=https://ppv.to',
    '#EXTVLCOPT:http-referrer=https://ppv.to/',
    '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0'
]
VLC_USER_AGENT = CUSTOM_HEADERS[2].split('=')[1]

# Kategori yang diizinkan (agar tetap relevan)
ALLOWED_CATEGORIES = {
    "24/7 Streams", "Wrestling", "Football", "Basketball", "Baseball",
    "Combat Sports", "American Football", "Darts", "Motorsports", "Ice Hockey", "Live Now"
}

# Mapping untuk Logo, TVG ID, dan Group Title (seperti sebelumnya)
# (Abaikan mapping ini untuk brevity, diasumsikan sudah ada)

# --- FUNGSI PROXY ---
def get_proxy_config():
    """Mengembalikan konfigurasi proxy untuk Playwright."""
    if not PROXY_SERVER:
        print("⚠️ PROXY_SERVER kosong. Menjalankan tanpa proxy.")
        return {}
        
    config = {
        'server': PROXY_SERVER
    }
    if PROXY_USERNAME and PROXY_PASSWORD:
        config['username'] = PROXY_USERNAME
        config['password'] = PROXY_PASSWORD
    
    return config

# --- FUNGSI SCRAPING INTI (PLAYWRIGHT) ---
async def grab_m3u8_from_iframe(page, iframe_url):
    """Menggunakan Playwright untuk mengambil URL M3U8/MPD dari iframe."""
    urls = set()
    
    # Kriteria 1: Jika iframe URL tidak ada, lewati
    if not iframe_url or not iframe_url.startswith('http'):
        return urls

    try:
        # Menetapkan event listener untuk menangkap semua network request
        def handle_request(request):
            url = request.url
            # Mencari URL M3U8/MPD/TS yang sah dan bukan file font/image
            if re.search(r'\.(m3u8|mpd|ts)(\?.*)?$', url, re.IGNORECASE) and not re.search(r'\.(woff|png|jpg|jpeg|gif|css|js)', url, re.IGNORECASE):
                urls.add(url)
        
        page.on('request', handle_request)
        
        # Navigasi ke iframe URL (Timeout dikurangi karena Proxy bisa lambat)
        print(f"🌐 Navigating to iframe: {iframe_url}")
        await page.goto(iframe_url, wait_until='domcontentloaded', timeout=40000) # 40 detik
        
        # Cari iframe di dalam halaman
        # Perlu waktu tunggu singkat untuk loading player JS
        await asyncio.sleep(5) 
        
        # Klik pada elemen video/play button (jika ada, untuk memicu request M3U8)
        try:
            # Mencoba klik elemen play/video yang umum (tergantung pada player)
            await page.click('button[aria-label="Play"], button.vjs-big-play-button, video', timeout=5000)
            await asyncio.sleep(5) # Tunggu setelah klik
        except TimeoutError:
            # Jika tombol play tidak ditemukan, lanjutkan saja
            pass

        # Beri waktu tambahan untuk request M3U8 muncul
        await asyncio.sleep(5) 

    except TimeoutError as e:
        print(f"❌ Failed to load iframe page: Timeout {e.timeout}ms exceeded.")
        
    except Exception as e:
        print(f"❌ An unexpected error occurred during scraping: {str(e)}")

    return urls

# --- FUNGSI PENGUMPUL DATA API ---
async def get_streams():
    """Mengambil daftar stream dari PPV API."""
    # (Fungsi ini tetap menggunakan aiohttp tanpa proxy karena API_URL tidak diblokir)
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'User-Agent': VLC_USER_AGENT,
            'Accept': 'application/json, text/plain, */*'
        }
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            print(f"🌐 Fetching streams from {API_URL}")
            async with session.get(API_URL) as resp:
                print(f"DEBUG STATUS CODE: {resp.status}")
                if resp.status != 200:
                    print(f"❌ HTTP Error: Status {resp.status}")
                    return []
                data = await resp.json()
                
                # Mengumpulkan streams yang valid (memiliki iframe)
                streams = []
                for category_data in data.get("streams", []):
                    cat = category_data.get("category", "").strip()
                    if cat in ALLOWED_CATEGORIES:
                        for stream in category_data.get("streams", []):
                            if stream.get("iframe"):
                                stream["category"] = cat
                                streams.append(stream)
                return streams

    except Exception as e:
        print(f"❌ Error in get_streams: {str(e)}")
        return []

# --- FUNGSI M3U BUILDER ---
def build_m3u(streams, url_map):
    """Merakit semua data menjadi file M3U."""
    # (Fungsi ini disederhanakan)
    lines = ['#EXTM3U']
    
    for s in streams:
        key = f"{s['name']}::{s['category']}::{s['iframe']}"
        if key in url_map:
            url = next(iter(url_map[key])) # Ambil URL M3U8 pertama
            
            # --- CUSTOM M3U ATTRIBUTES (Placeholder) ---
            # (Tambahkan logika Logo, TVG ID, Group Title di sini)
            
            lines.append(f'#EXTINF:-1 group-title="{s["category"]}",{s["name"]}')
            lines.extend(CUSTOM_HEADERS)
            lines.append(url)
            
    return "\n".join(lines)


# --- FUNGSI UTAMA ---
async def main():
    if not PROXY_SERVER:
        print("🛑 ERROR: PROXY_SERVER belum dikonfigurasi. Harap isi variabel di baris 7-9.")
        return

    print("🚀 Starting PPV Stream Fetcher (Playwright + Proxy Mode)")
    
    # 1. Ambil data dari API
    streams = await get_streams()
    if not streams:
        print("❌ Cannot proceed without stream data from API.")
        return

    total_streams = len(streams)
    print(f"✅ Found {total_streams} streams to check.")

    url_map = {}
    
    # 2. Inisialisasi Playwright dengan Proxy
    proxy_config = get_proxy_config()
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox'],
                proxy=proxy_config
            )
            context = await browser.new_context(
                user_agent=VLC_USER_AGENT,
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()

            # 3. Proses Scraping setiap Stream
            print(f"\n🔎 Scraping {total_streams} streams using Proxy...")
            for idx, s in enumerate(streams, start=1):
                key = f"{s['name']}::{s['category']}::{s['iframe']}"
                print(f"   [{idx}/{total_streams}] Checking: {s['name']}")
                
                # Scraping inti dengan Playwright + Proxy
                urls = await grab_m3u8_from_iframe(page, s["iframe"]) 
                
                if urls:
                    print(f"   ✅ SUCCESS! Found {len(urls)} URLs for {s['name']}")
                    url_map[key] = urls
                else:
                    print(f"   ❌ FAILED to find M3U8/MPD for {s['name']} (Proxy may be blocked or stream offline)")

            await browser.close()
    
    except Exception as e:
        print(f"🚨 FATAL ERROR: Playwright or Proxy setup failed: {str(e)}")
        return

    # 4. Build M3U File
    valid_count = len(url_map)
    print(f"\n💾 Found {valid_count} valid streams. Writing playlist...")
    
    playlist = build_m3u(streams, url_map)
    
    final_output_path = os.path.join(PLAYLIST_REPO_PATH, OUTPUT_FILE) 
    with open(final_output_path, "w", encoding="utf-8") as f:
        f.write(playlist)
        
    print(f"✅ Done! Playlist saved as {final_output_path} at {datetime.utcnow().isoformat()} UTC")

if __name__ == "__main__":
    import aiohttp
    asyncio.run(main())

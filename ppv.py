import asyncio
from playwright.async_api import async_playwright, TimeoutError
import aiohttp
import re
from datetime import datetime
import os
from urllib.parse import urlparse
import random # Import modul random baru

# --- KONFIGURASI DAN FILE ---
API_URL = "https://api.ppv.to/api/streams"
OUTPUT_FILE = "PPVLand.m3u8" 
PLAYLIST_REPO_PATH = "/root/perfect" # Sesuai dengan setting Anda

# Batas waktu jeda acak (dalam detik)
MIN_RANDOM_DELAY = 5
MAX_RANDOM_DELAY = 8

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

# Mapping untuk Logo, TVG ID, dan Group Title
CATEGORY_LOGOS = {
    "24/7 Streams": "http://drewlive24.duckdns.org:9000/Logos/247.png",
    "Wrestling": "http://drewlive24.duckdns.org:9000/Logos/wwe.png",
    "Football": "http://drewlive24.duckdns.org:9000/Logos/football.png",
    "Basketball": "http://drewlive24.duckdns.org:9000/Logos/basketball.png",
    "Baseball": "http://drewlive24.duckdns.org:9000/Logos/baseball.png",
    "Combat Sports": "http://drewlive24.duckdns.org:9000/Logos/combatsports.png",
    "American Football": "http://drewlive24.duckdns.org:9000/Logos/americanfootball.png",
    "Darts": "http://drewlive24.duckdns.org:9000/Logos/darts.png",
    "Motorsports": "http://drewlive24.duckdns.org:9000/Logos/motorsports.png",
    "Ice Hockey": "http://drewlive24.duckdns.org:9000/Logos/icehockey.png",
    "Live Now": "http://drewlive24.duckdns.org:9000/Logos/live.png",
}

GROUP_RENAME_MAP = {
    "24/7 Streams": "PPVLand 24/7 Channels",
    "Wrestling": "PPVLand Wrestling Events",
    "Football": "PPVLand Football Events",
    "Basketball": "PPVLand Basketball Events",
    "Baseball": "PPVLand Baseball Events",
    "Combat Sports": "PPVLand Combat Sports",
    "American Football": "PPVLand American Football",
    "Darts": "PPVLand Darts",
    "Motorsports": "PPVLand Motorsports",
    "Ice Hockey": "PPVLand Ice Hockey",
    "Live Now": "PPVLand Live Now",
}

# --- FUNGSI JEDA ACAP ---
def get_random_delay() -> float:
    """Menghasilkan jeda acak (float) antara MIN dan MAX."""
    # Menggunakan uniform untuk mendapatkan angka float (misalnya 5.43 detik)
    return random.uniform(MIN_RANDOM_DELAY, MAX_RANDOM_DELAY)

# --- FUNGSI SCRAPING INTI (PLAYWRIGHT) ---
async def grab_m3u8_from_iframe(page, iframe_url, stream_name):
    """Menggunakan Playwright untuk mengambil URL M3U8/MPD dari iframe."""
    urls = set()
    
    if not iframe_url or not iframe_url.startswith('http'):
        return urls

    # Dapatkan jeda acak baru untuk stream ini
    delay = get_random_delay()
    # Pembulatan untuk tampilan log saja
    print(f"   >>> Jeda acak untuk {stream_name}: {delay:.2f} detik.")

    try:
        # Menetapkan event listener untuk menangkap semua network request
        def handle_request(request):
            url = request.url
            # Mencari URL M3U8/MPD/TS yang sah
            if re.search(r'\.(m3u8|mpd|ts)(\?.*)?$', url, re.IGNORECASE) and not re.search(r'\.(woff|png|jpg|jpeg|gif|css|js|html)', url, re.IGNORECASE):
                urls.add(url)
        
        page.on('request', handle_request)
        
        # Navigasi ke iframe URL
        await page.goto(iframe_url, wait_until='domcontentloaded', timeout=40000)
        
        # Tunggu singkat untuk loading player JS
        await asyncio.sleep(2) 
        
        # Coba klik tombol play (untuk memicu request M3U8)
        try:
            # Mencoba klik elemen play/video yang umum
            await page.click('button[aria-label="Play"], button.vjs-big-play-button, video', timeout=5000)
            await asyncio.sleep(2) # Tunggu setelah klik
        except TimeoutError:
            pass

        # Jeda ACAP (Paling penting)
        print(f"   >>> Menunggu {delay:.2f} detik untuk network request...")
        await asyncio.sleep(delay) 

    except TimeoutError as e:
        print(f"❌ Gagal memuat halaman iframe (Timeout {e.timeout}ms).")
        
    except Exception as e:
        print(f"❌ Error tak terduga saat scraping: {str(e)}")

    return urls

# --- FUNGSI PENGUMPUL DATA API (TIDAK BERUBAH) ---
async def get_streams():
    """Mengambil daftar stream dari PPV API."""
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {'User-Agent': VLC_USER_AGENT, 'Accept': 'application/json, text/plain, */*'}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(API_URL) as resp:
                if resp.status != 200:
                    print(f"❌ HTTP Error: Status {resp.status}")
                    return []
                data = await resp.json()
                
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

# --- FUNGSI M3U BUILDER (TIDAK BERUBAH) ---
def build_m3u(streams, url_map):
    """Merakit semua data menjadi file M3U."""
    lines = ['#EXTM3U']
    
    for s in streams:
        key = f"{s['name']}::{s['category']}::{s['iframe']}"
        if key in url_map:
            url = next(iter(url_map[key])) # Ambil URL M3U8 pertama
            
            # Ambil data M3U8
            category = s["category"]
            name = s["name"].replace('"', '').replace("'", "")
            logo = CATEGORY_LOGOS.get(category, "")
            group_title = GROUP_RENAME_MAP.get(category, category)
            tvg_id = group_title.replace(" ", "_").replace("-", "_")
            
            # Buat baris EXTINF
            lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{group_title}",{name}')
            
            # Tambahkan header VLC
            lines.extend(CUSTOM_HEADERS)
            
            # Tambahkan URL Stream
            lines.append(url)
            
    return "\n".join(lines)


# --- FUNGSI UTAMA ---
async def main():
    print("🚀 Starting PPV Stream Fetcher (Playwright + RANDOM Delay Mode)")
    
    # 1. Ambil data dari API
    streams = await get_streams()
    if not streams:
        print("❌ Tidak dapat melanjutkan tanpa data stream dari API.")
        return

    total_streams = len(streams)
    print(f"✅ Ditemukan {total_streams} streams untuk dicek.")

    url_map = {}
    
    try:
        async with async_playwright() as p:
            # Gunakan chromium (paling stabil)
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox'],
            )
            # Konteks browser dengan User Agent yang disesuaikan
            context = await browser.new_context(
                user_agent=VLC_USER_AGENT,
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()

            # 2. Proses Scraping setiap Stream
            print(f"\n🔎 Scraping {total_streams} streams...")
            for idx, s in enumerate(streams, start=1):
                key = f"{s['name']}::{s['category']}::{s['iframe']}"
                print(f"   [{idx}/{total_streams}] Checking: {s['name']}")
                
                # Panggil scraping
                urls = await grab_m3u8_from_iframe(page, s["iframe"], s["name"]) 
                
                if urls:
                    print(f"   ✅ SUCCESS! Ditemukan {len(urls)} URLs untuk {s['name']}")
                    url_map[key] = urls
                else:
                    print(f"   ❌ FAILED: Gagal menemukan M3U8/MPD untuk {s['name']} (Blokir IP/Stream offline)")

            await browser.close()
    
    except Exception as e:
        print(f"🚨 FATAL ERROR: Playwright gagal memulai: {str(e)}")
        return

    # 3. Build M3U File
    valid_count = len(url_map)
    print(f"\n💾 Ditemukan {valid_count} stream valid. Menulis playlist...")
    
    playlist = build_m3u(streams, url_map)
    
    final_output_path = os.path.join(PLAYLIST_REPO_PATH, OUTPUT_FILE) 
    with open(final_output_path, "w", encoding="utf-8") as f:
        f.write(playlist)
        
    print(f"✅ Done! Playlist disimpan sebagai {final_output_path} pada {datetime.utcnow().isoformat()} UTC")

if __name__ == "__main__":
    import aiohttp
    os.environ['PWDEBUG'] = '0' 
    asyncio.run(main())

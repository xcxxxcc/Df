import asyncio
import random
from playwright.async_api import async_playwright
import aiohttp
from datetime import datetime
import os
from urllib.parse import urlparse

# --- KONFIGURASI DAN FILE ---
API_URL = "https://api.ppv.to/api/streams"
OUTPUT_FILE = "PPVLand.m3u8" 
PLAYLIST_REPO_PATH = "/root/perfect" # <<< SUDAH DIPERBAIKI KE FOLDER GIT UTAMA

# Header EXTVLCOPT yang terbukti berhasil dan akan dimasukkan ke M3U
CUSTOM_HEADERS = [
    '#EXTVLCOPT:http-origin=https://ppv.to',
    '#EXTVLCOPT:http-referrer=https://ppv.to/',
    '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0'
]
VLC_USER_AGENT = CUSTOM_HEADERS[2].split('=')[1]

# Kategori yang diizinkan untuk di-scrape
ALLOWED_CATEGORIES = {
    "24/7 Streams", "Wrestling", "Football", "Basketball", "Baseball",
    "Combat Sports", "American Football", "Darts", "Motorsports", "Ice Hockey"
}

# Mapping untuk Logo, TVG ID, dan Group Title
CATEGORY_LOGOS = {
    "24/7 Streams": "http://drewlive24.duckdns.org:9000/Logos/247.png",
    "Wrestling": "http://drewlive24.duckdns.org:9000/Logos/Wrestling.png",
    "Football": "http://drewlive24.duckdns.org:9000/Logos/Football.png",
    "Basketball": "http://drewlive24.duckdns.org:9000/Logos/Basketball.png",
    "Baseball": "http://drewlive24.duckdns.org:9000/Logos/Baseball.png",
    "American Football": "http://drewlive24.duckdns.org:9000/Logos/NFL3.png",
    "Combat Sports": "http://drewlive24.duckdns.org:9000/Logos/CombatSports2.png",
    "Darts": "http://drewlive24.duckdns.org:9000/Logos/Darts.png",
    "Motorsports": "http://drewlive24.duckdns.org:9000/Logos/Motorsports2.png",
    "Live Now": "http://drewlive24.duckdns.org:9000/Logos/DrewLiveSports.png",
    "Ice Hockey": "http://drewlive24.duckdns.org:9000/Logos/Hockey.png"
}

CATEGORY_TVG_IDS = {
    "24/7 Streams": "24.7.Dummy.us",
    "Wrestling": "PPV.EVENTS.Dummy.us",
    "Football": "Soccer.Dummy.us",
    "Basketball": "Basketball.Dummy.us",
    "Baseball": "MLB.Baseball.Dummy.us",
    "American Football": "NFL.Dummy.us",
    "Combat Sports": "PPV.EVENTS.Dummy.us",
    "Darts": "Darts.Dummy.us",
    "Motorsports": "Racing.Dummy.us",
    "Live Now": "24.7.Dummy.us",
    "Ice Hockey": "NHL.Hockey.Dummy.us"
}

GROUP_RENAME_MAP = {
    "24/7 Streams": "PPVLand - Live Channels 24/7",
    "Wrestling": "PPVLand - Wrestling Events",
    "Football": "PPVLand - Global Football Streams",
    "Basketball": "PPVLand - Basketball Hub",
    "Baseball": "PPVLand - MLB",
    "American Football": "PPVLand - NFL Action",
    "Combat Sports": "PPVLand - Combat Sports",
    "Darts": "PPVLand - Darts",
    "Motorsports": "PPVLand - Racing Action",
    "Live Now": "PPVLand - Live Now",
    "Ice Hockey": "PPVLand - NHL Action"
}

# List tim untuk identifikasi channel (tetap)
NFL_TEAMS = {
    "arizona cardinals", "atlanta falcons", "baltimore ravens", "buffalo bills",
    "carolina panthers", "chicago bears", "cincinnati bengals", "cleveland browns",
    "dallas cowboys", "denver broncos", "detroit lions", "green bay packers",
    "houston texans", "indianapolis colts", "jacksonville jaguars", "kansas city chiefs",
    "las vegas raiders", "los angeles chargers", "los angeles rams", "miami dolphins",
    "minnesota vikings", "new england patriots", "new orleans saints", "new york giants",
    "new york jets", "philadelphia eagles", "pittsburgh steelers", "san francisco 49ers",
    "seattle seahawks", "tampa bay buccaneers", "tennessee titans", "washington commanders"
}

COLLEGE_TEAMS = {
    "alabama crimson tide", "auburn tigers", "arkansas razorbacks", "georgia bulldogs",
    "florida gators", "lsu tigers", "ole miss rebels", "mississippi state bulldogs",
    "tennessee volunteers", "texas longhorns", "oklahoma sooners", "oklahoma state cowboys",
    "baylor bears", "tcu horned frogs", "kansas jayhawks", "kansas state wildcats",
    "iowa state cyclones", "iowa hawkeyes", "michigan wolverines", "ohio state buckeyes",
    "penn state nittany lions", "michigan state spartans", "wisconsin badgers",
    "minnesota golden gophers", "illinois fighting illini", "northwestern wildcats",
    "indiana hoosiers", "notre dame fighting irish", "usc trojans", "ucla bruins",
    "oregon ducks", "oregon state beavers", "washington huskies", "washington state cougars",
    "arizona wildcats", "stanford cardinal", "california golden bears", "colorado buffaloes",
    "florida state seminoles", "miami hurricanes", "clemson tigers", "north carolina tar heels",
    "duke blue devils", "nc state wolfpack", "wake forest demon deacons", "syracuse orange",
    "virginia cavaliers", "virginia tech hokies", "louisville cardinals", "pittsburgh panthers",
    "maryland terrapins", "rutgers scarlet knights", "nebraska cornhuskers", "purdue boilermakers",
    "texas a&m aggies", "kentucky wildcats", "missouri tigers", "vanderbilt commodores",
    "houston cougars", "utah utes", "byu cougars", "boise state broncos", "san diego state aztecs",
    "cincinnati bearcats", "memphis tigers", "ucf knights", "south florida bulls", "smu mustangs",
    "tulsa golden hurricane", "tulane green wave", "navy midshipmen", "army black knights",
    "arizona state sun devils", "texas tech red raiders", "florida atlantic owls"
}

# --- FUNGSI ASYNC AIOHTTP ---
async def check_m3u8_url(url, referer):
    """Memeriksa URL M3U8 menggunakan referer yang benar untuk validasi."""
    try:
        origin = "https://" + urlparse(referer).netloc
        headers = {
            "User-Agent": VLC_USER_AGENT,
            "Referer": referer,
            "Origin": origin
        }
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session: 
            async with session.get(url, headers=headers) as resp:
                # Menerima 200 (OK) atau 403 (Forbidden, tapi seringnya tetap bisa dimainkan dengan referer/header yang benar)
                return resp.status in [200, 403]
    except Exception:
        return False

async def get_streams():
    """Mengambil daftar stream dari PPV API menggunakan aiohttp."""
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'User-Agent': VLC_USER_AGENT,
            'Accept': 'application/json, text/plain, */*'
        }
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            print(f"🌐 Fetching streams from {API_URL}")
            async with session.get(API_URL) as resp:
                print(f"🔍 Response status: {resp.status}")
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ Error response: {error_text[:500]}")
                    return None
                return await resp.json()
    except Exception as e:
        print(f"❌ Error in get_streams: {str(e)}")
        return None

# --- FUNGSI ASYNC PLAYWRIGHT ---
async def grab_m3u8_from_iframe(page, iframe_url):
    """
    Menggunakan Playwright untuk memuat iframe, memantau traffic jaringan, 
    dan menangkap URL M3U8/MPD yang di-load oleh JavaScript.
    """
    found_streams = set()
    
    def handle_response(response):
        url = response.url
        # Tambahkan filter untuk menghindari URL yang terlalu panjang (biasanya iklan/tracking)
        if (".m3u8" in url or ".mpd" in url) and url.count('/') < 10: 
            if url not in found_streams:
                found_streams.add(url)

    page.on("response", handle_response)
    print(f"🌐 Navigating to iframe: {iframe_url}")
    
    try:
        await page.goto(iframe_url, timeout=30000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"❌ Failed to load iframe page: {e}")
        page.remove_listener("response", handle_response)
        return set()

    # Logika untuk mengklik (memicu player)
    try:
        await page.wait_for_timeout(3000) 
        nested_iframe = page.locator("iframe")
        
        if await nested_iframe.count() > 0:
            player_frame = page.frame_locator("iframe").first
            await player_frame.locator("body").click(timeout=5000, force=True)
        else:
            await page.locator("body").click(timeout=5000, force=True)
            
    except Exception:
        pass 

    print("⏳ Waiting 5-8s for stream to be requested...")
    # Jeda acak 5 hingga 8 detik untuk menghindari deteksi bot
    wait_time = random.uniform(5, 8) 
    await asyncio.sleep(wait_time)
    page.remove_listener("response", handle_response)

    if not found_streams:
        return set()

    # Validasi URL yang ditangkap secara paralel
    valid_urls = set()
    tasks = [check_m3u8_url(url, iframe_url) for url in found_streams]
    results = await asyncio.gather(*tasks)
    
    for url, is_valid in zip(found_streams, results):
        if is_valid:
            valid_urls.add(url)
            
    return valid_urls

async def grab_live_now_from_html(page, base_url="https://ppv.to/"):
    """Scraping stream 'Live Now' dari HTML halaman utama."""
    print("🌐 Scraping 'Live Now' streams from HTML...")
    live_now_streams = []
    try:
        await page.goto(base_url, timeout=20000)
        await asyncio.sleep(3)

        live_cards = await page.query_selector_all("#livecards a.item-card")
        for card in live_cards:
            href = await card.get_attribute("href")
            name_el = await card.query_selector(".card-title")
            poster_el = await card.query_selector("img.card-img-top")
            name = await name_el.inner_text() if name_el else "Unnamed Live"
            poster = await poster_el.get_attribute("src") if poster_el else None

            if href:
                iframe_url = f"{base_url.rstrip('/')}{href}"
                live_now_streams.append({
                    "name": name.strip(),
                    "iframe": iframe_url,
                    "category": "Live Now",
                    "poster": poster
                })
    except Exception as e:
        print(f"❌ Failed scraping 'Live Now': {e}")

    print(f"✅ Found {len(live_now_streams)} 'Live Now' streams")
    return live_now_streams

# --- FUNGSI M3U BUILDER ---
def build_m3u(streams, url_map):
    """Merakit semua data menjadi file M3U dengan header VLC."""
    lines = ['#EXTM3U url-tvg="https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz"']
    seen_names = set()
    
    for s in streams:
        name_lower = s["name"].strip().lower()
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)

        unique_key = f"{s['name']}::{s['category']}::{s['iframe']}"
        urls = url_map.get(unique_key, [])
        if not urls:
            continue

        orig_category = s.get("category") or "Misc"
        final_group = GROUP_RENAME_MAP.get(orig_category, f"PPVLand - {orig_category}")
        logo = s.get("poster") or CATEGORY_LOGOS.get(orig_category, "http://drewlive24.duckdns.org:9000/Logos/Default.png")
        tvg_id = CATEGORY_TVG_IDS.get(orig_category, "Misc.Dummy.us")

        # Logika Kustom untuk menentukan TVG ID dan Group Title Football
        if orig_category == "American Football":
            matched_team = None
            for team in NFL_TEAMS:
                if team in name_lower:
                    tvg_id = "NFL.Dummy.us"
                    final_group = "PPVLand - NFL Action"
                    matched_team = team
                    break
            if not matched_team:
                for team in COLLEGE_TEAMS:
                    if team in name_lower:
                        tvg_id = "NCAA.Football.Dummy.us"
                        final_group = "PPVLand - College Football"
                        matched_team = team
                        break

        url = next(iter(urls)) 
        
        # Baris #EXTINF
        lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{final_group}",{s["name"]}')
        
        # Header VLC (Origin, Referer, User-Agent)
        lines.extend(CUSTOM_HEADERS)
        
        # URL Stream M3U8
        lines.append(url)
        
    return "\n".join(lines)

# --- FUNGSI UTAMA ---
async def main():
    print("🚀 Starting PPV Stream Fetcher (Playwright Mode)")
    
    # 1. Ambil data dari API
    data = await get_streams()
    if not data:
        print("❌ Cannot proceed without API data.")
        return

    print(f"✅ Found {len(data['streams'])} categories")
    
    streams = []
    for category in data.get("streams", []):
        cat = category.get("category", "").strip() or "Misc"
        if cat not in ALLOWED_CATEGORIES:
            ALLOWED_CATEGORIES.add(cat) 
        
        for stream in category.get("streams", []):
            iframe = stream.get("iframe") 
            name = stream.get("name", "Unnamed Event")
            poster = stream.get("poster")
            if iframe:
                streams.append({
                    "name": name,
                    "iframe": iframe,
                    "category": cat,
                    "poster": poster
                })

    # Dedupilasi stream berdasarkan nama
    seen_names = set()
    deduped_streams = []
    for s in streams:
        name_key = s["name"].strip().lower()
        if name_key not in seen_names:
            seen_names.add(name_key)
            deduped_streams.append(s)
    streams = deduped_streams

    # 2. Mulai Playwright (Headless Browser)
    async with async_playwright() as p:
        # Gunakan Firefox karena sudah diinstal
        browser = await p.firefox.launch(headless=True) 
        context = await browser.new_context(
            extra_http_headers={'User-Agent': VLC_USER_AGENT} 
        )
        page = await context.new_page()
        url_map = {}

        # 3. Proses Stream dari API
        total_streams = len(streams)
        for idx, s in enumerate(streams, start=1):
            key = f"{s['name']}::{s['category']}::{s['iframe']}"
            print(f"\n🔎 Scraping stream {idx}/{total_streams}: {s['name']} ({s['category']})")
            
            # Ini adalah inti dari proses scraping menggunakan Playwright
            urls = await grab_m3u8_from_iframe(page, s["iframe"]) 
            
            if urls:
                url_map[key] = urls
            
        # 4. Proses Stream 'Live Now' (Scraping HTML)
        live_now_streams = await grab_live_now_from_html(page)
        for s in live_now_streams:
            key = f"{s['name']}::{s['category']}::{s['iframe']}"
            urls = await grab_m3u8_from_iframe(page, s["iframe"])
            if urls:
                url_map[key] = urls
            streams.append(s)

        await browser.close()

    # 5. Build M3U File
    print("\n💾 Writing final playlist to PPVLand.m3u8 ...")
    playlist = build_m3u(streams, url_map)
    
    # Simpan file di folder Repositori (/root/perfect/)
    final_output_path = os.path.join(PLAYLIST_REPO_PATH, OUTPUT_FILE) 
    with open(final_output_path, "w", encoding="utf-8") as f:
        f.write(playlist)
        
    print(f"✅ Done! Playlist saved as {final_output_path} at {datetime.utcnow().isoformat()} UTC")

if __name__ == "__main__":
    # Atur batas waktu (timeout) 40 menit karena proses scraping bisa lama
    asyncio.run(main(), timeout=2400) 

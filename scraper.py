import requests
import sys
import re
import concurrent.futures
from urllib.parse import urljoin, quote

# --- KONSTANTA ---
FALLBACK_LOGOS = {
    "american-football": "http://drewlive24.duckdns.org:9000/Logos/Am-Football2.png",
    "football":          "https://external-content.duckduckgo.com/iu/?u=https://i.imgur.com/RvN0XSF.png",
    "fight":             "http://drewlive24.duckdns.org:9000/Logos/Combat-Sports.png",
    "basketball":        "http://drewlive24.duckdns.org:9000/Logos/Basketball5.png",
    "motor sports":      "http://drewlive24.duckdns.org:9000/Logos/Motorsports3.png",
    "darts":             "http://drewlive24.duckdns.org:9000/Logos/Darts.png"
}

CUSTOM_HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
}

TV_IDS = {
    "Baseball": "MLB.Baseball.Dummy.us",
    "Fight": "PPV.EVENTS.Dummy.us",
    "American Football": "NFL.Dummy.us",
    "Afl": "AUS.Rules.Football.Dummy.us",
    "Football": "Soccer.Dummy.us",
    "Basketball": "Basketball.Dummy.us",
    "Hockey": "NHL.Hockey.Dummy.us",
    "Tennis": "Tennis.Dummy.us",
    "Darts": "Darts.Dummy.us",
    "Motor Sports": "Racing.Dummy.us"
}

# --- FUNGSI VALIDASI M3U8 (DINONAKTIFKAN DI process_match) ---
def check_m3u8_validity(url):
    """Mengecek apakah URL M3U8 dapat diakses menggunakan permintaan HEAD."""
    check_headers = {
        "User-Agent": CUSTOM_HEADERS["User-Agent"],
        "Referer": CUSTOM_HEADERS["Referer"],
        "Origin": CUSTOM_HEADERS["Origin"]
    }
    
    try:
        resp = requests.head(url, headers=check_headers, timeout=5, allow_redirects=True)
        if 200 <= resp.status_code < 300:
            return True
        else:
            print(f"    ⚠️ M3U8 gagal cek HEAD ({resp.status_code}): {url}")
            return False
    except requests.RequestException as e:
        print(f"    ❌ M3U8 gagal cek koneksi: {e}")
        return False

# --- FUNGSI EKSTRAKSI & API ---

def get_matches(endpoint="all"):
    url = f"https://streamed.pk/api/matches/{endpoint}"
    try:
        print(f"📡 Mengambil pertandingan {endpoint} dari API...")
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        print(f"✅ Berhasil mengambil pertandingan {endpoint}.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mengambil pertandingan {endpoint}: {e}", file=sys.stderr)
        return []

def find_m3u8_in_content(page_content):
    """Mencari URL M3U8 menggunakan pola regex yang diperluas."""
    patterns = [
        # Pola 1-4: Konfigurasi player JS
        r'source:\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',
        r'file:\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',
        r'hlsSource\s*=\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',
        r'src\s*:\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',
        
        # Pola 5: Tag <source> HTML5
        r'<source\s+src\s*=\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',

        # Pola 6: Variabel JS 'url' atau 'link'
        r'(?:url|link)\s*:\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',

        # Pola 7 (Paling luas): Mencari M3U8 yang terlampir di mana saja
        r'["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, page_content, re.IGNORECASE) 
        if match:
            return match.group(1)
    return None

def extract_m3u8_from_embed(embed_page_url, level=1):
    """
    Mengambil halaman embed (HTML) dan mengekstrak URL .m3u8 yang sebenarnya.
    Mendukung two-level scraping untuk IFRAME.
    """
    try:
        # Gunakan header yang benar-benar kustom
        temp_headers = CUSTOM_HEADERS.copy()
        if level > 1:
            # Jika ini adalah level iframe, referer-nya harus URL induknya
            temp_headers["Referer"] = embed_page_url 
            temp_headers["Origin"] = embed_page_url # Sesuaikan Origin

        resp = requests.get(embed_page_url, headers=temp_headers, timeout=10)
        resp.raise_for_status()
        
        page_content = resp.text

        # 1. Coba cari M3U8 langsung
        m3u8_link = find_m3u8_in_content(page_content)
        if m3u8_link:
            return m3u8_link

        # 2. Jika M3U8 tidak ditemukan di Level 1, cari IFRAME
        if level == 1:
            # Pola untuk mencari IFRAME
            iframe_match = re.search(
                r'<iframe[^>]+src=["\'](https?://[^\'"]+)["\']', 
                page_content, 
                re.IGNORECASE
            )
            
            if iframe_match:
                iframe_url = iframe_match.group(1)
                print(f"    ➡️ Ditemukan IFRAME Level 2: {iframe_url}. Melanjutkan scraping...")
                
                # Panggil fungsi ini secara rekursif (Level 2)
                return extract_m3u8_from_embed(iframe_url, level=2)

        # 3. Gagal di kedua level
        if level == 2:
             print(f"    *** DEBUG: GAGAL EKSTRAKSI DI LEVEL 2 ({embed_page_url}) ***")
             # Hapus baris debug untuk konten setelah Anda berhasil
             # print("--------------------------------------------------")
             # print(page_content[:1000])
             # print("--------------------------------------------------")
             
        return None
    except Exception as e:
        print(f"    ⚠️ Gagal mengekstrak M3U8 dari {embed_page_url}: {e}")
        return None


def get_stream_embed_urls(source):
    """Mengembalikan semua URL embed yang didapatkan dari API."""
    src_name = source.get('source')
    src_id = source.get('id')
    if not src_name or not src_id:
        return []

    urls_to_try = [
        f"https://streamed.pk/api/stream/{src_name}/{src_id}",
        f"https://streamed.pk/api/stream/alpha/{src_name}/{src_id}"
    ]

    embed_urls = []

    for api_url in urls_to_try:
        try:
            response = requests.get(api_url, headers=CUSTOM_HEADERS, timeout=10)
            response.raise_for_status()
            
            try:
                # Coba JSON
                streams = response.json()
                if streams:
                    for s in streams:
                        url = s.get('embedUrl')
                        if url and url not in embed_urls:
                            embed_urls.append(url)
                    continue
            except:
                pass

            # Fallback: pencarian regex di halaman
            m3u8_fallback = find_m3u8_in_content(response.text)
            if m3u8_fallback and m3u8_fallback not in embed_urls:
                embed_urls.append(m3u8_fallback)

        except requests.RequestException:
            continue

    return embed_urls


# --- FUNGSI PEMROSESAN METADATA & UTAMA ---

def validate_logo(url, category):
    cat = (category or "").lower().replace('-', ' ').strip()
    fallback = None
    for key in FALLBACK_LOGOS:
        if key.lower() == cat:
            fallback = FALLBACK_LOGOS[key]
            break

    if url:
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": CUSTOM_HEADERS["User-Agent"]})
            if resp.status_code == 200 and resp.content:
                return url
        except:
            pass

    return fallback


def build_logo_url(match):
    api_category = (match.get('category') or '').strip()
    poster = match.get('poster')
    logo_url = None

    if poster:
        if poster.startswith("http"):
            logo_url = poster
        else:
            logo_url = urljoin("https://streamed.pk", poster)

    if logo_url:
        logo_url = re.sub(r'(https://streamed\.pk)+', 'https://streamed.pk', logo_url)
        logo_url = re.sub(r'/+', '/', logo_url).replace('https:/', 'https://')

    logo_url = validate_logo(logo_url, api_category)
    return logo_url, api_category


def process_match(match):
    """
    Memproses satu pertandingan, mengambil embed URL,
    dan mengekstrak M3U8 (validasi koneksi dinonaktifkan untuk uji coba).
    """
    title = match.get('title', 'Untitled Match')
    sources = match.get('sources', [])
    m3u8_urls = []

    for source in sources:
        embed_urls = get_stream_embed_urls(source)
        for embed_url in embed_urls:
            if embed_url:
                print(f"  🔎 Mengecek embed untuk '{title}': {embed_url}")
                
                # --- LOGIKA EKSTRAKSI ---
                if embed_url.endswith('.m3u8'):
                    m3u8 = embed_url
                else:
                    # Kini fungsi ini akan menangani scraping dua level
                    m3u8 = extract_m3u8_from_embed(embed_url, level=1)
                
                if m3u8 and m3u8 not in m3u8_urls:
                    print(f"    ➡️ Ditemukan kandidat M3U8: {m3u8}")
                    
                    # --- VALIDASI DINONAKTIFKAN SEMENTARA UNTUK UJI COBA ---
                    # if check_m3u8_validity(m3u8):
                    #     print(f"    ✅ M3U8 valid dan akan ditambahkan.")
                    #     m3u8_urls.append(m3u8)
                    
                    # Tambahkan M3U8 tanpa validasi
                    print(f"    ✅ M3U8 ditambahkan TANPA validasi koneksi.")
                    m3u8_urls.append(m3u8)
                    # ----------------------------------------------------

    return match, m3u8_urls if m3u8_urls else None


def generate_m3u8():
    all_matches = get_matches("all")
    live_matches = get_matches("live")
    
    unique_matches = {}
    for m in all_matches + live_matches:
        unique_matches[m.get('id')] = m
    matches = list(unique_matches.values())

    if not matches:
        return "#EXTM3U\n#EXTINF:-1,Tidak Ada Pertandingan Ditemukan\n"

    content = ["#EXTM3U"]
    success = 0
    
    # --- STRUKTUR HEADER URL UNTUK PEMUTAR ---
    header_string = (
        f'Origin={quote(CUSTOM_HEADERS["Origin"])}'
        f'&Referer={quote(CUSTOM_HEADERS["Referer"])}'
        f'&User-Agent={quote(CUSTOM_HEADERS["User-Agent"])}'
    )
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_match, m): m for m in matches}
        for future in concurrent.futures.as_completed(futures):
            match, urls = future.result()
            title = match.get('title', 'Untitled Match')
            
            if urls:
                logo, cat = build_logo_url(match)
                display_cat = cat.replace('-', ' ').title() if cat else "General"
                tv_id = TV_IDS.get(display_cat, "General.Dummy.us")

                for url in urls:
                    # Gabungkan URL M3U8 dengan string header
                    url_with_headers = f"{url}|{header_string}" 
                    
                    content.append(f'#EXTINF:-1 tvg-id="{tv_id}" tvg-name="{title}" tvg-logo="{logo}" group-title="StreamedSU - {display_cat}",{title}')
                    content.append(url_with_headers) 
                    success += 1
                    print(f"  ✅ {title} ({logo}) TV-ID: {tv_id}")

    print(f"🎉 Ditemukan {success} stream yang berfungsi (tanpa validasi koneksi).")
    return "\n".join(content)


if __name__ == "__main__":
    playlist = generate_m3u8()
    try:
        with open("StreamedSU.m3u8", "w", encoding="utf-8") as f:
            f.write(playlist)
        print("💾 Playlist berhasil disimpan ke StreamedSU.m3u8.")
    except IOError as e:
        print(f"⚠️ Error saat menyimpan file: {e}")
        print("--- ISI PLAYLIST (Gagal Disimpan Ke File) ---")
        print(playlist)

import requests
import sys
import re
import concurrent.futures
from urllib.parse import urljoin

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

# --- FUNGSI BARU UNTUK VALIDASI M3U8 ---
def check_m3u8_validity(url):
    """Mengecek apakah URL M3U8 dapat diakses menggunakan permintaan HEAD."""
    # Gunakan header kustom untuk menghindari pemblokiran
    check_headers = {
        "User-Agent": CUSTOM_HEADERS["User-Agent"],
        "Referer": CUSTOM_HEADERS["Referer"],
        "Origin": CUSTOM_HEADERS["Origin"]
    }
    
    try:
        # Gunakan HEAD request (lebih cepat, hanya meminta header)
        resp = requests.head(url, headers=check_headers, timeout=5, allow_redirects=True)
        # 200-299 adalah kode status sukses
        if 200 <= resp.status_code < 300:
            return True
        else:
            print(f"    ⚠️ M3U8 gagal cek HEAD ({resp.status_code}): {url}")
            return False
    except requests.RequestException as e:
        # Tangani timeout atau error koneksi
        print(f"    ❌ M3U8 gagal cek koneksi: {e}")
        return False

# --- FUNGSI LAMA (DIREVISI) ---

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
    patterns = [
        r'source:\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',
        r'file:\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',
        r'hlsSource\s*=\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',
        r'src\s*:\s*["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']',
        r'["\'](https?://[^\'"]+\.m3u8?[^\'"]*)["\']'
    ]
    for pattern in patterns:
        match = re.search(pattern, page_content)
        if match:
            return match.group(1)
    return None


def extract_m3u8_from_alpha(embed_page_url):
    """Mengambil halaman alpha embed dan mengekstrak URL .m3u8 yang sebenarnya."""
    try:
        resp = requests.get(embed_page_url, headers=CUSTOM_HEADERS, timeout=10)
        resp.raise_for_status()
        return find_m3u8_in_content(resp.text)
    except:
        return None


def get_stream_embed_urls(source):
    """Mengembalikan semua URL embed, menyelesaikan URL alpha ke m3u8."""
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
            # Coba JSON dulu
            try:
                streams = response.json()
                if streams:
                    for s in streams:
                        url = s.get('embedUrl')
                        if url and url not in embed_urls:
                            # Jika URL alpha, selesaikan m3u8 dari halaman
                            if "alpha" in api_url:
                                m3u8 = extract_m3u8_from_alpha(url)
                                if m3u8 and m3u8 not in embed_urls:
                                    embed_urls.append(m3u8)
                            else:
                                embed_urls.append(url)
                    continue
            except:
                pass

            # Fallback: pencarian regex di halaman
            m3u8 = find_m3u8_in_content(response.text)
            if m3u8 and m3u8 not in embed_urls:
                embed_urls.append(m3u8)

        except requests.RequestException:
            continue

    return embed_urls


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
    mengekstrak M3U8, dan MEMVALIDASI M3U8.
    """
    title = match.get('title', 'Untitled Match')
    sources = match.get('sources', [])
    m3u8_urls = []

    for source in sources:
        embed_urls = get_stream_embed_urls(source)
        for embed_url in embed_urls:
            if embed_url:
                print(f"  🔎 Mengecek embed untuk '{title}': {embed_url}")
                # Ekstrak M3U8 dari URL embed
                m3u8 = extract_m3u8_from_alpha(embed_url) if "alpha" in embed_url else embed_url
                
                if m3u8 and m3u8 not in m3u8_urls:
                    print(f"    ➡️ Ditemukan kandidat M3U8: {m3u8}")
                    
                    # --- LANGKAH VALIDASI BARU ---
                    # Periksa apakah M3U8 dapat diakses sebelum menambahkannya
                    if check_m3u8_validity(m3u8):
                        print(f"    ✅ M3U8 valid dan akan ditambahkan.")
                        m3u8_urls.append(m3u8)
                    # -----------------------------

    # Hanya kembalikan URL M3U8 yang sudah divalidasi
    return match, m3u8_urls if m3u8_urls else None


def generate_m3u8():
    all_matches = get_matches("all")
    live_matches = get_matches("live")
    # Gabungkan semua pertandingan, Anda mungkin perlu menghapus duplikat di sini
    matches = all_matches + live_matches

    if not matches:
        return "#EXTM3U\n#EXTINF:-1,Tidak Ada Pertandingan Ditemukan\n"

    content = ["#EXTM3U"]
    success = 0

    vlc_header_lines = [
        f'#EXTVLCOPT:http-origin={CUSTOM_HEADERS["Origin"]}',
        f'#EXTVLCOPT:http-referrer={CUSTOM_HEADERS["Referer"]}',
        f'#EXTVLCOPT:http-user-agent={CUSTOM_HEADERS["User-Agent"]}'
    ]

    # Menggunakan multithreading untuk memproses pertandingan secara paralel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_match, m): m for m in matches}
        for future in concurrent.futures.as_completed(futures):
            match, urls = future.result()
            title = match.get('title', 'Untitled Match')
            
            # Hanya tambahkan jika ada URL yang valid (setelah proses_match dan validasi)
            if urls:
                logo, cat = build_logo_url(match)
                display_cat = cat.replace('-', ' ').title() if cat else "General"
                tv_id = TV_IDS.get(display_cat, "General.Dummy.us")

                for url in urls:
                    # Tambahkan baris EXTFINF, logo, group, dll.
                    content.append(f'#EXTINF:-1 tvg-id="{tv_id}" tvg-name="{title}" tvg-logo="{logo}" group-title="StreamedSU - {display_cat}",{title}')
                    # Tambahkan header kustom VLC
                    content.extend(vlc_header_lines)
                    # Tambahkan URL M3U8 yang valid
                    content.append(url)
                    success += 1
                    print(f"  ✅ {title} ({logo}) TV-ID: {tv_id}")

    print(f"🎉 Ditemukan {success} stream yang berfungsi (sudah divalidasi).")
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

# Membuat branch baru (misal: 'js-fix') dan pindah ke sana
git checkout -b js-fix

# Tambahkan file yang baru/diubah
git add scraper.py

# Commit perubahan
git commit -m "FEAT: Add JavaScript external file M3U8 extraction logic and final headers"

# Push branch baru ke GitHub
git push -u origin js-fix

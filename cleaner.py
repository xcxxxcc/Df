file_path = "/data/data/com.termux/files/home/Df/Poasla"
try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    clean_content = content.replace("🔴", "")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(clean_content)
except:
    pass

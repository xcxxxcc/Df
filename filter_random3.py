import os
import requests
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://addnewplaylist.iwansandra1974.workers.dev/%7Cuser-agent=OTT%20Navigator%201.7.9%20Android"
headers = {"Connection": "Keep-Alive", "User-Agent": "(ICAgICAgewogICAgICAidiI6ICIyIiwKICAgICAgInBzIjogInVodXl5eTAxIiwKICAgICAgImFkZCI6ICJkbzItc3RiLmJobS5teS5pZCIsCiAgICAgICJwb3J0IjogIjgwIiwKICAgICAgImlkIjogImQwOTk0N2Q1LWE1YTItNDU3My1iYjAxLWNhYWM1YTQwMmYzNyIsCiAgICAgICJhaWQiOiAiMCIsCiAgICAgICJuZXQiOiAid3MiLAogICAgICAicGF0aCI6ICIvdm1lc3MiLAogICAgICAidHlwZSI6ICJub25lIiwKICAgICAgImhvc3QiOiAiZG8yLXN0Yi5iaG0ubXkuaWQiLAogICAgICAic25pIjogImJ1Zy5jb20iLAogICAgICAidGxzIjogIm5vbmUiCn0K|ICAgICAgewogICAgICAidiI6ICIyIiwKICAgICAgInBzIjogInVodXl5eTAxIiwKICAgICAgImFkZCI6ICJkbzItc3RiLmJobS5teS5pZCIsCiAgICAgICJwb3J0IjogIjQ0MyIsCiAgICAgICJpZCI6ICJkMDk3NDdkNS1hNWEyLTQ1NzMtYmIwMS1jYWFjNWE0MDJmMzciLCJtaWQiOiAiMCIsIm5ldCI6ICJ3cyIsInBhdGgiOiAiL3ZtZXNzIiwidHlwZSI6ICJub25lIiwiaG9zdCI6ICJkbzItc3RiLmJobS5teS5pZCIsInNuaSI6ICJidWcuY29tIiwidGxzIjogInRscyJ9Cg==|geulis|iwan1|tvg|risko2|sapta3|iston4|dedi5|tjipto6|bagus7|jepa8|salman9|qilau1|lily2|warhol3|donga4|indra5|tato6|rino7|tie8|astri9|tirta1|yandi|sandy2|jaya3)"}

response = requests.get(url, headers=headers, verify=False)
entries = response.text.split("#EXTINF")
output = []

whitelist = ["Zhubo", "pildunNobar", "Live event 90sport", "Xoilacz", "voliball xoilacztv", "Shoot LiveEvent"]
blacklist = ["bonetvbumper", "iwanfalstv"]

for entry in entries:
    if not entry.strip(): continue
    full_entry = "#EXTINF" + entry
    if any(s in full_entry for s in whitelist) and not any(b in full_entry for b in blacklist):
        # Paksa group-title jadi RANDOM 3
        full_entry = re.sub(r'group-title="[^"]*"', 'group-title="RANDOM 3"', full_entry)
        output.append(full_entry.strip())

with open("random3_temp.m3u", "w") as f:
    f.write("\n".join(output))

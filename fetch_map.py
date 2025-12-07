import requests
import re

def fetch_awbw_map(map_id):
    url = f"https://awbw.amarriner.com/text_map.php?maps_id={map_id}"
    try:
        r = requests.get(url)
        matches = re.findall(r'((?:\d+,){10,}\d+)', r.text)
        return "\n".join(matches) if matches else None
    except: return None

import requests
import re
import json

UNIT_NAME_MAP = {
    "Infantry": "infantry", "Mech": "mech", "Recon": "recon", "Tank": "tank",
    "Md.Tank": "mediumTank", "Neotank": "neoTank", "APC": "apc",
    "Artillery": "artillery", "Rocket": "rocket", "Anti-Air": "antiAir",
    "Missile": "missile", "Fighter": "fighter", "Bomber": "bomber",
    "B-Copter": "battleCopter", "T-Copter": "transportCopter",
    "Battleship": "battleship", "Cruiser": "cruiser", "Lander": "lander",
    "Sub": "sub", "Black Boat": "blackBoat", "Stealth": "stealth"
}

def fetch_units(game_id):
    try:
        url = f"https://awbw.amarriner.com/game.php?games_id={game_id}"
        html = requests.get(url).text
        m_info = re.search(r"unitsInfo\s*=\s*(\{[\s\S]*?\});", html)
        m_players = re.search(r"playersInfo\s*=\s*(\{[\s\S]*?\});", html)
        
        if not m_info or not m_players: return []
        
        units_info = json.loads(m_info.group(1))
        players_info = json.loads(m_players.group(1))
        
        sorted_players = sorted(players_info.values(), key=lambda x: int(x['players_order']))
        pid_to_slot = {int(p['players_id']): i for i, p in enumerate(sorted_players)}
        
        ww_units = []
        for uid, u in units_info.items():
            name = u['units_name']
            if name == "Md. Tank": name = "Md.Tank"
            ww_type = UNIT_NAME_MAP.get(name)
            if not ww_type: continue
            
            ww_units.append({
                "id": uid,
                "type": ww_type,
                "position": {"x": int(u['units_x']), "y": int(u['units_y'])},
                "playerSlot": pid_to_slot.get(int(u['units_players_id']), -1),
                "stats": {"hp": int(float(u['units_hit_points']) * 10), "fuel": int(u['units_fuel'])}
            })
        return ww_units
    except: return []


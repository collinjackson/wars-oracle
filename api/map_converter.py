import sys

TERRAIN_MAP = {
    1: {"type": "plain"}, 2: {"type": "mountain"}, 3: {"type": "forest"},
    4: {"type": "river"}, 5: {"type": "river"}, 6: {"type": "river"}, 
    7: {"type": "river"}, 8: {"type": "river"}, 9: {"type": "river"},
    10: {"type": "river"}, 11: {"type": "river"}, 12: {"type": "river"}, 
    13: {"type": "river"}, 14: {"type": "river"},
    15: {"type": "sea"}, 16: {"type": "beach"},
    17: {"type": "shoal"}, 18: {"type": "shoal"}, 19: {"type": "shoal"},
    20: {"type": "shoal"}, 21: {"type": "shoal"}, 22: {"type": "shoal"},
    23: {"type": "shoal"}, 24: {"type": "shoal"}, 25: {"type": "shoal"},
    26: {"type": "shoal"}, 27: {"type": "bridge"},
    28: {"type": "road"}, 29: {"type": "road"}, 30: {"type": "road"},
    31: {"type": "road"}, 32: {"type": "road"}, 33: {"type": "road"},
    # Properties (Neutral defaults)
    34: {"type": "city"}, 35: {"type": "base"}, 36: {"type": "airport"}, 37: {"type": "port"},
    # ... (truncated standard IDs)
}

def parse_map_csv(csv_text, ownership_map=None):
    """
    Parses map and optionally overrides property ownership.
    ownership_map: dict "x,y" -> player_slot_int
    """
    if ownership_map is None: ownership_map = {}
    
    rows = []
    lines = csv_text.strip().split('\n')
    for y, line in enumerate(lines):
        if not line.strip(): continue
        row_ids = [int(x) for x in line.split(',') if x.strip().isdigit()]
        if not row_ids: continue
        
        ww_row = []
        for x, id in enumerate(row_ids):
            tile = TERRAIN_MAP.get(id, {"type": "plain", "id": id}).copy()
            
            # Check if we have dynamic ownership data
            key = f"{x},{y}"
            if key in ownership_map:
                tile['player'] = ownership_map[key]
            elif 'player' not in tile and tile['type'] in ['city', 'base', 'airport', 'port', 'hq', 'lab', 'comTower']:
                # Default to neutral (-1) if not in ownership map
                tile['player'] = -1
                
            ww_row.append(tile)
        rows.append(ww_row)
    return rows

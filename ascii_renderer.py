def render_ascii_map(game_map, units_by_player):
    TERRAIN_CHARS = {
        "plain": ".", "mountain": "^", "forest": "T", "river": "~", "road": "=", 
        "bridge": "=", "sea": "~", "beach": ",", "shoal": ",", 
        "city": "C", "base": "B", "airport": "A", "port": "P", 
        "hq": "H", "comTower": "!", "lab": "L", "silo": "$", "pipe": "|"
    }
    
    height = len(game_map)
    width = len(game_map[0])
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    for y in range(height):
        for x in range(width):
            tile = game_map[y][x]
            t = tile.get('type', 'plain') # Default to plain if type missing
            char = TERRAIN_CHARS.get(t, '?')
            
            owner = tile.get('player', -1)
            if owner != -1:
                char = char.upper() # Owned = Upper
            else:
                # If neutral property, maybe lower case? 
                if t in ["city", "base", "airport", "port", "comTower", "lab"]:
                    char = char.lower()
                # else keep as is (terrain chars)
                
            grid[y][x] = char

    UNIT_CHARS = {
        "infantry": "i", "mech": "m", "recon": "r", "tank": "t",
        "mediumTank": "M", "neoTank": "N", "apc": "a", "artillery": "A",
        "rocket": "R", "antiAir": "X", "missile": "S", "battleship": "B",
        "cruiser": "c", "sub": "s", "lander": "L", "blackBoat": "b",
        "transportCopter": "T", "battleCopter": "H", "fighter": "F", "bomber": "O"
    }
    
    for slot, units in units_by_player.items():
        for u in units:
            x, y = u['position']['x'], u['position']['y']
            utype = u['type']
            char = UNIT_CHARS.get(utype, '?')
            if 0 <= y < height and 0 <= x < width:
                grid[y][x] = char

    lines = []
    lines.append("   " + "".join([str((i//10)%10) if i%10==0 else " " for i in range(width)]))
    lines.append("   " + "".join([str(i%10) for i in range(width)]))
    for y in range(height):
        row_str = "".join(grid[y])
        lines.append(f"{y:2d} {row_str}")
    return "\n".join(lines)

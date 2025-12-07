import json
try:
    from ascii_renderer import render_ascii_map
except ImportError:
    def render_ascii_map(m, u): return "(ASCII Map Renderer Missing)"

def generate_context(map_file, units_file, rules_file, teams_data=None):
    with open(map_file) as f: game_map = json.load(f)
    with open(units_file) as f: units = json.load(f)
    with open(rules_file) as f: rules = json.load(f)
    
    # Support passing dict directly (from fetch_game_metadata) or path
    if isinstance(teams_data, str):
        try:
            with open(teams_data) as f: teams_data = json.load(f)
        except: teams_data = {"game_id": 0, "teams": {}}
    if not teams_data: teams_data = {"game_id": 0, "teams": {}}

    slot_to_meta = {}
    for team_name, team_data in teams_data["teams"].items():
        for p in team_data["players"]:
            slot_to_meta[p["slot"]] = {
                "team": team_name, 
                "name": p["username"], 
                "co": p["co"],
                "funds": p.get("funds", 0),
                "income": p.get("income", 0),
                "status": "ELIMINATED" if p.get("eliminated") else "Active"
            }

    height = len(game_map)
    width = len(game_map[0])
    
    context = []
    context.append("SYSTEM: You are the Wars Oracle. Analyze this game state.")
    context.append("Provide strategic advice based on unit positions, CO matchups, and economy.")
    context.append("")
    
    context.append(f"# Game Context (ID: {teams_data.get('game_id', '?')})")
    context.append(f"Map Size: {width}x{height}")
    context.append("")

    context.append("## Team Status")
    for team_name, team_data in teams_data["teams"].items():
        context.append(f"### Team {team_name}")
        for p in team_data["players"]:
            status = "[ELIMINATED]" if p.get("eliminated") else ""
            stats = p.get("live_stats", {})
            val = stats.get("unit_value", 0)
            count = stats.get("unit_count", 0)
            context.append(f"- {p['username']} ({p['co']}): Funds {p.get('funds',0)}G | Income {p.get('income',0)}G | Army Value {val} ({count} units) {status}")
    context.append("")
    
    units_by_player = {}
    for u in units:
        slot = u['playerSlot']
        if slot not in units_by_player: units_by_player[slot] = []
        units_by_player[slot].append(u)

    context.append("## Tactical Map (ASCII)")
    context.append("Legend: (.)Plain (^)Mtn (T)Forest (~)Sea/River (=)Road (C)City (B)Base (A)Airport (P)Port (H)HQ")
    context.append("```")
    context.append(render_ascii_map(game_map, units_by_player))
    context.append("```")
    context.append("")
    
    for slot in sorted(units_by_player.keys()):
        meta = slot_to_meta.get(slot, {"team": "?", "name": f"Player {slot}", "co": "?"})
        player_units = units_by_player[slot]
        if meta.get("status") == "ELIMINATED": continue # Skip eliminated units if any remain? Usually they vanish.
        
        context.append(f"### {meta['name']} (Team {meta['team']}, {meta['co']})")
        for u in player_units:
            utype = u['type']
            x, y = u['position']['x'], u['position']['y']
            hp = u['stats']['hp']
            try: terrain = game_map[y][x]['type']
            except: terrain = "unknown"
            context.append(f"- {utype} @ ({x},{y}) HP:{hp} Terrain:{terrain}")
        context.append("")

    context.append("## Rules")
    context.append("Matchups: " + str(rules.get('matchups', {})))
    return "\n".join(context)

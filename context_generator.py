import json
import math

try:
    from ascii_renderer import render_ascii_map
except ImportError:
    def render_ascii_map(m, u): return "(ASCII Map Renderer Missing)"

try:
    from analyzer import GameAnalyzer
except ImportError:
    GameAnalyzer = None

def generate_context(map_file, units_file, rules_file, teams_data=None, target_slot=None):
    with open(map_file) as f: game_map = json.load(f)
    with open(units_file) as f: units = json.load(f)
    with open(rules_file) as f: rules = json.load(f)
    
    if isinstance(teams_data, str):
        try:
            with open(teams_data) as f: teams_data = json.load(f)
        except: teams_data = {"game_id": 0, "teams": {}}
    if not teams_data: teams_data = {"game_id": 0, "teams": {}}

    # ... (existing setup code until line 149) ...


    slot_to_meta = {}
    target_identity = "Unknown"
    target_team = None
    
    for team_name, team_data in teams_data["teams"].items():
        for p in team_data["players"]:
            status = "ELIMINATED" if p.get("eliminated") else "Active"
            slot_to_meta[p["slot"]] = {
                "team": team_name, 
                "name": p["username"], 
                "co": p["co"],
                "funds": p.get("funds", 0),
                "income": p.get("income", 0),
                "status": status,
                "is_turn": p.get("is_turn", False)
            }
            if target_slot is not None and p["slot"] == target_slot:
                target_identity = f"{p['username']} (Team {team_name}, {p['co']})"
                target_team = team_name

    height = len(game_map)
    width = len(game_map[0])
    current_turn = teams_data.get('current_turn_username', 'Unknown')
    
    context = []
    if target_slot is not None:
        context.append(f"SYSTEM: You are the Wars Oracle advising {target_identity}.")
        context.append("IMPORTANT: Focus on the PLAYER NAME (e.g. ridiculotron), not just the CO (e.g. Eagle), as duplicates exist.")
        if slot_to_meta[target_slot]['status'] == "ELIMINATED":
             context.append("NOTE: This player is ELIMINATED. Advice should focus on observation or team support if applicable.")
        elif target_identity.startswith(current_turn):
            context.append("It is YOUR turn. You can move and produce units now.")
        else:
            funds = slot_to_meta[target_slot]['funds']
            context.append(f"It is NOT your turn. You have {funds}G stored.")
            context.append(f"Current turn: {current_turn}.")
    else:
        context.append(f"SYSTEM: You are the Wars Oracle. Analyze this game state. Current Turn: {current_turn}")
    
    context.append("CRITICAL RULES:")
    context.append("- CO Powers ONLY charge via combat damage dealt/taken. Do not suggest 'waiting' to charge.")
    context.append("- Sami's capture bonus (+50%) applies ONLY when capturing. Her infantry move normally otherwise.")
    context.append("- Bases produce ground units. Airports produce air units. Ports produce naval units.")
    context.append("- Distances are Manhattan (|x1-x2| + |y1-y2|). Units CANNOT move beyond their Move stat.")
    
    context.append("")
    context.append(f"# Game Context (ID: {teams_data.get('game_id', '?')})")
    context.append(f"Map Size: {width}x{height} | Current Turn: {current_turn}")
    context.append("")

    context.append("## Team Status")
    
    eliminated_players = []
    
    for team_name, team_data in teams_data["teams"].items():
        context.append(f"### Team {team_name}")
        for p in team_data["players"]:
            if p.get("eliminated"):
                eliminated_players.append(f"{p['username']} ({p['co']})")
                continue
                
            turn_marker = "◀ CURRENT TURN" if p.get("is_turn") else ""
            marker = "⭐ YOU" if p["slot"] == target_slot else ""
            stats = p.get("live_stats", {})
            val = stats.get("unit_value", 0)
            
            context.append(f"- {p['username']} ({p['co']}): Funds {p.get('funds',0)}G | Income {p.get('income',0)}G | Value {val} {marker} {turn_marker}")
    
    if eliminated_players:
        context.append("")
        context.append(f"Graveyard (Eliminated): {', '.join(eliminated_players)}")
        
    context.append("")
    
    units_by_player = {}
    active_unit_types = set()
    all_units_pos = {} # (x,y) -> unit
    enemy_blocking_pos = set() # (x,y)
    
    for u in units:
        u_slot = u['playerSlot']
        u_meta = slot_to_meta.get(u_slot, {})
        if u_meta.get("status") == "ELIMINATED":
            continue
            
        x, y = u['position']['x'], u['position']['y']
        all_units_pos[(x,y)] = u
        
        # Check if enemy (different team)
        # Note: u_meta['team'] might be same as target_team
        if target_team and u_meta.get('team') != target_team:
            enemy_blocking_pos.add((x,y))
        
        if u_slot not in units_by_player: units_by_player[u_slot] = []
        units_by_player[u_slot].append(u)
        active_unit_types.add(u['type'])

    context.append("## Tactical Map (ASCII)")
    context.append("Legend: (.)Plain (^)Mtn (T)Forest (~)Sea/River (=)Road (C)City (B)Base (A)Airport (P)Port (H)HQ")
    context.append("Owner Case: UPPER=Owned, lower=Neutral")
    context.append("```")
    context.append(render_ascii_map(game_map, units_by_player))
    context.append("```")
    context.append("")
    
    for slot in sorted(units_by_player.keys()):
        meta = slot_to_meta.get(slot, {"team": "?", "name": f"Player {slot}", "co": "?"})
        if meta.get("status") == "ELIMINATED": continue
        
        context.append(f"### {meta['name']} (Team {meta['team']}, {meta['co']})")
        player_units = units_by_player[slot]
        for u in player_units:
            utype = u['type']
            x, y = u['position']['x'], u['position']['y']
            hp = u['stats']['hp']
            context.append(f"- {utype} @ ({x},{y}) HP:{hp}")
        context.append("")

    context.append("## Relevant Unit Stats (Reference)")
    for u in active_unit_types:
        stats = rules.get("units", {}).get(u)
        if stats:
            context.append(f"- {u}: Cost {stats['cost']}G | Move {stats['move']} ({stats['type']}) | Range {stats['range']}")

    # --- TACTICAL ANALYSIS (Pre-computed Valid Moves) ---
    if target_slot is not None and target_slot in units_by_player:
        context.append("")
        context.append("## Valid Moves & Threats (Engine Verified)")
        context.append("Use this data to avoid hallucinating impossible moves.")
        
        # New Analyzer Integration
        if GameAnalyzer:
            analyzer = GameAnalyzer(map_file, units_file, rules_file, teams_data)
            analysis = analyzer.get_full_analysis(target_slot)
            
            # --- Strategic Summary ---
            context.append("### Strategic Summary")
            
            econ = analysis.get('economy', {})
            # Find stats for target and enemy
            my_stats = econ.get(str(target_slot)) or econ.get(target_slot)
            
            if my_stats:
                # Find main enemy (simplification)
                enemy_val = 0
                for s, data in econ.items():
                    if str(s) != str(target_slot) and data['unit_value'] > enemy_val:
                        enemy_val = data['unit_value']
                
                diff = my_stats['unit_value'] - enemy_val
                status = "AHEAD" if diff > 5000 else "BEHIND" if diff < -5000 else "EVEN"
                context.append(f"- Material Status: {status} ({diff:+} value)")
            
            # Threats High Level
            threats = analysis.get('threats', [])
            high_risk = [t for t in threats if t['damage_pct'] > 50]
            if high_risk:
                 context.append(f"- IMMEDIATE DANGER: {len(high_risk)} units at high risk.")
            
            context.append("")
            
            # --- Unit Specifics ---
            # We can reuse the loop but now use Analyzer's data structure if we wanted,
            # but for now let's keep the per-unit text format we had, just enhanced?
            # Actually, let's keep the existing "per unit" loop below as it lists valid moves nicely.
        
        # ... (keep existing per-unit loop for valid moves) ...
        my_units = units_by_player[target_slot]

        for u in my_units:
            utype = u['type']
            start_x, start_y = u['position']['x'], u['position']['y']
            u_stats = rules.get("units", {}).get(utype, {})
            move_pts = u_stats.get('move', 3)
            move_type = u_stats.get('type', 'foot')
            min_rng, max_rng = u_stats.get('range', [1,1])
            
            # Calculate Reachable Cells
            # We treat ENEMY units as blocking (cannot pass through)
            # We treat ALL units as blocking destination (cannot end on top)
            reachable = get_reachable_cells(start_x, start_y, move_pts, move_type, game_map, width, height, blocking_cells=enemy_blocking_pos)
            
            # Filter destinations: Cannot end on ANY unit (unless it's the unit itself)
            valid_destinations = [
                (rx, ry) for (rx, ry) in reachable 
                if (rx, ry) not in all_units_pos or (rx, ry) == (start_x, start_y)
            ]
            
            # Identify Targets
            threats = []
            captures = []
            
            # 1. Capture Logic (Infantry/Mech)
            if utype in ['infantry', 'mech']:
                for (rx, ry) in valid_destinations:
                    # Check if property is unowned or enemy
                    cell = game_map[ry][rx]
                    # Map converter gives 'player' ID. We need to check if it matches target_slot.
                    # cell['player'] is the OWNER slot.
                    # If owner != target_slot, it's captureable (if it's a building)
                    if cell.get('type') in ['city', 'base', 'airport', 'port', 'hq', 'lab', 'comTower']:
                        owner = cell.get('player', -1)
                        if owner != target_slot:
                            # Also check if it's already fully captured? No, API doesn't give capture points easily yet.
                            # Just assume if it's not ours, we can capture.
                            captures.append(f"({rx},{ry})")

            # 2. Attack Logic
            # Direct (Range 1)
            if max_rng == 1:
                for (rx, ry) in valid_destinations:
                    # Check adjacents for enemies
                    for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                        tx, ty = rx+dx, ry+dy
                        if (tx, ty) in all_units_pos:
                            target_u = all_units_pos[(tx, ty)]
                            # Check if enemy
                            t_meta = slot_to_meta.get(target_u['playerSlot'], {})
                            if t_meta.get('team') != target_team:
                                threats.append(f"{target_u['type']}@({tx},{ty})")
            
            # Indirect (Range > 1) - Move OR Fire usually
            # So check targets from CURRENT position only (unless user has move+fire skill, ignored for now)
            else:
                 # Check all cells in [min_rng, max_rng] from CURRENT pos
                 # Scan bounding box
                 for dy in range(-max_rng, max_rng+1):
                     for dx in range(-max_rng, max_rng+1):
                         dist = abs(dx) + abs(dy)
                         if min_rng <= dist <= max_rng:
                             tx, ty = start_x+dx, start_y+dy
                             if (tx, ty) in all_units_pos:
                                 target_u = all_units_pos[(tx, ty)]
                                 t_meta = slot_to_meta.get(target_u['playerSlot'], {})
                                 if t_meta.get('team') != target_team:
                                     threats.append(f"{target_u['type']}@({tx},{ty})")

            # Format Output
            # Limit list size to avoid token explosion
            threats = list(set(threats)) # dedupe
            captures = list(set(captures))
            
            summary = []
            if threats: summary.append(f"Can Attack: {', '.join(threats[:5])}" + ("..." if len(threats)>5 else ""))
            if captures: summary.append(f"Can Capture: {', '.join(captures)}")
            
            # Add simple "Reach" summary?
            # e.g. "Reach: 24 cells" or bounding box?
            # "Reach: North(Y=5), East(X=10)..."
            # Maybe just listing threats/captures is enough to ground the tactical advice.
            # If no threats/captures, maybe say "Safe Move" or "Transit"?
            
            if not threats and not captures:
                summary.append("Status: Transit / No immediate targets")
            
            context.append(f"- {utype} @ ({start_x},{start_y}): {' | '.join(summary)}")

    return "\n".join(context)

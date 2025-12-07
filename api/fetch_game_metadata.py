import requests
import re
import json

def fetch_game_metadata(game_id):
    """
    Scrapes public game page for Player Info (Team, CO, Funds, Income) and Property Ownership.
    Returns a structure compatible with 'teams.json' but enriched.
    """
    url = f"https://awbw.amarriner.com/game.php?games_id={game_id}"
    try:
        html = requests.get(url).text
        
        # 1. Extract playersInfo JSON
        m_info = re.search(r"(let|var|const)\s+playersInfo\s*=\s*(\{[\s\S]*?\});", html)
        m_puc = re.search(r"(let|var|const)\s+playersUnitCount\s*=\s*(\{[\s\S]*?\});", html)
        m_bld = re.search(r"(let|var|const)\s+playersBuildings\s*=\s*(\{[\s\S]*?\});", html)
        m_turn = re.search(r"(let|var|const)\s+currentTurn\s*=\s*(\d+);", html)
        current_turn_pid = int(m_turn.group(2)) if m_turn else None
        
        if not m_info: return None
        
        players_info = json.loads(m_info.group(2))
        puc = json.loads(m_puc.group(2)) if m_puc else {}
        buildings = json.loads(m_bld.group(2)) if m_bld else {}
        
        ownership_map = {} 
        sorted_players = sorted(players_info.values(), key=lambda x: int(x['players_order']))
        pid_to_slot = {str(p['players_id']): i for i, p in enumerate(sorted_players)}
        
        if isinstance(buildings, dict):
            for pid, x_map in buildings.items():
                if not isinstance(x_map, dict): continue
                slot = pid_to_slot.get(str(pid))
                if slot is None: continue
                for x_str, y_map in x_map.items():
                    if not isinstance(y_map, dict): continue
                    for y_str, b_id in y_map.items():
                        ownership_map[f"{x_str},{y_str}"] = slot

        teams = {}
        current_turn_username = "Unknown"
        
        for i, p in enumerate(sorted_players):
            pid = str(p['players_id'])
            team_letter = p.get('players_team', '?')
            
            if team_letter not in teams:
                teams[team_letter] = {"players": []}
                
            stats = puc.get(pid, {})
            is_current_turn = (int(pid) == current_turn_pid)
            if is_current_turn:
                current_turn_username = p.get('users_username', 'Unknown')
            
            # Clean up CO image
            co_image = p.get('co_image_path', '') 
            if co_image and not co_image.startswith('http'):
                co_image = f"https://awbw.amarriner.com/{co_image}"
                
            eliminated = (p.get('players_eliminated', 'N') == 'Y')
            
            # If eliminated, stats might be stale or should be zeroed?
            # Actually, eliminated players might still have units on board in some edge cases (zombies),
            # but usually they are wiped.
            # The issue reported is DUPLICATE usernames (one active, one eliminated).
            # We keep BOTH in the data structure, but mark one as eliminated.
            
            player_obj = {
                "id": int(pid),
                "username": p.get('users_username', 'Unknown'),
                "co": p.get('co_name', 'Unknown'),
                "co_image_url": co_image,
                "slot": i,
                "funds": int(p.get('players_funds', 0)),
                "income": int(p.get('players_income', 0)),
                "countries_code": p.get('countries_code', ''),
                "eliminated": eliminated,
                "is_turn": is_current_turn,
                "live_stats": {
                    "unit_count": stats.get('total', 0),
                    "unit_value": stats.get('value', 0)
                }
            }
            teams[team_letter]["players"].append(player_obj)
            
        return {
            "game_id": game_id, 
            "teams": teams, 
            "ownership": ownership_map,
            "current_turn_username": current_turn_username
        }
        
    except Exception as e:
        print(f"Error scraping metadata: {e}")
        return None

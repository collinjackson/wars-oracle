import json
import os
from game_logic import get_reachable_cells, calculate_damage

class GameAnalyzer:
    def __init__(self, map_file, units_file, rules_file, metadata_file=None):
        with open(map_file) as f: self.game_map = json.load(f)
        with open(units_file) as f: self.units = json.load(f)
        with open(rules_file) as f: self.rules = json.load(f)
        
        self.metadata = {}
        if metadata_file:
            if isinstance(metadata_file, str) and os.path.exists(metadata_file):
                with open(metadata_file) as f: self.metadata = json.load(f)
            elif isinstance(metadata_file, dict):
                self.metadata = metadata_file

        self.height = len(self.game_map)
        self.width = len(self.game_map[0]) if self.height > 0 else 0
        
        # Pre-process units
        self.units_by_slot = {}
        self.all_units_pos = {}
        self.unit_id_to_unit = {}
        
        for u in self.units:
            u_slot = u['playerSlot']
            if u_slot not in self.units_by_slot: self.units_by_slot[u_slot] = []
            self.units_by_slot[u_slot].append(u)
            
            x, y = u['position']['x'], u['position']['y']
            self.all_units_pos[(x, y)] = u
            self.unit_id_to_unit[u['id']] = u

    def get_player_team(self, slot):
        if not self.metadata: return str(slot)
        for team_name, team_data in self.metadata.get('teams', {}).items():
            for p in team_data.get('players', []):
                if p['slot'] == slot:
                    return team_name
        return str(slot)

    def is_enemy(self, slot_a, slot_b):
        return self.get_player_team(slot_a) != self.get_player_team(slot_b)

    def analyze_economy(self):
        stats = {}
        if not self.metadata: return stats
        
        for team_name, team_data in self.metadata.get('teams', {}).items():
            for p in team_data.get('players', []):
                slot = p['slot']
                stats[slot] = {
                    "username": p['username'],
                    "co": p['co'],
                    "funds": p.get('funds', 0),
                    "income": p.get('income', 0),
                    "unit_count": len(self.units_by_slot.get(slot, [])),
                    "unit_value": p.get("live_stats", {}).get("unit_value", 0)
                }
        return stats

    def analyze_threats(self, target_slot):
        """
        Identify immediate threats to the target player's units.
        """
        threats = []
        my_team = self.get_player_team(target_slot)
        
        # Identify enemy units
        enemy_units = []
        for slot, units in self.units_by_slot.items():
            if self.is_enemy(target_slot, slot):
                enemy_units.extend(units)
        
        # Check each enemy unit's reach
        # Note: This is computationally expensive if we do full pathfinding for every enemy unit.
        # Optimization: Only check enemies within max move+range distance of our bounding box?
        # For now, simplistic approach:
        
        # Build set of our unit positions
        my_units = self.units_by_slot.get(target_slot, [])
        my_unit_positions = {(u['position']['x'], u['position']['y']): u for u in my_units}
        
        blocking_for_enemies = set(self.all_units_pos.keys()) # Enemies are blocked by everyone basically (except allies, but let's assume worst case blocking)
        
        for enemy in enemy_units:
            e_type = enemy['type']
            ex, ey = enemy['position']['x'], enemy['position']['y']
            
            e_stats = self.rules.get("units", {}).get(e_type, {})
            move = e_stats.get('move', 3)
            m_type = e_stats.get('type', 'foot')
            min_rng, max_rng = e_stats.get('range', [1,1])
            
            # Simple Manhattan distance check first
            # If enemy is > move + max_rng away from ANY of our units, skip
            # (Optimization omitted for brevity, but recommended for large maps)

            reachable = get_reachable_cells(ex, ey, move, m_type, self.game_map, self.width, self.height, blocking_for_enemies)
            
            # For each reachable cell, check attack range
            attackable_positions = set()
            
            # If direct attacker (range 1)
            if max_rng == 1:
                for rx, ry in reachable:
                    for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                        tx, ty = rx+dx, ry+dy
                        if (tx, ty) in my_unit_positions:
                            attackable_positions.add((tx, ty))
            else:
                # Indirect - move then fire? Usually indirects (artillery/rockets) CANNOT move and fire.
                # So they threaten only from their CURRENT position.
                # Unless they are Battleships in some versions (but usually still move OR fire).
                # Assumption: Indirects threaten from CURRENT pos.
                # Valid move for indirects to attack is effectively just staying put (or moving 0).
                # Wait, if they move, they can't fire. So we only check from (ex, ey).
                
                # Check from current position
                for dy in range(-max_rng, max_rng+1):
                    for dx in range(-max_rng, max_rng+1):
                        dist = abs(dx) + abs(dy)
                        if min_rng <= dist <= max_rng:
                            tx, ty = ex+dx, ey+dy
                            if (tx, ty) in my_unit_positions:
                                attackable_positions.add((tx, ty))

            for tx, ty in attackable_positions:
                victim = my_unit_positions[(tx, ty)]
                
                # Calculate damage
                # Need terrain of victim
                t_cell = self.game_map[ty][tx]
                dmg = calculate_damage(e_type, victim['type'], enemy['stats']['hp'], victim['stats']['hp'], t_cell, self.rules)
                
                threats.append({
                    "attacker": {
                        "type": e_type,
                        "id": enemy['id'],
                        "pos": [ex, ey],
                        "player": enemy['playerSlot'] # attacker slot
                    },
                    "victim": {
                        "type": victim['type'],
                        "id": victim['id'],
                        "pos": [tx, ty]
                    },
                    "damage_pct": dmg
                })
                
        # Sort by damage descending
        threats.sort(key=lambda x: x['damage_pct'], reverse=True)
        return threats

    def analyze_captures(self, target_slot):
        """
        Identify capture opportunities for the target player.
        """
        captures = []
        my_units = self.units_by_slot.get(target_slot, [])
        my_team = self.get_player_team(target_slot)
        
        blocking = set() # Assume we can move through allies? 
        # Actually in AWBW/AW2 you can move through allies.
        # But for 'blocking_cells' in get_reachable_cells, we pass OBSTACLES.
        # So we collect ENEMY units.
        for slot, units in self.units_by_slot.items():
            if self.is_enemy(target_slot, slot):
                for u in units:
                    blocking.add((u['position']['x'], u['position']['y']))
        
        for u in my_units:
            if u['type'] not in ['infantry', 'mech']: continue
            
            ux, uy = u['position']['x'], u['position']['y']
            u_stats = self.rules.get("units", {}).get(u['type'], {})
            move = u_stats.get('move', 3)
            m_type = u_stats.get('type', 'foot')
            
            reachable = get_reachable_cells(ux, uy, move, m_type, self.game_map, self.width, self.height, blocking)
            
            for rx, ry in reachable:
                # Cannot end on occupied square unless it's us
                if (rx, ry) in self.all_units_pos and (rx, ry) != (ux, uy):
                    continue
                    
                cell = self.game_map[ry][rx]
                ctype = cell.get('type')
                
                if ctype in ['city', 'base', 'airport', 'port', 'hq', 'lab', 'comTower']:
                    owner = cell.get('player', -1)
                    if owner != target_slot:
                        captures.append({
                            "unit_id": u['id'],
                            "pos": [rx, ry],
                            "property_type": ctype,
                            "current_owner": owner,
                            "turns_to_reach": 1 # Immediate reach
                        })
                        
        return captures

    def get_full_analysis(self, target_slot):
        return {
            "economy": self.analyze_economy(),
            "threats": self.analyze_threats(target_slot),
            "captures": self.analyze_captures(target_slot)
        }


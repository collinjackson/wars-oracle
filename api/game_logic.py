from collections import deque
import math

# Terrain Movement Costs (Standard AWBW/AW2)
# 1 = Normal, 99 = Impassable (for pathfinding context)
MOVE_COSTS = {
    "foot": {
        "plain": 1, "mountain": 2, "wood": 1, "river": 2, "road": 1, 
        "city": 1, "base": 1, "airport": 1, "port": 1, "hq": 1, "sea": 99, "reef": 99, "shoal": 99
    },
    "mech": {
        "plain": 1, "mountain": 1, "wood": 1, "river": 1, "road": 1, 
        "city": 1, "base": 1, "airport": 1, "port": 1, "hq": 1, "sea": 99, "reef": 99, "shoal": 99
    },
    "tread": {
        "plain": 1, "mountain": 99, "wood": 2, "river": 99, "road": 1, 
        "city": 1, "base": 1, "airport": 1, "port": 1, "hq": 1, "sea": 99, "reef": 99, "shoal": 99
    },
    "tires": {
        "plain": 2, "mountain": 99, "wood": 3, "river": 99, "road": 1, 
        "city": 1, "base": 1, "airport": 1, "port": 1, "hq": 1, "sea": 99, "reef": 99, "shoal": 99
    },
    "air": {
        "plain": 1, "mountain": 1, "wood": 1, "river": 1, "road": 1, 
        "city": 1, "base": 1, "airport": 1, "port": 1, "hq": 1, "sea": 1, "reef": 1, "shoal": 1
    },
    "ship": {
        "plain": 99, "mountain": 99, "wood": 99, "river": 99, "road": 99, 
        "city": 99, "base": 99, "airport": 99, "port": 1, "hq": 99, "sea": 1, "reef": 2, "shoal": 1
    },
    "transport": { # Lander/Blackboat mostly same as ship but shoal access
        "plain": 99, "mountain": 99, "wood": 99, "river": 99, "road": 99, 
        "city": 99, "base": 99, "airport": 99, "port": 1, "hq": 99, "sea": 1, "reef": 2, "shoal": 1
    }
}

# Map characters to terrain types
TERRAIN_MAP = {
    '.': 'plain', ',': 'plain', # plain
    '^': 'mountain', # mtn
    'T': 'wood', 't': 'wood', # wood/forest
    '~': 'river', # river (visual approximation in ASCII, usually water is sea)
    'S': 'sea', 's': 'sea', # sea
    '=': 'road', '+': 'road', # road
    'C': 'city', 'c': 'city',
    'B': 'base', 'b': 'base',
    'A': 'airport', 'a': 'airport',
    'P': 'port', 'p': 'port',
    'H': 'hq', 'h': 'hq'
}

def get_terrain_type(cell):
    """
    Extracts terrain type from a cell object or char.
    Cell is expected to be a dict from map_converter (e.g. {'type': 'plain'}).
    """
    if isinstance(cell, dict):
        t = cell.get('type', 'plain')
        # Normalize types if needed
        if t == 'forest': return 'wood'
        if t == 'beach': return 'shoal'
        if t == 'bridge': return 'road'
        if t == 'hq': return 'hq' # handled in cost table
        if t == 'lab': return 'city' # treat lab as city for movement usually
        if t == 'comTower': return 'city' # treat tower as city
        return t
    return TERRAIN_MAP.get(cell, 'plain')

def get_reachable_cells(start_x, start_y, move_points, move_type, grid, width, height, blocking_cells=None):
    """
    Returns a set of (x, y) tuples reachable by the unit.
    grid: 2D array of tile objects (dicts)
    blocking_cells: Set of (x, y) occupied by units that BLOCK movement (Enemies).
    """
    if blocking_cells is None: blocking_cells = set()
    
    # BFS state: (x, y, remaining_move)
    visited = {} # (x,y) -> remaining_move
    queue = deque([(start_x, start_y, move_points)])
    visited[(start_x, start_y)] = move_points
    
    valid_destinations = set()
    valid_destinations.add((start_x, start_y))
    
    costs = MOVE_COSTS.get(move_type, MOVE_COSTS['foot'])
    
    while queue:
        cx, cy, current_mp = queue.popleft()
        
        # Neighbors (Up, Down, Left, Right)
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            
            if 0 <= nx < width and 0 <= ny < height:
                # Get terrain cost
                cell = grid[ny][nx]
                t_type = get_terrain_type(cell)
                cost = costs.get(t_type, 1)
                
                # Check blocking (Enemies)
                if (nx, ny) in blocking_cells:
                    # In AW, you generally cannot move THROUGH enemies at all.
                    # Stealth/BlackBombs are exceptions but rare.
                    cost = 999 
                
                if cost <= current_mp:
                    new_mp = current_mp - cost
                    
                    # If we found a better path to this cell, update and re-queue
                    if new_mp > visited.get((nx, ny), -1):
                        visited[(nx, ny)] = new_mp
                        valid_destinations.add((nx, ny))
                        queue.append((nx, ny, new_mp))
                        
    return valid_destinations

def calculate_damage(attacker_type, defender_type, attacker_hp, defender_hp, defender_terrain, rules):
    """
    Calculates expected damage percentage.
    attacker_hp: 0-10 (or 0-100)
    defender_hp: 0-10 (or 0-100)
    defender_terrain: Terrain object or type string (for defense stars)
    rules: The full rules.json object
    """
    # Normalize HP to 0-10 scale
    a_hp = attacker_hp if attacker_hp <= 10 else attacker_hp / 10
    d_hp = defender_hp if defender_hp <= 10 else defender_hp / 10
    
    # Get base damage
    matchups = rules.get("matchups", {})
    base_dmg = matchups.get(attacker_type, {}).get(defender_type, 0)
    
    if base_dmg == 0:
        # Check if maybe there's a reverse mapping or general class?
        # For now assume 0 means can't attack or negligible
        return 0
        
    # Get Terrain Defense
    terrain_stars = 0
    if isinstance(defender_terrain, dict):
        t_type = get_terrain_type(defender_terrain)
    else:
        t_type = defender_terrain
        
    terrain_stars = rules.get("terrain_defense", {}).get(t_type, 0)
    # Air units generally don't get terrain defense unless specified (AWBW rules vary slightly but standard is No)
    # Actually air units in AW2/AWBW don't get terrain stars.
    defender_unit_type = rules.get("units", {}).get(defender_type, {}).get("type", "ground")
    if defender_unit_type == "air":
        terrain_stars = 0
        
    # CO Modifier application (Simplified)
    # Ideally, we pass in the attacker/defender CO objects.
    # For now, let's just use base damage as requested, or maybe we can update the signature later.
    
    # Attack Power
    attack_power = base_dmg * math.ceil(a_hp) / 10.0 # Standard is Ceil(HP) for offense
    
    # Defense Factor
    # Each star is 10% defense. (standard)
    defense_factor = (100 - (terrain_stars * 10)) / 100.0
    
    final_damage = attack_power * defense_factor
    
    # Rounding? AWBW truncates usually.
    return round(final_damage, 1)

def calculate_threats(my_units, enemy_units, game_map_grid):
    """
    Returns a list of tactical opportunities.
    For each my_unit, finds reachable enemy_units.
    """
    # Parse map dimensions
    height = len(game_map_grid)
    width = len(game_map_grid[0]) if height > 0 else 0
    
    opportunities = []
    
    for u in my_units:
        # Simplification: Use standard ranges from rules.json or passed in?
        # For now, hardcode or infer.
        # This function might need more context.
        pass
    
    return opportunities


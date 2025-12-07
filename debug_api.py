import sys
import traceback
import os
# Mock Flask bits
def jsonify(d): return str(d)
def Response(t, mimetype): return t

try:
    from map_converter import parse_map_csv
    from unit_converter import fetch_units
    from context_generator import generate_context
    from fetch_map import fetch_awbw_map
    from fetch_game_metadata import fetch_game_metadata
    
    game_id = 1548776
    print(f"Debugging game {game_id}...")
    
    # 1. Metadata
    print("Fetching metadata...")
    metadata = fetch_game_metadata(game_id)
    if not metadata:
        print("Metadata fetch failed")
        sys.exit(1)
    print(f"Metadata keys: {metadata.keys()}")
    
    # 2. Map ID
    # We skip the scraping part and hardcode for debug if needed, but let's verify scraping
    import requests
    import re
    print("Fetching Map ID...")
    html = requests.get(f"https://awbw.amarriner.com/game.php?games_id={game_id}").text
    m_map = re.search(r"maps_id=(\d+)", html)
    if not m_map:
        print("Map ID not found")
        sys.exit(1)
    map_id = int(m_map.group(1))
    print(f"Map ID: {map_id}")
    
    # 3. Map Data
    print("Fetching Map CSV...")
    raw_map = fetch_awbw_map(map_id)
    if not raw_map:
        print("Map CSV fetch failed")
        sys.exit(1)
        
    # 4. Parse Map
    print("Parsing Map...")
    ownership = metadata.get('ownership', {})
    print(f"Ownership count: {len(ownership)}")
    game_map = parse_map_csv(raw_map, ownership)
    print(f"Map parsed: {len(game_map)}x{len(game_map[0])}")
    
    # 5. Units
    print("Fetching Units...")
    units = fetch_units(game_id)
    print(f"Units parsed: {len(units)}")
    
    # 6. Context Gen
    print("Generating Context...")
    # Mock file writes
    import json
    with open("debug_map.json", "w") as f: json.dump(game_map, f)
    with open("debug_units.json", "w") as f: json.dump(units, f)
    
    # Need rules.json
    if not os.path.exists("rules.json"):
        with open("rules.json", "w") as f: f.write('{"co_stats":{},"matchups":{}}')
    
    context = generate_context("debug_map.json", "debug_units.json", "rules.json", metadata)
    print("Context Generated successfully (first 100 chars):")
    print(context[:100])

except Exception:
    traceback.print_exc()


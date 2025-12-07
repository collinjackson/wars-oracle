from flask import Flask, jsonify, Response
from map_converter import parse_map_csv
from unit_converter import fetch_units
from context_generator import generate_context
from fetch_map import fetch_awbw_map
from fetch_game_metadata import fetch_game_metadata
import requests
import re
import json
import os

app = Flask(__name__)
TMP_DIR = "/tmp"

@app.route('/api/game/<int:game_id>/context', methods=['GET'])
def get_context(game_id):
    try:
        # 1. Fetch Map ID
        game_url = f"https://awbw.amarriner.com/game.php?games_id={game_id}"
        html = requests.get(game_url).text
        m_map = re.search(r"maps_id=(\d+)", html)
        if not m_map: return jsonify({"error": "Could not determine Map ID"}), 404
        map_id = int(m_map.group(1))
        
        # 2. Fetch Data
        raw_map = fetch_awbw_map(map_id)
        if not raw_map: return jsonify({"error": "Could not fetch map data"}), 500
            
        # 3. Fetch Metadata (Teams, Funds, COs, Ownership)
        metadata = fetch_game_metadata(game_id)
        
        # 4. Parse Map (with Ownership injection)
        # We pass the ownership map to parse_map_csv if we modify it, OR we pass it to context_generator.
        # Let's pass it to parse_map_csv to bake it into the map grid.
        ownership = metadata.get('ownership', {})
        game_map = parse_map_csv(raw_map, ownership)
        
        units = fetch_units(game_id)
        
        map_path = os.path.join(TMP_DIR, "map.json")
        units_path = os.path.join(TMP_DIR, "units.json")
        rules_path = "rules.json"
        
        with open(map_path, "w") as f: json.dump(game_map, f)
        with open(units_path, "w") as f: json.dump(units, f)
        
        context_text = generate_context(map_path, units_path, rules_path, metadata)
        
        return Response(context_text, mimetype='text/plain')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Wars Oracle Active. Use /api/game/<id>/context"

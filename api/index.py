from flask import Flask, jsonify, Response, request, send_file
import sys
import os

# Add current directory to path so we can import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from map_converter import parse_map_csv
from unit_converter import fetch_units
from context_generator import generate_context
from fetch_map import fetch_awbw_map
from fetch_game_metadata import fetch_game_metadata
from analyzer import GameAnalyzer
import requests
import re
import json
import os

app = Flask(__name__)
TMP_DIR = "/tmp"

def get_rules():
    with open("rules.json") as f: return json.load(f)

@app.route('/api/game/<int:game_id>/context', methods=['GET'])
def get_context(game_id):
    try:
        player_id = request.args.get('player_id')
        username = request.args.get('username')
        
        game_url = f"https://awbw.amarriner.com/game.php?games_id={game_id}"
        html = requests.get(game_url).text
        m_map = re.search(r"maps_id=(\d+)", html)
        if not m_map: return jsonify({"error": "Could not determine Map ID"}), 404
        map_id = int(m_map.group(1))
        
        raw_map = fetch_awbw_map(map_id)
        if not raw_map: return jsonify({"error": "Could not fetch map data"}), 500
            
        metadata = fetch_game_metadata(game_id)
        ownership = metadata.get('ownership', {})
        game_map = parse_map_csv(raw_map, ownership)
        units = fetch_units(game_id)
        
        target_slot = None
        if player_id:
            for team in metadata['teams'].values():
                for p in team['players']:
                    if str(p['id']) == str(player_id): target_slot = p['slot']; break
        elif username:
            for team in metadata['teams'].values():
                for p in team['players']:
                    if p['username'].lower() == username.lower(): target_slot = p['slot']; break
        
        map_path = os.path.join(TMP_DIR, "map.json")
        units_path = os.path.join(TMP_DIR, "units.json")
        rules_path = "rules.json"
        
        with open(map_path, "w") as f: json.dump(game_map, f)
        with open(units_path, "w") as f: json.dump(units, f)
        
        context_text = generate_context(map_path, units_path, rules_path, metadata, target_slot)
        
        return Response(context_text, mimetype='text/plain')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/game/<int:game_id>/players', methods=['GET'])
def get_players(game_id):
    try:
        metadata = fetch_game_metadata(game_id)
        if not metadata: return jsonify({"error": "Could not fetch metadata"}), 500
        players = []
        for team_name, team_data in metadata['teams'].items():
            for p in team_data['players']:
                players.append({
                    "username": p['username'],
                    "id": p['id'],
                    "team": team_name,
                    "co": p['co'],
                    "co_image_url": p.get("co_image_url"),
                    "eliminated": p['eliminated']
                })
        return jsonify(players)
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/rules/damage', methods=['GET'])
def get_damage_rules():
    r = get_rules()
    return jsonify(r.get('matchups', {}))

@app.route('/api/rules/terrain', methods=['GET'])
def get_terrain_rules():
    r = get_rules()
    return jsonify(r.get('terrain_defense', {}))

@app.route('/api/game/<int:game_id>/analysis', methods=['GET'])
def get_analysis(game_id):
    try:
        player_id = request.args.get('player_id')
        username = request.args.get('username')
        
        game_url = f"https://awbw.amarriner.com/game.php?games_id={game_id}"
        html = requests.get(game_url).text
        m_map = re.search(r"maps_id=(\d+)", html)
        if not m_map: return jsonify({"error": "Could not determine Map ID"}), 404
        map_id = int(m_map.group(1))
        
        raw_map = fetch_awbw_map(map_id)
        if not raw_map: return jsonify({"error": "Could not fetch map data"}), 500
            
        metadata = fetch_game_metadata(game_id)
        ownership = metadata.get('ownership', {})
        game_map = parse_map_csv(raw_map, ownership)
        units = fetch_units(game_id)
        
        target_slot = None
        if player_id:
            for team in metadata['teams'].values():
                for p in team['players']:
                    if str(p['id']) == str(player_id): target_slot = p['slot']; break
        elif username:
            for team in metadata['teams'].values():
                for p in team['players']:
                    if p['username'].lower() == username.lower(): target_slot = p['slot']; break
                    
        if target_slot is None:
             return jsonify({"error": "Could not identify target player slot"}), 400

        map_path = os.path.join(TMP_DIR, "map.json")
        units_path = os.path.join(TMP_DIR, "units.json")
        rules_path = "rules.json"
        
        with open(map_path, "w") as f: json.dump(game_map, f)
        with open(units_path, "w") as f: json.dump(units, f)
        
        # Initialize Analyzer
        analyzer = GameAnalyzer(map_path, units_path, rules_path, metadata)
        analysis = analyzer.get_full_analysis(target_slot)
        
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return jsonify({"status": "Wars Oracle API Running", "endpoints": ["/api/game/<id>/analysis", "/api/game/<id>/context"]})

if __name__ == '__main__':
    app.run(port=5328)

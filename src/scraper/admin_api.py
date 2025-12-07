# src/api/admin_api.py
from flask import Flask, request, jsonify
from datetime import datetime
import json
import logging

# Assuming scraper_config is correctly configured for pymongo and .env
# We use relative import, but need to run with `python -m src.api.admin_api` for local testing.
from ..scraper.scraper_config import get_mongo_client 

# Initialize Flask app (required for routing structure, even in serverless context)
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function to get database connection
def get_db():
    client = get_mongo_client()
    if client:
        return client['sports_schedule']
    return None

@app.route('/api/admin/unvalidated', methods=['GET'])
def get_unvalidated_games():
    """
    Endpoint to retrieve games lacking Layer 2 RSN mapping (is_validated: False).
    This populates the Admin Page's default view.
    """
    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    # Retrieve games from both collections that require validation
    try:
        nba_games = list(db['schedules'].find(
            {"is_validated": False, "regional_broadcast_placeholder": {"$ne": ""}}, 
            {"_id": 1, "sport": 1, "away_team": 1, "home_team": 1, "national_broadcasts": 1, "regional_broadcast_placeholder": 1, "date_str": 1, "time_str_et": 1}
        ).limit(50)) # Limit to 50 for a manageable queue

        epl_games = list(db['epl_schedules'].find(
            {"is_validated": False}, 
            {"_id": 1, "sport": 1, "away_team": 1, "home_team": 1, "national_broadcasts": 1, "date_str": 1, "time_str_et": 1}
        ).limit(50))
        
        # Merge, convert ObjectIds to strings, and return
        all_games = nba_games + epl_games
        for game in all_games:
            game['_id'] = str(game['_id'])

        return jsonify(all_games), 200

    except Exception as e:
        logger.error(f"Error retrieving unvalidated games: {e}")
        return jsonify({"error": "Internal server error during data retrieval"}), 500


@app.route('/api/admin/map', methods=['POST'])
def add_or_update_dma_map():
    """
    Endpoint to add or update a new Layer 2 DMA/RSN mapping rule.
    This handles the crucial proprietary data input.
    """
    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.json
        if not all(k in data for k in ['dma_code', 'team', 'sport', 'channel']):
            return jsonify({"error": "Missing required fields in rule data"}), 400

        rule = {
            "dma_code": data['dma_code'].upper(),
            "team_name": data['team'].strip(),
            "sport": data['sport'].upper(),
            "local_channel": data['channel'].strip(),
            "last_updated": datetime.utcnow().isoformat()
        }

        # Use the combination of DMA, Team, and Sport as the unique key for the rule
        result = db['dma_rules'].update_one(
            {'dma_code': rule['dma_code'], 'team_name': rule['team_name'], 'sport': rule['sport']},
            {'$set': rule},
            upsert=True
        )

        logger.info(f"Rule updated/inserted for {rule['dma_code']}/{rule['team_name']}. ID: {str(result.upserted_id or result.modified_count)}")
        return jsonify({"success": True, "message": "DMA Rule saved.", "id": str(result.upserted_id or result.modified_count)}), 200

    except Exception as e:
        logger.error(f"Error processing DMA map update: {e}")
        return jsonify({"error": "Internal server error during rule update"}), 500


# NOTE: You would add /api/admin/dma-map GET endpoint and a game validation endpoint here later.

if __name__ == '__main__':
    # For local development testing only
    app.run(host='0.0.0.0', port=5000, debug=True)
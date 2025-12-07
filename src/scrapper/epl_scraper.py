# src/scraper/epl_scraper.py

import requests
from bs4 import BeautifulSoup
from .scraper_config import get_mongo_client
import re # We'll use regular expressions for text cleanup

# We choose a US-centric site that clearly lists the TV schedule
EPL_SCHEDULE_URL = "https://worldsoccertalk.com/premier-league-tv-schedule/"

def fetch_schedule_page(url):
    """Fetches the HTML content from the target URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 
        print(f"Successfully fetched {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching EPL page: {e}")
        return None

def parse_epl_schedule(html_content):
    """
    Parses the EPL schedule page, specifically looking for structured data blocks.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    games_data = []

    # Target: We look for specific sections or elements holding game listings (e.g., list items, divs)
    # Based on similar schedule sites, let's look for common list item wrappers or day blocks.

    # This example targets the list items commonly found on schedule pages (adjust class as needed for the final URL)
    # Note: If the target site uses a simple HTML <ul> or <ol> list for games, this works well.
    game_list_items = soup.find_all('li', class_=re.compile(r'fixture|game-list-item')) 
    
    if not game_list_items:
        # Fallback to a wider search if no specific list class is found
        print("Falling back to generic paragraph search for EPL fixtures...")
        # Since search results showed simple lines like 'Time. Game / TV' (Source 1.5, 1.7), 
        # a more robust method might be necessary to locate the specific section headers.
        
        # Let's pivot to searching for the 'Matchweek' headers and then processing the text list below it.
        
        # We will stop here to avoid writing unreliable parsing logic without the target structure.
        # This highlights the importance of the initial data structure inspection.
        print("Manual inspection of HTML from target URL is necessary to define selectors.")
        return []

    # --- Sample logic if we were targeting a simple list (hypothetical, needs verification) ---
    for item in game_list_items:
        # Assume a simple text pattern: "Date. Time. Team A vs Team B. Channel(s)"
        game_text = item.text.strip()
        
        # Simple split logic (highly brittle, requires adjustment)
        parts = [p.strip() for p in game_text.split('.') if p.strip()]
        
        if len(parts) >= 3:
            # Example Data Structure from search results: 'Aston Villa vs. Arsenal (English Premier League) USA Network'
            matchup_pattern = re.search(r'([\w\s]+)\s+vs\.\s+([\w\s]+)', game_text)
            broadcast_pattern = re.search(r'\)\s+([\w\s,]+)$', game_text)
            
            if matchup_pattern:
                away_team = matchup_pattern.group(1).strip()
                home_team = matchup_pattern.group(2).strip()
            else:
                continue

            # Extract date/time from the first part or use regex
            time_str = parts[0] 
            date_str = parts[1]
            
            # Simple broadcast extraction
            broadcasts = broadcast_pattern.group(1).split(',') if broadcast_pattern else []

            games_data.append({
                'game_id': f"{away_team.replace(' ', '')}_{home_team.replace(' ', '')}_{date_str.replace(' ', '')}",
                'sport': 'EPL',
                'date_str': date_str,
                'time_str_et': time_str, 
                'away_team': away_team,
                'home_team': home_team,
                'national_broadcasts': [b.strip() for b in broadcasts if b.strip()],
                'regional_broadcast_placeholder': '', # EPL is typically uniform national US broadcasts
                'regional_map': {}, 
                'is_validated': False
            })

    return games_data

def main():
    """Runs the EPL scraper and updates MongoDB."""
    print("--- Starting EPL Tier 1 Scraper ---")
    
    # 1. Connect
    db = get_mongo_client()
    if not db:
        return
        
    # 2. Fetch
    html = fetch_schedule_page(EPL_SCHEDULE_URL)
    
    # 3. Parse
    games = parse_epl_schedule(html)
    print(f"Parsed {len(games)} EPL games.")
    
    if games:
        # 4. Load (To MongoDB) - Use 'epl_schedules' collection
        schedule_collection = db['epl_schedules']
        
        # Insert or Update (Upsert) Logic
        for game in games:
            schedule_collection.update_one(
                {'game_id': game['game_id']}, 
                {'$set': game},               
                upsert=True                  
            )
        print(f"Successfully processed {len(games)} EPL games in MongoDB.")
    
    print("--- EPL Scraper Finished ---")

if __name__ == "__main__":
    main()
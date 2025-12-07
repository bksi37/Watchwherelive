# src/scraper/nba_scraper.py

import requests
from bs4 import BeautifulSoup
from .scraper_config import get_mongo_client # Import the config file

# Target URL for NBA Schedule (Example from search results, check year)
# We will target the main schedule page for a given season/month.
NBA_SCHEDULE_URL = "https://www.basketball-reference.com/leagues/NBA_2026_games.html"

def fetch_schedule_page(url):
    """Fetches the HTML content from the target URL."""
    # Use a User-Agent header to mimic a real browser and avoid blocks
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"Successfully fetched {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        return None

def parse_nba_schedule(html_content):
    """
    Parses the NBA.com HTML content to extract core schedule data,
    targeting specific CSS class names.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    games_data = []

    # 1. Find all Schedule Day containers
    # The container holding all games for a specific date
    day_containers = soup.find_all('div', class_='ScheduleDay_sd__GFE_w')
    
    if not day_containers:
        print("Could not find schedule day containers (class='ScheduleDay_sd__GFE_w').")
        return []

    for day_container in day_containers:
        # Extract the Date (e.g., "Saturday, December 6")
        date_header = day_container.find('h4', class_='ScheduleDay_sdDay__3s2Xt')
        if not date_header:
            continue
        date_str = date_header.text.strip()
        
        # 2. Find all Game Containers within that day
        game_blocks = day_container.find_all('div', class_='ScheduleGame_sg__RmD9I')
        
        for game_block in game_blocks:
            # --- Extract Teams ---
            # Find all anchor links which contain team names and link to team pages
            team_links = game_block.find_all('a', class_='Link_styled__okbXW')
            
            if len(team_links) < 2:
                # Skip games with missing team data (e.g., TBD In-Season Tournament games)
                away_team = "TBD"
                home_team = "TBD"
                # If both are TBD, use the date and game type for the ID
                game_id = f"{date_str.replace(',','').replace(' ', '')}_TBD_Game"
                
                # Check for Emirate Cup games (TBD vs TBD)
                label = game_block.find('p', class_='ScheduleGame_sgLabel__wkprj')
                if label and "NBA Cup" in label.text:
                    home_team = game_block.find_all('p', class_='ScheduleGame_sgFigtext__gYud6')[-1].text.strip().replace(':', '')
                    away_team = game_block.find_all('p', class_='ScheduleGame_sgFigtext__gYud6')[-2].text.strip().replace(':', '')
                    game_id = f"{date_str.replace(',','').replace(' ', '')}_{away_team.replace(' ', '')}_{home_team.replace(' ', '')}"
                elif away_team == "TBD":
                    continue # Skip TBD games without cup info
            else:
                # The teams are typically the first two relevant links
                away_team = team_links[0].text.strip()
                home_team = team_links[1].text.strip()
                game_id = f"{date_str.replace(',','').replace(' ', '')}_{away_team.replace(' ', '')}_{home_team.replace(' ', '')}"
            
            # --- Extract Time & Status ---
            status_span = game_block.find('span', class_='ScheduleStatusText_base__Jgvjb')
            time_status = status_span.text.strip() if status_span else 'Final/TBD'
            
            # --- Extract Broadcasts (The Tier 1 value) ---
            broadcasters_div = game_block.find('div', class_='Broadcasters_base__Wet1u')
            
            tier1_broadcasts = []
            regional_tv = ""
            
            if broadcasters_div:
                # Look for broadcast image logos (NBA TV, Prime Video, Peacock, ABC/ESPN)
                for img in broadcasters_div.find_all('img', class_='Broadcasters_icon__82MTV'):
                    title = img.get('title')
                    if title and title not in tier1_broadcasts:
                        tier1_broadcasts.append(title)
                
                # Look for Regional TV Text (FanDuel Sports Network - Oklahoma, etc.)
                # This is the crucial non-League Pass data point.
                tv_p = broadcasters_div.find('p', class_='Broadcasters_title__B1dGd', string='TV')
                if tv_p:
                    # Check the immediate sibling for the actual regional network name
                    regional_link_container = tv_p.find_next_sibling('p')
                    if regional_link_container:
                        regional_link = regional_link_container.find('a', class_='Broadcasters_tv__AIeZb')
                        regional_span = regional_link_container.find('span', class_='Broadcasters_tv__AIeZb')
                        
                        if regional_link:
                            regional_tv = regional_link.text.strip()
                        elif regional_span:
                            regional_tv = regional_span.text.strip() # Covers FDSNOK/KWTV example

                # Clean up/Normalize broadcasters list
                if "LEAGUE PASS" in tier1_broadcasts:
                    tier1_broadcasts.remove("LEAGUE PASS")
                
            games_data.append({
                '_id': game_id,
                'sport': 'NBA',
                'date_str': date_str,
                'time_status': time_status,
                'away_team': away_team,
                'home_team': home_team,
                'national_broadcasts': tier1_broadcasts,
                'regional_broadcast_placeholder': regional_tv, # Needs Layer 2 lookup later
                'regional_map': {},
                'is_validated': False
            })

    return games_data
  
def main():
    """Runs the NBA scraper and updates MongoDB."""
    print("--- Starting NBA Tier 1 Scraper ---")
    
    db = get_mongo_client()
    if not db:
        return
        
    html = fetch_schedule_page(NBA_SCHEDULE_URL)
    games = parse_nba_schedule(html)
    
    if games:
        schedule_collection = db['schedules']
        
        # Insert or Update (Upsert) Logic: Prevents duplicate games
        for game in games:
            schedule_collection.update_one(
                {'game_id': game['game_id']}, # Query to find existing game
                {'$set': game},               # Data to set/update
                upsert=True                   # Insert if not found
            )
        print(f"Successfully processed {len(games)} NBA games in MongoDB.")
    
    print("--- NBA Scraper Finished ---")

if __name__ == "__main__":
    main()
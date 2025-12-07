import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient # For connecting to MongoDB

# --- Configuration ---
# IMPORTANT: Replace with your actual MongoDB connection string
MONGO_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/"
DB_NAME = "watchwherelive_db"

# Target URL for NBA Schedule (Example - may need adjustment)
# We choose a page that renders the data in standard HTML
NBA_SCHEDULE_URL = "https://www.basketball-reference.com/leagues/NBA_2026_games.html" 
# Note: Use the current/next season year

def get_mongo_client():
    """Returns a MongoDB client connection."""
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

def fetch_schedule_page(url):
    """Fetches the HTML content from the target URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Successfully fetched {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        return None

def parse_nba_schedule(html_content):
    """
    Parses the HTML to extract core schedule data.
    THIS IS THE PRIMARY CODE YOU WILL NEED TO CUSTOMIZE.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # --- Custom Parsing Logic Starts Here ---
    # We will look for the main table (often with an id like 'schedule')
    schedule_table = soup.find('table', id='schedule') 
    
    if not schedule_table:
        print("Could not find the schedule table. Check the target URL's HTML.")
        return []

    games_data = []
    # Find all rows (tr) in the table body (tbody)
    for row in schedule_table.find('tbody').find_all('tr'):
        # Skip header/separator rows
        if 'class' in row.attrs and 'thead' in row.attrs['class']:
            continue
            
        cols = row.find_all(['td', 'th']) # Find all cells in the row
        if len(cols) < 7: # Ensure we have enough columns for a game
            continue
            
        # Example extraction based on common table structure:
        game = {
            'date_utc': cols[0].text.strip(),
            'time_local': cols[1].text.strip(), # We'll standardize this later
            'away_team': cols[2].text.strip(),
            'home_team': cols[4].text.strip(),
            'national_broadcasts': cols[6].text.strip() if len(cols) > 6 else 'N/A',
            'sport': 'NBA',
            # Set initial Layer 2 data placeholders:
            'regional_broadcast_map': {},
            'is_validated': False
        }
        games_data.append(game)

    return games_data

def main():
    """Main function to run the scraper and insert data."""
    print("--- Starting NBA Tier 1 Scraper ---")
    
    # 1. Fetch
    html = fetch_schedule_page(NBA_SCHEDULE_URL)
    
    # 2. Parse
    games = parse_nba_schedule(html)
    print(f"Parsed {len(games)} games.")
    
    if games:
        # 3. Load (To MongoDB)
        # Note: We skip the actual MongoDB connection for now to test parsing first.
        # db = get_mongo_client()
        # schedule_collection = db['schedules']
        # result = schedule_collection.insert_many(games)
        
        print(f"First 5 parsed games (pre-MongoDB):")
        for game in games[:5]:
            print(game)
    
    print("--- Scraper Finished ---")

if __name__ == "__main__":
    main()

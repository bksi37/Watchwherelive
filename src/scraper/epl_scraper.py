# src/scraper/epl_scraper.py
# IMPORTANT: Requires Playwright to be installed and browsers downloaded.

import requests
from bs4 import BeautifulSoup
from .scraper_config import get_mongo_client
import re
from datetime import datetime, timezone
import logging
import asyncio
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reliable US-centric source for Premier League TV schedule
EPL_SCHEDULE_URL = "https://worldsoccertalk.com/premier-league-tv-schedule/"

async def fetch_schedule_page(url: str) -> str | None:
    """Fetches the fully rendered HTML content using Playwright."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navigate and wait for the page to settle
            await page.goto(url)

            # Wait for the specific H4 element that contains the game title to appear
            # This ensures the JavaScript has run and loaded the schedule data
            await page.wait_for_selector('h4.text-stvsMatchTitle', timeout=20000) 

            html_content = await page.content()
            await browser.close()
            logger.info(f"Successfully fetched and rendered EPL schedule from {url}")
            return html_content
    except Exception as e:
        logger.error(f"Playwright failed to load or find EPL schedule content: {e}")
        return None

def normalize_team_name(name: str) -> str:
    """Standardize common team name variations."""
    name = name.strip()
    replacements = {
        'Spurs': 'Tottenham Hotspur', 'Man Utd': 'Manchester United', 'Man United': 'Manchester United',
        'Man City': 'Manchester City', 'Chelsea FC': 'Chelsea', 'Liverpool FC': 'Liverpool',
        'Arsenal FC': 'Arsenal', 'Brighton & Hove Albion': 'Brighton', 'Newcastle Utd': 'Newcastle United',
        'Wolves': 'Wolverhampton Wanderers', 'West Ham Utd': 'West Ham United', 'Crystal Palace FC': 'Crystal Palace',
        'AFC Bournemouth': 'Bournemouth', 'Nottingham Forest FC': 'Nottingham Forest',
    }
    # Remove common suffixes first
    name = re.sub(r'\s*(AFC|FC|United|City|Town)\b', '', name, flags=re.IGNORECASE).strip()
    return replacements.get(name, name)


def parse_epl_schedule(html_content: str | None):
    """
    Parse the World Soccer Talk EPL TV schedule page using Playwright's rendered HTML.
    Uses the stable selectors confirmed from the user's HTML snippet.
    """
    if not html_content:
        logger.warning("No HTML content provided to parser.")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    games_data = []

    # 1. Find all date headers (The anchor for schedule sections)
    date_headers = soup.find_all('h3', class_='text-stvsDate')

    if not date_headers:
        logger.warning("No date headers found (class='text-stvsDate'). Check page structure.")
        return []

    for date_header in date_headers:
        raw_date = date_header.get_text(strip=True)
        if not raw_date:
            continue

        # 2. Find the immediate next sibling which contains the games (The <ul>)
        game_list = date_header.find_next_sibling('ul')
        if not game_list:
            logger.debug(f"No game list found after date: {raw_date}")
            continue

        # 3. Iterate over each list item (<li>)
        for item in game_list.find_all('li', recursive=False):
            try:
                # --- Time ---
                time_elem = item.find('span', class_='text-stvsMatchHour')
                time_str = time_elem.get_text(strip=True) if time_elem else "TBD"

                # --- Match Title (H4) ---
                title_elem = item.find('h4', class_='text-stvsMatchTitle')
                if not title_elem:
                    continue
                title_text = title_elem.get_text(strip=True)

                # Extract teams using regex: "Team A vs. Team B (..."
                match = re.search(r'(.+?)\s+vs?\.?\s+(.+?)\s+\(', title_text, re.IGNORECASE)
                if not match:
                    logger.debug(f"Could not parse matchup from: {title_text}")
                    continue

                away_team = normalize_team_name(match.group(1))
                home_team = normalize_team_name(match.group(2))

                # --- Broadcasters (Robust Logic using <a> tags) ---
                broadcasts = []
                # Find the container for provider links (using the known fragile class as a starting point)
                broadcast_container = item.find('div', class_='flex flex-wrap gap-[3px_5px]') 
                
                if broadcast_container:
                    # Target the specific inner container for provider text
                    for provider_div in broadcast_container.find_all('div', class_='text-stvsProviderLink'):
                        unique_providers = set()
                        # Scrape the text from all <a> tags inside, handling duplicates
                        for link in provider_div.find_all('a'):
                            provider_name = link.get_text(strip=True)
                            if provider_name:
                                unique_providers.add(provider_name)
                        
                        broadcasts.extend(list(unique_providers))
                
                # --- Cleaning and Deduplication ---
                national_broadcasts = []
                # Filter out known streaming services that aren't the primary network
                FILTERED_PROVIDERS = {'DirecTV Stream', 'Sling', 'fubo', 'YouTube TV', 'Hulu', 'Paramount+'}
                
                for b in broadcasts:
                    if b not in FILTERED_PROVIDERS:
                        provider_name = b.replace('Online', '').replace('streaming', '').strip()
                        if provider_name:
                            national_broadcasts.append(provider_name)

                national_broadcasts = sorted(set(national_broadcasts))
                
                # --- Generate unique game ID ---
                date_key = re.sub(r'\W+', '', raw_date.lower())
                game_id = f"EPL_{away_team.replace(' ', '')}_vs_{home_team.replace(' ', '')}_{date_key}"

                games_data.append({
                    'game_id': game_id,
                    'sport': 'EPL',
                    'league': 'Premier League',
                    'date_str': raw_date,
                    'time_str_et': time_str,
                    'away_team': away_team,
                    'home_team': home_team,
                    'matchup': f"{away_team} vs {home_team}",
                    'national_broadcasts': national_broadcasts,
                    'regional_broadcast_placeholder': '',
                    'regional_map': {},
                    'is_validated': False,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                })

            except Exception as e:
                logger.error(f"Error parsing game item: {e}")
                continue

    logger.info(f"Successfully parsed {len(games_data)} EPL games.")
    return games_data


async def main_async():
    """Asynchronous main function to run the scraper logic."""
    logger.info("=== Starting EPL Schedule Scraper ===")

    # Connect to MongoDB
    client = get_mongo_client()
    # FIX: Use 'is None' check
    if client is None: 
        logger.error("Could not connect to MongoDB. Exiting.")
        return

    db = client['watchwherelive_db'] 
    collection = db['schedules'] 

    # Fetch page using the async function
    html = await fetch_schedule_page(EPL_SCHEDULE_URL)
    if not html:
        logger.error("Failed to retrieve schedule page. Aborting.")
        return

    # Parse games (This part remains synchronous)
    games = parse_epl_schedule(html)

    if not games:
        logger.warning("No games parsed. Aborting MongoDB update.")
        return

    # Upsert into MongoDB
    upserted_count = 0
    for game in games:
        result = collection.update_one(
            {'game_id': game['game_id']},
            {'$set': game},
            upsert=True
        )
        if result.upserted_id or result.modified_count:
            upserted_count += 1

    logger.info(f"Successfully upserted {upserted_count}/{len(games)} EPL games into MongoDB.")
    logger.info("=== EPL Scraper Completed ===\n")

def main():
    """Synchronous entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
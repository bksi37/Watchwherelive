# src/scraper/nba_scraper.py
# IMPORTANT: Requires Playwright to be installed and browsers downloaded.

import requests
from bs4 import BeautifulSoup
from .scraper_config import get_mongo_client
import asyncio
from playwright.async_api import async_playwright
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Target URL for NBA Schedule
NBA_SCHEDULE_URL = "https://www.nba.com/schedule"

async def fetch_schedule_page(url: str) -> str | None:
    """Fetches the fully rendered HTML content using Playwright."""
    try:
        async with async_playwright() as p:
            # Launch a headless Chromium browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Navigate to the URL
            await page.goto(url)

            # Wait for a key schedule element to ensure the page is fully rendered
            # 'ScheduleDay_sd__GFE_w' is the class from your parser logic
            await page.wait_for_selector('div.ScheduleDay_sd__GFE_w', timeout=30000) 

            # Get the full, rendered HTML content
            html_content = await page.content()

            await browser.close()
            logger.info(f"Successfully fetched and rendered schedule from {url}")
            return html_content
    except Exception as e:
        logger.error(f"Playwright failed to load or find NBA schedule content: {e}")
        return None

def parse_nba_schedule(html_content):
    """
    Parses the NBA.com HTML content to extract core schedule data.
    The selectors here rely on the dynamic content loaded by Playwright.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    games_data = []

    # 1. Find all Schedule Day containers
    day_containers = soup.find_all('div', class_='ScheduleDay_sd__GFE_w')
    
    if not day_containers:
        logger.warning("Could not find NBA schedule day containers (class='ScheduleDay_sd__GFE_w').")
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
            team_links = game_block.find_all('a', class_='Link_styled__okbXW')
            
            if len(team_links) < 2:
                # Handle TBD games (simplified handling)
                away_team, home_team = "TBD", "TBD"
                game_id = f"{date_str.replace(',','').replace(' ', '')}_TBD_Game"
                
                # Attempt to find teams in non-standard NBA Cup games
                label = game_block.find('p', class_='ScheduleGame_sgLabel__wkprj')
                if label and "NBA Cup" in label.text:
                    # Logic to find cup teams
                    figures = game_block.find_all('p', class_='ScheduleGame_sgFigtext__gYud6')
                    if len(figures) >= 2:
                        home_team = figures[-1].text.strip().replace(':', '')
                        away_team = figures[-2].text.strip().replace(':', '')
                        game_id = f"{date_str.replace(',','').replace(' ', '')}_{away_team.replace(' ', '')}_{home_team.replace(' ', '')}"
                elif away_team == "TBD":
                    continue # Skip general TBD games
            else:
                away_team = team_links[0].text.strip()
                home_team = team_links[1].text.strip()
                game_id = f"{date_str.replace(',','').replace(' ', '')}_{away_team.replace(' ', '')}_{home_team.replace(' ', '')}"
            
            # --- Extract Time & Status ---
            status_span = game_block.find('span', class_='ScheduleStatusText_base__Jgvjb')
            time_status = status_span.text.strip() if status_span else 'Final/TBD'
            
            # --- Extract Broadcasts ---
            broadcasters_div = game_block.find('div', class_='Broadcasters_base__Wet1u')
            tier1_broadcasts = []
            regional_tv = ""
            
            if broadcasters_div:
                # Extract National Logos (NBA TV, ESPN, etc.)
                for img in broadcasters_div.find_all('img', class_='Broadcasters_icon__82MTV'):
                    title = img.get('title')
                    if title and title not in tier1_broadcasts and title != "LEAGUE PASS":
                        tier1_broadcasts.append(title)
                
                # Extract Regional TV Text
                tv_p = broadcasters_div.find('p', class_='Broadcasters_title__B1dGd', string='TV')
                if tv_p:
                    regional_link_container = tv_p.find_next_sibling('p')
                    if regional_link_container:
                        regional_elem = regional_link_container.find(['a', 'span'], class_='Broadcasters_tv__AIeZb')
                        if regional_elem:
                            regional_tv = regional_elem.text.strip()

            games_data.append({
                '_id': game_id,
                'sport': 'NBA',
                'date_str': date_str,
                'time_status': time_status,
                'away_team': away_team,
                'home_team': home_team,
                'national_broadcasts': tier1_broadcasts,
                'regional_broadcast_placeholder': regional_tv,
                'regional_map': {},
                'is_validated': False
            })

    logger.info(f"Successfully parsed {len(games_data)} NBA games.")
    return games_data
 
async def main_async():
    """Asynchronous main function to run the scraper logic."""
    logger.info("--- Starting NBA Tier 1 Scraper ---")
    
    db = get_mongo_client()
    # FIX: Use 'is None' check
    if db is None:
        logger.error("Could not connect to MongoDB. Exiting.")
        return
        
    html = await fetch_schedule_page(NBA_SCHEDULE_URL)
    if not html:
        logger.error("Failed to retrieve schedule page. Aborting.")
        return

    games = parse_nba_schedule(html)
    
    if games:
        schedule_collection = db['schedules']
        
        # Insert or Update (Upsert) Logic
        for game in games:
            schedule_collection.update_one(
                {'game_id': game['game_id']}, # Query to find existing game
                {'$set': game},               # Data to set/update
                upsert=True                   # Insert if not found
            )
        logger.info(f"Successfully processed {len(games)} NBA games in MongoDB.")
    
    logger.info("--- NBA Scraper Finished ---")

def main():
    """Synchronous entry point."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
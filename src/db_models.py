# --- MongoDB Data Structures (Conceptual/Example) ---

# 1. SCHEDULES Collection (The Core Schedule Data)
# This is populated by the scraper (run_scrape.py)
SCHEDULE_SCHEMA = {
    "_id": "Unique Game ID (e.g., LAL_GSW_20251210)",
    "sport": "NBA",
    "date_utc": "YYYY-MM-DD",
    "time_utc": "HH:MM:SS",
    "home_team": "Team Name (e.g., Los Angeles Lakers)",
    "away_team": "Team Name (e.g., Golden State Warriors)",
    "national_broadcasts": ["ESPN", "ABC", "TNT"], # Tier 1 Data
    "regional_broadcast_map": {
        # This is the Layer 2 Proprietary Data - Populated or verified by Admin
        "LA-DMA": "Spectrum SportsNet",
        "SF-DMA": "NBC Sports Bay Area",
        "NY-DMA": "MSG" 
    },
    "is_validated": False # Flag for the Admin Review Queue
}

# 2. USER_LOCATION_MAP Collection (Static Geo-Mapping)
# This is a static lookup table that maps a ZIP code to a TV market
LOCATION_SCHEMA = {
    "_id": "ZIP Code (e.g., 90210)",
    "dma_code": "LA-DMA",
    "state": "CA",
    "rsn_affiliations": {
        "NBA": "Spectrum SportsNet",
        "MLB": "SportsNet LA"
    }
}

# In a full application, you would use an ODM like Pydantic or MongoEngine here.
# For the MVP, these dictionaries serve as your documentation/schema.
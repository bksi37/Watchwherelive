# src/scraper/scraper_config.py
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# The script now securely retrieves the URI from the environment.
# Note: When deploying to AWS Lambda/Netlify Functions, you set this variable 
# in the cloud console, NOT via a .env file.
MONGO_URI = os.getenv("MONGO_URI") 
DB_NAME = "watchwherelive_db" # We will use this as the database name

def get_mongo_client():
    """Returns a MongoDB database object for the WatchWhereLive DB."""
    if not MONGO_URI:
        print("Error: MONGO_URI not found. Check your .env file or environment variables.")
        return None
        
    try:
        # Use the connection string to create the MongoClient
        client = MongoClient(MONGO_URI)
        
        # Ping the server to confirm a successful connection
        client.admin.command('ping') 
        print("MongoDB connection successful. Using database: 'watchwherelive_db'")
        return client[DB_NAME]
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None
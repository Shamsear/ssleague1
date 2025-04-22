import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Handle potential "postgres://" format from Render
    database_url = os.environ.get('DATABASE_URL') or 'postgresql://postgres:shamsear@localhost/auction_db'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INITIAL_BALANCE = 15000
    MINIMUM_BID = 10
    MAX_PLAYERS_PER_TEAM = 25
    POSITIONS = ['GK', 'CB', 'RB', 'LB', 'DMF', 'CMF', 'AMF', 'LMF', 'RMF', 'RWF', 'LWF', 'SS', 'CF']
    POSITION_GROUPS = ['CB-1', 'CB-2', 'DMF-1', 'DMF-2', 'CMF-1', 'CMF-2', 'AMF-1', 'AMF-2', 'CF-1', 'CF-2'] 
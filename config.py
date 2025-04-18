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
    POSITIONS = ['GK', 'CB', 'RB', 'LB', 'CMF', 'DMF', 'RMF', 'LMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF']
    
    # VAPID keys for web push notifications
    # In production, generate these keys using the pywebpush library
    # and store them securely in environment variables
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY') or 'your_vapid_private_key_here'
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY') or 'your_vapid_public_key_here'
    VAPID_CLAIMS = {
        "sub": "mailto:" + os.environ.get('VAPID_CONTACT_EMAIL', 'admin@example.com')
    } 
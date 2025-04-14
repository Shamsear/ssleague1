import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Fix for Render PostgreSQL connection
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url or 'postgresql://postgres:shamsear@localhost/auction_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INITIAL_BALANCE = 15000
    MINIMUM_BID = 10
    
    # VAPID keys for Web Push Notifications
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY') or 'HH0hKKKH2HUUk63N_64nnVkxYRc9CHRfBQ-6w50RGLBGxKP-eHPEgw'
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY') or 'BNTpP0jRXvXGlmXL2l7mqqcKJ-mE01m-QdBODLzd4gKBvYcGPKqAXV8lE1_1I5jpLkQ1nH3FfOWOMrWKhXQGV8M'
    VAPID_CLAIMS = {
        "sub": "mailto:admin@southsoccers.com"
    }
    
    POSITIONS = ['GK', 'CB', 'RB', 'LB', 'CMF', 'DMF', 'RMF', 'LMF', 'AMF', 'SS', 'CF'] 
    PLAYING_STYLES = ['Anchor Man', 'Box-to-Box', 'Creative Playmaker', 'Cross Specialist', 'Defensive Fullback', 
                      'Fox in the Box', 'Goal Poacher', 'Hole Player', 'Orchestrator', 
                      'Offensive Fullback', 'Prolific Winger', 'Target Man', 'The Destroyer', 'Build Up', 
                      'Classic No. 10', 'Defensive Goalkeeper', 'Offensive Goalkeeper'] 
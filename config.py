import os
from dotenv import load_dotenv
import re

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Handle Render PostgreSQL URL format
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INITIAL_BALANCE = 15000
    MINIMUM_BID = 10
    POSITIONS = ['GK', 'CB', 'RB', 'LB', 'CMF', 'DMF', 'RMF', 'LMF', 'AMF', 'SS', 'CF'] 
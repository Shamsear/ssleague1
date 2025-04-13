import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:shamsear@localhost/auction_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INITIAL_BALANCE = 15000
    MINIMUM_BID = 10
    POSITIONS = ['GK', 'CB', 'RB', 'LB', 'CMF', 'DMF', 'RMF', 'LMF', 'AMF', 'SS', 'CF'] 
import os
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Handle potential "postgres://" format from Render and remove invalid schema parameter
    database_url = os.environ.get('DATABASE_URL') or 'postgresql://postgres:password@localhost/auction_db'
    print(f"DEBUG: DATABASE_URL from env: {os.environ.get('DATABASE_URL')}")
    print(f"DEBUG: Final database_url: {database_url}")
    
    # Check if it's a Render PostgreSQL database
    if 'render.com' in database_url:
        print("DEBUG: Detected Render PostgreSQL database")
    elif 'supabase.co' in database_url:
        print("DEBUG: Detected Supabase URL")
    
    # Convert postgres:// to postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Parse URL and remove invalid parameters for PostgreSQL
    try:
        parsed = urlparse(database_url)
        if parsed.query:
            # Parse query parameters
            params = parse_qs(parsed.query)
            # Remove 'schema' parameter as it's not valid for psycopg2
            if 'schema' in params:
                del params['schema']
        else:
            params = {}
        
        # Add SSL requirement for Supabase and other cloud providers
        if 'supabase.co' in database_url or 'render.com' in database_url:
            if 'sslmode' not in params:
                params['sslmode'] = ['require']
        
        # Rebuild URL with valid parameters
        if params:
            new_query = urlencode(params, doseq=True)
            database_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                                     parsed.params, new_query, parsed.fragment))
        else:
            database_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                                     parsed.params, '', parsed.fragment))
    except Exception as e:
        # If URL parsing fails, fall back to simple string replacement
        print(f"Warning: Could not parse DATABASE_URL: {e}")
        if '?schema=' in database_url:
            base_url, params = database_url.split('?', 1)
            param_parts = params.split('&')
            valid_params = [param for param in param_parts if not param.startswith('schema=')]
            if valid_params:
                database_url = base_url + '?' + '&'.join(valid_params)
            else:
                database_url = base_url
        
        # Add SSL for Supabase as fallback
        if 'supabase.co' in database_url and 'sslmode=' not in database_url:
            separator = '&' if '?' in database_url else '?'
            database_url += f'{separator}sslmode=require'
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database connection pool settings for cloud databases
    # Optimized for Supabase connection pooler
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,  # Reduced for Supabase pooler
        'pool_recycle': 1800,  # 30 minutes
        'pool_pre_ping': True,
        'max_overflow': 10,  # Reduced overflow
        'pool_timeout': 30,
        'connect_args': {
            'connect_timeout': 30,
            'application_name': 'ss_auction_app',
            'sslmode': 'require',
            'options': '-c statement_timeout=30000'  # 30 second statement timeout
        }
    }
    INITIAL_BALANCE = 15000
    MINIMUM_BID = 10
    MAX_PLAYERS_PER_TEAM = 25
    POSITIONS = ['GK', 'CB', 'RB', 'LB', 'DMF', 'CMF', 'AMF', 'LMF', 'RMF', 'RWF', 'LWF', 'SS', 'CF']
    POSITION_GROUPS = ['CB-1', 'CB-2', 'DMF-1', 'DMF-2', 'CMF-1', 'CMF-2', 'AMF-1', 'AMF-2', 'CF-1', 'CF-2'] 
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
    elif 'neon.tech' in database_url:
        print("DEBUG: Detected Neon database")
    
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
        
        # Add SSL requirement for cloud providers (Neon, Supabase, Render)
        if 'neon.tech' in database_url or 'supabase.co' in database_url or 'render.com' in database_url:
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
        
        # Add SSL for cloud providers as fallback
        if ('neon.tech' in database_url or 'supabase.co' in database_url) and 'sslmode=' not in database_url:
            separator = '&' if '?' in database_url else '?'
            database_url += f'{separator}sslmode=require'
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database connection pool settings optimized for Neon with 8GB RAM
    # Maximizing connection pool for faster page loads and responses
    
    # Determine if we're using Neon for optimal configuration
    is_neon = 'neon.tech' in database_url
    
    # Connection arguments optimized for performance
    connect_args = {
        'connect_timeout': 10,  # Reduced from 30 for faster failover
        'application_name': 'ss_auction_app',
        'sslmode': 'require',
        'keepalives': 1,  # Enable TCP keepalives
        'keepalives_idle': 30,  # Start keepalives after 30 seconds
        'keepalives_interval': 10,  # Keepalive interval
        'keepalives_count': 5,  # Number of keepalives before timeout
    }
    
    # Neon pooler doesn't support statement_timeout in connection options
    if not is_neon:
        connect_args['options'] = '-c statement_timeout=30000'  # 30 second statement timeout
    else:
        # Neon-specific optimizations
        connect_args['tcp_user_timeout'] = '30000'  # 30 second TCP timeout
    
    # ULTRA aggressive connection pooling for 8GB RAM Neon database - MAXIMUM SPEED
    if is_neon:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 50,  # MASSIVELY increased - maintain 50 persistent connections
            'max_overflow': 50,  # Allow up to 100 total connections!
            'pool_timeout': 3,  # Ultra-fast timeout - fail immediately
            'pool_recycle': 120,  # Recycle every 2 minutes for freshness
            'pool_pre_ping': False,  # Skip ping for speed (connections are fresh)
            'echo_pool': False,  # Set to True for debugging
            'connect_args': connect_args,
            
            # Maximum performance optimizations
            'pool_reset_on_return': None,  # Skip reset for speed
            'pool_use_lifo': True,  # Use LIFO to keep connections HOT
        }
    else:
        # Conservative settings for other providers
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 1800,
            'pool_pre_ping': True,
            'connect_args': connect_args
        }
    INITIAL_BALANCE = 15000
    MINIMUM_BID = 10
    MAX_PLAYERS_PER_TEAM = 25
    POSITIONS = ['GK', 'CB', 'RB', 'LB', 'DMF', 'CMF', 'AMF', 'LMF', 'RMF', 'RWF', 'LWF', 'SS', 'CF']
    POSITION_GROUPS = ['CB-1', 'CB-2', 'DMF-1', 'DMF-2', 'CMF-1', 'CMF-2', 'AMF-1', 'AMF-2', 'CF-1', 'CF-2']
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', 'ssleaguebot')  # Bot username without @
    TELEGRAM_WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL')  # e.g., 'https://yourapp.com/telegram/webhook'
    TELEGRAM_LINK_EXPIRES_HOURS = int(os.environ.get('TELEGRAM_LINK_EXPIRES_HOURS', '24'))  # Deep link expiration

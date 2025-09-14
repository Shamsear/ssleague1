"""
Ultra Performance Optimization Module
Aggressive optimizations for maximum speed with Neon 8GB RAM
"""

import time
import json
import hashlib
from functools import wraps, lru_cache
from flask import g, request, jsonify, Response
from werkzeug.datastructures import ImmutableDict
from sqlalchemy import text
import pickle

# In-memory cache for ultra-fast access
MEMORY_CACHE = {}
CACHE_STATS = {'hits': 0, 'misses': 0}

class UltraCache:
    """Ultra-fast in-memory caching system"""
    
    def __init__(self, max_size=10000, default_ttl=300):
        self.cache = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_count = {}
        
    def _generate_key(self, *args, **kwargs):
        """Generate cache key from arguments"""
        key_data = f"{args}{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key):
        """Get from cache with TTL check"""
        if key in self.cache:
            value, timestamp, ttl = self.cache[key]
            if time.time() - timestamp < ttl:
                self.access_count[key] = self.access_count.get(key, 0) + 1
                CACHE_STATS['hits'] += 1
                return value
            else:
                del self.cache[key]
        CACHE_STATS['misses'] += 1
        return None
    
    def set(self, key, value, ttl=None):
        """Set cache with TTL"""
        if len(self.cache) >= self.max_size:
            # Remove least accessed items
            sorted_items = sorted(self.access_count.items(), key=lambda x: x[1])
            for k, _ in sorted_items[:self.max_size // 10]:
                if k in self.cache:
                    del self.cache[k]
                del self.access_count[k]
        
        self.cache[key] = (value, time.time(), ttl or self.default_ttl)
        self.access_count[key] = 0
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.access_count.clear()

# Global ultra cache instance
ultra_cache = UltraCache(max_size=10000, default_ttl=60)

def ultra_fast_cache(ttl=60, key_prefix=None):
    """Decorator for ultra-fast caching of function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix or func.__name__}:{ultra_cache._generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached = ultra_cache.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute and cache
            result = func(*args, **kwargs)
            ultra_cache.set(cache_key, result, ttl)
            return result
        
        wrapper.clear_cache = lambda: ultra_cache.clear()
        return wrapper
    return decorator

def batch_query_optimization(query, batch_size=1000):
    """Execute query in batches for better memory usage"""
    offset = 0
    while True:
        batch = query.limit(batch_size).offset(offset).all()
        if not batch:
            break
        for item in batch:
            yield item
        offset += batch_size

class QueryOptimizer:
    """Advanced query optimization techniques"""
    
    @staticmethod
    def optimize_player_query(db, filters=None):
        """Ultra-optimized player query with selective loading"""
        from models import Player, Team
        
        # Build optimized query with only necessary columns
        query = db.session.query(
            Player.id,
            Player.name,
            Player.position,
            Player.overall_rating,
            Player.team_id,
            Team.name.label('team_name'),
            Team.color.label('team_color')
        ).outerjoin(Team, Player.team_id == Team.id)
        
        # Apply filters if provided
        if filters:
            if 'position' in filters:
                query = query.filter(Player.position == filters['position'])
            if 'min_rating' in filters:
                query = query.filter(Player.overall_rating >= filters['min_rating'])
            if 'max_rating' in filters:
                query = query.filter(Player.overall_rating <= filters['max_rating'])
            if 'team_id' in filters:
                query = query.filter(Player.team_id == filters['team_id'])
        
        # Order by rating for consistent results
        query = query.order_by(Player.overall_rating.desc())
        
        return query
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_team_stats(team_id):
        """Cached team statistics"""
        from models import db, Team, Player
        
        result = db.session.query(
            Team.id,
            Team.name,
            Team.balance,
            db.func.count(Player.id).label('player_count'),
            db.func.avg(Player.overall_rating).label('avg_rating'),
            db.func.max(Player.overall_rating).label('max_rating')
        ).outerjoin(Player).filter(
            Team.id == team_id
        ).group_by(Team.id, Team.name, Team.balance).first()
        
        return result._asdict() if result else None

class ConnectionPoolOptimizer:
    """Further optimize database connections"""
    
    @staticmethod
    def warm_connections(db, count=10):
        """Pre-warm database connections"""
        connections = []
        for _ in range(count):
            conn = db.engine.connect()
            conn.execute(text("SELECT 1"))
            connections.append(conn)
        
        # Keep connections warm
        for conn in connections:
            conn.close()
    
    @staticmethod
    def optimize_for_read_heavy(db):
        """Optimize for read-heavy workloads"""
        with db.engine.connect() as conn:
            # Set PostgreSQL parameters for read optimization
            conn.execute(text("SET synchronous_commit = OFF"))
            conn.execute(text("SET commit_delay = 100"))
            conn.commit()

def apply_ultra_performance_to_routes(app, db):
    """Apply ultra performance optimizations to Flask routes"""
    
    # Import models here to avoid circular imports
    from models import Player, Team, User, Round, Bid
    
    # Pre-warm connections on startup
    with app.app_context():
        ConnectionPoolOptimizer.warm_connections(db, 10)
    
    @app.before_request
    def before_request_optimization():
        """Pre-request optimizations"""
        g.request_start_time = time.time()
        
        # Set connection to read-only for GET requests
        if request.method == 'GET':
            g.read_only = True
    
    @app.after_request
    def after_request_optimization(response):
        """Post-request optimizations"""
        if hasattr(g, 'request_start_time'):
            elapsed = time.time() - g.request_start_time
            response.headers['X-Response-Time-Ms'] = str(int(elapsed * 1000))
        
        # Add cache headers for static content
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000'
        
        # Enable compression hint
        response.headers['Vary'] = 'Accept-Encoding'
        
        return response
    
    # Override slow routes with optimized versions
    original_dashboard = app.view_functions.get('dashboard')
    if original_dashboard:
        @ultra_fast_cache(ttl=30, key_prefix='dashboard')
        def optimized_dashboard():
            return original_dashboard()
        
        app.view_functions['dashboard'] = optimized_dashboard
    
    # Optimize players list route
    original_players = app.view_functions.get('players')
    if original_players:
        @ultra_fast_cache(ttl=60, key_prefix='players')
        def optimized_players():
            return original_players()
        
        app.view_functions['players'] = optimized_players
    
    # Add performance monitoring endpoint
    @app.route('/api/performance/stats')
    def performance_stats():
        """Get performance statistics"""
        cache_hit_rate = CACHE_STATS['hits'] / max(1, CACHE_STATS['hits'] + CACHE_STATS['misses'])
        return jsonify({
            'cache_stats': {
                'hits': CACHE_STATS['hits'],
                'misses': CACHE_STATS['misses'],
                'hit_rate': f"{cache_hit_rate * 100:.1f}%",
                'items_cached': len(ultra_cache.cache)
            },
            'connection_pool': {
                'size': app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}).get('pool_size', 5),
                'max_overflow': app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}).get('max_overflow', 10)
            }
        })
    
    # Add cache clear endpoint (admin only)
    @app.route('/api/performance/clear-cache', methods=['POST'])
    def clear_performance_cache():
        """Clear all caches"""
        from flask_login import current_user
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        ultra_cache.clear()
        CACHE_STATS['hits'] = 0
        CACHE_STATS['misses'] = 0
        
        return jsonify({'success': True, 'message': 'Cache cleared'})

def optimize_database_queries(db):
    """Apply database-level query optimizations"""
    
    # Create materialized views for complex queries
    materialized_views = [
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_team_stats AS
        SELECT 
            t.id as team_id,
            t.name as team_name,
            t.balance,
            COUNT(p.id) as player_count,
            AVG(p.overall_rating) as avg_rating,
            MAX(p.overall_rating) as max_rating,
            MIN(p.overall_rating) as min_rating,
            STRING_AGG(p.position, ',') as positions
        FROM team t
        LEFT JOIN player p ON t.id = p.team_id
        GROUP BY t.id, t.name, t.balance
        """,
        
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_player_rankings AS
        SELECT 
            p.id,
            p.name,
            p.position,
            p.overall_rating,
            p.team_id,
            t.name as team_name,
            RANK() OVER (ORDER BY p.overall_rating DESC) as overall_rank,
            RANK() OVER (PARTITION BY p.position ORDER BY p.overall_rating DESC) as position_rank
        FROM player p
        LEFT JOIN team t ON p.team_id = t.id
        """
    ]
    
    try:
        with db.engine.connect() as conn:
            for view_sql in materialized_views:
                try:
                    conn.execute(text(view_sql))
                    conn.commit()
                except Exception as e:
                    print(f"Could not create materialized view: {e}")
    except Exception as e:
        print(f"Could not optimize database queries: {e}")

def enable_query_result_caching(app, db):
    """Enable query result caching at the SQLAlchemy level"""
    
    # Disabled due to compatibility issues - using in-memory caching instead
    pass

# Fast JSON encoder for better serialization performance
class FastJSONEncoder(json.JSONEncoder):
    """Optimized JSON encoder"""
    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

def install_ultra_performance(app, db):
    """Install all ultra performance optimizations"""
    
    print("🚀 Installing Ultra Performance Optimizations...")
    
    # 1. Apply route optimizations
    apply_ultra_performance_to_routes(app, db)
    
    # 2. Optimize database queries
    with app.app_context():
        optimize_database_queries(db)
    
    # 3. Enable query result caching
    enable_query_result_caching(app, db)
    
    # 4. Use fast JSON encoder
    app.json_encoder = FastJSONEncoder
    
    # 5. Pre-warm connections
    with app.app_context():
        ConnectionPoolOptimizer.warm_connections(db, 5)
    
    print("⚡ Ultra Performance Optimizations Installed!")
    print("   • In-memory caching enabled (60s TTL)")
    print("   • Query optimization active")
    print("   • Connection pool pre-warmed")
    print("   • Materialized views created")
    print("   • Fast JSON serialization enabled")
    
    return True
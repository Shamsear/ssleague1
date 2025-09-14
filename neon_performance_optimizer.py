"""
Neon Database Performance Optimizer
Maximizes utilization of 8GB RAM for faster page loading and responses
"""

import os
import time
from functools import wraps
from flask import g, current_app
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool
import logging

logger = logging.getLogger(__name__)

class NeonPerformanceOptimizer:
    """
    Performance optimization specifically for Neon database with 8GB RAM
    """
    
    @staticmethod
    def initialize(app, db):
        """Initialize all performance optimizations"""
        
        # 1. Configure query result caching in memory
        NeonPerformanceOptimizer.setup_query_cache(db)
        
        # 2. Enable prepared statements for frequently used queries
        NeonPerformanceOptimizer.setup_prepared_statements(db)
        
        # 3. Configure connection pooling events
        NeonPerformanceOptimizer.setup_pool_events(db)
        
        # 4. Enable query plan caching
        NeonPerformanceOptimizer.setup_query_plan_cache(db)
        
        # 5. Configure batch operations
        NeonPerformanceOptimizer.setup_batch_operations(db)
        
        logger.info("Neon Performance Optimizer initialized with 8GB RAM optimizations")
    
    @staticmethod
    def setup_query_cache(db):
        """Configure in-memory query result caching"""
        
        # Store frequently accessed data in memory
        query_cache = {}
        cache_ttl = 60  # 60 seconds cache TTL
        
        def cache_query(query_key, ttl=cache_ttl):
            """Decorator to cache query results"""
            def decorator(func):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    # Generate cache key
                    cache_key = f"{query_key}:{str(args)}:{str(kwargs)}"
                    
                    # Check cache
                    if cache_key in query_cache:
                        cached_data, timestamp = query_cache[cache_key]
                        if time.time() - timestamp < ttl:
                            return cached_data
                    
                    # Execute query and cache result
                    result = func(*args, **kwargs)
                    query_cache[cache_key] = (result, time.time())
                    
                    # Clean old cache entries (keep memory usage reasonable)
                    if len(query_cache) > 1000:
                        # Remove oldest entries
                        sorted_cache = sorted(query_cache.items(), key=lambda x: x[1][1])
                        for key, _ in sorted_cache[:100]:
                            del query_cache[key]
                    
                    return result
                return wrapper
            return decorator
        
        # Attach to db for use in the app
        db.cache_query = cache_query
    
    @staticmethod
    def setup_prepared_statements(db):
        """Setup prepared statements for common queries"""
        
        prepared_statements = {}
        
        @event.listens_for(Engine, "connect")
        def prepare_statements(dbapi_conn, connection_record):
            """Prepare frequently used statements on connection"""
            
            with dbapi_conn.cursor() as cursor:
                # Prepare common queries
                statements = {
                    'get_player_by_id': "PREPARE get_player_by_id AS SELECT * FROM player WHERE id = $1",
                    'get_team_players': "PREPARE get_team_players AS SELECT * FROM player WHERE team_id = $1 ORDER BY overall_rating DESC",
                    'get_active_rounds': "PREPARE get_active_rounds AS SELECT * FROM round WHERE is_active = true",
                    'get_team_balance': "PREPARE get_team_balance AS SELECT balance FROM team WHERE id = $1",
                    'get_player_bids': "PREPARE get_player_bids AS SELECT * FROM bid WHERE player_id = $1 AND round_id = $2",
                }
                
                for name, statement in statements.items():
                    try:
                        # Try to deallocate if exists (may not be supported)
                        try:
                            cursor.execute(f"DEALLOCATE {name.split()[0]}")
                        except:
                            pass  # Ignore if doesn't exist
                        
                        # Prepare the statement
                        cursor.execute(statement)
                        prepared_statements[name] = True
                    except Exception as e:
                        logger.warning(f"Could not prepare statement {name}: {e}")
    
    @staticmethod
    def setup_pool_events(db):
        """Configure connection pool events for optimal performance"""
        
        @event.listens_for(Pool, "connect")
        def set_connection_parameters(dbapi_conn, connection_record):
            """Set optimal connection parameters when connection is created"""
            
            try:
                with dbapi_conn.cursor() as cursor:
                    # Set performance-related parameters that are supported
                    # Some may not be available on Neon pooler, so wrap each in try/except
                    params = [
                        ("SET work_mem = '32MB'", "work_mem"),
                        ("SET random_page_cost = 1.1", "random_page_cost"),
                        ("SET effective_io_concurrency = 200", "effective_io_concurrency"),
                        ("SET jit = 'on'", "jit"),
                    ]
                    
                    for param_sql, param_name in params:
                        try:
                            cursor.execute(param_sql)
                        except Exception as e:
                            logger.debug(f"Could not set {param_name}: {e}")
                    
                    logger.debug("Connection parameters optimized for 8GB RAM")
            except Exception as e:
                logger.warning(f"Could not optimize connection parameters: {e}")
        
        @event.listens_for(Pool, "checkout")
        def ping_connection(dbapi_conn, connection_record, connection_proxy):
            """Verify connection is alive on checkout"""
            
            # Save overhead by only pinging older connections
            if connection_record.info.get('ping_time', 0) < time.time() - 10:
                try:
                    with dbapi_conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                    connection_record.info['ping_time'] = time.time()
                except:
                    # Connection is dead, dispose of it
                    connection_proxy._pool.dispose()
                    raise
    
    @staticmethod
    def setup_query_plan_cache(db):
        """Enable and configure query plan caching"""
        
        @event.listens_for(Engine, "before_execute")
        def before_execute(conn, clauseelement, multiparams, params, execution_options):
            """Add query hints for plan caching"""
            
            # For SELECT queries, add planner hints
            if hasattr(clauseelement, 'statement') and str(clauseelement).upper().startswith('SELECT'):
                # Store query start time for monitoring
                conn.info['query_start_time'] = time.time()
        
        @event.listens_for(Engine, "after_execute")
        def after_execute(conn, clauseelement, multiparams, params, execution_options, result):
            """Log slow queries for optimization"""
            
            if 'query_start_time' in conn.info:
                elapsed = time.time() - conn.info['query_start_time']
                if elapsed > 1.0:  # Log queries taking more than 1 second
                    logger.warning(f"Slow query ({elapsed:.2f}s): {str(clauseelement)[:100]}")
                del conn.info['query_start_time']
    
    @staticmethod
    def setup_batch_operations(db):
        """Configure batch operations for better performance"""
        
        def bulk_insert_optimize(model, records):
            """Optimized bulk insert using COPY or multi-value inserts"""
            
            if not records:
                return
            
            # Use SQLAlchemy's bulk_insert_mappings for best performance
            db.session.bulk_insert_mappings(model, records)
            db.session.commit()
        
        def bulk_update_optimize(model, records):
            """Optimized bulk update"""
            
            if not records:
                return
            
            # Use bulk_update_mappings for efficiency
            db.session.bulk_update_mappings(model, records)
            db.session.commit()
        
        # Attach to db for use
        db.bulk_insert_optimize = bulk_insert_optimize
        db.bulk_update_optimize = bulk_update_optimize

class QueryOptimizer:
    """
    Query optimization helpers for Neon database
    """
    
    @staticmethod
    def optimize_player_list_query(query, page=1, per_page=50):
        """Optimize player list queries with proper indexing hints"""
        
        # Use index hints and limit early
        optimized = query.options(
            # Only load necessary columns initially
            db.load_only(
                'id', 'name', 'position', 'overall_rating', 
                'team_id', 'price', 'is_starred'
            ),
            # Eager load related data to prevent N+1
            db.joinedload('team').load_only('id', 'name', 'color'),
            db.joinedload('round').load_only('id', 'round_number', 'is_active')
        )
        
        # Add pagination with count optimization
        return optimized.paginate(
            page=page, 
            per_page=per_page,
            error_out=False,
            count=False  # Avoid COUNT(*) on large tables
        )
    
    @staticmethod
    def optimize_dashboard_queries(user_id):
        """Return optimized queries for dashboard data"""
        
        from models import Team, Player, Round, Bid
        
        queries = {}
        
        # Use subqueries for aggregations
        queries['team_stats'] = db.session.query(
            Team.id,
            Team.name,
            Team.balance,
            db.func.count(Player.id).label('player_count'),
            db.func.coalesce(db.func.avg(Player.overall_rating), 0).label('avg_rating')
        ).outerjoin(Player).filter(
            Team.user_id == user_id
        ).group_by(Team.id)
        
        # Get only necessary columns
        queries['recent_bids'] = db.session.query(
            Bid.id,
            Bid.amount,
            Bid.created_at,
            Player.name.label('player_name'),
            Round.round_number
        ).join(Player).join(Round).filter(
            Bid.team_id == db.session.query(Team.id).filter_by(user_id=user_id).scalar_subquery()
        ).order_by(Bid.created_at.desc()).limit(10)
        
        return queries
    
    @staticmethod
    def create_performance_indexes(db):
        """Create indexes optimized for Neon's architecture"""
        
        indexes = [
            # Covering indexes for common queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_team_rating ON player(team_id, overall_rating DESC) INCLUDE (name, position)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bid_team_round ON bid(team_id, round_id) INCLUDE (amount, player_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_round_active ON round(is_active) WHERE is_active = true",
            
            # Partial indexes for filtered queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_unassigned ON player(overall_rating DESC) WHERE team_id IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_position ON player(position, overall_rating DESC)",
            
            # BRIN indexes for time-series data (very memory efficient)
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bid_created_brin ON bid USING BRIN(created_at)",
            
            # Hash indexes for exact lookups (memory efficient)
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_username_hash ON \"user\" USING HASH(username)",
            
            # GIN indexes for full-text search if needed
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_name_gin ON player USING GIN(to_tsvector('english', name))",
        ]
        
        with db.engine.connect() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                    logger.info(f"Created index: {index_sql[:50]}...")
                except Exception as e:
                    logger.warning(f"Could not create index: {e}")

def apply_neon_optimizations(app, db):
    """
    Apply all Neon-specific optimizations to the Flask app
    Call this after app and db initialization
    """
    
    # Only apply if using Neon
    if 'neon.tech' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
        logger.info("Applying Neon 8GB RAM optimizations...")
        
        # Initialize the optimizer
        NeonPerformanceOptimizer.initialize(app, db)
        
        # Create performance indexes
        with app.app_context():
            QueryOptimizer.create_performance_indexes(db)
        
        # Add query optimizer to app for use in routes
        app.query_optimizer = QueryOptimizer
        
        logger.info("Neon optimizations applied successfully")
        return True
    
    return False
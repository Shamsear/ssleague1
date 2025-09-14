-- Fix PostgreSQL collation version mismatch
-- Run this script as the database superuser (usually postgres)

-- Connect to the auction_db database
\c auction_db

-- Refresh the collation version
ALTER DATABASE auction_db REFRESH COLLATION VERSION;

-- If you need to rebuild indexes that use text columns, you can run:
-- REINDEX DATABASE auction_db;

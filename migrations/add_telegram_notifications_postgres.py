"""Add Telegram notification support for PostgreSQL/Neon

This migration adds tables for:
- telegram_user: Links app users to Telegram accounts
- notification_log: Tracks all sent notifications  
- notification_settings: Global bot settings
"""

import os
import sys
import psycopg2
from datetime import datetime, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get database connection using the same config as the app"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    # Handle postgres:// to postgresql:// conversion like in config.py
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Parse the URL
    parsed = urlparse(database_url)
    
    # Create connection
    connection = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],  # Remove leading slash
        user=parsed.username,
        password=parsed.password,
        sslmode='require'  # Neon requires SSL
    )
    
    return connection

def run_migration():
    """Run the Telegram notifications migration for PostgreSQL"""
    print("🚀 Starting Telegram notifications migration for PostgreSQL/Neon...")
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        print("🔧 Creating Telegram notification tables...")
        
        # Create telegram_user table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telegram_user (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id),
                telegram_chat_id VARCHAR(50) NOT NULL UNIQUE,
                telegram_username VARCHAR(100),
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                
                -- Notification preferences
                notify_login BOOLEAN DEFAULT TRUE,
                notify_bids BOOLEAN DEFAULT TRUE,
                notify_auction_start BOOLEAN DEFAULT TRUE,
                notify_auction_end BOOLEAN DEFAULT TRUE,
                notify_team_changes BOOLEAN DEFAULT TRUE,
                notify_admin_actions BOOLEAN DEFAULT TRUE,
                notify_system_alerts BOOLEAN DEFAULT TRUE,
                
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')
        print("  ✅ telegram_user table created")
        
        # Create notification_log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_log (
                id SERIAL PRIMARY KEY,
                telegram_user_id INTEGER NOT NULL REFERENCES telegram_user(id),
                notification_type VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                user_action VARCHAR(100),
                actor_user_id INTEGER REFERENCES "user"(id),
                
                -- Delivery status
                status VARCHAR(20) DEFAULT 'pending',
                sent_at TIMESTAMP WITH TIME ZONE,
                delivered_at TIMESTAMP WITH TIME ZONE,
                failed_reason TEXT,
                
                -- Metadata
                message_data JSONB,
                telegram_message_id VARCHAR(50),
                
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')
        print("  ✅ notification_log table created")
        
        # Create notification_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_settings (
                id SERIAL PRIMARY KEY,
                setting_name VARCHAR(100) NOT NULL UNIQUE,
                setting_value TEXT,
                description TEXT,
                
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')
        print("  ✅ notification_settings table created")
        
        # Create indexes for better performance
        print("📈 Creating indexes...")
        
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_telegram_user_chat_id ON telegram_user (telegram_chat_id)',
            'CREATE INDEX IF NOT EXISTS idx_telegram_user_user_id ON telegram_user (user_id)',
            'CREATE INDEX IF NOT EXISTS idx_telegram_user_active ON telegram_user (is_active)',
            'CREATE INDEX IF NOT EXISTS idx_notification_log_telegram_user ON notification_log (telegram_user_id)',
            'CREATE INDEX IF NOT EXISTS idx_notification_log_type ON notification_log (notification_type)',
            'CREATE INDEX IF NOT EXISTS idx_notification_log_status ON notification_log (status)',
            'CREATE INDEX IF NOT EXISTS idx_notification_log_created ON notification_log (created_at)',
            'CREATE INDEX IF NOT EXISTS idx_notification_log_actor ON notification_log (actor_user_id)',
            'CREATE INDEX IF NOT EXISTS idx_notification_settings_name ON notification_settings (setting_name)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print("  ✅ All indexes created")
        
        # Insert default settings
        print("⚙️ Adding default settings...")
        
        default_settings = [
            ('bot_enabled', 'true', 'Whether the Telegram bot is enabled'),
            ('max_notifications_per_hour', '100', 'Maximum notifications to send per hour'),
            ('rate_limit_enabled', 'true', 'Whether to enforce rate limiting'),
            ('admin_chat_id', '', 'Chat ID for admin notifications'),
            ('webhook_secret', '', 'Secret token for webhook validation'),
        ]
        
        for setting_name, setting_value, description in default_settings:
            cursor.execute('''
                INSERT INTO notification_settings 
                (setting_name, setting_value, description) 
                VALUES (%s, %s, %s)
                ON CONFLICT (setting_name) DO NOTHING
            ''', (setting_name, setting_value, description))
        
        print("  ✅ Default settings added")
        
        # Create triggers for updated_at timestamps
        print("🔄 Creating update triggers...")
        
        # Function to update timestamp
        cursor.execute('''
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        ''')
        
        # Triggers for each table
        trigger_tables = ['telegram_user', 'notification_log', 'notification_settings']
        
        for table in trigger_tables:
            cursor.execute(f'''
                DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                CREATE TRIGGER update_{table}_updated_at 
                    BEFORE UPDATE ON {table} 
                    FOR EACH ROW 
                    EXECUTE FUNCTION update_updated_at_column();
            ''')
        
        print("  ✅ Update triggers created")
        
        # Commit all changes
        conn.commit()
        print("✅ All changes committed to database")
        
        # Show table info
        print("\n📋 Migration Summary:")
        
        tables = ['telegram_user', 'notification_log', 'notification_settings']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  • {table}: {count} rows")
        
        print(f"\n🎉 Migration completed successfully!")
        print(f"📊 Database: Neon PostgreSQL")
        print(f"🕐 Completed at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL error: {e}")
        print(f"Error code: {e.pgcode}")
        print(f"Error details: {e.pgerror}")
        return False
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def rollback_migration():
    """Rollback the Telegram notifications migration"""
    print("🔄 Starting rollback of Telegram notifications migration...")
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        print("🗑️ Dropping tables and triggers...")
        
        # Drop triggers first
        trigger_tables = ['telegram_user', 'notification_log', 'notification_settings']
        for table in trigger_tables:
            cursor.execute(f'DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}')
        
        # Drop function
        cursor.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
        
        # Drop tables in reverse order (to handle foreign keys)
        tables_to_drop = [
            'notification_log',
            'notification_settings', 
            'telegram_user'
        ]
        
        for table in tables_to_drop:
            cursor.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
            print(f"  🗑️ Dropped table: {table}")
        
        conn.commit()
        print("✅ Rollback completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL error during rollback: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def test_connection():
    """Test database connection"""
    print("🔌 Testing database connection...")
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"📊 Database version: {version}")
        
        # Check if we're on Neon
        if 'neon' in version.lower():
            print("🌟 Confirmed: Running on Neon database")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'rollback':
            success = rollback_migration()
        elif sys.argv[1] == 'test':
            success = test_connection()
        else:
            print("Usage: python add_telegram_notifications_postgres.py [test|rollback]")
            sys.exit(1)
    else:
        success = run_migration()
    
    if not success:
        print(f"\n💥 Operation failed!")
        sys.exit(1)
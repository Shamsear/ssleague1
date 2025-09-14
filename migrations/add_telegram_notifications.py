"""Add Telegram notification support

This migration adds tables for:
- TelegramUser: Links app users to Telegram accounts
- NotificationLog: Tracks all sent notifications  
- NotificationSettings: Global bot settings
"""

import sqlite3
import os
from datetime import datetime, timezone
import sys

def run_migration():
    """Run the Telegram notifications migration"""
    
    # Determine database path
    db_paths = [
        'efootball_real.db',
        os.path.join(os.path.dirname(__file__), '..', 'efootball_real.db')
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database file not found!")
        return False
    
    print(f"📊 Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Creating Telegram notification tables...")
        
        # Create telegram_user table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telegram_user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                telegram_chat_id VARCHAR(50) NOT NULL UNIQUE,
                telegram_username VARCHAR(100),
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                is_active BOOLEAN DEFAULT 1,
                
                -- Notification preferences
                notify_login BOOLEAN DEFAULT 1,
                notify_bids BOOLEAN DEFAULT 1,
                notify_auction_start BOOLEAN DEFAULT 1,
                notify_auction_end BOOLEAN DEFAULT 1,
                notify_team_changes BOOLEAN DEFAULT 1,
                notify_admin_actions BOOLEAN DEFAULT 1,
                notify_system_alerts BOOLEAN DEFAULT 1,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (user_id) REFERENCES user (id)
            )
        ''')
        
        # Create notification_log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                notification_type VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                user_action VARCHAR(100),
                actor_user_id INTEGER,
                
                -- Delivery status
                status VARCHAR(20) DEFAULT 'pending',
                sent_at TIMESTAMP,
                delivered_at TIMESTAMP,
                failed_reason TEXT,
                
                -- Metadata
                message_data TEXT,
                telegram_message_id VARCHAR(50),
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (telegram_user_id) REFERENCES telegram_user (id),
                FOREIGN KEY (actor_user_id) REFERENCES user (id)
            )
        ''')
        
        # Create notification_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name VARCHAR(100) NOT NULL UNIQUE,
                setting_value TEXT,
                description TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        print("📈 Creating indexes...")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_telegram_user_chat_id ON telegram_user (telegram_chat_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_telegram_user_user_id ON telegram_user (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_log_telegram_user ON notification_log (telegram_user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_log_type ON notification_log (notification_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_log_status ON notification_log (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_log_created ON notification_log (created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notification_settings_name ON notification_settings (setting_name)')
        
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
                INSERT OR IGNORE INTO notification_settings 
                (setting_name, setting_value, description) 
                VALUES (?, ?, ?)
            ''', (setting_name, setting_value, description))
        
        # Commit changes
        conn.commit()
        print("✅ Telegram notification tables created successfully!")
        
        # Show table info
        print("\n📋 Table Summary:")
        
        tables = ['telegram_user', 'notification_log', 'notification_settings']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  • {table}: {count} rows")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

def rollback_migration():
    """Rollback the Telegram notifications migration"""
    
    # Determine database path
    db_paths = [
        'efootball_real.db',
        os.path.join(os.path.dirname(__file__), '..', 'efootball_real.db')
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database file not found!")
        return False
    
    print(f"📊 Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Rolling back Telegram notification tables...")
        
        # Drop tables in reverse order (to handle foreign keys)
        tables_to_drop = [
            'notification_log',
            'notification_settings', 
            'telegram_user'
        ]
        
        for table in tables_to_drop:
            cursor.execute(f'DROP TABLE IF EXISTS {table}')
            print(f"  🗑️ Dropped table: {table}")
        
        conn.commit()
        print("✅ Rollback completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error during rollback: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        success = rollback_migration()
    else:
        success = run_migration()
    
    if success:
        print(f"\n🎉 Migration {'rollback' if len(sys.argv) > 1 and sys.argv[1] == 'rollback' else 'completed'} successfully!")
    else:
        print(f"\n💥 Migration {'rollback' if len(sys.argv) > 1 and sys.argv[1] == 'rollback' else ''} failed!")
        sys.exit(1)
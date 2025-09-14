#!/usr/bin/env python3
"""
Migration script to fix the telegram_user_id foreign key constraint
to allow NULL values and SET NULL on delete for preserving notification history.

Run this script to fix the database constraint error when unlinking Telegram users.
"""

from flask import Flask
from config import Config
from models import db
import sqlite3
import os

def create_app():
    """Create minimal Flask app for migration"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

def fix_postgresql_constraints():
    """Fix constraints for PostgreSQL database"""
    try:
        # Use newer SQLAlchemy syntax with text()
        from sqlalchemy import text
        
        # Check if constraint exists first
        check_constraint = text("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'notification_log' 
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name LIKE '%telegram_user_id%'
        """)
        
        result = db.session.execute(check_constraint).fetchall()
        constraint_exists = len(result) > 0
        
        if constraint_exists:
            constraint_name = result[0][0]
            print(f"📋 Found existing constraint: {constraint_name}")
            
            # Drop the existing foreign key constraint
            drop_constraint = text(f"""
                ALTER TABLE notification_log 
                DROP CONSTRAINT {constraint_name}
            """)
            db.session.execute(drop_constraint)
            print("✅ Dropped existing foreign key constraint")
        else:
            print("📋 No existing foreign key constraint found")
        
        # Allow NULL values in telegram_user_id column
        alter_column = text("""
            ALTER TABLE notification_log 
            ALTER COLUMN telegram_user_id DROP NOT NULL
        """)
        try:
            db.session.execute(alter_column)
            print("✅ Set telegram_user_id column to nullable")
        except Exception as e:
            if "does not exist" in str(e).lower():
                print("📋 Column is already nullable")
            else:
                raise
        
        # Add the new foreign key constraint with SET NULL on delete
        add_constraint = text("""
            ALTER TABLE notification_log 
            ADD CONSTRAINT notification_log_telegram_user_id_fkey 
            FOREIGN KEY (telegram_user_id) 
            REFERENCES telegram_user(id) ON DELETE SET NULL
        """)
        db.session.execute(add_constraint)
        print("✅ Added new foreign key constraint with SET NULL on delete")
        
        # Commit the changes
        db.session.commit()
        
        print("✅ PostgreSQL constraints updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating PostgreSQL constraints: {e}")
        db.session.rollback()
        return False

def fix_sqlite_constraints():
    """Fix constraints for SQLite database (requires table recreation)"""
    try:
        from sqlalchemy import text
        
        # For SQLite, we need to recreate the table since it doesn't support 
        # ALTER COLUMN operations directly
        
        # First, backup existing data
        print("📋 Backing up notification_log data...")
        backup_query = text("""
            SELECT id, telegram_user_id, notification_type, message, user_action, 
                   actor_user_id, status, sent_at, delivered_at, failed_reason,
                   message_data, telegram_message_id, created_at, updated_at
            FROM notification_log
        """)
        backup_data = db.session.execute(backup_query).fetchall()
        
        print(f"📋 Found {len(backup_data)} notification log entries")
        
        # Drop and recreate the table with new constraints
        print("🔄 Recreating notification_log table...")
        drop_table = text("DROP TABLE notification_log")
        db.session.execute(drop_table)
        
        # Recreate table with nullable telegram_user_id
        create_table = text("""
            CREATE TABLE notification_log (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER,
                notification_type VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                user_action VARCHAR(100),
                actor_user_id INTEGER,
                status VARCHAR(20) DEFAULT 'pending',
                sent_at DATETIME,
                delivered_at DATETIME,
                failed_reason TEXT,
                message_data TEXT,
                telegram_message_id VARCHAR(50),
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY(telegram_user_id) REFERENCES telegram_user (id) ON DELETE SET NULL,
                FOREIGN KEY(actor_user_id) REFERENCES user (id)
            )
        """)
        db.session.execute(create_table)
        
        # Restore the data
        print("♻️ Restoring notification_log data...")
        insert_query = text("""
            INSERT INTO notification_log 
            (id, telegram_user_id, notification_type, message, user_action, 
             actor_user_id, status, sent_at, delivered_at, failed_reason,
             message_data, telegram_message_id, created_at, updated_at)
            VALUES (:id, :telegram_user_id, :notification_type, :message, :user_action, 
                    :actor_user_id, :status, :sent_at, :delivered_at, :failed_reason,
                    :message_data, :telegram_message_id, :created_at, :updated_at)
        """)
        
        for row in backup_data:
            row_dict = {
                'id': row[0], 'telegram_user_id': row[1], 'notification_type': row[2],
                'message': row[3], 'user_action': row[4], 'actor_user_id': row[5],
                'status': row[6], 'sent_at': row[7], 'delivered_at': row[8],
                'failed_reason': row[9], 'message_data': row[10], 
                'telegram_message_id': row[11], 'created_at': row[12], 'updated_at': row[13]
            }
            db.session.execute(insert_query, row_dict)
        
        # Commit all changes
        db.session.commit()
        
        print("✅ SQLite table recreated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating SQLite constraints: {e}")
        db.session.rollback()
        return False

def main():
    """Main migration function"""
    print("🔧 Starting Telegram unlink constraint fix migration...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check database type
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            print(f"📊 Database URL: {database_url[:50]}...")
            
            if 'postgresql' in database_url or 'postgres' in database_url:
                print("🐘 Detected PostgreSQL database")
                success = fix_postgresql_constraints()
            elif 'sqlite' in database_url or database_url.startswith('sqlite'):
                print("🗄️ Detected SQLite database")
                success = fix_sqlite_constraints()
            else:
                print("❓ Unknown database type - attempting PostgreSQL fix...")
                success = fix_postgresql_constraints()
            
            if success:
                print("🎉 Migration completed successfully!")
                print("✅ telegram_user_id is now nullable with SET NULL on delete")
                print("✅ Notification history will be preserved when users unlink")
                print("✅ Unlink errors should be resolved")
            else:
                print("❌ Migration failed. Please check the errors above.")
                return 1
                
        except Exception as e:
            print(f"💥 Migration failed with error: {e}")
            return 1
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
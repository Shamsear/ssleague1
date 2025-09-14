#!/usr/bin/env python3
"""
Complete Database Migration Script: Supabase to Neon
Migrates all tables, data, and relationships from Supabase to Neon
"""

import os
import sys
import json
from datetime import datetime
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseMigrator:
    def __init__(self, source_url, target_url):
        self.source_url = source_url
        self.target_url = target_url
        self.source_conn = None
        self.target_conn = None
        self.tables_order = []
        self.migration_stats = {
            'tables_migrated': 0,
            'rows_migrated': 0,
            'errors': []
        }
    
    def connect(self):
        """Establish connections to both databases"""
        try:
            logger.info("Connecting to source database (Supabase)...")
            self.source_conn = psycopg2.connect(self.source_url)
            logger.info("✅ Connected to Supabase")
            
            logger.info("Connecting to target database (Neon)...")
            self.target_conn = psycopg2.connect(self.target_url)
            logger.info("✅ Connected to Neon")
            
            # Set autocommit to False for transaction support
            self.source_conn.autocommit = False
            self.target_conn.autocommit = False
            
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            raise
    
    def get_tables_in_order(self):
        """Get all tables ordered by foreign key dependencies"""
        # Simplified query that works with Supabase
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        
        with self.source_conn.cursor() as cursor:
            cursor.execute(query)
            self.tables_order = [row[0] for row in cursor.fetchall()]
            logger.info(f"Found {len(self.tables_order)} tables to migrate")
            logger.info(f"Migration order: {', '.join(self.tables_order)}")
        
        return self.tables_order
    
    def get_table_ddl(self, table_name):
        """Get CREATE TABLE statement for a table"""
        with self.source_conn.cursor() as cursor:
            # Get column definitions
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                    AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            columns = cursor.fetchall()
            
            # Build CREATE TABLE statement
            col_defs = []
            for col in columns:
                col_name, data_type, char_len, num_prec, num_scale, nullable, default = col
                
                # Build column type
                if data_type == 'character varying' and char_len:
                    col_type = f"VARCHAR({char_len})"
                elif data_type == 'numeric' and num_prec:
                    if num_scale:
                        col_type = f"NUMERIC({num_prec},{num_scale})"
                    else:
                        col_type = f"NUMERIC({num_prec})"
                else:
                    col_type = data_type.upper()
                
                # Build column definition
                col_def = f'"{col_name}" {col_type}'
                
                if nullable == 'NO':
                    col_def += ' NOT NULL'
                
                if default and not default.startswith('nextval'):
                    col_def += f' DEFAULT {default}'
                
                col_defs.append(col_def)
            
            # Get primary key
            cursor.execute("""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = 'public'
                    AND tc.table_name = %s
                    AND tc.constraint_type = 'PRIMARY KEY'
                ORDER BY kcu.ordinal_position
            """, (table_name,))
            
            pk_columns = [row[0] for row in cursor.fetchall()]
            if pk_columns:
                pk_cols_quoted = ', '.join([f'"{col}"' for col in pk_columns])
                col_defs.append(f'PRIMARY KEY ({pk_cols_quoted})')
            
            create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n    ' + ',\n    '.join(col_defs) + '\n);'
            
            return create_sql
    
    def create_table(self, table_name):
        """Create table in target database"""
        try:
            ddl = self.get_table_ddl(table_name)
            
            with self.target_conn.cursor() as cursor:
                # Drop table if exists (for clean migration)
                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
                # Create table
                cursor.execute(ddl)
                self.target_conn.commit()
                
            logger.info(f"✅ Created table: {table_name}")
            return True
            
        except Exception as e:
            self.target_conn.rollback()
            logger.error(f"❌ Failed to create table {table_name}: {str(e)}")
            self.migration_stats['errors'].append(f"Table creation failed for {table_name}: {str(e)}")
            return False
    
    def copy_table_data(self, table_name):
        """Copy all data from source table to target table"""
        try:
            with self.source_conn.cursor(cursor_factory=RealDictCursor) as source_cursor:
                # Get all data from source
                source_cursor.execute(f'SELECT * FROM "{table_name}"')
                rows = source_cursor.fetchall()
                
                if not rows:
                    logger.info(f"   Table {table_name} is empty")
                    return 0
                
                # Get column names
                columns = list(rows[0].keys())
                
                with self.target_conn.cursor() as target_cursor:
                    # Prepare INSERT statement
                    placeholders = ', '.join(['%s'] * len(columns))
                    column_names = ', '.join([f'"{col}"' for col in columns])
                    insert_sql = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
                    
                    # Insert all rows
                    row_count = 0
                    for row in rows:
                        values = [row[col] for col in columns]
                        target_cursor.execute(insert_sql, values)
                        row_count += 1
                        
                        # Commit every 1000 rows for large tables
                        if row_count % 1000 == 0:
                            self.target_conn.commit()
                            logger.info(f"   Inserted {row_count} rows into {table_name}...")
                    
                    self.target_conn.commit()
                    
                logger.info(f"✅ Copied {row_count} rows to table: {table_name}")
                self.migration_stats['rows_migrated'] += row_count
                return row_count
                
        except Exception as e:
            self.target_conn.rollback()
            logger.error(f"❌ Failed to copy data for table {table_name}: {str(e)}")
            self.migration_stats['errors'].append(f"Data copy failed for {table_name}: {str(e)}")
            return 0
    
    def migrate_sequences(self):
        """Migrate sequences (for auto-increment fields)"""
        try:
            with self.source_conn.cursor() as cursor:
                # Get all sequences
                cursor.execute("""
                    SELECT sequence_name, data_type, start_value, increment, minimum_value, maximum_value
                    FROM information_schema.sequences
                    WHERE sequence_schema = 'public'
                """)
                sequences = cursor.fetchall()
                
                for seq in sequences:
                    seq_name = seq[0]
                    
                    # Get current value
                    cursor.execute(f"SELECT last_value FROM {seq_name}")
                    current_val = cursor.fetchone()[0]
                    
                    with self.target_conn.cursor() as target_cursor:
                        # Create sequence in target
                        target_cursor.execute(f"""
                            CREATE SEQUENCE IF NOT EXISTS {seq_name}
                            START WITH {current_val + 1}
                        """)
                        
                        logger.info(f"✅ Migrated sequence: {seq_name}")
                
                self.target_conn.commit()
                
        except Exception as e:
            logger.warning(f"Sequence migration issue (may be normal): {str(e)}")
    
    def migrate_constraints(self):
        """Migrate foreign key constraints after all data is copied"""
        try:
            with self.source_conn.cursor() as cursor:
                # Get all foreign key constraints
                cursor.execute("""
                    SELECT
                        tc.table_name,
                        tc.constraint_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public'
                    ORDER BY tc.table_name
                """)
                
                constraints = cursor.fetchall()
                
                with self.target_conn.cursor() as target_cursor:
                    for constraint in constraints:
                        table, name, column, ref_table, ref_column = constraint
                        
                        try:
                            # Add foreign key constraint
                            alter_sql = f"""
                                ALTER TABLE "{table}"
                                ADD CONSTRAINT "{name}"
                                FOREIGN KEY ("{column}")
                                REFERENCES "{ref_table}" ("{ref_column}")
                            """
                            target_cursor.execute(alter_sql)
                            logger.info(f"✅ Added constraint: {name} on {table}")
                            
                        except psycopg2.errors.DuplicateObject:
                            logger.info(f"   Constraint {name} already exists")
                        except Exception as e:
                            logger.warning(f"   Could not add constraint {name}: {str(e)}")
                
                self.target_conn.commit()
                
        except Exception as e:
            logger.error(f"Constraint migration failed: {str(e)}")
            self.migration_stats['errors'].append(f"Constraint migration failed: {str(e)}")
    
    def migrate_indexes(self):
        """Migrate indexes for better performance"""
        try:
            with self.source_conn.cursor() as cursor:
                # Get all indexes
                cursor.execute("""
                    SELECT
                        indexname,
                        tablename,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                        AND indexname NOT LIKE '%_pkey'
                    ORDER BY tablename, indexname
                """)
                
                indexes = cursor.fetchall()
                
                with self.target_conn.cursor() as target_cursor:
                    for idx_name, table_name, idx_def in indexes:
                        try:
                            target_cursor.execute(idx_def)
                            logger.info(f"✅ Created index: {idx_name} on {table_name}")
                        except psycopg2.errors.DuplicateTable:
                            logger.info(f"   Index {idx_name} already exists")
                        except Exception as e:
                            logger.warning(f"   Could not create index {idx_name}: {str(e)}")
                
                self.target_conn.commit()
                
        except Exception as e:
            logger.warning(f"Index migration issue: {str(e)}")
    
    def verify_migration(self):
        """Verify that all data was migrated correctly"""
        logger.info("\n" + "="*60)
        logger.info("VERIFICATION")
        logger.info("="*60)
        
        verification_results = {}
        
        for table in self.tables_order:
            with self.source_conn.cursor() as source_cursor:
                source_cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                source_count = source_cursor.fetchone()[0]
            
            with self.target_conn.cursor() as target_cursor:
                try:
                    target_cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                    target_count = target_cursor.fetchone()[0]
                    
                    if source_count == target_count:
                        logger.info(f"✅ {table}: {source_count} rows (matched)")
                        verification_results[table] = 'OK'
                    else:
                        logger.warning(f"⚠️  {table}: Source={source_count}, Target={target_count} (mismatch)")
                        verification_results[table] = 'MISMATCH'
                        
                except Exception as e:
                    logger.error(f"❌ {table}: Could not verify ({str(e)})")
                    verification_results[table] = 'ERROR'
        
        return verification_results
    
    def run_migration(self):
        """Execute the complete migration process"""
        try:
            logger.info("\n" + "🚀"*20)
            logger.info("STARTING SUPABASE TO NEON MIGRATION")
            logger.info("🚀"*20)
            
            # Connect to databases
            self.connect()
            
            # Get tables in dependency order
            self.get_tables_in_order()
            
            # Create tables and copy data
            logger.info("\n" + "="*60)
            logger.info("MIGRATING TABLES AND DATA")
            logger.info("="*60)
            
            for table in self.tables_order:
                logger.info(f"\nProcessing table: {table}")
                
                # Create table structure
                if self.create_table(table):
                    # Copy data
                    self.copy_table_data(table)
                    self.migration_stats['tables_migrated'] += 1
            
            # Migrate sequences
            logger.info("\n" + "="*60)
            logger.info("MIGRATING SEQUENCES")
            logger.info("="*60)
            self.migrate_sequences()
            
            # Migrate constraints
            logger.info("\n" + "="*60)
            logger.info("MIGRATING CONSTRAINTS")
            logger.info("="*60)
            self.migrate_constraints()
            
            # Migrate indexes
            logger.info("\n" + "="*60)
            logger.info("MIGRATING INDEXES")
            logger.info("="*60)
            self.migrate_indexes()
            
            # Verify migration
            verification = self.verify_migration()
            
            # Print summary
            logger.info("\n" + "="*60)
            logger.info("MIGRATION SUMMARY")
            logger.info("="*60)
            logger.info(f"Tables migrated: {self.migration_stats['tables_migrated']}")
            logger.info(f"Total rows migrated: {self.migration_stats['rows_migrated']}")
            logger.info(f"Errors encountered: {len(self.migration_stats['errors'])}")
            
            if self.migration_stats['errors']:
                logger.error("\nErrors:")
                for error in self.migration_stats['errors']:
                    logger.error(f"  - {error}")
            
            # Check verification results
            failed_tables = [t for t, status in verification.items() if status != 'OK']
            if not failed_tables:
                logger.info("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
                return True
            else:
                logger.warning(f"\n⚠️  Migration completed with issues in tables: {', '.join(failed_tables)}")
                return False
                
        except Exception as e:
            logger.error(f"\n💥 MIGRATION FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            # Close connections
            if self.source_conn:
                self.source_conn.close()
            if self.target_conn:
                self.target_conn.close()

def main():
    """Main migration function"""
    
    # Create backup of current .env file
    logger.info("Creating backup of .env file...")
    with open('.env', 'r') as f:
        env_content = f.read()
    
    backup_file = f'.env.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    with open(backup_file, 'w') as f:
        f.write(env_content)
    logger.info(f"✅ Backup saved to {backup_file}")
    
    # Get Supabase URL (we'll temporarily switch back to get data)
    supabase_url = "postgresql://postgres.ibgcfbnqqbdqyukhxcuz:shamsear1234@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
    
    # Get Neon URL from current environment
    neon_url = os.environ.get('DATABASE_URL')
    
    if not neon_url or 'neon.tech' not in neon_url:
        logger.error("Neon database URL not found in environment variables")
        sys.exit(1)
    
    logger.info(f"\n📍 Source: Supabase")
    logger.info(f"📍 Target: Neon\n")
    
    # Ask for confirmation
    print("\n" + "⚠️ "*10)
    print("WARNING: This will REPLACE all data in your Neon database!")
    print("Make sure you have a backup if needed.")
    print("⚠️ "*10 + "\n")
    
    response = input("Do you want to proceed? (yes/no): ").strip().lower()
    if response != 'yes':
        logger.info("Migration cancelled by user")
        sys.exit(0)
    
    # Run migration
    migrator = DatabaseMigrator(supabase_url, neon_url)
    success = migrator.run_migration()
    
    if success:
        logger.info("\n✅ Migration completed successfully!")
        logger.info("Your application is now using Neon database.")
        logger.info(f"\nBackup of old configuration saved to: {backup_file}")
        sys.exit(0)
    else:
        logger.error("\n❌ Migration completed with some issues. Please review the logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
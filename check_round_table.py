import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def check_round_table():
    """Check the round table structure and dependencies"""
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("=== ROUND TABLE ANALYSIS ===")
        print()
        
        # 1. Check table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'round'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        print("📋 Table Structure:")
        print("-" * 50)
        for col in columns:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            max_length = f"({col[4]})" if col[4] else ""
            default = f" DEFAULT {col[3]}" if col[3] else ""
            print(f"  - {col[0]}: {col[1]}{max_length} {nullable}{default}")
        
        # 2. Check current data
        cursor.execute("SELECT COUNT(*) FROM round")
        count = cursor.fetchone()[0]
        print(f"\n📊 Current Records: {count}")
        
        if count > 0:
            cursor.execute("SELECT * FROM round ORDER BY id LIMIT 5")
            sample_data = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            print(f"\n🔍 Sample Data:")
            print(f"Columns: {column_names}")
            for i, row in enumerate(sample_data, 1):
                print(f"Row {i}: {row}")
        
        # 3. Check foreign key relationships (tables that reference round)
        cursor.execute("""
            SELECT 
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name='round'
        """)
        
        foreign_keys = cursor.fetchall()
        
        print(f"\n🔗 Tables that reference 'round' table:")
        print("-" * 50)
        if foreign_keys:
            for fk in foreign_keys:
                print(f"  - {fk[0]}.{fk[1]} → round.{fk[3]}")
                
                # Check how many records in each referencing table
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {fk[0]} WHERE {fk[1]} IS NOT NULL")
                    ref_count = cursor.fetchone()[0]
                    print(f"    └─ {ref_count} records reference round table")
                except Exception as e:
                    print(f"    └─ Error checking references: {e}")
        else:
            print("  ✅ No tables reference the round table")
        
        # 4. Check what round references (outgoing foreign keys)
        cursor.execute("""
            SELECT 
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name='round'
        """)
        
        outgoing_fks = cursor.fetchall()
        
        print(f"\n🔗 Tables that 'round' references:")
        print("-" * 50)
        if outgoing_fks:
            for fk in outgoing_fks:
                print(f"  - round.{fk[1]} → {fk[2]}.{fk[3]}")
        else:
            print("  ✅ Round table doesn't reference other tables")
        
        # 5. Check current sequence value
        cursor.execute("SELECT last_value FROM round_id_seq")
        last_value = cursor.fetchone()[0]
        print(f"\n🔢 Current Sequence Value: {last_value}")
        
        print(f"\n⚠️  POTENTIAL ISSUES IF RESET:")
        print("-" * 50)
        
        if foreign_keys:
            print("❌ CRITICAL: Other tables reference this round table!")
            print("   Truncating round will break foreign key constraints.")
            print("   You need to:")
            print("   1. First truncate/delete referencing table data, OR")
            print("   2. Use CASCADE (will delete related data in other tables)")
            
            for fk in foreign_keys:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {fk[0]} WHERE {fk[1]} IS NOT NULL")
                    ref_count = cursor.fetchone()[0]
                    if ref_count > 0:
                        print(f"   ⚠️  {fk[0]} has {ref_count} records that will be affected")
                except:
                    pass
        else:
            print("✅ SAFE: No foreign key constraints to worry about")
            
        if count > 0:
            print(f"⚠️  Will delete {count} existing round records")
        else:
            print("✅ Table is empty, safe to reset sequence")
            
    except Exception as e:
        print(f"Error analyzing round table: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    check_round_table()
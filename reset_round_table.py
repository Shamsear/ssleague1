import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def reset_round_table():
    """Reset the round table ID sequence to start from 1"""
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("=== RESETTING ROUND TABLE ===")
        
        # Double-check current state
        cursor.execute("SELECT COUNT(*) FROM round")
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT last_value FROM round_id_seq")
        current_seq = cursor.fetchone()[0]
        
        print(f"📊 Current records in round table: {count}")
        print(f"🔢 Current sequence value: {current_seq}")
        
        if count > 0:
            print("⚠️  WARNING: Table contains data!")
            response = input("Are you sure you want to delete all round data? (y/N): ").lower().strip()
            if response != 'y':
                print("❌ Reset cancelled.")
                return
        
        # Check if any referencing tables have data
        cursor.execute("SELECT COUNT(*) FROM player WHERE round_id IS NOT NULL")
        player_refs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bid WHERE round_id IS NOT NULL") 
        bid_refs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tiebreaker WHERE round_id IS NOT NULL")
        tiebreaker_refs = cursor.fetchone()[0]
        
        total_refs = player_refs + bid_refs + tiebreaker_refs
        
        if total_refs > 0:
            print(f"⚠️  WARNING: Found {total_refs} records in other tables referencing rounds!")
            print(f"   - Players with round_id: {player_refs}")
            print(f"   - Bids with round_id: {bid_refs}")  
            print(f"   - Tiebreakers with round_id: {tiebreaker_refs}")
            print("   These will need to be cleared or the operation will fail.")
            
            response = input("Continue anyway? This may require CASCADE deletion (y/N): ").lower().strip()
            if response != 'y':
                print("❌ Reset cancelled.")
                return
        
        print("\n🔄 Resetting round table...")
        
        try:
            # Method 1: Try simple truncate first
            if count == 0:
                print("📋 Table is empty, just resetting sequence...")
                cursor.execute("SELECT setval('round_id_seq', 1, false)")
            else:
                print("🗑️  Truncating table and resetting sequence...")
                cursor.execute("TRUNCATE TABLE round RESTART IDENTITY")
                
        except psycopg2.errors.ForeignKeyViolation:
            print("⚠️  Foreign key constraint detected, using CASCADE...")
            cursor.execute("TRUNCATE TABLE round RESTART IDENTITY CASCADE")
            print("🗑️  Truncated round table and related references with CASCADE")
        
        conn.commit()
        
        # Verify the reset
        cursor.execute("SELECT COUNT(*) FROM round")
        new_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT last_value, is_called FROM round_id_seq")
        seq_info = cursor.fetchone()
        
        print("\n✅ Reset completed successfully!")
        print(f"📊 Records in table: {new_count}")
        print(f"🔢 Sequence reset to: {seq_info[0]} (is_called: {seq_info[1]})")
        
        # Test by inserting a sample record
        print("\n🧪 Testing with sample insert...")
        cursor.execute("""
            INSERT INTO round (position, status) 
            VALUES ('GK', 'test') 
            RETURNING id
        """)
        test_id = cursor.fetchone()[0]
        print(f"✅ Test insert successful, got ID: {test_id}")
        
        # Clean up test record
        cursor.execute("DELETE FROM round WHERE id = %s", (test_id,))
        cursor.execute("SELECT setval('round_id_seq', 1, false)")  # Reset again after test
        conn.commit()
        print("🧹 Test record cleaned up, sequence reset to 1")
        
    except Exception as e:
        print(f"❌ Error resetting round table: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    """Main function"""
    try:
        reset_round_table()
        print(f"\n🎉 Round table reset complete! Next inserted round will have ID = 1")
        
    except Exception as e:
        print(f"\n💥 Reset failed: {e}")

if __name__ == "__main__":
    main()
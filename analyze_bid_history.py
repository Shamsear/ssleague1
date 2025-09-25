import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def analyze_bid_history_preservation():
    """Analyze what bid history will be preserved vs cleaned"""
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("=== BID HISTORY PRESERVATION ANALYSIS ===")
        
        # Simulate the cleanup logic to see what would be preserved
        print("\n📊 Current bid breakdown:")
        
        # 1. Total bids from inactive rounds
        cursor.execute("""
            SELECT COUNT(*) 
            FROM bid b
            JOIN round r ON b.round_id = r.id
            WHERE r.is_active = false
        """)
        total_inactive_bids = cursor.fetchone()[0]
        print(f"   Total bids from inactive rounds: {total_inactive_bids}")
        
        # 2. Bids that will be PRESERVED (winning bids - player allocated to bidding team)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM bid b
            JOIN round r ON b.round_id = r.id
            JOIN player p ON b.player_id = p.id
            WHERE r.is_active = false 
              AND p.team_id IS NOT NULL 
              AND p.team_id = b.team_id
        """)
        preserved_bids = cursor.fetchone()[0]
        print(f"   ✅ Bids to be PRESERVED: {preserved_bids} (winning bids)")
        
        # 3. Bids that will be CLEANED (losing bids)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM bid b
            JOIN round r ON b.round_id = r.id
            JOIN player p ON b.player_id = p.id
            WHERE r.is_active = false 
              AND (p.team_id IS NULL OR p.team_id != b.team_id)
        """)
        cleaned_bids = cursor.fetchone()[0]
        print(f"   🗑️  Bids to be CLEANED: {cleaned_bids} (losing bids)")
        
        # Verify totals match
        if total_inactive_bids == preserved_bids + cleaned_bids:
            print(f"   ✅ Totals match: {total_inactive_bids} = {preserved_bids} + {cleaned_bids}")
        else:
            print(f"   ⚠️  Totals mismatch: {total_inactive_bids} ≠ {preserved_bids} + {cleaned_bids}")
        
        # 4. Show detailed breakdown of what will be preserved
        print("\n🏆 WINNING BIDS TO BE PRESERVED (bid history):")
        cursor.execute("""
            SELECT 
                t.name as team_name,
                p.name as player_name,
                b.amount,
                r.position,
                r.id as round_id,
                b.timestamp
            FROM bid b
            JOIN round r ON b.round_id = r.id
            JOIN player p ON b.player_id = p.id
            JOIN team t ON b.team_id = t.id
            WHERE r.is_active = false 
              AND p.team_id IS NOT NULL 
              AND p.team_id = b.team_id
            ORDER BY r.position, t.name, b.timestamp
        """)
        
        winning_bids = cursor.fetchall()
        if winning_bids:
            current_team = None
            for team_name, player_name, amount, position, round_id, timestamp in winning_bids:
                if team_name != current_team:
                    print(f"\n   Team '{team_name}':")
                    current_team = team_name
                print(f"     - Won '{player_name}' ({position}) for £{amount:,} in Round {round_id}")
        else:
            print("   (No winning bids found)")
        
        # 5. Show what will be cleaned (first 10 examples)
        print("\n❌ LOSING BIDS TO BE CLEANED (examples):")
        cursor.execute("""
            SELECT 
                t.name as team_name,
                p.name as player_name,
                b.amount,
                r.position,
                r.id as round_id,
                CASE 
                    WHEN p.team_id IS NULL THEN 'Player not allocated'
                    ELSE CONCAT('Player went to team_id ', p.team_id)
                END as reason
            FROM bid b
            JOIN round r ON b.round_id = r.id
            JOIN player p ON b.player_id = p.id
            LEFT JOIN team t ON b.team_id = t.id
            WHERE r.is_active = false 
              AND (p.team_id IS NULL OR p.team_id != b.team_id)
            ORDER BY r.position, b.timestamp
            LIMIT 10
        """)
        
        losing_bids = cursor.fetchall()
        if losing_bids:
            for team_name, player_name, amount, position, round_id, reason in losing_bids:
                print(f"   - Team '{team_name}' bid £{amount:,} on '{player_name}' ({position}, Round {round_id}) - {reason}")
        else:
            print("   (No losing bids found)")
        
        # 6. Summary for bid history access
        print(f"\n📋 BID HISTORY ACCESSIBILITY AFTER CLEANUP:")
        print(f"   ✅ Teams CAN view their successful bids: {preserved_bids} bids preserved")
        print(f"   ❌ Teams CANNOT view their unsuccessful bids: {cleaned_bids} bids removed")
        print(f"\n💡 RECOMMENDATION:")
        
        if cleaned_bids > 0:
            print("   Consider adding a bid_history table to archive ALL bids before cleanup")
            print("   This would preserve complete auction history while still cleaning up active interfaces")
        else:
            print("   Current cleanup approach is safe - no historical data loss concerns")
    
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    analyze_bid_history_preservation()
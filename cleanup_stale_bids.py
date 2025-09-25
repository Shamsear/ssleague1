import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def cleanup_stale_bids():
    """Clean up stale bids from inactive rounds"""
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("=== CLEANING UP STALE BIDS ===")
        
        # Find all bids from inactive rounds where:
        # 1. The player is not allocated to anyone (team_id = NULL), OR
        # 2. The player is allocated to a different team than the one that placed the bid
        cursor.execute("""
            SELECT 
                b.id as bid_id,
                b.team_id as bid_team_id,
                b.round_id,
                b.amount,
                r.position,
                r.is_active,
                p.team_id as player_team_id,
                p.name as player_name,
                t.name as team_name
            FROM bid b
            JOIN round r ON b.round_id = r.id
            JOIN player p ON b.player_id = p.id
            LEFT JOIN team t ON b.team_id = t.id
            WHERE r.is_active = false 
              AND (p.team_id IS NULL OR p.team_id != b.team_id)
            ORDER BY r.position, b.round_id, b.team_id
        """)
        
        stale_bids = cursor.fetchall()
        
        if not stale_bids:
            print("✅ No stale bids found - database is clean!")
            return
        
        print(f"⚠️  Found {len(stale_bids)} stale bids from inactive rounds:")
        
        # Group by position for better reporting
        by_position = {}
        for bid in stale_bids:
            bid_id, bid_team_id, round_id, amount, position, is_active, player_team_id, player_name, team_name = bid
            
            if position not in by_position:
                by_position[position] = []
            by_position[position].append({
                'bid_id': bid_id,
                'round_id': round_id,
                'amount': amount,
                'player_name': player_name,
                'team_name': team_name,
                'player_team_id': player_team_id,
                'bid_team_id': bid_team_id
            })
        
        # Display what will be cleaned
        for position, bids in by_position.items():
            print(f"\n  {position} Position:")
            for bid in bids:
                if bid['player_team_id'] is None:
                    status = "unallocated player"
                else:
                    status = f"player allocated to different team (team_id: {bid['player_team_id']})"
                
                print(f"    - Bid {bid['bid_id']}: Team '{bid['team_name']}' bid £{bid['amount']:,} on '{bid['player_name']}' (Round {bid['round_id']}, {status})")
        
        # Ask for confirmation
        print(f"\n🗑️  This will delete {len(stale_bids)} stale bids.")
        print("These are bids from inactive rounds where:")
        print("  • Player is not allocated to anyone, OR")
        print("  • Player is allocated to a different team than the bidder")
        print("\nThis cleanup prevents old bids from showing in new round interfaces.")
        
        confirm = input("\nProceed with cleanup? (y/N): ").lower().strip()
        
        if confirm != 'y':
            print("❌ Cleanup cancelled.")
            return
        
        # Delete the stale bids
        bid_ids = [bid[0] for bid in stale_bids]  # Extract bid IDs
        
        # Use parameterized query for safety
        placeholders = ','.join(['%s'] * len(bid_ids))
        cursor.execute(f"DELETE FROM bid WHERE id IN ({placeholders})", bid_ids)
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"\n✅ Successfully deleted {deleted_count} stale bids!")
        print("🎉 Stale bid cleanup complete!")
        
        # Verify cleanup
        cursor.execute("""
            SELECT COUNT(*) 
            FROM bid b
            JOIN round r ON b.round_id = r.id
            JOIN player p ON b.player_id = p.id
            WHERE r.is_active = false 
              AND (p.team_id IS NULL OR p.team_id != b.team_id)
        """)
        
        remaining_stale = cursor.fetchone()[0]
        if remaining_stale == 0:
            print("✅ Verification: No stale bids remaining")
        else:
            print(f"⚠️  Warning: {remaining_stale} stale bids still remain")
    
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    cleanup_stale_bids()
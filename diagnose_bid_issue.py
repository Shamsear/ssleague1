import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def diagnose_bid_issue():
    """Diagnose the stale bid issue"""
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        print("=== DIAGNOSING BID ISSUE ===")
        
        # 1. Check for active rounds and their IDs
        cursor.execute("SELECT id, position, is_active FROM round ORDER BY id DESC LIMIT 10")
        rounds = cursor.fetchall()
        
        print(f"\n📊 Recent Rounds:")
        for round_id, position, is_active in rounds:
            status = "ACTIVE" if is_active else "inactive"
            print(f"   Round {round_id}: {position} - {status}")
        
        # 2. Get active round IDs
        cursor.execute("SELECT id FROM round WHERE is_active = true")
        active_round_ids = [row[0] for row in cursor.fetchall()]
        print(f"\n🎯 Active Round IDs: {active_round_ids}")
        
        # 3. Check for bids associated with inactive rounds
        cursor.execute("""
            SELECT 
                b.id as bid_id,
                b.team_id,
                b.player_id,
                b.round_id,
                b.amount,
                r.position,
                r.is_active,
                t.name as team_name,
                p.name as player_name
            FROM bid b
            JOIN round r ON b.round_id = r.id
            LEFT JOIN team t ON b.team_id = t.id
            LEFT JOIN player p ON b.player_id = p.id
            WHERE r.is_active = false
            ORDER BY b.timestamp DESC
            LIMIT 20
        """)
        
        stale_bids = cursor.fetchall()
        print(f"\n⚠️  Found {len(stale_bids)} bids from inactive rounds:")
        
        for bid in stale_bids:
            bid_id, team_id, player_id, round_id, amount, position, is_active, team_name, player_name = bid
            print(f"   Bid {bid_id}: Team '{team_name}' bid £{amount:,} on '{player_name}' (Round {round_id} - {position}, Active: {is_active})")
        
        # 4. Check for bids in active rounds
        if active_round_ids:
            placeholders = ','.join(['%s'] * len(active_round_ids))
            cursor.execute(f"""
                SELECT 
                    b.id as bid_id,
                    b.team_id,
                    b.player_id,
                    b.round_id,
                    b.amount,
                    r.position,
                    r.is_active,
                    t.name as team_name,
                    p.name as player_name
                FROM bid b
                JOIN round r ON b.round_id = r.id
                LEFT JOIN team t ON b.team_id = t.id
                LEFT JOIN player p ON b.player_id = p.id
                WHERE b.round_id IN ({placeholders})
                ORDER BY b.timestamp DESC
            """, active_round_ids)
            
            active_bids = cursor.fetchall()
            print(f"\n✅ Found {len(active_bids)} bids in active rounds:")
            
            for bid in active_bids:
                bid_id, team_id, player_id, round_id, amount, position, is_active, team_name, player_name = bid
                print(f"   Bid {bid_id}: Team '{team_name}' bid £{amount:,} on '{player_name}' (Round {round_id} - {position})")
        
        # 5. Check for teams with multiple bids for same position across rounds
        cursor.execute("""
            SELECT 
                t.name as team_name,
                r.position,
                COUNT(b.id) as bid_count,
                STRING_AGG(DISTINCT CONCAT('Round ', r.id, ' (', 
                    CASE WHEN r.is_active THEN 'Active' ELSE 'Inactive' END, 
                    ')'), ', ') as rounds
            FROM bid b
            JOIN round r ON b.round_id = r.id
            JOIN team t ON b.team_id = t.id
            GROUP BY t.name, r.position
            HAVING COUNT(b.id) > 1
            ORDER BY t.name, r.position
        """)
        
        multi_bids = cursor.fetchall()
        if multi_bids:
            print(f"\n🔍 Teams with multiple bids for same position:")
            for team_name, position, bid_count, rounds in multi_bids:
                print(f"   Team '{team_name}' - {position}: {bid_count} bids across {rounds}")
        else:
            print(f"\n✅ No teams found with multiple bids for same position")
        
        # 6. Check for specific problematic scenario: same team, same position, different rounds
        cursor.execute("""
            SELECT 
                t.name as team_name,
                r.position,
                b.round_id,
                r.is_active,
                COUNT(b.id) as bid_count,
                STRING_AGG(CONCAT(p.name, ' (£', b.amount, ')'), ', ') as player_bids
            FROM bid b
            JOIN round r ON b.round_id = r.id
            JOIN team t ON b.team_id = t.id
            JOIN player p ON b.player_id = p.id
            GROUP BY t.name, r.position, b.round_id, r.is_active
            HAVING COUNT(b.id) >= 1
            ORDER BY t.name, r.position, b.round_id DESC
        """)
        
        detailed_bids = cursor.fetchall()
        print(f"\n📋 Detailed bid breakdown by team/position/round:")
        current_team_position = None
        
        for team_name, position, round_id, is_active, bid_count, player_bids in detailed_bids:
            team_position = f"{team_name} - {position}"
            if team_position != current_team_position:
                print(f"\n   {team_position}:")
                current_team_position = team_position
            
            status = "ACTIVE" if is_active else "inactive"
            print(f"     Round {round_id} ({status}): {bid_count} bids - {player_bids}")
    
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    diagnose_bid_issue()
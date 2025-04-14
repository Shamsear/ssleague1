from app import app, db
from models import Round
from sqlalchemy import text

def fix_rounds():
    """Update all rounds to ensure they have proper status values"""
    with app.app_context():
        try:
            print("Checking all rounds for missing status values...")
            
            # Check for rounds with NULL status
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM round WHERE status IS NULL"))
                null_count = result.scalar()
                
                if null_count > 0:
                    print(f"Found {null_count} rounds with NULL status values")
                    
                    # Update active rounds
                    conn.execute(text("UPDATE round SET status = 'active' WHERE status IS NULL AND is_active = TRUE"))
                    
                    # Update inactive rounds
                    conn.execute(text("UPDATE round SET status = 'completed' WHERE status IS NULL AND is_active = FALSE"))
                    
                    print("Updated rounds with appropriate status values")
                else:
                    print("No rounds with NULL status values found")
                
            # Count rounds by status
            rounds = Round.query.all()
            status_counts = {}
            for r in rounds:
                if r.status not in status_counts:
                    status_counts[r.status] = 0
                status_counts[r.status] += 1
                
            print("\nRound status summary:")
            for status, count in status_counts.items():
                print(f"  {status}: {count} rounds")
                
            # Check for rounds waiting for tiebreakers
            waiting_rounds = Round.query.filter_by(status="waiting_for_tiebreakers").all()
            if waiting_rounds:
                print(f"\nFound {len(waiting_rounds)} rounds waiting for tiebreakers:")
                for r in waiting_rounds:
                    active_tiebreakers = Round.query.filter_by(
                        parent_round_id=r.id,
                        is_active=True
                    ).count()
                    
                    print(f"  Round {r.id}: {active_tiebreakers} active tiebreakers remaining")
            
            print("\nRound status check complete")
            
        except Exception as e:
            print(f"Error checking rounds: {str(e)}")
            import traceback
            traceback.print_exc()
            
if __name__ == "__main__":
    fix_rounds() 
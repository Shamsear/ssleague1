from app import app, db
from models import Round, AuctionStatus

def run_migration():
    """Add missing columns to the database schema."""
    print("Starting database schema migration...")
    
    # Connect to the database
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        try:
            # Check if Round.status column exists
            status_exists = False
            try:
                # Try to get a Round and access its status
                round = Round.query.first()
                if round:
                    _ = round.status
                    status_exists = True
            except Exception as e:
                if "column round.status does not exist" in str(e):
                    status_exists = False
                else:
                    # Some other error, re-raise
                    raise

            # Add Round.status column if it doesn't exist
            if not status_exists:
                print("Adding 'status' column to Round table...")
                connection.execute('ALTER TABLE round ADD COLUMN status VARCHAR(50) DEFAULT \'active\'')

            # Check if AuctionStatus table exists
            try:
                AuctionStatus.query.first()
                print("AuctionStatus table exists.")
            except Exception as e:
                if "relation \"auction_status\" does not exist" in str(e):
                    print("Creating AuctionStatus table...")
                    # Create the AuctionStatus table
                    connection.execute('''
                        CREATE TABLE auction_status (
                            id SERIAL PRIMARY KEY,
                            current_round INTEGER DEFAULT 0,
                            is_active BOOLEAN DEFAULT FALSE,
                            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            status VARCHAR(50) DEFAULT 'not_started',
                            finalization_status VARCHAR(100),
                            last_finalization_message VARCHAR(500)
                        )
                    ''')
                else:
                    # Some other error, re-raise
                    raise
            
            # Commit all changes
            transaction.commit()
            print("Migration completed successfully!")
            
        except Exception as e:
            # Roll back in case of error
            transaction.rollback()
            print(f"Migration failed: {str(e)}")
            raise

if __name__ == '__main__':
    run_migration() 
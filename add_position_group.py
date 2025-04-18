from sqlalchemy import create_engine, MetaData, Table, Column, String
from app import db, app
from models import Player

def add_position_group_column():
    print("Adding position_group column to Player table...")
    
    try:
        with app.app_context():
            # Check if the column exists already
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('player')]
            
            if 'position_group' not in columns:
                # Add the column
                metadata = MetaData()
                player_table = Table('player', metadata, autoload_with=db.engine)
                
                with db.engine.begin() as conn:
                    conn.execute(db.text("ALTER TABLE player ADD COLUMN position_group VARCHAR(10)"))
                
                print("Column added successfully!")
            else:
                print("Column already exists, skipping.")
            
            print("Migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    add_position_group_column() 
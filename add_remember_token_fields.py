from app import app, db
from models import User
from sqlalchemy import text

def add_remember_token_fields():
    """
    Add remember_token and remember_token_expiry fields to the User table
    """
    with app.app_context():
        # Check if columns already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        # Only proceed if columns don't exist yet
        needs_remember_token = 'remember_token' not in columns
        needs_expiry = 'remember_token_expiry' not in columns
        
        if needs_remember_token or needs_expiry:
            print("Adding remember token fields to User table...")
            
            # Create the SQL statements
            statements = []
            if needs_remember_token:
                statements.append("ALTER TABLE \"user\" ADD COLUMN remember_token VARCHAR(128);")
            if needs_expiry:
                statements.append("ALTER TABLE \"user\" ADD COLUMN remember_token_expiry TIMESTAMP;")
            
            # Execute the statements
            with db.engine.begin() as connection:
                try:
                    for statement in statements:
                        print(f"Executing: {statement}")
                        connection.execute(text(statement))
                    
                    print("Fields added successfully!")
                except Exception as e:
                    print(f"Error adding fields: {e}")
                    raise
        else:
            print("Remember token fields already exist in User table.")

if __name__ == "__main__":
    add_remember_token_fields() 
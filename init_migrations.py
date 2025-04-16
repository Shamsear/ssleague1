from app import app, db
from flask_migrate import Migrate, init, migrate, upgrade

# Initialize Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        # Initialize migrations
        init()
        
        # Create the first migration
        migrate()
        
        # Apply the migration
        upgrade()
        
        print("Migrations initialized successfully") 
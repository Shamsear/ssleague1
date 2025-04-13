from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import os
import argparse

def init_db(import_data=False):
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                is_admin=True,
                is_approved=True
            )
            admin.set_password('admin123')  # Change this password immediately after deployment
            db.session.add(admin)
            db.session.commit()
            print("Admin user created!")
        
        # Import data if requested and SQLite file exists
        if import_data and os.path.exists('efootball_real.db'):
            from migrate_sqlite_to_postgres import migrate_players
            migrate_players()
        
        print("Database initialized!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initialize the database')
    parser.add_argument('--import-data', action='store_true', help='Import data from SQLite')
    args = parser.parse_args()
    
    init_db(import_data=args.import_data) 
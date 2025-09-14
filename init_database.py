"""
Initialize database with all required tables including remember token fields
"""
from app import app, db
from models import User, Team, Category

def init_database():
    """Initialize the database with all tables"""
    with app.app_context():
        # Drop all tables (optional - comment out if you want to keep existing data)
        # db.drop_all()
        
        # Create all tables based on the models
        db.create_all()
        
        print("Database tables created successfully!")
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create default admin user
            admin = User(username='admin', is_admin=True, is_approved=True)
            admin.set_password('admin123')  # Change this password!
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created (username: admin, password: admin123)")
            print("⚠️  Please change the admin password after first login!")
        
        # Create default categories if they don't exist
        categories = [
            {'name': 'Red', 'color': 'red', 'priority': 1},
            {'name': 'Black', 'color': 'black', 'priority': 2},
            {'name': 'Blue', 'color': 'blue', 'priority': 3},
            {'name': 'White', 'color': 'white', 'priority': 4}
        ]
        
        for cat_data in categories:
            if not Category.query.filter_by(name=cat_data['name']).first():
                category = Category(**cat_data)
                db.session.add(category)
        
        db.session.commit()
        print("Default categories created")
        
        print("\n✅ Database initialization complete!")
        print("\nYou can now run the application with: python app.py")

if __name__ == '__main__':
    init_database()
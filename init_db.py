from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def init_db():
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
        
        print("Database initialized!")

if __name__ == '__main__':
    init_db() 
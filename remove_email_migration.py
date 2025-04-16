from app import app, db
from flask_migrate import Migrate, upgrade
from alembic import op
import sqlalchemy as sa

migrate = Migrate(app, db)

def upgrade_database():
    with app.app_context():
        # Create a migration to remove the email column
        op.drop_column('user', 'email')
        print("Email column has been removed from the user table")

if __name__ == '__main__':
    with app.app_context():
        upgrade_database() 
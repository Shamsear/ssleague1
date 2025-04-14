from migrate_db import migrate_database

if __name__ == "__main__":
    print("Running database migrations to fix schema issues...")
    migrate_database()
    print("Migration completed. Try accessing the dashboard again.") 
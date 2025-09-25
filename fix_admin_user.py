import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
cursor = conn.cursor()

print('Checking for admin users...')
cursor.execute('SELECT id, username, is_admin, user_role FROM "user" WHERE is_admin = true')
admin_users = cursor.fetchall()

if admin_users:
    print('Found admin users:')
    for user in admin_users:
        print(f'  {user[1]} (ID: {user[0]}) - is_admin: {user[2]}, user_role: {user[3]}')
    
    # Update admin users to super_admin
    cursor.execute('UPDATE "user" SET user_role = \'super_admin\' WHERE is_admin = true')
    rows_updated = cursor.rowcount
    conn.commit()
    print(f'Updated {rows_updated} admin user(s) to super_admin role')
else:
    print('No admin users found')

cursor.close()
conn.close()
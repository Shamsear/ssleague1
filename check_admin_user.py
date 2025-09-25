import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
cursor = conn.cursor()

print('Checking admin user details...')
cursor.execute("SELECT id, username, is_admin, user_role FROM \"user\" WHERE is_admin = true OR user_role = 'super_admin'")
admin_users = cursor.fetchall()

for user in admin_users:
    print(f'User: {user[1]} (ID: {user[0]}) - is_admin: {user[2]}, user_role: {user[3]}')

cursor.close()
conn.close()
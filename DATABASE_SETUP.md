# Database Setup - Render PostgreSQL

## Steps to set up Render PostgreSQL Database

### 1. Create PostgreSQL Database
- Go to https://render.com
- Click "New +" → "PostgreSQL"
- Fill out:
  - **Name**: `ssleague-db`
  - **Database**: `ssleague`
  - **User**: `ssleague_user`
  - **Region**: Same as web service
  - **Plan**: Free

### 2. Get Database URL
- Once created, go to your database service
- Copy the "External Database URL"
- It looks like: `postgresql://user:pass@host.render.com/dbname`

### 3. Update Web Service
- Go to your web service (`ssleague-new`)
- Click "Environment"
- Update `DATABASE_URL` with the new Render PostgreSQL URL
- Save changes

### 4. Deploy
- Your app will automatically redeploy
- Database tables will be created during deployment via `init_db.py`

## Benefits of Render PostgreSQL
✅ Same infrastructure - better connectivity  
✅ Free tier available  
✅ Easy to manage in same dashboard  
✅ Automatic backups  
✅ SSL connections by default

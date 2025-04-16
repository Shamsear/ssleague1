# Deployment Guide for eFootball Auction App on Render

This guide walks through deploying your eFootball Auction App to Render with your existing PostgreSQL database.

## Prerequisites

1. A [Render](https://render.com) account
2. Your application code pushed to a Git repository (GitHub, GitLab, etc.)
3. Your existing PostgreSQL database on Render:
   ```
   postgresql://efootball_auction_user:pXdd6FfpI9oRUoDoak5HKI8UJdtxcRMP@dpg-cvvltaadbo4c738a9hg0-a/efootball_auction
   ```

## Deployment Steps

### 1. Connect your repository to Render

1. Log in to your Render account
2. Click on "New" and select "Web Service"
3. Connect your Git repository where this code is stored

### 2. Configure your Web Service

1. Name: `efootball-auction-app`
2. Environment: `Python`
3. Region: Choose the region closest to your users
4. Branch: `main` (or your default branch)
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `gunicorn app:app`
7. Plan: Free

### 3. Set Environment Variables

Add the following environment variables:
- `SECRET_KEY`: Generate a random string (or let Render generate one for you)
- `DATABASE_URL`: `postgresql://efootball_auction_user:pXdd6FfpI9oRUoDoak5HKI8UJdtxcRMP@dpg-cvvltaadbo4c738a9hg0-a/efootball_auction`
- `PYTHON_VERSION`: `3.11.0`

### 4. Deploy your Service

1. Click "Create Web Service"
2. Wait for the build and deployment process to complete

## Database Initialization

The deployment will automatically:
1. Apply all database migrations to create tables
2. Create an admin user if one doesn't exist
3. Attempt to populate the database with data from the efootball_real.db file

If the automatic migration fails, you can run it manually:

1. Go to your web service in the Render dashboard
2. Click on "Shell"
3. Run the following commands:
   ```
   python init_db.py
   ```

## Accessing Your Application

1. Once deployed, click on the web service URL (something like `https://efootball-auction-app.onrender.com`)
2. Log in with the default admin credentials:
   - Username: `admin`
   - Password: `admin123`
3. **IMPORTANT**: Change the admin password immediately after your first login!

## Troubleshooting

If you encounter issues:

1. Check the application logs in the Render dashboard for error messages
2. Verify database connection:
   ```
   python -c "import psycopg2; conn = psycopg2.connect('postgresql://efootball_auction_user:pXdd6FfpI9oRUoDoak5HKI8UJdtxcRMP@dpg-cvvltaadbo4c738a9hg0-a/efootball_auction'); print('Connection successful')"
   ```
3. Manually run migrations and data population:
   ```
   flask db upgrade
   python migrate_data.py
   ```

For more help, visit the [Render Documentation](https://render.com/docs) 
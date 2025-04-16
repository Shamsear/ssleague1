# Deploying to Render

This guide will help you deploy your eFootball Auction application to Render.

## Prerequisites

- A Render account (https://render.com)
- Your code pushed to a Git repository (GitHub, GitLab, etc.)

## Deployment Steps

### 1. Create a Postgres Database on Render

1. Log in to your Render account
2. Go to the Dashboard and click "New +"
3. Select "PostgreSQL"
4. Fill in the following details:
   - Name: efootball-auction-db (or your preferred name)
   - Database: efootball_auction
   - User: (leave as default)
   - Region: (choose the closest to your users)
   - Plan: Free
5. Click "Create Database"
6. **Important**: Note the "Internal Database URL". You'll need this for your app configuration.

### 2. Deploy the Web Service

1. From your Render dashboard, click "New +" again
2. Select "Web Service"
3. Connect your Git repository
4. Fill in the following details:
   - Name: efootball-auction (or your preferred name)
   - Environment: Python
   - Region: (choose the closest to your users)
   - Branch: main (or your preferred branch)
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Plan: Free (or your preferred plan)
5. Add the following environment variables:
   - `DATABASE_URL`: Paste the Internal Database URL from step 1.6
   - `SECRET_KEY`: Generate a secure random string
6. Click "Create Web Service"

### 3. Set Up Your Database

After your service is deployed, you'll need to set up your database schema:

1. Go to your Web Service dashboard
2. Click "Shell" tab
3. Run the following commands:
   ```
   flask db upgrade
   ```

If you want to populate the database with initial data:
   ```
   python populate_db.py
   ```

### 4. Access Your Application

Once deployed, your application will be available at the URL provided by Render: 
`https://efootball-auction.onrender.com` (or your custom name)

## Troubleshooting

- Check the Logs section in your Web Service dashboard for any errors
- If you're seeing database connection issues, verify that your DATABASE_URL environment variable is correct
- If you need to make changes to your database schema, you can run migrations through the Shell tab

## Note on Free Tier Limitations

- Free tier PostgreSQL databases on Render are deleted after 90 days
- Free tier web services will spin down after 15 minutes of inactivity, which may cause a delay on the first request after inactivity 
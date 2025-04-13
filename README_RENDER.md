# eFootball Auction App - Render Deployment Guide

This document provides instructions for deploying the eFootball Auction application on Render.

## Deployment Steps

### Option 1: Deploy directly from the Render Dashboard

1. Log in to your Render account at https://dashboard.render.com/
2. Click on the "New +" button and select "Blueprint" from the dropdown menu
3. Connect your GitHub/GitLab repository containing this application
4. Render will automatically detect the `render.yaml` file and set up your services
5. Review the configuration and click "Apply"
6. Render will create a web service and a PostgreSQL database as specified in the `render.yaml` file

### Option 2: Deploy using Render's Deploy Button

1. Add the following button to your repository's README.md:
   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)
2. When users click this button, they'll be taken to Render where they can deploy the application

## Environment Variables

The following environment variables are automatically configured by Render:

- `DATABASE_URL`: Connection string for the PostgreSQL database
- `SECRET_KEY`: Auto-generated secure key for Flask sessions
- `PYTHON_VERSION`: Set to 3.10.12

## Database Migrations

To run database migrations manually after deployment:

1. Go to your web service on the Render dashboard
2. Click on "Shell"
3. Run the following command:
   ```
   flask db upgrade
   ```

## File Storage

Player photos are stored in the `images/player_photos` directory. Note that Render's free tier has an ephemeral filesystem, so uploaded files will be lost when the service restarts. For production use, consider using a cloud storage service like AWS S3 or Google Cloud Storage.

## Troubleshooting

If you encounter issues during deployment:

1. Check the logs in the Render dashboard
2. Ensure your database connection string is properly formatted
3. Verify that all required dependencies are listed in requirements.txt

For more information, visit the [Render documentation](https://render.com/docs).
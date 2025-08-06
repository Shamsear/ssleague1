# Render Deployment Checklist for SS League Flask App

## Prerequisites ✅
- [x] Flask app configured with proper config.py
- [x] Database connection handling for PostgreSQL
- [x] VAPID keys generated
- [x] render.yaml configured
- [x] requirements.txt complete
- [x] init_db.py with connection retry logic

## Step 1: Environment Variables Setup in Render Dashboard

### Required Environment Variables to Add Manually:

1. **VAPID_PRIVATE_KEY**
   ```
   LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1JR0hBZ0VBTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEJHMHdhd0lCQVFRZ3p5ZDRIOCt6eDZFRUQ5TDMKUkRTZ3E0S1p2NEFQWTJ3SmE5QUhPK3Jmd2wyaFJBTkNBQVQzdmdHWXpDcUQ4VnovRkh4V3BRQ1NYZUhPNnVqSQp3VXB2aTk2L3d6OXJQRkJZSzhDWGd4YzZKZ0ZXdlFaQ2JPb2gvNHhROGR0WTNIN1o4cjU0dlJvWQotLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tCg==
   ```

2. **VAPID_PUBLIC_KEY**
   ```
   LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFOTc0Qm1Nd3FnL0ZjL3hSOFZxVUFrbDNoenVybwp5TUZLYjR2ZXY4TS9henhRV0N2QWw0TVhPaVlCVnIwR1FtenFJZitNVVBIYldOeCsyZksrZUwwYUdBPT0KLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg==
   ```

3. **VAPID_CLAIMS_SUB**
   ```
   mailto:admin@yourdomain.com
   ```
   (Replace yourdomain.com with your actual domain)

### Auto-configured Environment Variables (handled by render.yaml):
- SECRET_KEY (auto-generated)
- DATABASE_URL (from Render PostgreSQL database)
- PYTHON_VERSION, FLASK_APP, FLASK_ENV, FLASK_DEBUG, WEB_CONCURRENCY

## Step 2: Database Configuration Verification

### Your current setup handles:
- ✅ postgres:// to postgresql:// conversion
- ✅ Invalid 'schema' parameter removal
- ✅ SSL requirements for cloud providers
- ✅ Connection pooling with timeouts
- ✅ Retry logic in init_db.py

## Step 3: Deployment Process

1. **Push your code to GitHub/GitLab**
2. **Create new Web Service in Render:**
   - Connect your repository
   - Use the render.yaml configuration
   - Verify the database is created first

3. **Add VAPID environment variables manually in Render Dashboard:**
   - Go to Environment tab in your service
   - Add the three VAPID variables above

4. **Monitor the build logs for:**
   - Dependency installation success
   - Database connection attempts
   - Database table creation
   - Admin user creation
   - Player import (if SQLite file exists)

## Step 4: Troubleshooting Common Issues

### If build fails during database initialization:

1. **Check DATABASE_URL format:**
   ```bash
   echo $DATABASE_URL
   ```
   Should start with postgresql:// and not have ?schema= parameter

2. **Verify database connectivity:**
   - Ensure Render PostgreSQL is running
   - Check if DATABASE_URL environment variable is correctly linked

3. **Database connection timeout:**
   - The init_db.py has retry logic with exponential backoff
   - Network issues are handled gracefully

### If app starts but crashes:

1. **Check application logs in Render dashboard**
2. **Verify all environment variables are set**
3. **Ensure gunicorn configuration is correct**

## Step 5: Post-Deployment Verification

1. **Test basic functionality:**
   - Visit your app URL
   - Try logging in with admin/admin123
   - Verify database operations work

2. **Test push notifications:**
   - Subscribe to notifications
   - Send a test notification

3. **Monitor application metrics:**
   - Check Render dashboard for resource usage
   - Monitor database connections

## Step 6: Security Hardening (Post-Deployment)

1. **Change default admin password**
2. **Set up proper domain for VAPID_CLAIMS_SUB**
3. **Consider upgrading to paid Render plan for production**

## Backup & Recovery

- Database backups: Render provides automated backups on paid plans
- Code backups: Ensure your code is in version control
- Environment variables: Keep a secure copy of your VAPID keys

## Additional Notes

- **Free Tier Limitations:** Render free tier has limitations on resource usage and uptime
- **Database Connection Limits:** Free PostgreSQL has connection limits
- **Cold Starts:** Free tier services may sleep after 15 minutes of inactivity

## Support & Debugging

If deployment fails, check:
1. Render build logs (detailed output)
2. Application logs (runtime errors)
3. Database connectivity (network issues)
4. Environment variables (missing or incorrect values)

Your app is well-configured for deployment. The main things to watch for are:
- Ensure VAPID keys are added to environment variables
- Monitor the database initialization process during build
- Verify all dependencies install correctly

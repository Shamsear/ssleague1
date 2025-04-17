# Football Auction System

A sophisticated auction system for football team management and player bidding, built with Flask, SQLAlchemy, and modern UI frameworks.

## Features

- User role-based authentication (Admin and Team managers)
- Team registration and comprehensive management
- Admin-controlled auction rounds with customizable timers
- Position-based and bulk bidding mechanisms
- Advanced tiebreaker system for contested bids
- Real-time bid tracking with interactive notifications
- Team balance and budget management
- Responsive glass-morphism UI optimized for both desktop and mobile
- Player statistics and performance tracking
- Push notifications for important events
- Export functionality for teams and player data

## Prerequisites

- Python 3.8 or higher
- SQLite (default) or PostgreSQL
- pip (Python package manager)
- Modern web browser with JavaScript enabled

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd football-auction-system
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Configure the database:
   - The system uses SQLite by default, which requires no additional setup
   - For PostgreSQL, create a database and update the connection string in the .env file

5. Create a `.env` file in the project root with the following content:
```
# For SQLite (default)
DATABASE_URL=sqlite:///auction.db
# For PostgreSQL (optional)
# DATABASE_URL=postgresql://username:password@localhost/football_auction_db
SECRET_KEY=your-secret-key-here
VAPID_PRIVATE_KEY=your-vapid-private-key  # For push notifications
VAPID_PUBLIC_KEY=your-vapid-public-key    # For push notifications
VAPID_CLAIMS=mailto:admin@example.com     # Contact for push notifications
```

6. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

7. (Optional) Import initial player data:
```bash
python init_db.py
```

## Running the Application

1. Start the Flask development server:
```bash
python app.py
```

2. Access the application at `http://localhost:5000`

## Usage

### For Team Managers
1. Register a new team account and wait for admin approval
2. Log in to access the team dashboard
3. View active rounds and place bids on players
4. Participate in tiebreakers for contested players
5. Manage your team's budget and squad composition
6. Export player statistics and team information

### For Admins
1. Log in with admin credentials (default: username 'admin')
2. Approve new team registrations
3. Configure auction settings (max rounds, min balance)
4. Start new standard or bulk bidding rounds
5. Monitor team activities and balances
6. Finalize rounds to allocate players
7. Manage password reset requests
8. Export comprehensive auction data

## Project Structure

```
football-auction-system/
├── app.py                 # Main application file
├── config.py              # Configuration settings
├── models.py              # Database models
├── requirements.txt       # Project dependencies
├── init_db.py             # Database initialization script
├── .env                   # Environment variables
├── static/                # Static files (CSS, JS, images)
│   ├── js/                # JavaScript files
│   ├── css/               # CSS files (if any)
│   └── images/            # Image assets
└── templates/             # HTML templates
    ├── base.html          # Base template with navigation
    ├── admin_dashboard.html      # Admin dashboard
    ├── admin_players.html        # Player management
    ├── admin_teams.html          # Team management
    ├── admin_rounds.html         # Round management
    ├── admin_bulk_round.html     # Bulk round management
    ├── admin_auction_settings.html  # Auction settings
    ├── team_dashboard.html       # Team dashboard
    ├── team_players.html         # Team players view
    ├── team_round.html           # Active round view
    ├── tiebreaker_team.html      # Tiebreaker interface
    └── various other templates
```

## Key Features in Detail

### Bidding Mechanisms
- **Standard Rounds**: Position-based rounds with customizable duration
- **Bulk Bidding**: Fixed-price rounds for multiple player acquisitions
- **Tiebreakers**: Real-time resolution for contested bids

### Team Management
- Squad composition tracking
- Position distribution visualization
- Budget management with balance history
- Player acquisition cost tracking

### Admin Tools
- Complete auction configuration
- User management and approval system
- Round management with timer controls
- Export capabilities for data analysis

## Deployment

For production deployment, consider using:
- Gunicorn as a WSGI server
- Nginx as a reverse proxy
- PostgreSQL for database (instead of SQLite)
- A proper VAPID key pair for push notifications

## Deploying to Render

Follow these steps to deploy the Football Auction System to Render:

### Prerequisites
- A [Render](https://render.com) account
- Your project in a Git repository (GitHub, GitLab, etc.)
- VAPID keys for push notifications (generate them locally before deployment)

### Step 1: Create a Web Service

1. Log in to your Render account
2. Click on "New" and select "Web Service"
3. Connect your Git repository
4. Fill in the following details:
   - **Name**: `football-auction`
   - **Environment**: `Python 3`
   - **Region**: Choose the region closest to your users
   - **Branch**: `main` (or your default branch)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

### Step 2: Configure Environment Variables

1. Scroll down to the "Environment" section
2. Add the following key-value pairs:
   - `SECRET_KEY`: Generate a secure random string
   - `DATABASE_URL`: This will be auto-filled if you connect a Render PostgreSQL database
   - `VAPID_PRIVATE_KEY`: Your generated private key
   - `VAPID_PUBLIC_KEY`: Your generated public key
   - `VAPID_CLAIMS`: `mailto:your-email@example.com`
   - `FLASK_ENV`: `production`

### Step 3: Add a PostgreSQL Database (Recommended)

1. Go to the Render dashboard and click "New" 
2. Select "PostgreSQL"
3. Choose a name and plan that fits your needs
4. After creation, note the "Internal Database URL"
5. Go back to your Web Service settings
6. Update the `DATABASE_URL` environment variable with the "Internal Database URL"

### Step 4: Deploy and Initialize the Database

1. Click "Create Web Service" to start the deployment
2. Once deployed, go to the "Shell" tab of your Web Service
3. Run the following commands to initialize the database:
   ```
   flask db init
   flask db migrate
   flask db upgrade
   ```
4. Optionally, create an admin user:
   ```
   python -c "from app import app, db; from models import User; app.app_context().push(); admin = User(username='admin', is_admin=True); admin.set_password('secure-password'); db.session.add(admin); db.session.commit()"
   ```

### Step 5: Custom Domain (Optional)

1. Go to the "Settings" tab of your Web Service
2. Scroll to the "Custom Domain" section
3. Click "Add Domain" and follow the instructions to configure your domain

### Step 6: Continuous Deployment

Render automatically deploys your app when you push to your default branch. For each deployment:

1. Update your code and push to your Git repository
2. Render will automatically build and deploy the new version
3. Monitor the "Logs" tab for any deployment issues

### Additional Notes

- **SSL**: Render provides free SSL certificates for all services
- **Auto-scaling**: Upgrade to paid plans for auto-scaling options
- **Database Backups**: Configure automatic backups for your PostgreSQL database
- **Monitoring**: Use the Render dashboard to monitor performance and logs

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
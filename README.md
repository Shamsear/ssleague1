# Auction System

A closed auction system for team management and player bidding, built with Flask, PostgreSQL, and Tailwind CSS.

## Features

- Team registration and management
- Admin-controlled auction rounds
- Position-based player bidding
- Real-time bid management
- Team balance tracking
- Modern and responsive UI

## Prerequisites

- Python 3.8 or higher
- PostgreSQL
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd auction-system
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

4. Set up the PostgreSQL database:
```bash
createdb auction_db
```

5. Create a `.env` file in the project root with the following content:
```
DATABASE_URL=postgresql://postgres:postgres@localhost/auction_db
SECRET_KEY=your-secret-key-here
```

6. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

## Running the Application

1. Start the Flask development server:
```bash
python app.py
```

2. Access the application at `http://localhost:5000`

## Deploying on Render

This application is configured for deployment on Render's cloud platform.

1. Create a new Render account at [render.com](https://render.com) if you don't have one.

2. From your Render dashboard, click "New" and select "Blueprint" to deploy from a Git repository.

3. Connect your GitHub/GitLab repository containing this application.

4. Render will automatically detect the `render.yaml` configuration file and set up your services.

5. You'll need to set up the following environment variables in the Render dashboard:
   - `SECRET_KEY`: A secure random string for session management
   - `DATABASE_URL`: This will be automatically provided by Render if you create a PostgreSQL database

6. After deployment, you can access your admin account with:
   - Username: `admin`
   - Password: `admin123`

7. **IMPORTANT**: Change the admin password immediately after first login for security reasons.

## Database Migration

The application includes a database migration script to transfer player data from the SQLite database (`efootball_real.db`) to PostgreSQL on Render:

1. Make sure your `efootball_real.db` file is included in your repository.

2. The migration happens automatically during the build process on Render through the `init_db.py --import-data` command.

3. To run the migration locally:
```bash
python init_db.py --import-data
```

4. To manually migrate only player data:
```bash
python migrate_sqlite_to_postgres.py
```

5. The migration script preserves player IDs, names, ratings, positions, nationalities, values, and playing styles.

## Usage

### For Teams
1. Register a new team account
2. Log in to access the team dashboard
3. View active rounds and place bids on players
4. Monitor your team's balance and acquired players

### For Admins
1. Log in with admin credentials
2. Start new rounds for different positions
3. Monitor team activities and balances
4. Finalize rounds to allocate players

## Project Structure

```
auction-system/
├── app.py              # Main application file
├── config.py           # Configuration settings
├── models.py           # Database models
├── requirements.txt    # Project dependencies
├── .env               # Environment variables
└── templates/         # HTML templates
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── admin_round.html
    └── team_round.html
```

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
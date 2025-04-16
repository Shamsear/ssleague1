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
# Initialize database migrations
flask db init
flask db migrate
flask db upgrade

# Initialize the database with tables and admin user
python init_db.py

# OR, to reset the database (drops all tables and recreates them):
python init_db.py --drop-all

# To also import players from efootball_real.db:
python init_db.py --drop-all --import-players
```

## Running the Application

1. Start the Flask development server:
```bash
python app.py
```

2. Access the application at `http://localhost:5000`

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
    ├── admin_dashboard.html
    └── team_dashboard.html
```

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Deployment on Render

### Prerequisites
- A Render account (https://render.com)
- A PostgreSQL database on Render or another provider

### Steps to Deploy

1. Create a new PostgreSQL database in Render or use an existing one
   - Note the connection string for later use

2. Create a new Web Service in Render:
   - Connect your GitHub repository
   - Choose "Python" as the environment
   - Use the following settings:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn app:app`

3. Add the following environment variables in Render dashboard:
   - `SECRET_KEY`: Generate a secure random string
   - `DATABASE_URL`: Your PostgreSQL connection string from step 1
   - `FLASK_APP`: app.py

4. Deploy the application
   - Render will automatically build and deploy your application
   - The deployment will automatically initialize the database and create migrations
   - The deployment will drop all existing tables and recreate them using the `--drop-all` flag
   - An admin user will be created with username 'admin' and password 'admin' (change this after first login)
   - Your app will be available at the URL provided by Render

### Using the render.yaml file (Alternative)

If you prefer to use Infrastructure as Code, you can use the provided `render.yaml` file:

1. Update the `DATABASE_URL` in the `render.yaml` file with your actual database connection string
2. Push the changes to your repository
3. In Render, choose "Blueprint" when creating a new service and select your repository
4. Render will automatically configure and deploy your application based on the settings in `render.yaml`

### After Deployment

If you need to reset the database after deployment:

1. Connect to your Render instance using the Shell option in the dashboard
2. Run the reset script:
```bash
# Reset the database (no players)
python reset_db.py

# Reset the database and import players
python reset_db.py --import-players
```
This will drop all tables and recreate them with a fresh admin user. 
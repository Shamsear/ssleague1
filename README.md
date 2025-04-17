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
from flask import Flask
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app
from app import app

# For Vercel serverless functions
from vercel_serverless_flask import make_handler

# Create the handler
handler = make_handler(app)

# Required for local development
if __name__ == "__main__":
    app.run() 
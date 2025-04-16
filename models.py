from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    team = db.relationship('Team', backref='user', uselist=False)
    password_reset_requests = db.relationship('PasswordResetRequest', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    balance = db.Column(db.Integer, default=15000)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    players = db.relationship('Player', backref='team', lazy=True)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(10), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'), nullable=True)
    acquisition_value = db.Column(db.Integer, nullable=True)
    
    # Added fields for efootball player attributes
    team_name = db.Column(db.String(100), nullable=True)
    nationality = db.Column(db.String(100), nullable=True)
    offensive_awareness = db.Column(db.Integer, nullable=True)
    ball_control = db.Column(db.Integer, nullable=True)
    dribbling = db.Column(db.Integer, nullable=True)
    tight_possession = db.Column(db.Integer, nullable=True)
    low_pass = db.Column(db.Integer, nullable=True)
    lofted_pass = db.Column(db.Integer, nullable=True)
    finishing = db.Column(db.Integer, nullable=True)
    heading = db.Column(db.Integer, nullable=True)
    set_piece_taking = db.Column(db.Integer, nullable=True)
    curl = db.Column(db.Integer, nullable=True)
    speed = db.Column(db.Integer, nullable=True)
    acceleration = db.Column(db.Integer, nullable=True)
    kicking_power = db.Column(db.Integer, nullable=True)
    jumping = db.Column(db.Integer, nullable=True)
    physical_contact = db.Column(db.Integer, nullable=True)
    balance = db.Column(db.Integer, nullable=True)
    stamina = db.Column(db.Integer, nullable=True)
    defensive_awareness = db.Column(db.Integer, nullable=True)
    tackling = db.Column(db.Integer, nullable=True)
    aggression = db.Column(db.Integer, nullable=True)
    defensive_engagement = db.Column(db.Integer, nullable=True)
    gk_awareness = db.Column(db.Integer, nullable=True)
    gk_catching = db.Column(db.Integer, nullable=True)
    gk_parrying = db.Column(db.Integer, nullable=True)
    gk_reflexes = db.Column(db.Integer, nullable=True)
    gk_reach = db.Column(db.Integer, nullable=True)
    overall_rating = db.Column(db.Integer, nullable=True)
    playing_style = db.Column(db.String(50), nullable=True)
    player_id = db.Column(db.Integer, nullable=True)

    def has_bid_from_team(self, team_id):
        return any(bid.team_id == team_id for bid in self.bids)

class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    players = db.relationship('Player', backref='round', lazy=True)
    bids = db.relationship('Bid', backref='round', lazy=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=300)
    status = db.Column(db.String(20), default="active")  # active, processing, completed
    max_bids_per_team = db.Column(db.Integer, default=5)  # Maximum bids each team can place

    def is_timer_expired(self):
        if not self.start_time:
            return False
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        return elapsed >= self.duration

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    is_hidden = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    team = db.relationship('Team', backref='bids')
    player = db.relationship('Player', backref='bids')

class Tiebreaker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    original_amount = db.Column(db.Integer, nullable=False)
    resolved = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    round = db.relationship('Round', backref='tiebreakers')
    player = db.relationship('Player', backref='tiebreakers')
    team_tiebreakers = db.relationship('TeamTiebreaker', backref='tiebreaker', lazy=True)

class TeamTiebreaker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tiebreaker_id = db.Column(db.Integer, db.ForeignKey('tiebreaker.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    new_amount = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    team = db.relationship('Team', backref='tiebreakers')

class PasswordResetRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def generate_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        return self.reset_token
    
    @classmethod
    def get_by_token(cls, token):
        return cls.query.filter_by(reset_token=token, status='approved').first() 
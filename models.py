from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    team = db.relationship('Team', backref='user', uselist=False)

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
    is_active = db.Column(db.Boolean, default=True)

    def get_player_count(self):
        return Player.query.filter_by(team_id=self.id).count()
    
    def get_position_counts(self):
        positions = {}
        for player in self.players:
            positions[player.position] = positions.get(player.position, 0) + 1
        return positions
    
    def get_total_bid_amount(self):
        """Get the total amount spent on successful bids by this team"""
        bids = Bid.query.filter_by(team_id=self.id).all()
        total = 0
        for bid in bids:
            player = Player.query.get(bid.player_id)
            if player and player.team_id == self.id:
                total += bid.amount
        return total
    
    def can_afford(self, amount):
        """Check if the team can afford a bid amount"""
        return self.balance >= amount

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(10), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'), nullable=True)
    
    # Additional fields from efootball_real.db
    team_name = db.Column(db.String(100))
    nationality = db.Column(db.String(100))
    offensive_awareness = db.Column(db.Integer)
    ball_control = db.Column(db.Integer)
    dribbling = db.Column(db.Integer)
    tight_possession = db.Column(db.Integer)
    low_pass = db.Column(db.Integer)
    lofted_pass = db.Column(db.Integer)
    finishing = db.Column(db.Integer)
    heading = db.Column(db.Integer)
    set_piece_taking = db.Column(db.Integer)
    curl = db.Column(db.Integer)
    speed = db.Column(db.Integer)
    acceleration = db.Column(db.Integer)
    kicking_power = db.Column(db.Integer)
    jumping = db.Column(db.Integer)
    physical_contact = db.Column(db.Integer)
    balance = db.Column(db.Integer)
    stamina = db.Column(db.Integer)
    defensive_awareness = db.Column(db.Integer)
    tackling = db.Column(db.Integer)
    aggression = db.Column(db.Integer)
    defensive_engagement = db.Column(db.Integer)
    gk_awareness = db.Column(db.Integer)
    gk_catching = db.Column(db.Integer)
    gk_parrying = db.Column(db.Integer)
    gk_reflexes = db.Column(db.Integer)
    gk_reach = db.Column(db.Integer)
    overall_rating = db.Column(db.Integer)
    playing_style = db.Column(db.String(100))
    player_id = db.Column(db.String(50))

    def has_bid_from_team(self, team_id):
        return any(bid.team_id == team_id for bid in self.bids)

    def can_team_bid(self, team_id):
        # Count total bids for this team
        total_bids = Bid.query.filter_by(team_id=team_id).count()
        return total_bids < 20

    def highest_bid(self, round_id=None):
        """Get the highest bid for this player in a specific round or any round"""
        query = Bid.query.filter_by(player_id=self.id)
        if round_id:
            query = query.filter_by(round_id=round_id)
        highest = query.order_by(Bid.amount.desc()).first()
        return highest
    
    def get_position_category(self):
        """Return a general position category (GK, DEF, MID, FWD)"""
        if self.position in ['GK']:
            return 'GK'
        elif self.position in ['CB', 'LB', 'RB', 'LWB', 'RWB']:
            return 'DEF'
        elif self.position in ['DMF', 'CMF', 'AMF', 'LMF', 'RMF']:
            return 'MID'
        elif self.position in ['LWF', 'RWF', 'SS', 'CF']:
            return 'FWD'
        else:
            return 'OTHER'
    
    def to_dict(self):
        """Return a dictionary representation of the player for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'team_id': self.team_id,
            'team_name': self.team_name,
            'nationality': self.nationality,
            'overall_rating': self.overall_rating,
            'playing_style': self.playing_style,
            'player_id': self.player_id
        }

class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(50), default="active")  # active, completed, waiting_for_tiebreakers
    players = db.relationship('Player', backref='round', lazy=True, foreign_keys='Player.round_id')
    bids = db.relationship('Bid', backref='round', lazy=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=300)
    is_tiebreaker = db.Column(db.Boolean, default=False)
    parent_round_id = db.Column(db.Integer, db.ForeignKey('round.id'), nullable=True)
    parent_round = db.relationship('Round', remote_side=[id], backref='tiebreaker_rounds')
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    tiebreaker_player = db.relationship('Player', foreign_keys=[player_id], backref='tiebreaker_rounds')
    max_bids_per_team = db.Column(db.Integer, default=1)  # Default to 1 bid per team

    def is_timer_expired(self):
        if not self.start_time:
            return False
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        return elapsed >= self.duration
        
    def has_bid_from_team(self, team_id):
        return any(bid.team_id == team_id for bid in self.bids)

    def get_team_bid_count(self, team_id):
        return sum(1 for bid in self.bids if bid.team_id == team_id)

    def get_remaining_time(self):
        """Get the remaining time in seconds for this round"""
        if not self.start_time:
            return self.duration
        
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        remaining = self.duration - elapsed
        return max(0, remaining)
    
    def get_highest_bid_for_player(self, player_id):
        """Get the highest bid for a specific player in this round"""
        return Bid.query.filter_by(
            round_id=self.id,
            player_id=player_id
        ).order_by(Bid.amount.desc()).first()
    
    def to_dict(self):
        """Return a dictionary representation of the round for API responses"""
        return {
            'id': self.id,
            'position': self.position,
            'is_active': self.is_active,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'duration': self.duration,
            'is_tiebreaker': self.is_tiebreaker,
            'parent_round_id': self.parent_round_id,
            'player_id': self.player_id,
            'remaining_time': self.get_remaining_time()
        }

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

class TiebreakerBid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    team = db.relationship('Team', backref='tiebreaker_bids')
    player = db.relationship('Player', backref='tiebreaker_bids')
    round = db.relationship('Round', backref='tiebreaker_bids')

class StarredPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    team = db.relationship('Team', backref='starred_players')
    player = db.relationship('Player', backref='starred_by')

class AuctionStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_round = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="not_started")  # not_started, in_progress, paused, completed
    finalization_status = db.Column(db.String(100), nullable=True)
    last_finalization_message = db.Column(db.String(500), nullable=True)
    
    def update_status(self, status, message=None):
        self.status = status
        self.last_updated = datetime.utcnow()
        if message:
            self.last_finalization_message = message
        db.session.commit()
    
    def get_current_round(self):
        """Get the current active round object"""
        if self.current_round <= 0:
            return None
        return Round.query.filter_by(position=str(self.current_round), is_active=True).first()
    
    def get_tiebreaker_count(self):
        """Get the count of active tiebreaker rounds"""
        return Round.query.filter_by(is_active=True, is_tiebreaker=True).count()
    
    def to_dict(self):
        """Return a dictionary representation of the auction status for API responses"""
        return {
            'current_round': self.current_round,
            'is_active': self.is_active,
            'status': self.status,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'finalization_status': self.finalization_status,
            'tiebreaker_count': self.get_tiebreaker_count()
        } 
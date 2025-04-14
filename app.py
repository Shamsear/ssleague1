from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Team, Player, Round, Bid, TiebreakerBid, StarredPlayer, PushSubscription
from config import Config
from forms import LoginForm, RegistrationForm
from werkzeug.security import generate_password_hash
import json
from datetime import datetime, timedelta
import os
import pandas as pd
import io
import pywebpush
from pywebpush import webpush, WebPushException
import base64
import socket_events  # Import the socket events module

app = Flask(__name__)
app.config.from_object(Config)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # Set remember cookie to last 30 days

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Socket.IO
socketio = socket_events.init_app(app)

# Add a Jinja helper for current time
@app.template_global()
def now():
    return datetime.utcnow()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            # Check if admin or approved user
            if user.is_admin or user.is_approved:
                login_user(user, remember=form.remember.data)
                return redirect(url_for('dashboard'))
            else:
                flash('Your account is waiting for admin approval. Please try again later.', 'warning')
        else:
            flash('Invalid username or password')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        
        team = Team(name=form.team_name.data, user=user)
        db.session.add(team)
        
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    # Check if any active rounds have expired
    active_rounds = Round.query.filter_by(is_active=True, is_tiebreaker=False).all()
    for round in active_rounds:
        if round.is_timer_expired():
            finalize_round_internal(round.id)
    
    # Check if any active tiebreaker rounds have expired
    active_tiebreakers = Round.query.filter_by(is_active=True, is_tiebreaker=True).all()
    for round in active_tiebreakers:
        if round.is_timer_expired():
            finalize_tiebreaker_round(round.id)
    
    # Refresh the data after potentially finalizing rounds
    if current_user.is_admin:
        teams = Team.query.all()
        active_rounds = Round.query.filter_by(is_active=True, is_tiebreaker=False).all()
        active_tiebreakers = Round.query.filter_by(is_active=True, is_tiebreaker=True).all()
        rounds = Round.query.all()
        
        # Get pending user approvals count
        pending_approvals = User.query.filter_by(is_approved=False, is_admin=False).count()
        
        return render_template('admin_dashboard.html', 
                              teams=teams, 
                              active_rounds=active_rounds,
                              active_tiebreakers=active_tiebreakers,
                              rounds=rounds, 
                              pending_approvals=pending_approvals,
                              config=Config)
    
    # For team users, get only the tiebreakers they're participating in
    team_id = current_user.team.id
    tiebreaker_round_ids = db.session.query(TiebreakerBid.round_id).filter_by(team_id=team_id).distinct().all()
    tiebreaker_round_ids = [r[0] for r in tiebreaker_round_ids]
    
    active_tiebreakers = Round.query.filter(
        Round.id.in_(tiebreaker_round_ids) if tiebreaker_round_ids else False,
        Round.is_active == True,
        Round.is_tiebreaker == True
    ).all()
    
    active_rounds = Round.query.filter_by(is_active=True, is_tiebreaker=False).all()
    past_rounds = Round.query.filter_by(is_active=False).all()
    
    return render_template('team_dashboard.html', 
                          active_rounds=active_rounds,
                          active_tiebreakers=active_tiebreakers,
                          past_rounds=past_rounds, 
                          config=Config)

@app.route('/team/round')
@login_required
def team_round():
    if current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    active_rounds = Round.query.filter_by(is_active=True).all()
    
    # No active rounds, redirect to dashboard
    if not active_rounds:
        flash('There are no active rounds at the moment.', 'info')
        return redirect(url_for('dashboard'))
    
    # Get the first active round
    active_round = active_rounds[0]
    
    return render_template('team_round.html', active_round=active_round)

@app.route('/team/tiebreaker/<int:round_id>')
@login_required
def team_tiebreaker(round_id):
    """Render the tiebreaker interface for a specific tiebreaker round"""
    if current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    # Get the tiebreaker round
    tiebreaker_round = Round.query.get_or_404(round_id)
    
    # Check if it's a tiebreaker round
    if not tiebreaker_round.is_tiebreaker:
        flash('This is not a tiebreaker round.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if the team is part of this tiebreaker
    team_id = current_user.team.id
    tiebreaker_bid = TiebreakerBid.query.filter_by(
        team_id=team_id,
        round_id=round_id
    ).first()
    
    if not tiebreaker_bid:
        flash('Your team is not part of this tiebreaker.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get the player for this tiebreaker
    player = Player.query.get(tiebreaker_round.player_id)
    
    # Get all competing teams
    competing_teams = db.session.query(Team).join(
        TiebreakerBid, TiebreakerBid.team_id == Team.id
    ).filter(
        TiebreakerBid.round_id == round_id
    ).all()
    
    # Check if the round has expired
    is_expired = tiebreaker_round.is_timer_expired()
    if is_expired:
        # Finalize the round
        finalize_tiebreaker_round(round_id)
        flash('This tiebreaker round has ended.', 'info')
        return redirect(url_for('dashboard'))
    
    return render_template(
        'team_tiebreaker.html',
        tiebreaker_round=tiebreaker_round,
        player=player,
        competing_teams=competing_teams,
        current_bid=tiebreaker_bid
    )

@app.route('/team/players')
@login_required
def team_players():
    if current_user.is_admin:
        return redirect(url_for('dashboard'))
    return render_template('team_players.html')

@app.route('/team/players/data')
@login_required
def team_players_data():
    if not current_user.team:
        flash('You need to be part of a team to view this page.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get query parameters for pagination and filtering
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 40, type=int)  # Default to 40 players per page
    position_filter = request.args.get('position', None)
    playing_style_filter = request.args.get('playing_style', None)
    search_query = request.args.get('q', None)
    
    # Build the query
    query = Player.query
    
    # Apply position filter if provided
    if position_filter and position_filter in Config.POSITIONS:
        query = query.filter_by(position=position_filter)
    
    # Apply playing style filter if provided
    if playing_style_filter and playing_style_filter in Config.PLAYING_STYLES:
        query = query.filter_by(playing_style=playing_style_filter)
    
    # Apply search filter if provided
    if search_query and search_query.strip():
        search_term = f"%{search_query.strip()}%"
        query = query.filter(Player.name.ilike(search_term))
    
    # Get paginated results
    players_pagination = query.order_by(Player.overall_rating.desc()).paginate(page=page, per_page=per_page)
    
    # Get the starred players for the current team
    team_id = current_user.team.id
    starred_players = StarredPlayer.query.filter_by(team_id=team_id).all()
    starred_player_ids = [sp.player_id for sp in starred_players]
    
    return render_template(
        'team_players_data.html',
        players_pagination=players_pagination,
        players=players_pagination.items,
        config=Config,
        current_position=position_filter,
        current_playing_style=playing_style_filter,
        search_query=search_query,
        starred_player_ids=starred_player_ids
    )

@app.route('/team/bids')
@login_required
def team_bids():
    if current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    active_rounds = Round.query.filter_by(is_active=True).all()
    return render_template('team_bids.html', active_rounds=active_rounds)

@app.route('/api/player/<int:player_id>')
@login_required
def get_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    # Find winning bid to get cost and acquisition date
    winning_bid = None
    if player.team_id:
        winning_bid = Bid.query.filter_by(
            team_id=player.team_id, 
            player_id=player.id
        ).order_by(Bid.amount.desc()).first()
    
    player_data = {
        'id': player.id,
        'name': player.name,
        'position': player.position,
        'overall_rating': player.overall_rating,
        'team_id': player.team_id,
        'player_id': player.player_id if hasattr(player, 'player_id') else None,
        # Cost and acquisition date
        'cost': winning_bid.amount if winning_bid else None,
        'acquired_at': winning_bid.timestamp.isoformat() if winning_bid else None,
        # Player attributes with safe access
        'speed': player.speed if hasattr(player, 'speed') else None,
        'dribbling': player.dribbling if hasattr(player, 'dribbling') else None,
        'offensive_awareness': player.offensive_awareness if hasattr(player, 'offensive_awareness') else None,
        'ball_control': player.ball_control if hasattr(player, 'ball_control') else None,
        'physical_contact': player.physical_contact if hasattr(player, 'physical_contact') else None,
        'finishing': player.finishing if hasattr(player, 'finishing') else None,
        'heading': player.heading if hasattr(player, 'heading') else None,
        'acceleration': player.acceleration if hasattr(player, 'acceleration') else None,
        'kicking_power': player.kicking_power if hasattr(player, 'kicking_power') else None,
        'defensive_awareness': player.defensive_awareness if hasattr(player, 'defensive_awareness') else None,
        'tackling': player.tackling if hasattr(player, 'tackling') else None,
        'aggression': player.aggression if hasattr(player, 'aggression') else None,
        'tight_possession': player.tight_possession if hasattr(player, 'tight_possession') else None,
        'low_pass': player.low_pass if hasattr(player, 'low_pass') else None,
        'lofted_pass': player.lofted_pass if hasattr(player, 'lofted_pass') else None,
        'stamina': player.stamina if hasattr(player, 'stamina') else None,
        'balance': player.balance if hasattr(player, 'balance') else None,
        'defensive_engagement': player.defensive_engagement if hasattr(player, 'defensive_engagement') else None,
        'set_piece_taking': player.set_piece_taking if hasattr(player, 'set_piece_taking') else None,
        'curl': player.curl if hasattr(player, 'curl') else None,
        'jumping': player.jumping if hasattr(player, 'jumping') else None,
        'nationality': player.nationality if hasattr(player, 'nationality') else None,
        'playing_style': player.playing_style if hasattr(player, 'playing_style') else None,
        'team_name': player.team_name if hasattr(player, 'team_name') else None,
        # Goalkeeper specific stats
        'gk_awareness': player.gk_awareness if hasattr(player, 'gk_awareness') else None,
        'gk_catching': player.gk_catching if hasattr(player, 'gk_catching') else None,
        'gk_parrying': player.gk_parrying if hasattr(player, 'gk_parrying') else None,
        'gk_reflexes': player.gk_reflexes if hasattr(player, 'gk_reflexes') else None,
        'gk_reach': player.gk_reach if hasattr(player, 'gk_reach') else None,
    }
    
    return jsonify(player_data)

@app.route('/api/round/<int:round_id>')
@login_required
def get_round(round_id):
    """API endpoint to get round details"""
    round = Round.query.get_or_404(round_id)
    
    # Get all players in this round
    players_data = []
    for player in round.players:
        player_data = {
            'id': player.id,
            'name': player.name,
            'position': player.position,
            'overall_rating': player.overall_rating,
            'team': None,
            'bid_amount': None
        }
        
        # Get winning bid for this player
        if not round.is_active:
            highest_bid = Bid.query.filter_by(player_id=player.id, round_id=round_id).order_by(Bid.amount.desc()).first()
            if highest_bid:
                player_data['bid_amount'] = highest_bid.amount
                player_data['team'] = {
                    'id': highest_bid.team.id,
                    'name': highest_bid.team.name
                }
        
        # If player is assigned to a team
        if player.team_id:
            player_data['team'] = {
                'id': player.team.id,
                'name': player.team.name
            }
            
        players_data.append(player_data)
    
    round_data = {
        'id': round.id,
        'position': round.position,
        'start_time': round.start_time.isoformat() if round.start_time else None,
        'duration': round.duration,
        'is_active': round.is_active,
        'max_bids_per_team': round.max_bids_per_team,
        'players': players_data
    }
    
    return jsonify(round_data)

@app.route('/start_round', methods=['POST'])
@login_required
def start_round():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    position = request.json.get('position')
    duration = request.json.get('duration', 300)  # Default to 5 minutes (300 seconds)
    max_bids_per_team = request.json.get('max_bids_per_team', 1)  # Default to 1 bid per team
    
    if not position or position not in Config.POSITIONS:
        return jsonify({'error': 'Invalid position'}), 400
    
    try:
        duration = int(duration)
        if duration < 30:  # Minimum duration of 30 seconds
            return jsonify({'error': 'Duration must be at least 30 seconds'}), 400
        # No maximum limit, allowing admin to set any reasonable duration
    except ValueError:
        return jsonify({'error': 'Invalid duration value'}), 400
    
    try:
        max_bids_per_team = int(max_bids_per_team)
        if max_bids_per_team < 1:  # Minimum of 1 bid per team
            return jsonify({'error': 'Maximum bids per team must be at least 1'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid maximum bids per team value'}), 400
    
    # Check if there's already an active round
    active_round = Round.query.filter_by(is_active=True).first()
    if active_round:
        return jsonify({
            'error': f'There is already an active round for position {active_round.position}. Please finalize it before starting a new round.'
        }), 400
    
    # Create new round with timer
    round = Round(
        position=position, 
        start_time=datetime.utcnow(),
        duration=duration,
        max_bids_per_team=max_bids_per_team
    )
    db.session.add(round)
    db.session.flush()  # Get the round ID
    
    # Add players of the specified position to the round
    players = Player.query.filter_by(position=position, team_id=None).all()
    for player in players:
        player.round_id = round.id
    
    db.session.commit()
    
    # Send notification to all teams about the new round
    send_notification_to_all_teams({
        'title': 'New Auction Round Started!',
        'body': f'A new round for {position} players has started. Place your bids now!',
        'data': {
            'type': 'round_start',
            'round_id': round.id,
            'position': position,
            'duration': duration
        },
        'tag': f'round_start_{round.id}',
        'renotify': True
    })
    
    # Broadcast round start via Socket.IO for real-time updates
    socket_events.broadcast_round_start({
        'round_id': round.id,
        'position': position,
        'duration': duration,
        'start_time': round.start_time.isoformat() if round.start_time else datetime.utcnow().isoformat(),
        'player_count': len(players),
        'max_bids_per_team': max_bids_per_team
    })
    
    return jsonify({
        'success': True,
        'message': f'Round for {position} started successfully',
        'round_id': round.id
    })

@app.route('/update_round_timer/<int:round_id>', methods=['POST'])
@login_required
def update_round_timer(round_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    round = Round.query.get_or_404(round_id)
    if not round.is_active:
        return jsonify({'error': 'Cannot update timer for an inactive round'}), 400
    
    duration = request.json.get('duration')
    if not duration:
        return jsonify({'error': 'Duration is required'}), 400
    
    try:
        duration = int(duration)
        if duration < 30:  # Minimum duration of 30 seconds
            return jsonify({'error': 'Duration must be at least 30 seconds'}), 400
        # No maximum limit, allowing admin to set any reasonable duration
    except ValueError:
        return jsonify({'error': 'Invalid duration value'}), 400
    
    round.duration = duration
    round.start_time = datetime.utcnow()  # Reset the timer
    db.session.commit()
    
    return jsonify({
        'message': 'Round timer updated successfully',
        'duration': duration,
        'expires_at': (round.start_time.isoformat() if round.start_time else None)
    })

@app.route('/check_round_status/<int:round_id>')
@login_required
def check_round_status(round_id):
    round = Round.query.get_or_404(round_id)
    current_time = datetime.utcnow()
    time_elapsed = (current_time - round.start_time).total_seconds()
    remaining = max(0, round.duration - time_elapsed)
    
    status = 'active'
    
    # Check if the round is already inactive
    if not round.is_active:
        status = 'ended'
    # Check if the timer has expired but round is still active
    elif time_elapsed >= round.duration:
        # Timer expired - finalize the round automatically
        if round.is_tiebreaker:
            finalize_tiebreaker_round(round.id)
        else:
            finalize_round_internal(round.id)
        status = 'ended'
    
    return jsonify({
        'status': status,
        'active': status == 'active',
        'remaining': remaining
    })

def finalize_round_internal(round_id):
    """
    Internal function to finalize a round and allocate players
    """
    # Get the round
    round = Round.query.get(round_id)
    if not round:
        return False, "Round not found"
    
    if not round.is_active:
        return False, "Round is already finalized"
    
    # Mark the round as inactive
    round.is_active = False
    
    # Get all bids for the round, ordered by amount (highest first)
    bids = Bid.query.filter_by(round_id=round_id).order_by(Bid.amount.desc()).all()
    
    # Get all players in this round
    players = Player.query.filter_by(round_id=round_id).all()
    
    if not bids:
        # If no bids were placed, just end the round and keep players available for the next round
        db.session.commit()
        
        # Send notification to admins that round ended with no bids
        send_notification_to_admins({
            'title': 'Round Ended - No Bids',
            'body': f'Round for {round.position} players ended with no bids placed.',
            'data': {
                'type': 'round_end',
                'round_id': round.id,
                'position': round.position,
                'result': 'no_bids'
            },
            'tag': f'round_end_{round.id}',
            'renotify': True
        })
        
        return True, "Round finalized successfully (no bids)"

    # Process all players
    winning_bids = []
    tiebreaker_players = []
    tiebreaker_teams = {}
    
    # Track which teams won players (for notifications)
    winning_teams = {}  # team_id -> [player_names]
    
    # Process each player separately
    for player in players:
        # Get bids for this player
        player_bids = [b for b in bids if b.player_id == player.id]
        
        if not player_bids:
            # No bids for this player, keep them available for the next round
            player.round_id = None
            continue
            
        # Get highest bid(s) for this player
        max_bid_amount = max(b.amount for b in player_bids)
        highest_bids = [b for b in player_bids if b.amount == max_bid_amount]
        
        if len(highest_bids) == 1:
            # Clear winner - allocate player to team
            winning_bid = highest_bids[0]
            team = Team.query.get(winning_bid.team_id)
            
            # Check if team has enough balance
            if team.balance >= winning_bid.amount:
                # Allocate player to team
                player.team_id = team.id
                player.round_id = None
                player.cost = winning_bid.amount
                player.acquired_at = datetime.utcnow()
                
                # Deduct amount from team balance
                team.balance -= winning_bid.amount
                
                # Record this as a winning bid
                winning_bids.append({
                    'player_name': player.name,
                    'team_name': team.name,
                    'amount': winning_bid.amount
                })
                
                # Track for notifications
                if team.id not in winning_teams:
                    winning_teams[team.id] = []
                winning_teams[team.id].append(player.name)
            else:
                # Team doesn't have enough balance, keep player available
                player.round_id = None
        else:
            # Multiple highest bids - prepare for tiebreaker
            tiebreaker_players.append(player)
            
            # Track the teams involved in this tiebreaker
            for bid in highest_bids:
                if player.id not in tiebreaker_teams:
                    tiebreaker_teams[player.id] = []
                tiebreaker_teams[player.id].append(bid.team_id)
    
    # Commit all changes
    db.session.commit()
    
    # Send notification to all teams about the round ending
    send_notification_to_all_teams({
        'title': 'Auction Round Ended',
        'body': f'The auction round for {round.position} players has ended.',
        'data': {
            'type': 'round_end',
            'round_id': round.id,
            'position': round.position
        },
        'tag': f'round_end_{round.id}',
        'renotify': True
    })
    
    # Broadcast round end via Socket.IO for real-time updates
    socket_events.broadcast_round_end({
        'round_id': round.id,
        'position': round.position,
        'winning_bids': winning_bids,
        'has_tiebreakers': len(tiebreaker_players) > 0
    })
    
    # Send notifications to teams that won players
    for team_id, player_names in winning_teams.items():
        if player_names:
            player_list = ', '.join(player_names)
            send_notification_to_team(team_id, {
                'title': 'You Won Players!',
                'body': f'You successfully acquired: {player_list}',
                'data': {
                    'type': 'player_won',
                    'player_names': player_names
                },
                'tag': f'player_won_{round.id}_{team_id}',
                'renotify': True
            })
    
    # If there are tiebreakers needed, create tiebreaker rounds
    if tiebreaker_players:
        tiebreaker_rounds = []
        
        for player in tiebreaker_players:
            team_ids = tiebreaker_teams.get(player.id, [])
            if not team_ids:
                continue
                
            # Create a tiebreaker round
            tiebreaker_round = Round(
                position=player.position,
                is_active=True,
                start_time=datetime.utcnow(),
                duration=180,  # 3 minutes for tiebreaker
                is_tiebreaker=True,
                parent_round_id=round_id,
                player_id=player.id
            )
            db.session.add(tiebreaker_round)
            db.session.flush()  # Get the round ID
            
            # Add the involved teams to the tiebreaker round
            for team_id in team_ids:
                # Get the original bid amount
                original_bid = next((b for b in bids if b.team_id == team_id and b.player_id == player.id), None)
                if original_bid:
                    tiebreaker_bid = TiebreakerBid(
                        team_id=team_id,
                        player_id=player.id,
                        round_id=tiebreaker_round.id,
                        amount=original_bid.amount
                    )
                    db.session.add(tiebreaker_bid)
            
            tiebreaker_rounds.append({
                'round_id': tiebreaker_round.id,
                'player_name': player.name,
                'team_count': len(team_ids)
            })
            
            # Send notification to teams involved in the tiebreaker
            for team_id in team_ids:
                send_notification_to_team(team_id, {
                    'title': 'Tiebreaker Round Started',
                    'body': f'You are in a tiebreaker for {player.name}. Submit your final bid now!',
                    'data': {
                        'type': 'tiebreaker_start',
                        'round_id': tiebreaker_round.id,
                        'player_id': player.id,
                        'player_name': player.name
                    },
                    'tag': f'tiebreaker_{tiebreaker_round.id}',
                    'renotify': True
                })
        
    db.session.commit()
    
    if tiebreaker_rounds:
        return True, {
            'message': 'Round finalized with tiebreakers',
            'winning_bids': winning_bids,
            'tiebreaker_rounds': tiebreaker_rounds
        }
    
    return True, {
        'message': 'Round finalized successfully',
        'winning_bids': winning_bids
    }

@app.route('/finalize_round/<int:round_id>', methods=['POST'])
@login_required
def finalize_round(round_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    round = Round.query.get_or_404(round_id)
    if not round.is_active:
        return jsonify({'error': 'Round already finalized'}), 400
    
    success = finalize_round_internal(round_id)
    if success:
        return jsonify({'message': 'Round finalized successfully'})
    else:
        return jsonify({'error': 'Failed to finalize round'}), 500

@app.route('/place_bid', methods=['POST'])
@login_required
def place_bid():
    if current_user.is_admin:
        return jsonify({'error': 'Admins cannot place bids'}), 403
    
    data = request.json
    round_id = data.get('round_id')
    player_id = data.get('player_id')
    amount = data.get('amount')
    
    if not all([round_id, player_id, amount]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    round = Round.query.get_or_404(round_id)
    if round.is_timer_expired():
        # If timer expired, finalize the round and reject the bid
        finalize_round_internal(round_id)
        return jsonify({'error': 'Round timer has expired'}), 400
    
    if amount < Config.MINIMUM_BID:
        return jsonify({'error': f'Bid must be at least {Config.MINIMUM_BID}'}), 400
    
    team = current_user.team
    if team.balance < amount:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    # Check if team has reached the maximum number of bids (20)
    total_bids = Bid.query.filter_by(team_id=team.id).count()
    if total_bids >= 20:
        return jsonify({'error': 'Maximum bid limit (20) reached for your team'}), 400
    
    # Count number of unique players this team has bid on in this round
    unique_player_bids_count = db.session.query(Bid.player_id).filter_by(
        team_id=team.id, 
        round_id=round_id
    ).distinct().count()
    
    # If bidding on a new player, check if already at the max bids per team limit
    has_bid_on_player = Bid.query.filter_by(
        team_id=team.id,
        round_id=round_id,
        player_id=player_id
    ).first() is not None
    
    if not has_bid_on_player and unique_player_bids_count >= round.max_bids_per_team:
        return jsonify({
            'error': f'You can only bid on {round.max_bids_per_team} player(s) per round. Please delete an existing bid if you wish to bid on a different player.'
        }), 400
    
    # Check if the team has already placed this bid amount on the same player
    existing_same_amount_bid = Bid.query.filter_by(
        team_id=team.id,
        round_id=round_id,
        player_id=player_id,
        amount=amount
    ).first()
    
    if existing_same_amount_bid:
        return jsonify({
            'error': f'You have already placed a bid of {amount} on this player. Please use a different amount.'
        }), 400
    
    # Check if the team has already placed this bid amount on ANY player in this round
    existing_bid_with_same_amount = Bid.query.filter_by(
        team_id=team.id,
        round_id=round_id,
        amount=amount
    ).first()
    
    if existing_bid_with_same_amount:
        other_player = Player.query.get(existing_bid_with_same_amount.player_id)
        return jsonify({
            'error': f'You have already placed a bid of {amount} on {other_player.name}. Each bid amount must be unique across all players in a round.'
        }), 400
    
    # Create the new bid
    bid = Bid(
        team_id=team.id,
        player_id=player_id,
        round_id=round_id,
        amount=amount
    )
    db.session.add(bid)
    db.session.commit()
    
    # We don't need to send outbid notifications since this is a closed auction
    # Players cannot see each other's bids, so outbid notifications would be confusing
    # Only the final results are important
    
    # Send real-time update via Socket.IO to admins only
    socket_events.broadcast_to_admins({
        'type': 'new_bid',
        'team_name': current_user.team.name,
        'player_id': player_id,
        'round_id': round_id,
        'amount': amount,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return jsonify({'message': 'Bid placed successfully'})

@app.route('/delete_bid/<int:bid_id>', methods=['DELETE'])
@login_required
def delete_bid(bid_id):
    if current_user.is_admin:
        return jsonify({'error': 'Admins cannot delete bids'}), 403
    
    bid = Bid.query.get_or_404(bid_id)
    round = Round.query.get(bid.round_id)
    
    # Check if the round timer has expired
    if round and round.is_timer_expired():
        # If timer expired, finalize the round and reject the deletion
        finalize_round_internal(round.id)
        return jsonify({'error': 'Round timer has expired'}), 400
    
    # Check if the bid belongs to the current team
    if bid.team_id != current_user.team.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if the round is still active
    if not bid.round.is_active:
        return jsonify({'error': 'Cannot delete bid from a finalized round'}), 400
    
    db.session.delete(bid)
    db.session.commit()
    
    return jsonify({'message': 'Bid deleted successfully'})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/place_tiebreaker_bid', methods=['POST'])
@login_required
def place_tiebreaker_bid():
    if current_user.is_admin:
        return jsonify({'error': 'Admins cannot place bids'}), 403
    
    data = request.json
    round_id = data.get('round_id')
    player_id = data.get('player_id')
    amount = data.get('amount')
    
    if not all([round_id, player_id, amount]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    round = Round.query.get_or_404(round_id)
    if not round.is_tiebreaker:
        return jsonify({'error': 'This is not a tiebreaker round'}), 400
    
    if round.is_timer_expired():
        finalize_tiebreaker_round(round_id)
        return jsonify({'error': 'Round timer has expired'}), 400
    
    team = current_user.team
    if team.balance < amount:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    # Check if team is allowed in this tiebreaker
    existing_bid = TiebreakerBid.query.filter_by(
        team_id=team.id,
        round_id=round_id
    ).first()
    
    if not existing_bid:
        return jsonify({'error': 'Your team is not part of this tiebreaker'}), 403
    
    # Update the bid amount
    existing_bid.amount = amount
    db.session.commit()
    
    # In a closed auction, we don't send notifications about bid updates
    # The final results will be announced when the tiebreaker ends
    
    # Send real-time update via Socket.IO to admins only
    socket_events.broadcast_to_admins({
        'type': 'tiebreaker_bid',
        'team_name': current_user.team.name,
        'player_id': player_id,
        'round_id': round_id,
        'amount': amount,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return jsonify({'message': 'Tiebreaker bid placed successfully'})

def finalize_tiebreaker_round(round_id):
    """
    Finalize a tiebreaker round, determine the winner and allocate the player
    """
    tiebreaker_round = Round.query.get(round_id)
    if not tiebreaker_round or not tiebreaker_round.is_active or not tiebreaker_round.is_tiebreaker:
        return False
    
    # Mark the round as inactive
    tiebreaker_round.is_active = False
    
    # Get the player being contested
    player = Player.query.get(tiebreaker_round.player_id)
    if not player:
        db.session.commit()
        return False
    
    # Get all tiebreaker bids for this round
    bids = TiebreakerBid.query.filter_by(round_id=round_id).all()
    
    if not bids:
        # No bids placed in tiebreaker round, just end it
        db.session.commit()
        return True
    
    # Find the highest bid
    highest_bid = max(bids, key=lambda x: x.amount)
    
    # Check if there's still a tie
    matching_bids = [bid for bid in bids if bid.amount == highest_bid.amount]
    
    if len(matching_bids) == 1:
        # Clear winner
        winning_bid = matching_bids[0]
        team = Team.query.get(winning_bid.team_id)
        
        # Check if team has enough balance
        if team.balance >= winning_bid.amount:
            # Allocate player to team
            player.team_id = team.id
            player.cost = winning_bid.amount
            player.acquired_at = datetime.utcnow()
            
            # Deduct amount from team balance
            team.balance -= winning_bid.amount
            
            # Send notification to winning team
            send_notification_to_team(team.id, {
                'title': 'You Won the Tiebreaker!',
                'body': f'You successfully acquired {player.name} for {winning_bid.amount} coins!',
                'data': {
                    'type': 'player_won',
                    'player_name': player.name,
                    'player_id': player.id,
                    'amount': winning_bid.amount
                },
                'tag': f'tiebreaker_won_{round_id}_{team.id}',
                'renotify': True
            })
            
            # Notify other teams that participated in the tiebreaker
            for bid in bids:
                if bid.team_id != team.id:
                    send_notification_to_team(bid.team_id, {
                        'title': 'Tiebreaker Ended',
                        'body': f'The tiebreaker for {player.name} has ended. Another team placed a higher bid.',
                        'data': {
                            'type': 'tiebreaker_lost',
                            'player_name': player.name,
                            'player_id': player.id
                        },
                        'tag': f'tiebreaker_lost_{round_id}_{bid.team_id}',
                        'renotify': True
                    })
        else:
            # Team doesn't have enough balance
            # In a real implementation, you might want to go to the next highest bidder
            # or handle this differently
            send_notification_to_team(team.id, {
                'title': 'Insufficient Balance',
                'body': f'Your winning bid of {winning_bid.amount} for {player.name} couldn\'t be processed due to insufficient balance.',
                'data': {
                    'type': 'insufficient_balance',
                    'player_name': player.name,
                    'amount': winning_bid.amount
                },
                'tag': f'insufficient_balance_{round_id}_{team.id}',
                'renotify': True
            })
    else:
        # Still a tie - currently we'll just pick the first bid as the winner
        # but this could be handled differently based on your requirements
        winning_bid = matching_bids[0]
        team = Team.query.get(winning_bid.team_id)
        
        # Check if team has enough balance
        if team.balance >= winning_bid.amount:
            # Allocate player to team
            player.team_id = team.id
            player.cost = winning_bid.amount
            player.acquired_at = datetime.utcnow()
            
            # Deduct amount from team balance
            team.balance -= winning_bid.amount
            
            # Notify the winning team
            send_notification_to_team(team.id, {
                'title': 'You Won the Tiebreaker!',
                'body': f'After a tie, you were selected to acquire {player.name} for {winning_bid.amount} coins!',
                'data': {
                    'type': 'player_won',
                    'player_name': player.name,
                    'player_id': player.id,
                    'amount': winning_bid.amount,
                    'tie_resolution': True
                },
                'tag': f'tiebreaker_won_{round_id}_{team.id}',
                'renotify': True
            })
            
            # Notify other teams that tied
            for bid in matching_bids:
                if bid.team_id != team.id:
                    send_notification_to_team(bid.team_id, {
                        'title': 'Tiebreaker Ended in a Tie',
                        'body': f'The tiebreaker for {player.name} ended in a tie. Another team was randomly selected.',
                        'data': {
                            'type': 'tiebreaker_tie_lost',
                            'player_name': player.name,
                            'player_id': player.id
                        },
                        'tag': f'tiebreaker_tie_lost_{round_id}_{bid.team_id}',
                        'renotify': True
                    })
    
    # Clear the round_id to remove player from auction
    player.round_id = None
    
    # If there was a parent round, check if all tiebreakers are resolved
    if tiebreaker_round.parent_round_id:
        resume_after_tiebreaker(tiebreaker_round.parent_round_id)
    
    # Commit all changes
    db.session.commit()
    
    # Notify admins about the tiebreaker result
    send_notification_to_admins({
        'title': 'Tiebreaker Round Completed',
        'body': f'Tiebreaker for {player.name} has been completed.',
        'data': {
            'type': 'tiebreaker_completed',
            'round_id': round_id,
            'player_name': player.name,
            'player_id': player.id
        },
        'tag': f'tiebreaker_admin_{round_id}',
        'renotify': True
    })
    
    return True

def resume_after_tiebreaker(round_id):
    """Resume the finalization process after tiebreakers have been resolved"""
    round = Round.query.get(round_id)
    if not round:
        return False
    
    print(f"Resuming finalization for round {round_id} after tiebreakers")
    
    # Get latest bids (edited bids handled)
    all_bids = Bid.query.filter_by(round_id=round_id).all()
    latest_bids = {}
    for bid in all_bids:
        key = f"{bid.player_id}-{bid.team_id}"
        if key not in latest_bids or bid.timestamp > latest_bids[key].timestamp:
            latest_bids[key] = bid
    
    # Convert to list and sort by amount (highest first)
    sorted_bids = sorted(latest_bids.values(), key=lambda x: x.amount, reverse=True)
    
    # Find currently allocated teams and players
    allocated_teams = set()
    allocated_players = set()
    
    for player in Player.query.filter_by(round_id=round_id).all():
        if player.team_id:
            allocated_teams.add(player.team_id)
            allocated_players.add(player.id)
    
    # Also check tiebreaker rounds
    for tiebreaker in Round.query.filter_by(parent_round_id=round_id).all():
        if tiebreaker.player_id and not tiebreaker.is_active:
            player = Player.query.get(tiebreaker.player_id)
            if player and player.team_id:
                allocated_teams.add(player.team_id)
                allocated_players.add(player.id)
    
    # Process remaining bids
    for bid in sorted_bids:
        # Skip if team or player already allocated
        if bid.team_id in allocated_teams or bid.player_id in allocated_players:
            continue
            
        # No need to check for ties - they should have been handled already
        # Allocate player to team
        print(f"Allocating player ID {bid.player_id} to team ID {bid.team_id} for {bid.amount}")
        player = Player.query.get(bid.player_id)
        team = Team.query.get(bid.team_id)
        
        # Update team's balance
        team.balance -= bid.amount
        
        # Set the player's team
        player.team_id = team.id
        
        # Mark as allocated
        allocated_teams.add(team.id)
        allocated_players.add(player.id)
    
    db.session.commit()
    print(f"Finalization completed for round {round_id} after tiebreakers")
    return True

@app.route('/finalize_tiebreaker/<int:round_id>', methods=['POST'])
@login_required
def finalize_tiebreaker(round_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can finalize rounds'}), 403
    
    if finalize_tiebreaker_round(round_id):
        return jsonify({'message': 'Tiebreaker round finalized successfully'})
    else:
        return jsonify({'error': 'Failed to finalize tiebreaker round'}), 400

@app.route('/admin/teams')
@login_required
def admin_teams():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    teams = Team.query.all()
    team_details = []
    
    for team in teams:
        # Get position counts
        position_counts = {}
        for position in Config.POSITIONS:
            position_counts[position] = 0
        
        # Calculate total team value and get position distribution
        total_team_value = 0
        players_by_position = {}
        
        for player in team.players:
            position_counts[player.position] += 1
            
            # Get player's acquisition value (from winning bid)
            acquisition_value = 0
            winning_bid = Bid.query.filter_by(
                team_id=team.id,
                player_id=player.id
            ).order_by(Bid.amount.desc()).first()
            
            if winning_bid:
                acquisition_value = winning_bid.amount
            
            total_team_value += acquisition_value
            
            # Group players by position
            if player.position not in players_by_position:
                players_by_position[player.position] = []
            
            players_by_position[player.position].append({
                'id': player.id,
                'name': player.name,
                'overall_rating': player.overall_rating,
                'acquisition_value': acquisition_value
            })
        
        # Get active and completed bid counts
        active_bids_count = 0
        completed_rounds = Round.query.filter_by(is_active=False).all()
        completed_round_ids = [r.id for r in completed_rounds]
        
        # Get active rounds
        active_rounds = Round.query.filter_by(is_active=True).all()
        
        # Count active bids
        for round in active_rounds:
            active_bids_count += Bid.query.filter_by(team_id=team.id, round_id=round.id).count()
        
        # Count completed bids
        completed_bids_count = Bid.query.filter(
            Bid.team_id == team.id,
            Bid.round_id.in_(completed_round_ids)
        ).count()
        
        # Find if team has a user
        team_user = User.query.filter_by(id=team.user_id).first()
        
        team_details.append({
            'team': team,
            'position_counts': position_counts,
            'total_players': len(team.players),
            'total_team_value': total_team_value,
            'active_bids_count': active_bids_count,
            'completed_bids_count': completed_bids_count,
            'players_by_position': players_by_position,
            'has_user': team_user is not None,
            'username': team_user.username if team_user else None
        })
    
    return render_template('admin_teams.html', teams=team_details)

@app.route('/admin/players')
@login_required
def admin_players():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    # Get query parameters for pagination and filtering
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)  # Default to 20 players per page
    position_filter = request.args.get('position', None)
    search_query = request.args.get('q', None)
    
    # Build the query
    query = Player.query
    
    # Apply position filter if provided
    if position_filter and position_filter in Config.POSITIONS:
        query = query.filter_by(position=position_filter)
    
    # Apply search filter if provided
    if search_query and search_query.strip():
        search_term = f"%{search_query.strip()}%"
        query = query.filter(Player.name.ilike(search_term))
    
    # Get paginated results
    players_pagination = query.order_by(Player.overall_rating.desc()).paginate(page=page, per_page=per_page)
    
    # Get all teams for the edit form
    teams = Team.query.all()
    
    return render_template(
        'admin_players.html', 
        players_pagination=players_pagination,
        players=players_pagination.items,
        teams=teams,
        config=Config,
        current_position=position_filter,
        search_query=search_query
    )

@app.route('/admin/rounds')
@login_required
def admin_rounds():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    # Get active rounds
    active_rounds = Round.query.filter_by(is_active=True).all()
    
    # Get past (inactive) rounds
    past_rounds = Round.query.filter_by(is_active=False).all()
    
    # Get all rounds for completeness
    rounds = Round.query.all()
    
    return render_template('admin_rounds.html', 
                          rounds=rounds, 
                          active_rounds=active_rounds, 
                          past_rounds=past_rounds,
                          config=Config)

@app.route('/admin/edit_round/<int:round_id>', methods=['POST'])
@login_required
def admin_edit_round(round_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    round = Round.query.get_or_404(round_id)
    if not round.is_active:
        return jsonify({'error': 'Cannot edit a completed round'}), 400
    
    position = request.json.get('position')
    duration = request.json.get('duration')
    
    if position and position not in Config.POSITIONS:
        return jsonify({'error': 'Invalid position'}), 400
    
    if duration:
        try:
            duration = int(duration)
            if duration < 30:
                return jsonify({'error': 'Duration must be at least 30 seconds'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid duration value'}), 400
    
    if position:
        round.position = position
    if duration:
        round.duration = duration
        round.start_time = datetime.utcnow()  # Reset the timer
    
    db.session.commit()
    return jsonify({'message': 'Round updated successfully'})

@app.route('/admin/delete_round/<int:round_id>', methods=['POST'])
@login_required
def admin_delete_round(round_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    round = Round.query.get_or_404(round_id)
    if round.is_active:
        return jsonify({'error': 'Cannot delete an active round'}), 400
    
    try:
        print(f"Processing round deletion - ID: {round_id}, Position: {round.position}")
        
        # Find all players from this round that have been allocated to teams
        allocated_players = []
        refund_total = 0
        freed_players_count = 0
        
        for player in round.players:
            if player.team_id is not None:
                print(f"Found allocated player: {player.name} (ID: {player.id}) to team ID: {player.team_id}")
                # Find the winning bid for this player
                winning_bid = Bid.query.filter_by(
                    round_id=round_id,
                    player_id=player.id,
                    team_id=player.team_id
                ).first()
                
                if winning_bid:
                    # Refund the team
                    team = Team.query.get(player.team_id)
                    if team:
                        team.balance += winning_bid.amount
                        refund_total += winning_bid.amount
                        print(f"Refunded {winning_bid.amount} to team: {team.name}")
                
                # Free the player
                player.team_id = None
                freed_players_count += 1
        
        # Delete all bids associated with this round
        bid_count = Bid.query.filter_by(round_id=round_id).count()
        Bid.query.filter_by(round_id=round_id).delete()
        print(f"Deleted {bid_count} bids from round")
        
        # Also delete any tiebreaker bids if this was a tiebreaker round
        tiebreaker_bid_count = 0
        if round.is_tiebreaker:
            tiebreaker_bid_count = TiebreakerBid.query.filter_by(round_id=round_id).count()
            TiebreakerBid.query.filter_by(round_id=round_id).delete()
            print(f"Deleted {tiebreaker_bid_count} tiebreaker bids from round")
            
        # Clear round_id from any players in this round
        player_count = 0
        for player in round.players:
            player.round_id = None
            player_count += 1
        print(f"Cleared round_id from {player_count} players")
            
        # Delete tiebreaker rounds that might reference this round as parent
        tiebreaker_rounds = Round.query.filter_by(parent_round_id=round_id).all()
        tiebreaker_round_count = len(tiebreaker_rounds)
        for tiebreaker in tiebreaker_rounds:
            # Recursively handle tiebreaker rounds
            tiebreaker_bids_deleted = TiebreakerBid.query.filter_by(round_id=tiebreaker.id).count()
            TiebreakerBid.query.filter_by(round_id=tiebreaker.id).delete()
            print(f"Deleted tiebreaker round ID: {tiebreaker.id} with {tiebreaker_bids_deleted} bids")
            db.session.delete(tiebreaker)
            
        # Now we can safely delete the round
        db.session.delete(round)
        db.session.commit()
        
        summary = f"Round deleted successfully. Freed {freed_players_count} players, refunded {refund_total} to teams, removed {bid_count} bids, and {tiebreaker_round_count} tiebreaker rounds."
        print(summary)
        return jsonify({'message': summary})
    except Exception as e:
        db.session.rollback()
        error_message = f"Failed to delete round: {str(e)}"
        print(f"ERROR: {error_message}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': error_message}), 500

@app.route('/admin/add_team', methods=['POST'])
@login_required
def admin_add_team():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    name = request.json.get('name')
    balance = request.json.get('balance', 1000000)  # Default balance
    
    if not name:
        return jsonify({'error': 'Team name is required'}), 400
    
    if Team.query.filter_by(name=name).first():
        return jsonify({'error': 'Team name already exists'}), 400
    
    try:
        balance = int(balance)
        if balance < 0:
            return jsonify({'error': 'Balance cannot be negative'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid balance value'}), 400
    
    team = Team(name=name, balance=balance)
    db.session.add(team)
    db.session.commit()
    
    return jsonify({'message': 'Team added successfully'})

@app.route('/admin/edit_team/<int:team_id>', methods=['POST'])
@login_required
def admin_edit_team(team_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    team = Team.query.get_or_404(team_id)
    name = request.json.get('name')
    balance = request.json.get('balance')
    
    if name and name != team.name:
        if Team.query.filter_by(name=name).first():
            return jsonify({'error': 'Team name already exists'}), 400
        team.name = name
    
    if balance is not None:
        try:
            balance = int(balance)
            if balance < 0:
                return jsonify({'error': 'Balance cannot be negative'}), 400
            team.balance = balance
        except ValueError:
            return jsonify({'error': 'Invalid balance value'}), 400
    
    db.session.commit()
    return jsonify({'message': 'Team updated successfully'})

@app.route('/admin/delete_team/<int:team_id>', methods=['POST'])
@login_required
def admin_delete_team(team_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    team = Team.query.get_or_404(team_id)
    
    # Check if team has any players
    if team.players:
        return jsonify({'error': 'Cannot delete a team with players'}), 400
    
    db.session.delete(team)
    db.session.commit()
    return jsonify({'message': 'Team deleted successfully'})

@app.route('/admin/add_player', methods=['POST'])
@login_required
def admin_add_player():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    required_fields = ['name', 'position', 'overall_rating']
    
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    if data['position'] not in Config.POSITIONS:
        return jsonify({'error': 'Invalid position'}), 400
    
    try:
        overall_rating = int(data['overall_rating'])
        if not (1 <= overall_rating <= 99):
            return jsonify({'error': 'Overall rating must be between 1 and 99'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid overall rating value'}), 400
    
    player = Player(
        name=data['name'],
        position=data['position'],
        overall_rating=overall_rating,
        offensive_awareness=data.get('offensive_awareness', 50),
        ball_control=data.get('ball_control', 50),
        dribbling=data.get('dribbling', 50),
        tight_possession=data.get('tight_possession', 50),
        low_pass=data.get('low_pass', 50),
        lofted_pass=data.get('lofted_pass', 50),
        finishing=data.get('finishing', 50),
        heading=data.get('heading', 50),
        set_piece_taking=data.get('set_piece_taking', 50),
        curl=data.get('curl', 50),
        speed=data.get('speed', 50),
        acceleration=data.get('acceleration', 50),
        kicking_power=data.get('kicking_power', 50),
        jumping=data.get('jumping', 50),
        physical_contact=data.get('physical_contact', 50),
        balance=data.get('balance', 50),
        stamina=data.get('stamina', 50),
        defensive_awareness=data.get('defensive_awareness', 50),
        tackling=data.get('tackling', 50),
        aggression=data.get('aggression', 50),
        defensive_engagement=data.get('defensive_engagement', 50)
    )
    
    db.session.add(player)
    db.session.commit()
    
    return jsonify({'message': 'Player added successfully'})

@app.route('/admin/edit_player/<int:player_id>', methods=['POST'])
@login_required
def admin_edit_player(player_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    player = Player.query.get_or_404(player_id)
    data = request.json
    
    if 'position' in data and data['position'] not in Config.POSITIONS:
        return jsonify({'error': 'Invalid position'}), 400
    
    if 'overall_rating' in data:
        try:
            overall_rating = int(data['overall_rating'])
            if not (1 <= overall_rating <= 99):
                return jsonify({'error': 'Overall rating must be between 1 and 99'}), 400
            player.overall_rating = overall_rating
        except ValueError:
            return jsonify({'error': 'Invalid overall rating value'}), 400
    
    # Update other attributes if provided
    for attr in ['name', 'position', 'offensive_awareness', 'ball_control', 'dribbling',
                'tight_possession', 'low_pass', 'lofted_pass', 'finishing', 'heading',
                'set_piece_taking', 'curl', 'speed', 'acceleration', 'kicking_power',
                'jumping', 'physical_contact', 'balance', 'stamina', 'defensive_awareness',
                'tackling', 'aggression', 'defensive_engagement']:
        if attr in data:
            setattr(player, attr, data[attr])
    
    db.session.commit()
    return jsonify({'message': 'Player updated successfully'})

@app.route('/admin/delete_player/<int:player_id>', methods=['POST'])
@login_required
def admin_delete_player(player_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    player = Player.query.get_or_404(player_id)
    
    # Check if player is in a team
    if player.team_id:
        return jsonify({'error': 'Cannot delete a player that is in a team'}), 400
    
    # Check if player is in an active round
    if player.round_id and Round.query.get(player.round_id).is_active:
        return jsonify({'error': 'Cannot delete a player that is in an active round'}), 400
    
    db.session.delete(player)
    db.session.commit()
    return jsonify({'message': 'Player deleted successfully'})

@app.route('/api/active_tiebreakers')
@login_required
def get_active_tiebreakers():
    """API endpoint to get active tiebreaker rounds for the current team"""
    if current_user.is_admin:
        # For admins, get all active tiebreaker rounds
        tiebreaker_rounds = Round.query.filter_by(is_active=True, is_tiebreaker=True).all()
    else:
        # For team users, get only tiebreaker rounds they're participating in
        team_id = current_user.team.id
        # Query for rounds where this team has a tiebreaker bid
        tiebreaker_rounds_ids = db.session.query(TiebreakerBid.round_id).filter_by(team_id=team_id).distinct().all()
        tiebreaker_rounds_ids = [r[0] for r in tiebreaker_rounds_ids]  # Extract IDs from result tuples
        
        # Get the active tiebreaker rounds
        tiebreaker_rounds = Round.query.filter(
            Round.id.in_(tiebreaker_rounds_ids),
            Round.is_active == True,
            Round.is_tiebreaker == True
        ).all()

    result = []
    for round in tiebreaker_rounds:
        # Get the player this tiebreaker is for
        player = Player.query.get(round.player_id)
        
        # Get all bids for this tiebreaker
        tiebreaker_bids = TiebreakerBid.query.filter_by(round_id=round.id).all()
        
        # Format bids data
        bids_data = []
        for bid in tiebreaker_bids:
            team = Team.query.get(bid.team_id)
            bids_data.append({
                'id': bid.id,
                'team_id': bid.team_id,
                'team_name': team.name,
                'amount': bid.amount,
                'is_current_team': bid.team_id == current_user.team.id if not current_user.is_admin else False
            })
        
        # Calculate time remaining
        current_time = datetime.utcnow()
        elapsed = (current_time - round.start_time).total_seconds()
        time_remaining = max(0, round.duration - elapsed)
        
        round_data = {
            'id': round.id,
            'player': {
                'id': player.id,
                'name': player.name,
                'position': player.position,
                'overall_rating': player.overall_rating
            },
            'start_time': round.start_time.isoformat(),
            'duration': round.duration,
            'time_remaining': time_remaining,
            'bids': bids_data,
            'parent_round_id': round.parent_round_id
        }
        result.append(round_data)
    
    return jsonify(result)

@app.route('/admin/round/<int:round_id>')
@login_required
def admin_view_round(round_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    round = Round.query.get_or_404(round_id)
    teams = Team.query.all()
    
    # Get all bids for this round
    all_bids = Bid.query.filter_by(round_id=round_id).all()
    print(f"Found {len(all_bids)} bids for round {round_id}")
    
    # Get team bids data
    team_bids = {}
    for team in teams:
        team_bids[team.id] = {
            'team': team,
            'bids': []
        }
    
    # Collect winning bids data
    winning_bids = []
    
    # Process all bids
    for bid in all_bids:
        # Add to team bids
        if bid.team_id in team_bids:
            player = Player.query.get(bid.player_id)
            if not player:
                print(f"Warning: Player not found for bid {bid.id} (player_id: {bid.player_id})")
                continue
                
            is_winning = player.team_id == bid.team_id
            
            # Format the timestamp for display
            created_at = bid.timestamp.strftime('%d/%m/%Y %H:%M:%S') if bid.timestamp else 'N/A'
            
            # Create bid data structure
            bid_data = {
                'player': player,
                'amount': bid.amount,
                'is_winning': is_winning,
                'created_at': created_at
            }
            
            # Add to team bids
            team_bids[bid.team_id]['bids'].append(bid_data)
            print(f"Added bid for player {player.name} to team {team_bids[bid.team_id]['team'].name} (amount: {bid.amount}, winning: {is_winning})")
            
            # If this is a winning bid, add to winning bids list
            if is_winning:
                winning_bids.append({
                    'bid': bid,
                    'player': player,
                    'team': team_bids[bid.team_id]['team']
                })
    
    # Sort team bids by timestamp (newest first)
    for team_id in team_bids:
        team_bids[team_id]['bids'].sort(key=lambda x: x['created_at'], reverse=True)
    
    # Sort winning bids by bid amount (descending)
    winning_bids.sort(key=lambda x: x['bid'].amount, reverse=True)
    
    # Debug count of bids per team
    for team_id, team_data in team_bids.items():
        print(f"Team {team_data['team'].name} has {len(team_data['bids'])} bids")
    
    return render_template(
        'admin_view_round.html',
        round=round,
        team_bids=team_bids,
        winning_bids=winning_bids,
        teams=teams
    )

# Add a route to serve player images
@app.route('/images/player_photos/<filename>')
def player_photos(filename):
    # Use absolute path to images folder
    return send_from_directory(os.path.join(app.root_path, 'static/images/player_photos'), filename)

@app.route('/api/star_player/<int:player_id>', methods=['POST'])
@login_required
def star_player(player_id):
    if not current_user.team:
        return jsonify({'error': 'You need to be part of a team to star players'}), 403
    
    player = Player.query.get_or_404(player_id)
    team_id = current_user.team.id
    
    # Check if player is already starred
    existing_star = StarredPlayer.query.filter_by(team_id=team_id, player_id=player_id).first()
    if existing_star:
        return jsonify({'message': 'Player already starred'}), 200
    
    # Add player to starred list
    star = StarredPlayer(team_id=team_id, player_id=player_id)
    db.session.add(star)
    db.session.commit()
    
    return jsonify({'message': 'Player starred successfully'})

@app.route('/api/unstar_player/<int:player_id>', methods=['POST'])
@login_required
def unstar_player(player_id):
    if not current_user.team:
        return jsonify({'error': 'You need to be part of a team'}), 403
    
    team_id = current_user.team.id
    
    # Find and remove the star
    star = StarredPlayer.query.filter_by(team_id=team_id, player_id=player_id).first()
    if not star:
        return jsonify({'message': 'Player is not starred'}), 200
    
    db.session.delete(star)
    db.session.commit()
    
    return jsonify({'message': 'Player unstarred successfully'})

@app.route('/export_winning_bids')
@login_required
def export_winning_bids():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    # Get the round ID from the query parameters
    round_id = request.args.get('round_id')
    if not round_id:
        flash('Round ID is required', 'error')
        return redirect(url_for('admin_rounds'))
    
    round = Round.query.get_or_404(round_id)
    teams = Team.query.all()
    
    # Get all bids for this round
    all_bids = Bid.query.filter_by(round_id=round_id).all()
    
    # Prepare team bids data
    team_bids = {}
    for team in teams:
        team_bids[team.id] = {
            'team': team,
            'bids': []
        }
    
    # Collect winning bids data
    winning_bids = []
    
    # Process all bids
    for bid in all_bids:
        # Add to team bids
        if bid.team_id in team_bids:
            player = Player.query.get(bid.player_id)
            is_winning = player.team_id == bid.team_id
            
            # If this is a winning bid, add to winning bids list
            if is_winning:
                winning_bids.append({
                    'bid': bid,
                    'player': player,
                    'team': team_bids[bid.team_id]['team']
                })
    
    # Sort winning bids by bid amount (descending)
    winning_bids.sort(key=lambda x: x['bid'].amount, reverse=True)
    
    # Create a pandas DataFrame for export
    if winning_bids:
        data = {
            'Player': [wb['player'].name for wb in winning_bids],
            'Team': [wb['team'].name for wb in winning_bids],
            'Bid Amount': [wb['bid'].amount for wb in winning_bids],
            'Position': [wb['player'].position for wb in winning_bids],
            'Rating': [wb['player'].overall_rating for wb in winning_bids]
        }
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Winning Bids', index=False)
            
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Winning Bids']
            
            # Set column widths
            worksheet.set_column('A:A', 25)  # Player name
            worksheet.set_column('B:B', 25)  # Team name
            worksheet.set_column('C:C', 15)  # Bid amount
            worksheet.set_column('D:D', 10)  # Position
            worksheet.set_column('E:E', 10)  # Rating
            
            # Add formatting
            header_format = workbook.add_format({
                'bold': True, 
                'bg_color': '#D3D3D3',
                'border': 1
            })
            
            # Apply header formatting
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
        
        # Set up response
        output.seek(0)
        round_position = round.position.replace(' ', '_')
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"winning_bids_{round_position}_{now}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        flash('No winning bids found for this round', 'warning')
        return redirect(url_for('admin_view_round', round_id=round_id))

@app.route('/admin/export_players')
@login_required
def admin_export_players():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    # Get all players
    players = Player.query.all()
    
    # Create a dictionary to organize players by position
    players_by_position = {}
    for position in Config.POSITIONS:
        players_by_position[position] = []
    
    # Group players by position
    for player in players:
        if player.position in players_by_position:
            players_by_position[player.position].append(player)
    
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Create header format
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })
        
        # Create a summary sheet first
        all_players_data = []
        for player in players:
            team_name = player.team.name if player.team else "Free Agent"
            all_players_data.append({
                'Name': player.name,
                'Position': player.position,
                'Rating': player.overall_rating,
                'Team': team_name
            })
        
        # Create summary dataframe and sheet
        if all_players_data:
            df_all = pd.DataFrame(all_players_data)
            df_all.to_excel(writer, sheet_name='All Players', index=False)
            
            # Format summary sheet
            worksheet = writer.sheets['All Players']
            worksheet.set_column('A:A', 25)  # Name
            worksheet.set_column('B:B', 10)  # Position
            worksheet.set_column('C:C', 10)  # Rating
            worksheet.set_column('D:D', 20)  # Team
            
            # Apply header formatting
            for col_num, value in enumerate(df_all.columns.values):
                worksheet.write(0, col_num, value, header_format)
        
        # Create a sheet for each position with detailed stats
        for position, position_players in players_by_position.items():
            if not position_players:
                continue
                
            players_data = []
            for player in position_players:
                team_name = player.team.name if player.team else "Free Agent"
                player_data = {
                    'Name': player.name,
                    'Team': team_name,
                    'Overall Rating': player.overall_rating,
                    'Nationality': player.nationality or 'N/A',
                    'Playing Style': player.playing_style or 'N/A',
                    'Speed': player.speed,
                    'Acceleration': player.acceleration,
                    'Ball Control': player.ball_control,
                    'Dribbling': player.dribbling,
                    'Low Pass': player.low_pass,
                    'Lofted Pass': player.lofted_pass,
                    'Finishing': player.finishing,
                    'Heading': player.heading,
                    'Set Piece Taking': player.set_piece_taking,
                    'Curl': player.curl,
                    'Physical Contact': player.physical_contact,
                    'Balance': player.balance,
                    'Stamina': player.stamina,
                    'Defensive Awareness': player.defensive_awareness,
                    'Tackling': player.tackling,
                    'Aggression': player.aggression,
                    'Defensive Engagement': player.defensive_engagement
                }
                
                # Add goalkeeper specific stats if position is GK
                if position == 'GK':
                    player_data.update({
                        'GK Awareness': player.gk_awareness,
                        'GK Catching': player.gk_catching,
                        'GK Parrying': player.gk_parrying,
                        'GK Reflexes': player.gk_reflexes,
                        'GK Reach': player.gk_reach
                    })
                
                players_data.append(player_data)
            
            if players_data:
                # Create dataframe and sheet for this position
                df_position = pd.DataFrame(players_data)
                sheet_name = position  # Use position as sheet name
                df_position.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Format position sheet
                worksheet = writer.sheets[sheet_name]
                
                # Set column widths
                worksheet.set_column('A:A', 25)  # Name
                worksheet.set_column('B:B', 20)  # Team
                worksheet.set_column('C:C', 15)  # Overall Rating
                worksheet.set_column('D:D', 15)  # Nationality
                worksheet.set_column('E:E', 20)  # Playing Style
                
                # Apply header formatting
                for col_num, value in enumerate(df_position.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Add conditional formatting for rating cells
                worksheet.conditional_format(1, 2, len(players_data), 2, {
                    'type': '3_color_scale',
                    'min_color': '#FFFFFF',
                    'mid_color': '#ADD8E6',
                    'max_color': '#006400'
                })
                
                # Add conditional formatting for attribute cells
                attr_start_col = 5  # Starting from 'Speed' column
                attr_end_col = len(df_position.columns) - 1
                worksheet.conditional_format(1, attr_start_col, len(players_data), attr_end_col, {
                    'type': '3_color_scale',
                    'min_color': '#FFFFFF',
                    'mid_color': '#FFEB84',
                    'max_color': '#329932'
                })
    
    # Set up response
    output.seek(0)
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"players_database_{now}.xlsx"
    
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/admin/export_team_squad/<int:team_id>')
@login_required
def export_team_squad(team_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    # Get the team
    team = Team.query.get_or_404(team_id)
    
    # Get all players in the team
    players = Player.query.filter_by(team_id=team_id).all()
    
    if not players:
        flash(f'No players found for team: {team.name}', 'warning')
        return redirect(url_for('admin_teams'))
    
    # Group players by position
    players_by_position = {}
    for position in Config.POSITIONS:
        players_by_position[position] = []
    
    # Calculate acquisition values and group by position
    for player in players:
        # Get player's acquisition value (from winning bid)
        winning_bid = Bid.query.filter_by(
            team_id=team.id,
            player_id=player.id
        ).order_by(Bid.amount.desc()).first()
        
        acquisition_value = winning_bid.amount if winning_bid else 0
        
        # Add player to position group
        if player.position in players_by_position:
            players_by_position[player.position].append({
                'id': player.id,
                'name': player.name,
                'overall_rating': player.overall_rating,
                'acquisition_value': acquisition_value,
                'nationality': player.nationality or 'N/A',
                'playing_style': player.playing_style or 'N/A'
            })
    
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Create header format
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })
        
        # Create summary sheet with all players
        all_player_data = []
        total_value = 0
        
        for position in Config.POSITIONS:
            for player in players_by_position[position]:
                total_value += player['acquisition_value']
                all_player_data.append({
                    'Name': player['name'],
                    'Position': position,
                    'Rating': player['overall_rating'],
                    'Value': player['acquisition_value'],
                    'Nationality': player['nationality'],
                    'Playing Style': player['playing_style']
                })
        
        # Create team summary sheet
        summary_data = [{
            'Team': team.name,
            'Total Players': len(players),
            'Total Value': total_value,
            'Average Value': total_value / len(players) if players else 0,
            'Balance': team.balance
        }]
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Team Summary', index=False)
        
        # Format team summary sheet
        worksheet_summary = writer.sheets['Team Summary']
        worksheet_summary.set_column('A:A', 25)  # Team
        worksheet_summary.set_column('B:B', 15)  # Total Players
        worksheet_summary.set_column('C:C', 15)  # Total Value
        worksheet_summary.set_column('D:D', 15)  # Average Value
        worksheet_summary.set_column('E:E', 15)  # Balance
        
        # Apply header formatting to summary
        for col_num, value in enumerate(df_summary.columns.values):
            worksheet_summary.write(0, col_num, value, header_format)
        
        # Create sheet with all players
        if all_player_data:
            df_all = pd.DataFrame(all_player_data)
            df_all.to_excel(writer, sheet_name='All Players', index=False)
            
            # Format main player sheet
            worksheet = writer.sheets['All Players']
            worksheet.set_column('A:A', 25)  # Name
            worksheet.set_column('B:B', 10)  # Position
            worksheet.set_column('C:C', 10)  # Rating
            worksheet.set_column('D:D', 15)  # Value
            worksheet.set_column('E:E', 15)  # Nationality
            worksheet.set_column('F:F', 20)  # Playing Style
            
            # Apply header formatting
            for col_num, value in enumerate(df_all.columns.values):
                worksheet.write(0, col_num, value, header_format)
        
        # Create a sheet for each position with players
        for position, position_players in players_by_position.items():
            if not position_players:
                continue
            
            # Sort players by rating (highest first)
            position_players.sort(key=lambda x: x['overall_rating'], reverse=True)
            
            df_position = pd.DataFrame(position_players)
            # Rename columns for better readability
            df_position = df_position.rename(columns={
                'name': 'Name',
                'overall_rating': 'Rating',
                'acquisition_value': 'Value',
                'nationality': 'Nationality',
                'playing_style': 'Playing Style'
            })
            # Select and order columns
            df_position = df_position[['Name', 'Rating', 'Value', 'Nationality', 'Playing Style']]
            
            position_sheet_name = position[:31]  # Limit sheet name length
            df_position.to_excel(writer, sheet_name=position_sheet_name, index=False)
            
            # Format position sheet
            worksheet = writer.sheets[position_sheet_name]
            worksheet.set_column('A:A', 25)  # Name
            worksheet.set_column('B:B', 10)  # Rating
            worksheet.set_column('C:C', 15)  # Value
            worksheet.set_column('D:D', 15)  # Nationality
            worksheet.set_column('E:E', 20)  # Playing Style
            
            # Apply header formatting
            for col_num, value in enumerate(df_position.columns.values):
                worksheet.write(0, col_num, value, header_format)
    
    # Set up response
    output.seek(0)
    team_name = team.name.replace(' ', '_')
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"team_squad_{team_name}_{now}.xlsx"
    
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/admin/users', methods=['GET'])
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/approve/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    
    flash(f'User {user.username} has been approved.', 'success')
    return redirect(url_for('admin_users'))

# Helper function to determine if a notification should be sent in a closed auction
def should_send_notification(notification_type, payload=None):
    """
    Filter notifications based on closed auction rules
    Return True if notification should be sent, False otherwise
    """
    # In a closed auction, we only want essential notifications:
    important_notifications = [
        'round_start',        # New auction round started
        'round_end',          # Auction round ended
        'player_won',         # Player won by a team
        'tiebreaker_start',   # Tiebreaker round started
        'tiebreaker_completed' # Tiebreaker round completed
    ]
    
    # Skip outbid notifications in closed auctions
    skip_notifications = [
        'outbid',             # Player has been outbid
        'bid_update'          # Bid has been updated
    ]
    
    if notification_type in important_notifications:
        return True
    
    if notification_type in skip_notifications:
        return False
    
    # For any other notification types, allow them by default
    return True

# Helper function for sending push notifications
def send_push_notification(user_id, payload):
    """
    Send push notification to a specific user via their stored push subscriptions
    """
    try:
        # Skip notification if it's not important for a closed auction
        notification_type = payload.get('data', {}).get('type')
        if notification_type and not should_send_notification(notification_type, payload):
            print(f"Skipping notification of type {notification_type} in closed auction")
            return False
            
        # Get all push subscriptions for the user
        subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
        
        if not subscriptions:
            return False
        
        for subscription in subscriptions:
            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth
                }
            }
            
            try:
                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps(payload),
                    vapid_private_key=Config.VAPID_PRIVATE_KEY,
                    vapid_claims=Config.VAPID_CLAIMS
                )
            except WebPushException as e:
                # If pushing failed due to subscription expiration or invalidation
                if e.response and e.response.status_code in [404, 410]:
                    db.session.delete(subscription)
                    db.session.commit()
                print(f"Error sending notification: {e}")
                
        return True
    except Exception as e:
        print(f"Error in send_push_notification: {e}")
        return False

def send_notification_to_all_teams(payload, exclude_user_ids=None):
    """
    Send push notification to all team users except those in exclude_user_ids
    """
    exclude_user_ids = exclude_user_ids or []
    users = User.query.filter(User.is_admin.is_(False), User.id.notin_(exclude_user_ids)).all()
    
    for user in users:
        send_push_notification(user.id, payload)
    
    return True

def send_notification_to_team(team_id, payload):
    """
    Send push notification to a specific team
    """
    team = Team.query.get(team_id)
    if team and team.user:
        return send_push_notification(team.user.id, payload)
    return False

def send_notification_to_admins(payload):
    """
    Send push notification to all admin users
    """
    admin_users = User.query.filter_by(is_admin=True).all()
    
    for admin in admin_users:
        send_push_notification(admin.id, payload)
    
    return True

# API endpoint to get the public VAPID key
@app.route('/api/vapid-public-key')
@login_required
def get_vapid_public_key():
    return jsonify({'publicKey': Config.VAPID_PUBLIC_KEY})

# API endpoint to subscribe to push notifications
@app.route('/api/subscribe', methods=['POST'])
@login_required
def subscribe():
    try:
        # Get the subscription info from the request
        subscription_json = request.json.get('subscription')
        
        if not subscription_json:
            return jsonify({'error': 'No subscription data provided'}), 400
        
        # Extract the necessary data
        endpoint = subscription_json.get('endpoint')
        p256dh = subscription_json.get('keys', {}).get('p256dh')
        auth = subscription_json.get('keys', {}).get('auth')
        
        if not endpoint or not p256dh or not auth:
            return jsonify({'error': 'Invalid subscription data'}), 400
        
        # Check if subscription already exists
        existing_sub = PushSubscription.query.filter_by(
            user_id=current_user.id,
            endpoint=endpoint
        ).first()
        
        if existing_sub:
            # Update the keys if they've changed
            existing_sub.p256dh = p256dh
            existing_sub.auth = auth
            existing_sub.updated_at = datetime.utcnow()
        else:
            # Create a new subscription
            new_subscription = PushSubscription(
                user_id=current_user.id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth
            )
            db.session.add(new_subscription)
        
        db.session.commit()
        
        # Send a test notification
        send_push_notification(current_user.id, {
            'title': 'Notifications Enabled',
            'body': 'You will now receive notifications for important updates!',
            'tag': 'welcome',
            'renotify': True
        })
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in subscribe: {e}")
        return jsonify({'error': str(e)}), 500

# API endpoint to unsubscribe from push notifications
@app.route('/api/unsubscribe', methods=['POST'])
@login_required
def unsubscribe():
    try:
        # Get the subscription info from the request
        subscription_json = request.json.get('subscription')
        
        if not subscription_json:
            return jsonify({'error': 'No subscription data provided'}), 400
        
        # Extract the endpoint
        endpoint = subscription_json.get('endpoint')
        
        if not endpoint:
            return jsonify({'error': 'Invalid subscription data'}), 400
        
        # Find and delete the subscription
        subscription = PushSubscription.query.filter_by(
            user_id=current_user.id,
            endpoint=endpoint
        ).first()
        
        if subscription:
            db.session.delete(subscription)
            db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in unsubscribe: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Run with Socket.IO instead of the regular Flask development server
    socketio.run(app, debug=True, host='0.0.0.0') 
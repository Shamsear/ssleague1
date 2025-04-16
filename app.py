from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Team, Player, Round, Bid, Tiebreaker, TeamTiebreaker, PasswordResetRequest
from config import Config
from werkzeug.security import generate_password_hash
import json
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
import io
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # Check if user is either an admin or has been approved
            if user.is_admin or user.is_approved:
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Your account is pending approval. Please contact an administrator.')
                return render_template('login.html')
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        team_name = request.form.get('team_name')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        # Check if this is an admin account
        is_admin = username.lower() == 'admin'
        
        user = User(username=username, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        
        # Only create a team if the user is not an admin
        if not is_admin:
            team = Team(name=team_name, user=user)
            db.session.add(team)
        
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Check if any active rounds have expired
    active_rounds = Round.query.filter_by(is_active=True).all()
    for round in active_rounds:
        if round.is_timer_expired():
            finalize_round_internal(round.id)
    
    # Refresh the data after potentially finalizing rounds
    if current_user.is_admin:
        teams = Team.query.all()
        
        # Get pending users (users that are not approved and not admins)
        pending_users = User.query.filter(User.is_approved == False, User.is_admin == False).all()
        
        # Get pending password reset requests
        pending_resets = PasswordResetRequest.query.filter_by(status='pending').all()
        
        return render_template('admin_dashboard.html', 
                              teams=teams,
                              pending_users=pending_users,
                              pending_resets=pending_resets,
                              config=Config)
    
    # For team users
    active_rounds = Round.query.filter_by(is_active=True).all()
    rounds = Round.query.all()
    
    # Get tiebreakers for this team
    team_tiebreakers = TeamTiebreaker.query.join(Tiebreaker).filter(
        TeamTiebreaker.team_id == current_user.team.id,
        Tiebreaker.resolved == False
    ).all()
    
    # Get bid counts for each active round
    bid_counts = {}
    for round in active_rounds:
        bid_counts[round.id] = Bid.query.filter_by(
            round_id=round.id,
            team_id=current_user.team.id
        ).count()
    
    # Get round results for completed rounds
    round_results = []
    completed_rounds = Round.query.filter_by(is_active=False).all()
    for round in completed_rounds:
        # Get players in this round where the user has placed a bid
        user_bids = Bid.query.filter_by(team_id=current_user.team.id, round_id=round.id).all()
        
        for bid in user_bids:
            player = Player.query.get(bid.player_id)
            if player:
                # Get winning bid for this player
                winning_bid = Bid.query.filter_by(team_id=player.team_id, player_id=player.id).first() if player.team_id else None
                winning_team = Team.query.get(player.team_id).name if player.team_id else "None"
                
                result = {
                    'player_name': player.name,
                    'position': player.position,
                    'your_bid': bid.amount,
                    'winning_bid': winning_bid.amount if winning_bid else 0,
                    'winning_team': winning_team,
                    'won': player.team_id == current_user.team.id
                }
                
                round_results.append(result)
    
    return render_template('team_dashboard.html', 
                          active_rounds=active_rounds, 
                          rounds=rounds,
                          team_tiebreakers=team_tiebreakers,
                          bid_counts=bid_counts,
                          round_results=round_results)

@app.route('/start_round', methods=['POST'])
@login_required
def start_round():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    position = request.json.get('position')
    duration = request.json.get('duration', 300)  # Default to 5 minutes (300 seconds)
    max_bids_per_team = request.json.get('max_bids_per_team', 5)  # Default to 5 bids per team
    
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
    
    return jsonify({
        'message': 'Round started successfully',
        'round_id': round.id,
        'player_count': len(players),
        'duration': duration,
        'max_bids_per_team': max_bids_per_team,
        'expires_at': (round.start_time.isoformat() if round.start_time else None)
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
    if not round.is_active:
        return jsonify({'active': False, 'message': 'Round is already finalized'})
    
    expired = round.is_timer_expired()
    if expired:
        # Finalize the round if expired
        finalize_round_internal(round_id)
        return jsonify({'active': False, 'message': 'Round timer expired and has been finalized'})
    
    # Calculate remaining time
    elapsed = (datetime.utcnow() - round.start_time).total_seconds() if round.start_time else 0
    remaining = max(0, round.duration - elapsed)
    
    return jsonify({
        'active': True,
        'remaining': remaining,
        'duration': round.duration,
        'start_time': round.start_time.isoformat() if round.start_time else None
    })

def finalize_round_internal(round_id):
    """Internal function to finalize a round, can be called programmatically"""
    round = Round.query.get(round_id)
    if not round or not round.is_active:
        return False
    
    # Check for existing tiebreakers that need resolution
    existing_tiebreakers = Tiebreaker.query.filter_by(round_id=round_id, resolved=False).all()
    if existing_tiebreakers:
        # Cannot finalize until tiebreakers are resolved
        return {"status": "tiebreaker_pending", "tiebreakers": [t.id for t in existing_tiebreakers]}
    
    bids = Bid.query.filter_by(round_id=round_id).all()
    
    # Start processing bids
    return process_bids_with_tiebreaker_check(round_id, bids)

def process_bids_with_tiebreaker_check(round_id, bids):
    """Process bids in descending order, checking for ties and creating tiebreakers if needed"""
    round = Round.query.get(round_id)
    allocated_teams = set()
    allocated_players = set()
    
    # Continue processing while there are bids
    while bids:
        # Sort bids in descending order
        bids.sort(key=lambda x: x.amount, reverse=True)
        
        # Get highest bid amount
        highest_bid_amount = bids[0].amount
        
        # Find all bids with the highest amount (could be just one or multiple if tied)
        highest_bids = [bid for bid in bids if bid.amount == highest_bid_amount]
        
        # If there's a tie and multiple teams bidding for the same player
        if len(highest_bids) > 1 and len(set(bid.player_id for bid in highest_bids)) == 1:
            player_id = highest_bids[0].player_id
            tied_team_ids = [bid.team_id for bid in highest_bids]
            
            # Create a tiebreaker for this tie
            tiebreaker = Tiebreaker(
                round_id=round_id,
                player_id=player_id,
                original_amount=highest_bid_amount,
                resolved=False
            )
            db.session.add(tiebreaker)
            db.session.commit()
            
            # Add all tied teams to the tiebreaker
            for team_id in tied_team_ids:
                team_tiebreaker = TeamTiebreaker(
                    tiebreaker_id=tiebreaker.id,
                    team_id=team_id,
                    new_amount=None  # Will be set during tiebreaker resolution
                )
                db.session.add(team_tiebreaker)
            
            db.session.commit()
            
            # Return status indicating tiebreaker needed
            round.status = "processing"  # Update round status to processing
            db.session.commit()
            return {"status": "tiebreaker_needed", "tiebreaker_id": tiebreaker.id}
        
        # No tie for highest bid, proceed with allocation
        highest_bid = highest_bids[0]
        
        # Only allocate if both team and player haven't been allocated yet
        if highest_bid.team_id not in allocated_teams and highest_bid.player_id not in allocated_players:
            team = Team.query.get(highest_bid.team_id)
            player = Player.query.get(highest_bid.player_id)
            
            team.balance -= highest_bid.amount
            player.team_id = team.id
            player.acquisition_value = highest_bid.amount  # Set acquisition value to winning bid amount
            
            allocated_teams.add(team.id)
            allocated_players.add(player.id)
            
            # Remove all bids for this player and this team
            bids = [bid for bid in bids if bid.player_id != highest_bid.player_id and bid.team_id != highest_bid.team_id]
        else:
            # This highest bid cannot be allocated (team or player already used)
            # Remove it and continue with next highest
            bids.remove(highest_bid)
    
    # All bids processed successfully
    round.is_active = False
    round.status = "completed"
    db.session.commit()
    return {"status": "success"}

@app.route('/finalize_round/<int:round_id>', methods=['POST'])
@login_required
def finalize_round(round_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    round = Round.query.get_or_404(round_id)
    if not round.is_active:
        return jsonify({'error': 'Round already finalized'}), 400
    
    result = finalize_round_internal(round_id)
    
    if isinstance(result, dict):
        status = result.get("status")
        
        if status == "success":
            return jsonify({'message': 'Round finalized successfully'})
        elif status == "tiebreaker_needed":
            tiebreaker_id = result.get("tiebreaker_id")
            return jsonify({
                'message': 'Tiebreaker needed',
                'tiebreaker_id': tiebreaker_id
            }), 202  # Accepted but processing
        elif status == "tiebreaker_pending":
            tiebreakers = result.get("tiebreakers")
            return jsonify({
                'message': 'Existing tiebreakers need resolution',
                'tiebreaker_ids': tiebreakers
            }), 202
    
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
    
    # Check if the team has already reached the maximum bids for this round
    team_bids_count = Bid.query.filter_by(team_id=team.id, round_id=round_id).count()
    if team_bids_count >= round.max_bids_per_team:
        return jsonify({'error': f'You have reached the maximum number of bids ({round.max_bids_per_team}) for this round'}), 400
    
    # Check if the team has already placed this bid amount on another player in the same round
    existing_bid = Bid.query.filter_by(
        team_id=team.id,
        round_id=round_id,
        amount=amount
    ).first()
    
    if existing_bid:
        return jsonify({
            'error': f'You have already placed a bid of {amount} on another player in this round. Please use a different amount.'
        }), 400
    
    bid = Bid(
        team_id=team.id,
        player_id=player_id,
        round_id=round_id,
        amount=amount
    )
    db.session.add(bid)
    db.session.commit()
    
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

@app.route('/tiebreaker/<int:tiebreaker_id>', methods=['GET'])
@login_required
def get_tiebreaker(tiebreaker_id):
    tiebreaker = Tiebreaker.query.get_or_404(tiebreaker_id)
    
    if current_user.is_admin:
        # Admin view
        team_tiebreakers = TeamTiebreaker.query.filter_by(tiebreaker_id=tiebreaker_id).all()
        teams = [Team.query.get(tt.team_id) for tt in team_tiebreakers]
        player = Player.query.get(tiebreaker.player_id)
        
        return render_template('tiebreaker_admin.html', 
                             tiebreaker=tiebreaker, 
                             teams=teams,
                             team_tiebreakers=team_tiebreakers,
                             player=player)
    else:
        # Team view - only show if this team is part of the tiebreaker
        team_tiebreaker = TeamTiebreaker.query.filter_by(
            tiebreaker_id=tiebreaker_id, 
            team_id=current_user.team.id
        ).first()
        
        if not team_tiebreaker:
            return jsonify({'error': 'Not authorized to view this tiebreaker'}), 403
        
        player = Player.query.get(tiebreaker.player_id)
        return render_template('tiebreaker_team.html', 
                             tiebreaker=tiebreaker,
                             team_tiebreaker=team_tiebreaker,
                             player=player)

@app.route('/submit_tiebreaker_bid', methods=['POST'])
@login_required
def submit_tiebreaker_bid():
    if current_user.is_admin:
        return jsonify({'error': 'Admins cannot submit bids'}), 403
    
    data = request.json
    tiebreaker_id = data.get('tiebreaker_id')
    new_amount = data.get('amount')
    
    if not all([tiebreaker_id, new_amount]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    tiebreaker = Tiebreaker.query.get_or_404(tiebreaker_id)
    if tiebreaker.resolved:
        return jsonify({'error': 'Tiebreaker already resolved'}), 400
    
    team_tiebreaker = TeamTiebreaker.query.filter_by(
        tiebreaker_id=tiebreaker_id,
        team_id=current_user.team.id
    ).first()
    
    if not team_tiebreaker:
        return jsonify({'error': 'Your team is not part of this tiebreaker'}), 403
    
    # New bid must be higher than original
    if new_amount <= tiebreaker.original_amount:
        return jsonify({'error': f'New bid must be higher than original amount of {tiebreaker.original_amount}'}), 400
    
    # Check team balance
    if current_user.team.balance < new_amount:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    # Update the team's tiebreaker bid
    team_tiebreaker.new_amount = new_amount
    db.session.commit()
    
    # Check if all teams have submitted new bids
    all_team_tiebreakers = TeamTiebreaker.query.filter_by(tiebreaker_id=tiebreaker_id).all()
    all_submitted = all(tt.new_amount is not None for tt in all_team_tiebreakers)
    
    if all_submitted:
        # All teams have submitted, resolve the tiebreaker
        tiebreaker.resolved = True
        db.session.commit()
        
        # Update the original bids with new amounts
        round_id = tiebreaker.round_id
        player_id = tiebreaker.player_id
        
        for tt in all_team_tiebreakers:
            bid = Bid.query.filter_by(
                round_id=round_id,
                player_id=player_id,
                team_id=tt.team_id
            ).first()
            
            if bid:
                bid.amount = tt.new_amount
        
        db.session.commit()
        
        # Try to finalize the round again
        result = finalize_round_internal(round_id)
        
        if isinstance(result, dict) and result.get("status") == "success":
            return jsonify({'message': 'Tiebreaker resolved and round finalized'})
        
        # If we get here, round finalization might require more tiebreakers
        return jsonify({'message': 'Tiebreaker resolved, additional processing needed'})
    
    return jsonify({'message': 'Bid submitted successfully, waiting for other teams'})

@app.route('/check_tiebreaker_status/<int:tiebreaker_id>')
@login_required
def check_tiebreaker_status(tiebreaker_id):
    tiebreaker = Tiebreaker.query.get_or_404(tiebreaker_id)
    
    # Check if this tiebreaker is resolved
    if tiebreaker.resolved:
        # Check if the round is still active
        round = Round.query.get(tiebreaker.round_id)
        if round.is_active:
            return jsonify({
                'status': 'processing',
                'message': 'Tiebreaker resolved, round still processing'
            })
        else:
            return jsonify({
                'status': 'completed',
                'message': 'Round finalized'
            })
    
    # Count how many teams have submitted bids
    team_tiebreakers = TeamTiebreaker.query.filter_by(tiebreaker_id=tiebreaker_id).all()
    submitted = sum(1 for tt in team_tiebreakers if tt.new_amount is not None)
    total = len(team_tiebreakers)
    
    return jsonify({
        'status': 'waiting',
        'message': f'{submitted} of {total} teams have submitted tiebreaker bids'
    })

@app.route('/players')
@login_required
def all_players():
    page = request.args.get('page', 1, type=int)
    position = request.args.get('position', '')
    search_query = request.args.get('q', '')
    
    query = Player.query
    
    # Apply filters
    if position:
        query = query.filter_by(position=position)
    
    if search_query:
        query = query.filter(Player.name.ilike(f'%{search_query}%'))
    
    # Paginate results
    players_pagination = query.order_by(Player.name).paginate(page=page, per_page=20)
    
    return render_template('admin_players.html', 
                          players=players_pagination.items,
                          players_pagination=players_pagination,
                          current_position=position,
                          search_query=search_query,
                          config=Config)

@app.route('/player/<int:player_id>')
@login_required
def player_detail(player_id):
    # Get the player
    player = Player.query.get_or_404(player_id)
    
    # Get referrer to check where the request came from
    referrer = request.referrer or ""
    from_players_database = "team_players_data" in referrer
    
    # If not from the database page, make sure the player belongs to the current user's team
    if not from_players_database and player not in current_user.team.players:
        flash('You do not have access to this player', 'danger')
        return redirect(url_for('team_players'))
    
    # Get all player attributes as a dictionary
    player_stats = {}
    for key, value in player.__dict__.items():
        if not key.startswith('_') and key not in ['id', 'player_id', 'name', 'position', 
                                                   'overall_rating', 'created_at', 'updated_at', 
                                                   'acquired_at', 'team_id', 'round_id', 'cost']:
            player_stats[key] = value
    
    # Mock performance data (in a real app this would come from a database)
    player_performance = []
    # You can populate this with real data if available
    
    return render_template('player_detail.html', player=player, 
                           player_stats=player_stats, 
                           player_performance=player_performance)

@app.route('/players/position/<position>')
@login_required
def players_by_position(position):
    players = Player.query.filter_by(position=position).all()
    return render_template('admin_players.html', players=players, position=position)

@app.route('/api/players')
@login_required
def api_players():
    players = Player.query.all()
    result = []
    for player in players:
        result.append({
            'id': player.id,
            'name': player.name,
            'position': player.position,
            'team_name': player.team_name,
            'nationality': player.nationality,
            'overall_rating': player.overall_rating,
            'playing_style': player.playing_style,
            'team_id': player.team_id
        })
    return jsonify(result)

@app.route('/api/player/<int:player_id>')
@login_required
def api_player_detail(player_id):
    player = Player.query.get_or_404(player_id)
    result = {
        'id': player.id,
        'name': player.name,
        'position': player.position,
        'team_name': player.team_name,
        'nationality': player.nationality,
        'offensive_awareness': player.offensive_awareness,
        'ball_control': player.ball_control,
        'dribbling': player.dribbling,
        'tight_possession': player.tight_possession,
        'low_pass': player.low_pass,
        'lofted_pass': player.lofted_pass,
        'finishing': player.finishing,
        'heading': player.heading,
        'set_piece_taking': player.set_piece_taking,
        'curl': player.curl,
        'speed': player.speed,
        'acceleration': player.acceleration,
        'kicking_power': player.kicking_power,
        'jumping': player.jumping,
        'physical_contact': player.physical_contact,
        'balance': player.balance,
        'stamina': player.stamina,
        'defensive_awareness': player.defensive_awareness,
        'tackling': player.tackling,
        'aggression': player.aggression,
        'defensive_engagement': player.defensive_engagement,
        'gk_awareness': player.gk_awareness,
        'gk_catching': player.gk_catching,
        'gk_parrying': player.gk_parrying,
        'gk_reflexes': player.gk_reflexes,
        'gk_reach': player.gk_reach,
        'overall_rating': player.overall_rating,
        'playing_style': player.playing_style,
        'player_id': player.player_id,
        'team_id': player.team_id
    }
    return jsonify(result)

@app.route('/admin/players')
@login_required
def admin_players():
    if not current_user.is_admin:
        flash('You do not have permission to access this page')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    position = request.args.get('position', '')
    search_query = request.args.get('q', '')
    
    query = Player.query
    
    # Apply filters
    if position:
        query = query.filter_by(position=position)
    
    if search_query:
        query = query.filter(Player.name.ilike(f'%{search_query}%'))
    
    # Paginate results
    players_pagination = query.order_by(Player.name).paginate(page=page, per_page=20)
    
    return render_template('admin_players.html', 
                          players=players_pagination.items,
                          players_pagination=players_pagination,
                          current_position=position,
                          search_query=search_query,
                          config=Config,
                          teams=Team.query.all())

@app.route('/admin/export_players')
@login_required
def admin_export_players():
    if not current_user.is_admin:
        flash('You do not have permission to access this feature')
        return redirect(url_for('dashboard'))
    
    try:
        # Create a BytesIO object to store the Excel file
        output = io.BytesIO()
        
        # Create Excel writer object
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Get all players
            players = Player.query.all()
            
            # Create a dictionary to store DataFrames for each position
            position_dfs = {}
            
            # Process each player
            for player in players:
                # Create a dictionary with all player attributes
                player_data = {
                    'Name': player.name,
                    'Position': player.position,
                    'Overall Rating': player.overall_rating,
                    'Team': player.team.name if player.team else 'Free Agent',
                    'Nationality': player.nationality,
                    'Playing Style': player.playing_style,
                    'Offensive Awareness': player.offensive_awareness,
                    'Ball Control': player.ball_control,
                    'Dribbling': player.dribbling,
                    'Tight Possession': player.tight_possession,
                    'Low Pass': player.low_pass,
                    'Lofted Pass': player.lofted_pass,
                    'Finishing': player.finishing,
                    'Heading': player.heading,
                    'Set Piece Taking': player.set_piece_taking,
                    'Curl': player.curl,
                    'Speed': player.speed,
                    'Acceleration': player.acceleration,
                    'Kicking Power': player.kicking_power,
                    'Jumping': player.jumping,
                    'Physical Contact': player.physical_contact,
                    'Balance': player.balance,
                    'Stamina': player.stamina,
                    'Defensive Awareness': player.defensive_awareness,
                    'Tackling': player.tackling,
                    'Aggression': player.aggression,
                    'Defensive Engagement': player.defensive_engagement,
                    'GK Awareness': player.gk_awareness,
                    'GK Catching': player.gk_catching,
                    'GK Parrying': player.gk_parrying,
                    'GK Reflexes': player.gk_reflexes,
                    'GK Reach': player.gk_reach
                }
                
                # Add player data to the appropriate position DataFrame
                if player.position not in position_dfs:
                    position_dfs[player.position] = []
                position_dfs[player.position].append(player_data)
            
            # Create and write each position sheet
            for position, players_data in position_dfs.items():
                df = pd.DataFrame(players_data)
                df = df.sort_values('Overall Rating', ascending=False)
                df.to_excel(writer, sheet_name=position, index=False)
                
                # Get the worksheet object
                worksheet = writer.sheets[position]
                
                # Format the header row
                header_format = writer.book.add_format({
                    'bold': True,
                    'bg_color': '#D3D3D3',
                    'border': 1
                })
                
                # Apply the format to the header row
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Auto-adjust columns width
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    worksheet.set_column(idx, idx, max_length + 2)
            
            # Create an "All Players" sheet
            all_players_data = []
            for players_data in position_dfs.values():
                all_players_data.extend(players_data)
            
            df_all = pd.DataFrame(all_players_data)
            df_all = df_all.sort_values(['Position', 'Overall Rating'], ascending=[True, False])
            df_all.to_excel(writer, sheet_name='All Players', index=False)
            
            # Format the "All Players" sheet
            worksheet = writer.sheets['All Players']
            for col_num, value in enumerate(df_all.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            for idx, col in enumerate(df_all.columns):
                max_length = max(
                    df_all[col].astype(str).apply(len).max(),
                    len(col)
                )
                worksheet.set_column(idx, idx, max_length + 2)
        
        # Prepare the response
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='players_export.xlsx'
        )
    
    except ImportError:
        flash('Required packages (pandas, xlsxwriter) are not installed')
        return redirect(url_for('admin_players'))
    except Exception as e:
        flash(f'Error exporting players: {str(e)}')
        return redirect(url_for('admin_players'))

@app.route('/admin/add_player', methods=['POST'])
@login_required
def admin_add_player():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    name = data.get('name')
    position = data.get('position')
    overall_rating = data.get('overall_rating')
    
    if not all([name, position, overall_rating]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    player = Player(
        name=name,
        position=position,
        overall_rating=overall_rating
    )
    db.session.add(player)
    db.session.commit()
    
    return jsonify({'message': 'Player added successfully', 'id': player.id})

@app.route('/admin/edit_player/<int:player_id>', methods=['POST'])
@login_required
def admin_edit_player(player_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    player = Player.query.get_or_404(player_id)
    data = request.json
    
    player.name = data.get('name', player.name)
    player.position = data.get('position', player.position)
    player.overall_rating = data.get('overall_rating', player.overall_rating)
    player.team_id = data.get('team_id', player.team_id)
    
    db.session.commit()
    
    return jsonify({'message': 'Player updated successfully'})

@app.route('/admin/delete_player/<int:player_id>', methods=['POST'])
@login_required
def admin_delete_player(player_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    player = Player.query.get_or_404(player_id)
    
    # Check if player is part of an active round
    if player.round_id:
        round = Round.query.get(player.round_id)
        if round and round.is_active:
            return jsonify({'error': 'Cannot delete player that is part of an active round'}), 400
    
    # Delete associated bids
    Bid.query.filter_by(player_id=player_id).delete()
    
    # Delete associated tiebreakers
    tiebreakers = Tiebreaker.query.filter_by(player_id=player_id).all()
    for tiebreaker in tiebreakers:
        TeamTiebreaker.query.filter_by(tiebreaker_id=tiebreaker.id).delete()
    Tiebreaker.query.filter_by(player_id=player_id).delete()
    
    # Delete the player
    db.session.delete(player)
    db.session.commit()
    
    return jsonify({'message': 'Player deleted successfully'})

@app.route('/export_team_squad/<int:team_id>')
@login_required
def export_team_squad(team_id):
    # Check if user is admin or the team owner
    team = Team.query.get_or_404(team_id)
    if not current_user.is_admin and (not current_user.team or current_user.team.id != team_id):
        flash('You do not have permission to export this team data')
        return redirect(url_for('dashboard'))
    
    try:
        import pandas as pd
        import io
    except ImportError:
        flash('Required libraries not available')
        return redirect(url_for('admin_teams' if current_user.is_admin else 'dashboard'))
    
    # Get team players
    players = Player.query.filter_by(team_id=team_id).all()
    
    # Create DataFrame
    players_data = []
    for player in players:
        players_data.append({
            'ID': player.id,
            'Name': player.name,
            'Position': player.position,
            'Rating': player.overall_rating,
            'Acquisition Value': player.acquisition_value if player.acquisition_value else 0,
        })
    
    if not players_data:
        flash('No players found for this team')
        return redirect(url_for('admin_teams' if current_user.is_admin else 'dashboard'))
    
    df = pd.DataFrame(players_data)
    
    # Create an Excel file with position sheets
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # All players sheet
        df.to_excel(writer, sheet_name='All Players', index=False)
        
        # Position sheets
        for position in Config.POSITIONS:
            position_df = df[df['Position'] == position]
            if not position_df.empty:
                position_df.to_excel(writer, sheet_name=position, index=False)
        
        # Format the header
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9EAD3',
            'border': 1
        })
        
        # Apply formatting to all sheets
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, max(len(value) + 2, 12))
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'{team.name}_Squad.xlsx'
    )

@app.route('/admin/rounds')
@login_required
def admin_rounds():
    if not current_user.is_admin:
        flash('You do not have permission to access this page')
        return redirect(url_for('dashboard'))
    
    # Get all relevant data for round management
    teams = Team.query.all()
    active_rounds = Round.query.filter_by(is_active=True).all()
    rounds = Round.query.all()
    active_tiebreakers = Tiebreaker.query.filter_by(resolved=False).all()
    
    return render_template('admin_rounds.html', 
                          teams=teams, 
                          active_rounds=active_rounds, 
                          rounds=rounds, 
                          active_tiebreakers=active_tiebreakers,
                          config=Config)

@app.route('/admin/round/<int:round_id>')
@login_required
def admin_round_detail(round_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page')
        return redirect(url_for('dashboard'))
    
    round = Round.query.get_or_404(round_id)
    
    # Get all teams to track bids across teams
    teams = Team.query.all()
    
    # Get all bids for this round
    bids = Bid.query.filter_by(round_id=round_id).all()
    
    # Organize bids by player and team
    bids_by_player = {}
    for player in round.players:
        bids_by_player[player.id] = {
            'player': player,
            'winning_bid': None,
            'bids': [],
            'team_bids': {team.id: None for team in teams}
        }
    
    # Fill in the bid data
    for bid in bids:
        if bid.player_id in bids_by_player:
            bids_by_player[bid.player_id]['bids'].append(bid)
            bids_by_player[bid.player_id]['team_bids'][bid.team_id] = bid
            
            # Check if this is the winning bid
            player = Player.query.get(bid.player_id)
            if player.team_id == bid.team_id:
                bids_by_player[bid.player_id]['winning_bid'] = bid
                
                # Ensure acquisition value is set if not already (for backward compatibility)
                if player.acquisition_value is None:
                    player.acquisition_value = bid.amount
                    db.session.commit()
    
    return render_template('admin_round_detail.html',
                          round=round,
                          teams=teams,
                          bids_by_player=bids_by_player,
                          config=Config)

@app.route('/admin/export_round/<int:round_id>')
@login_required
def admin_export_round(round_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this feature')
        return redirect(url_for('dashboard'))
    
    round = Round.query.get_or_404(round_id)
    
    try:
        # Create a BytesIO object to store the Excel file
        output = io.BytesIO()
        
        # Create Excel writer object
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Get winning bids data
            export_data = []
            
            for player in round.players:
                # Find the winning bid for this player if it exists
                winning_bid = None
                for bid in player.bids:
                    if bid.team_id == player.team_id:
                        winning_bid = bid
                        break
                
                if winning_bid:
                    export_data.append({
                        'Player': player.name,
                        'Position': player.position,
                        'Team': winning_bid.team.name,
                        'Bid Amount': winning_bid.amount,
                        'Overall Rating': player.overall_rating,
                        'Nationality': player.nationality,
                        'Playing Style': player.playing_style
                    })
            
            # Create dataframe and export to Excel
            if export_data:
                df = pd.DataFrame(export_data)
                df.to_excel(writer, sheet_name='Winning Bids', index=False)
                
                # Format the worksheet
                worksheet = writer.sheets['Winning Bids']
                
                # Add header format
                header_format = writer.book.add_format({
                    'bold': True,
                    'bg_color': '#D3D3D3',
                    'border': 1
                })
                
                # Apply the format to the header row
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Auto-adjust column width
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    worksheet.set_column(idx, idx, max_length + 2)
                
                # Create a sheet for all bids
                all_bids_data = []
                for player in round.players:
                    for bid in player.bids:
                        all_bids_data.append({
                            'Player': player.name,
                            'Position': player.position,
                            'Team': bid.team.name,
                            'Bid Amount': bid.amount,
                            'Timestamp': bid.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'Status': 'Won' if bid.team_id == player.team_id else 'Lost'
                        })
                
                if all_bids_data:
                    df_all = pd.DataFrame(all_bids_data)
                    df_all.to_excel(writer, sheet_name='All Bids', index=False)
                    
                    # Format the All Bids worksheet
                    worksheet = writer.sheets['All Bids']
                    for col_num, value in enumerate(df_all.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                    
                    for idx, col in enumerate(df_all.columns):
                        max_length = max(
                            df_all[col].astype(str).apply(len).max(),
                            len(col)
                        )
                        worksheet.set_column(idx, idx, max_length + 2)
            
        # Prepare the response
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'round_{round_id}_{round.position}_results.xlsx'
        )
    
    except ImportError:
        flash('Required packages (pandas, xlsxwriter) are not installed')
        return redirect(url_for('admin_round_detail', round_id=round_id))
    except Exception as e:
        flash(f'Error exporting round data: {str(e)}')
        return redirect(url_for('admin_round_detail', round_id=round_id))

@app.route('/admin/delete_round/<int:round_id>', methods=['POST'])
@login_required
def admin_delete_round(round_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    round = Round.query.get_or_404(round_id)
    
    if round.is_active:
        return jsonify({'error': 'Cannot delete an active round. Please finalize it first.'}), 400
    
    try:
        # Get all players allocated in this round
        players_in_round = Player.query.filter_by(round_id=round_id).all()
        allocated_players = []
        
        # Find players that were allocated to teams in this round
        for player in players_in_round:
            # Check if player has a winning bid in this round
            winning_bid = Bid.query.filter_by(
                player_id=player.id, 
                round_id=round_id, 
                team_id=player.team_id
            ).first()
            
            if winning_bid:
                allocated_players.append(player)
        
        # Get all players with team_id set but may not be in this round anymore
        all_players = Player.query.all()
        refunded_amount = 0
        
        # Release allocated players from their teams
        for player in allocated_players:
            # Get the team to refund the acquisition value
            team = Team.query.get(player.team_id)
            if team and player.acquisition_value:
                team.balance += player.acquisition_value
                refunded_amount += player.acquisition_value
            
            # Reset player's team and acquisition value
            player.team_id = None
            player.acquisition_value = None
            player.round_id = None
        
        # Delete all bids for this round
        Bid.query.filter_by(round_id=round_id).delete()
        
        # Delete all tiebreakers for this round
        tiebreakers = Tiebreaker.query.filter_by(round_id=round_id).all()
        for tiebreaker in tiebreakers:
            TeamTiebreaker.query.filter_by(tiebreaker_id=tiebreaker.id).delete()
        Tiebreaker.query.filter_by(round_id=round_id).delete()
        
        # Release any remaining players from the round
        for player in players_in_round:
            if player.round_id == round_id:
                player.round_id = None
        
        # Delete the round
        db.session.delete(round)
        db.session.commit()
        
        return jsonify({
            'message': 'Round deleted successfully',
            'released_players': len(allocated_players),
            'refunded_amount': refunded_amount
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete round: {str(e)}'}), 500

@app.route('/admin/teams')
@login_required
def admin_teams():
    if not current_user.is_admin:
        flash('You do not have permission to access this page')
        return redirect(url_for('dashboard'))
    
    # Get all teams with their data
    teams = Team.query.all()
    teams_data = []
    
    for team in teams:
        # Get players for this team
        players = Player.query.filter_by(team_id=team.id).all()
        
        # Calculate position counts
        position_counts = {position: 0 for position in Config.POSITIONS}
        for player in players:
            if player.position in position_counts:
                position_counts[player.position] += 1
        
        # Calculate total team value
        total_team_value = sum(player.acquisition_value for player in players if player.acquisition_value)
        
        # Get players by position
        players_by_position = {}
        for position in Config.POSITIONS:
            players_by_position[position] = [p for p in players if p.position == position]
        
        # Get bid counts
        active_bids_count = Bid.query.join(Player).filter(
            Bid.team_id == team.id,
            Player.round_id != None,
            Player.team_id != team.id
        ).count()
        
        completed_bids_count = Bid.query.filter_by(team_id=team.id).count()
        
        # Get username if associated with a user
        has_user = team.user_id is not None
        username = team.user.username if has_user else ""
        
        teams_data.append({
            'team': team,
            'total_players': len(players),
            'position_counts': position_counts,
            'total_team_value': total_team_value,
            'players_by_position': players_by_position,
            'active_bids_count': active_bids_count,
            'completed_bids_count': completed_bids_count,
            'has_user': has_user,
            'username': username
        })
    
    return render_template('admin_teams.html', teams=teams_data, config=Config)

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('You do not have permission to access this page')
        return redirect(url_for('dashboard'))
    
    # Get all users
    users = User.query.all()
    
    # Calculate statistics
    pending_approvals = sum(1 for user in users if not user.is_approved and not user.is_admin)
    admin_count = sum(1 for user in users if user.is_admin)
    
    return render_template('admin_users.html', 
                          users=users,
                          pending_approvals=pending_approvals,
                          admin_count=admin_count)

@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Don't approve admin users
    if user.is_admin:
        flash('Admin users do not need approval')
        return redirect(url_for('admin_users'))
        
    user.is_approved = True
    db.session.commit()
    
    flash(f'User {user.username} has been approved')
    return redirect(url_for('admin_users'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete yourself')
        return redirect(url_for('admin_users'))
    
    # Delete the user's team if it exists
    if user.team:
        db.session.delete(user.team)
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.username} has been deleted')
    return redirect(url_for('admin_users'))

@app.route('/admin/add_team', methods=['POST'])
@login_required
def admin_add_team():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    name = data.get('name')
    balance = data.get('balance', 1000000)  # Default balance if not provided
    
    if not name:
        return jsonify({'error': 'Team name is required'}), 400
    
    # Check if a team with this name already exists
    if Team.query.filter_by(name=name).first():
        return jsonify({'error': 'A team with this name already exists'}), 400
    
    # Create the team
    team = Team(name=name, balance=balance)
    db.session.add(team)
    db.session.commit()
    
    return jsonify({'message': 'Team added successfully', 'id': team.id})

@app.route('/admin/edit_team/<int:team_id>', methods=['POST'])
@login_required
def admin_edit_team(team_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    team = Team.query.get_or_404(team_id)
    data = request.json
    
    name = data.get('name')
    balance = data.get('balance')
    
    if not name:
        return jsonify({'error': 'Team name is required'}), 400
    
    # Check if another team with this name already exists
    existing_team = Team.query.filter_by(name=name).first()
    if existing_team and existing_team.id != team_id:
        return jsonify({'error': 'Another team with this name already exists'}), 400
    
    team.name = name
    if balance is not None:
        team.balance = balance
    
    db.session.commit()
    
    return jsonify({'message': 'Team updated successfully'})

@app.route('/admin/delete_team/<int:team_id>', methods=['POST'])
@login_required
def admin_delete_team(team_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    team = Team.query.get_or_404(team_id)
    
    # Check if team has players
    players = Player.query.filter_by(team_id=team_id).all()
    if players:
        return jsonify({'error': 'Cannot delete team with players. Please remove all players first.'}), 400
    
    # Check if team has active bids
    active_bids = Bid.query.join(Player).filter(
        Bid.team_id == team_id,
        Player.round_id != None
    ).all()
    
    if active_bids:
        return jsonify({'error': 'Cannot delete team with active bids'}), 400
    
    # Check if team is associated with a user
    if team.user_id:
        # Option 1: Prevent deletion if team has a user
        # return jsonify({'error': 'Cannot delete team that is associated with a user'}), 400
        
        # Option 2: Remove the team association from the user
        user = User.query.get(team.user_id)
        if user:
            user.team_id = None
    
    # Delete bids made by this team
    Bid.query.filter_by(team_id=team_id).delete()
    
    # Delete team tiebreakers
    TeamTiebreaker.query.filter_by(team_id=team_id).delete()
    
    # Delete the team
    db.session.delete(team)
    db.session.commit()
    
    return jsonify({'message': 'Team deleted successfully'})

@app.route('/team_players')
@login_required
def team_players():
    # Get filter and sort parameters
    position_filter = request.args.get('position', 'all')
    sort_by = request.args.get('sort', 'name')
    
    # Get the team's players
    players = current_user.team.players
    
    # Apply position filter if needed
    if position_filter != 'all':
        players = [p for p in players if p.position == position_filter]
    
    # Apply sorting
    if sort_by == 'rating':
        players = sorted(players, key=lambda p: p.overall_rating or 0, reverse=True)
    elif sort_by == 'cost':
        players = sorted(players, key=lambda p: p.cost or 0, reverse=True)
    elif sort_by == 'position':
        players = sorted(players, key=lambda p: p.position)
    else:  # Default: sort by name
        players = sorted(players, key=lambda p: p.name)
    
    return render_template('team_players.html', players=players)

@app.route('/team_players_data')
@login_required
def team_players_data():
    """
    Display all available players in the database with search, sort and filter options.
    Players can be filtered by position, playing style, and searched by name.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of players per page
    search_query = request.args.get('q', '')
    current_position = request.args.get('position', '')
    current_playing_style = request.args.get('playing_style', '')
    
    # Query players based on filters
    query = Player.query
    
    # Apply search filter if provided
    if search_query:
        query = query.filter(Player.name.ilike(f'%{search_query}%'))
    
    # Apply position filter if provided
    if current_position:
        query = query.filter(Player.position == current_position)
    
    # Apply playing style filter if provided
    if current_playing_style:
        query = query.filter(Player.playing_style == current_playing_style)
    
    # Get starred players for the current user
    # You need to implement this part if you have a StarredPlayer model
    # For now, we'll use an empty list
    starred_player_ids = []
    
    # Paginate results
    players_pagination = query.order_by(Player.overall_rating.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('team_players_data.html',
                          players=players_pagination.items,
                          players_pagination=players_pagination,
                          search_query=search_query,
                          current_position=current_position,
                          current_playing_style=current_playing_style,
                          starred_player_ids=starred_player_ids,
                          config=Config)

@app.route('/api/star_player/<int:player_id>', methods=['POST'])
@login_required
def star_player(player_id):
    """Add a player to the user's starred players list"""
    # Implementation depends on your database model for starred players
    # For now, just return success
    return jsonify({'success': True, 'message': 'Player starred successfully'})

@app.route('/api/unstar_player/<int:player_id>', methods=['POST'])
@login_required
def unstar_player(player_id):
    """Remove a player from the user's starred players list"""
    # Implementation depends on your database model for starred players
    # For now, just return success
    return jsonify({'success': True, 'message': 'Player unstarred successfully'})

@app.route('/team_bids')
@login_required
def team_bids():
    """
    Display a team's bidding history and statistics.
    This page shows current and past bids for the current user's team.
    """
    # Get active rounds for the "Place New Bid" button
    active_rounds = Round.query.filter_by(is_active=True).all()
    
    return render_template('team_bids.html',
                          active_rounds=active_rounds)

@app.route('/team_round')
@login_required
def team_round():
    """
    Redirects to the dashboard page where users can place bids in active rounds.
    This is a convenience route for the team_bids page.
    """
    return redirect(url_for('dashboard'))

# Password reset routes
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        reason = request.form.get('reason')
        
        if not username or not reason:
            flash('Username and reason are required', 'error')
            return render_template('reset_password_request.html')
        
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('User not found', 'error')
            return render_template('reset_password_request.html')
        
        # Check if there's already a pending request
        existing_request = PasswordResetRequest.query.filter_by(
            user_id=user.id, 
            status='pending'
        ).first()
        
        if existing_request:
            flash('You already have a pending password reset request', 'error')
            return render_template('reset_password_request.html')
        
        # Create a new password reset request
        reset_request = PasswordResetRequest(
            user_id=user.id,
            reason=reason
        )
        db.session.add(reset_request)
        db.session.commit()
        
        flash('Your password reset request has been submitted. An administrator will review your request.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password_request.html')

@app.route('/admin/password_requests')
@login_required
def admin_password_requests():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    reset_requests = PasswordResetRequest.query.order_by(
        PasswordResetRequest.status == 'pending',
        PasswordResetRequest.status == 'approved',
        PasswordResetRequest.created_at.desc()
    ).all()
    
    return render_template('admin_password_requests.html', reset_requests=reset_requests)

@app.route('/admin/approve_reset_request/<int:request_id>', methods=['POST'])
@login_required
def approve_reset_request(request_id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    reset_request = PasswordResetRequest.query.get_or_404(request_id)
    
    if reset_request.status != 'pending':
        flash('This request has already been processed', 'error')
        return redirect(url_for('admin_password_requests'))
    
    # Generate a unique token for this request
    token = reset_request.generate_token()
    
    # Update the status to approved
    reset_request.status = 'approved'
    db.session.commit()
    
    # Get the username for the message
    user = User.query.get(reset_request.user_id)
    
    flash(f'Password reset request for {user.username} has been approved. Please copy and share the reset link with the user from the admin panel.', 'success')
    return redirect(url_for('admin_password_requests'))

@app.route('/admin/reject_reset_request/<int:request_id>', methods=['POST'])
@login_required
def reject_reset_request(request_id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    reset_request = PasswordResetRequest.query.get_or_404(request_id)
    
    if reset_request.status != 'pending':
        flash('This request has already been processed', 'error')
        return redirect(url_for('admin_password_requests'))
    
    # Update the status to rejected
    reset_request.status = 'rejected'
    db.session.commit()
    
    flash('Password reset request rejected', 'success')
    return redirect(url_for('admin_password_requests'))

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_form(token):
    # Check if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Find the reset request with this token
    reset_request = PasswordResetRequest.get_by_token(token)
    
    if not reset_request:
        flash('Invalid or expired reset token', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or not confirm_password:
            flash('Please fill in all fields', 'error')
            return render_template('reset_password.html', reset_token=token)
        
        if new_password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', reset_token=token)
        
        # Reset the password
        user = User.query.get(reset_request.user_id)
        user.set_password(new_password)
        
        # Mark the request as completed
        reset_request.status = 'completed'
        reset_request.reset_token = None  # Invalidate the token
        db.session.commit()
        
        flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', reset_token=token)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 
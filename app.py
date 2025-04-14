from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Team, Player, Round, Bid, TiebreakerBid, StarredPlayer
from config import Config
from forms import LoginForm, RegistrationForm
from werkzeug.security import generate_password_hash
import json
from datetime import datetime, timedelta
import os
import pandas as pd
import io

app = Flask(__name__)
app.config.from_object(Config)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # Set remember cookie to last 30 days

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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
    active_rounds = Round.query.filter_by(is_active=True).all()
    for round in active_rounds:
        if round.is_timer_expired():
            print(f"Round {round.id} timer expired. Finalizing automatically.")
            try:
                # Use the unified finalization function with the appropriate flag
                finalize_auction_round(round.id, is_tiebreaker=round.is_tiebreaker)
            except Exception as e:
                print(f"Error auto-finalizing round {round.id}: {str(e)}")
    
    # Refresh the data after potentially finalizing rounds
    if current_user.is_admin:
        teams = Team.query.all()
        active_rounds = Round.query.filter_by(is_active=True, is_tiebreaker=False).all()
        
        # Get active tiebreaker rounds with related data
        tiebreaker_rounds = Round.query.filter_by(is_active=True, is_tiebreaker=True).all()
        
        # Load related data for each tiebreaker round
        for round in tiebreaker_rounds:
            # Load the player data
            round.player = Player.query.get(round.player_id)
            
            # Load tiebreaker bids with team data
            round.tiebreaker_bids = TiebreakerBid.query.filter_by(round_id=round.id).all()
            for bid in round.tiebreaker_bids:
                bid.team = Team.query.get(bid.team_id)
            
            # Sort bids by amount (highest first)
            round.tiebreaker_bids.sort(key=lambda x: x.amount, reverse=True)
        
        rounds = Round.query.all()
        
        # Get pending user approvals count
        pending_approvals = User.query.filter_by(is_approved=False, is_admin=False).count()
        
        # Get total players count for stats
        total_players = Player.query.count()
        
        return render_template('admin_dashboard.html', 
                              teams=teams, 
                              active_rounds=active_rounds,
                              tiebreaker_rounds=tiebreaker_rounds,
                              rounds=rounds, 
                              pending_approvals=pending_approvals,
                              total_players=total_players,
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
        # Finalize the round using the consolidated function
        finalize_auction_round(round_id, is_tiebreaker=True)
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
    
    # Get all bids for the current team
    team_bids = current_user.team.bids
    
    # Group bids by player and bid amount to detect ties
    player_bid_amounts = {}
    for bid in Bid.query.all():
        key = f"{bid.player_id}-{bid.amount}"
        if key not in player_bid_amounts:
            player_bid_amounts[key] = []
        player_bid_amounts[key].append(bid)
    
    # Mark tied bids
    tied_bid_ids = set()
    for key, bids in player_bid_amounts.items():
        if len(bids) > 1:  # If multiple teams bid the same amount for a player
            for bid in bids:
                tied_bid_ids.add(bid.id)
    
    # Add is_tied property to each bid
    for bid in team_bids:
        bid.is_tied = bid.id in tied_bid_ids
    
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
    current_time = datetime.utcnow()
    time_elapsed = (current_time - round.start_time).total_seconds()
    remaining = max(0, round.duration - time_elapsed)
    
    status = 'active'
    
    # Check if the round is already inactive
    if not round.is_active:
        status = 'ended'
    # Check if the timer has expired but round is still active
    elif time_elapsed >= round.duration:
        # Timer expired - finalize the round automatically using the consolidated function
        finalize_auction_round(round.id, is_tiebreaker=round.is_tiebreaker)
        status = 'ended'
    
    return jsonify({
        'status': status,
        'active': status == 'active',
        'remaining': remaining
    })

def track_finalization_status(round_id, status, message=None):
    """Track the status of round finalization attempts to help debugging
    
    Args:
        round_id: The ID of the round being finalized
        status: 'started', 'completed', 'failed', 'resumed'
        message: Optional message with details
    """
    try:
        # Log to console for now
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] Round {round_id} finalization {status}: {message if message else 'No details'}")
        
        # In a future version we could store this in the database
        # for better tracking of auction process issues
        return True
    except Exception as e:
        print(f"Error logging finalization status: {str(e)}")
        return False

def report_auction_status():
    """Generate a comprehensive report on the current state of all auction rounds.
    
    This helps identify any stuck or problematic rounds.
    """
    try:
        active_main_rounds = Round.query.filter_by(is_active=True, is_tiebreaker=False).all()
        active_tiebreaker_rounds = Round.query.filter_by(is_active=True, is_tiebreaker=True).all()
        
        print("\n=== AUCTION STATUS REPORT ===")
        
        # Main rounds
        print(f"\nActive Main Rounds: {len(active_main_rounds)}")
        for r in active_main_rounds:
            elapsed = (datetime.utcnow() - r.start_time).total_seconds() if r.start_time else 0
            print(f"  Round ID: {r.id}, Position: {r.position}, Duration: {r.duration}s, Elapsed: {elapsed:.1f}s")
            # Count players in this round
            player_count = Player.query.filter_by(round_id=r.id).count()
            # Count bids in this round
            bid_count = Bid.query.filter_by(round_id=r.id).count()
            print(f"    Players: {player_count}, Bids: {bid_count}")
        
        # Tiebreaker rounds
        print(f"\nActive Tiebreaker Rounds: {len(active_tiebreaker_rounds)}")
        for r in active_tiebreaker_rounds:
            elapsed = (datetime.utcnow() - r.start_time).total_seconds() if r.start_time else 0
            parent = Round.query.get(r.parent_round_id) if r.parent_round_id else None
            parent_status = f"Parent: {r.parent_round_id} ({'active' if parent and parent.is_active else 'inactive' if parent else 'unknown'})"
            
            print(f"  Tiebreaker ID: {r.id}, Position: {r.position}, {parent_status}")
            print(f"    Duration: {r.duration}s, Elapsed: {elapsed:.1f}s")
            
            # Get player info
            player = Player.query.get(r.player_id)
            if player:
                print(f"    Player: {player.name} (ID: {player.id})")
            
            # Count bids
            bid_count = TiebreakerBid.query.filter_by(round_id=r.id).count()
            print(f"    Bids: {bid_count}")
        
        print("\n=== END OF REPORT ===\n")
        return True
    except Exception as e:
        print(f"Error generating auction status report: {str(e)}")
        return False

def validate_active_bids(round_id):
    """Validate all active bids to ensure teams have sufficient balance.
    
    Returns:
        tuple: (is_valid, list of invalid bids)
    """
    all_bids = Bid.query.filter_by(round_id=round_id).all()
    teams = {}  # Cache team objects
    invalid_bids = []
    
    # Group bids by team
    team_bids = {}
    for bid in all_bids:
        if bid.team_id not in team_bids:
            team_bids[bid.team_id] = []
            # Cache the team object
            if bid.team_id not in teams:
                teams[bid.team_id] = Team.query.get(bid.team_id)
        
        team_bids[bid.team_id].append(bid)
    
    # Validate each team's bids
    for team_id, bids in team_bids.items():
        team = teams[team_id]
        # Calculate total bid amount
        total_bid_amount = sum(bid.amount for bid in bids)
        
        # Check if team has enough balance
        if total_bid_amount > team.balance:
            for bid in bids:
                invalid_bids.append({
                    'bid_id': bid.id,
                    'team_id': team_id,
                    'team_name': team.name,
                    'player_id': bid.player_id,
                    'amount': bid.amount,
                    'balance': team.balance
                })
    
    return (len(invalid_bids) == 0, invalid_bids)

def finalize_round_internal(round_id):
    """Internal function to handle the finalization of a round"""
    round = Round.query.get(round_id)
    if not round or not round.is_active:
        return False
    
    track_finalization_status(round_id, "started", f"position: {round.position}")
    
    print(f"Starting round finalization for round {round_id} (position: {round.position})")
    
    # Get all bids for this round and sort by amount (highest first)
    all_bids = Bid.query.filter_by(round_id=round_id).all()
    
    # Validate all active bids to ensure teams have sufficient balance
    is_valid, invalid_bids = validate_active_bids(round_id)
    if not is_valid:
        print(f"WARNING: Found {len(invalid_bids)} invalid bids due to insufficient team balance")
        for invalid in invalid_bids:
            print(f"  Team {invalid['team_name']} (ID: {invalid['team_id']}) has insufficient balance ({invalid['balance']}) for bid amount {invalid['amount']}")
    
    # Group bids by player and team to find the latest bid for each player-team combination
    # This handles edited bids by keeping only the latest bid amount for each team-player pair
    latest_bids = {}
    for bid in all_bids:
        key = f"{bid.player_id}-{bid.team_id}"
        if key not in latest_bids or bid.timestamp > latest_bids[key].timestamp:
            latest_bids[key] = bid
    
    # Convert to list and sort by amount (highest first)
    sorted_bids = sorted(latest_bids.values(), key=lambda x: x.amount, reverse=True)
    
    print(f"Found {len(sorted_bids)} unique bids after handling edited values")
    
    # Ensure we get the latest allocation state from the database
    # This helps prevent issues if other processes have modified allocations
    db.session.flush()
    
    # Keep track of allocated teams and players to prevent duplicates
    allocated_teams = set()
    allocated_players = set()
    
    # Pre-load current allocations to ensure we don't create conflicts
    # Get all players that already have a team assigned (globally, not just this round)
    for player in Player.query.filter(Player.team_id != None).all():
        allocated_players.add(player.id)
        allocated_teams.add(player.team_id)
    
    print(f"Pre-loaded {len(allocated_players)} allocated players and {len(allocated_teams)} allocated teams")
    
    # Track ties that need tiebreaker rounds
    ties_to_resolve = []
    
    try:
        # First pass: identify ties and create tiebreaker rounds
        i = 0
        while i < len(sorted_bids):
            current_bid = sorted_bids[i]
            
            # Skip if team or player already allocated
            if current_bid.team_id in allocated_teams or current_bid.player_id in allocated_players:
                i += 1
                continue
                
            # Check for ties (same amount for same player)
            tied_bids = []
            j = i
            while j < len(sorted_bids) and sorted_bids[j].amount == current_bid.amount and sorted_bids[j].player_id == current_bid.player_id:
                if sorted_bids[j].team_id not in allocated_teams:
                    tied_bids.append(sorted_bids[j])
                j += 1
                
            # Process ties
            if len(tied_bids) > 1:
                print(f"Found tie: {len(tied_bids)} teams bid {current_bid.amount} for player ID {current_bid.player_id}")
                # Create a tiebreaker round
                player = Player.query.get(current_bid.player_id)
                tiebreaker_round = Round(
                    position=round.position,
                    is_active=True,
                    is_tiebreaker=True,
                    parent_round_id=round.id,
                    player_id=current_bid.player_id,
                    duration=180  # 3 minutes for tiebreaker
                )
                db.session.add(tiebreaker_round)
                db.session.flush()  # Get the ID without committing
                
                # Add the tied teams to the tiebreaker round
                for bid in tied_bids:
                    # Get the team and check its balance against the original bid amount first
                    team = Team.query.get(bid.team_id)
                    original_bid = Bid.query.filter_by(
                        round_id=round.parent_round_id,
                        team_id=bid.team_id,
                        player_id=round.player_id
                    ).first()
                    
                    # Skip teams with insufficient balance for the original bid
                    if original_bid and team.balance < original_bid.amount:
                        print(f"Team {team.id} has insufficient balance for subsequent tiebreaker round - skipping")
                        continue
                    
                    # Use the original bid amount as starting point for the tiebreaker
                    tiebreaker_bid = TiebreakerBid(
                        team_id=bid.team_id,
                        player_id=bid.player_id,
                        round_id=tiebreaker_round.id,
                        amount=bid.amount  # Use original bid amount instead of 0
                    )
                    db.session.add(tiebreaker_bid)
                    
                # Store tie information for later processing
                ties_to_resolve.append({
                    'tiebreaker_round_id': tiebreaker_round.id,
                    'player_id': current_bid.player_id,
                    'bid_amount': current_bid.amount,
                    'tied_teams': [bid.team_id for bid in tied_bids]
                })
                
                # Reserve this player to prevent other allocations
                allocated_players.add(current_bid.player_id)
                
                # Skip all these tied bids
                i = j
            else:
                # No tie, just a single bid
                i += 1
        
        # Commit tiebreaker rounds to the database
        db.session.commit()
        
        # If we have ties to resolve, we need to pause the main finalization
        if ties_to_resolve:
            print(f"Round {round_id} has {len(ties_to_resolve)} ties to resolve. Pausing main finalization.")
            round.is_active = False  # Deactivate the main round
            db.session.commit()
            track_finalization_status(round_id, "paused", f"Created {len(ties_to_resolve)} tiebreaker rounds")
            return True
            
        # Second pass: allocate players to teams based on highest bids
        print("No ties found. Proceeding with player allocation.")
        allocation_count = 0
        
        # Keep track of players that were involved in tiebreaker rounds
        tiebreaker_players = set()
        for tr in Round.query.filter_by(parent_round_id=round_id, is_tiebreaker=True).all():
            if tr.player_id:
                tiebreaker_players.add(tr.player_id)
        
        print(f"Found {len(tiebreaker_players)} players involved in tiebreaker rounds - skipping these")
        
        for bid in sorted_bids:
            # Skip if team or player already allocated
            if bid.team_id in allocated_teams or bid.player_id in allocated_players:
                continue
                
            # Skip players that were handled by tiebreaker rounds
            if bid.player_id in tiebreaker_players:
                continue
            
            # Double-check current allocation status in database before proceeding
            player = Player.query.get(bid.player_id)
            team = Team.query.get(bid.team_id)
            
            if player.team_id is not None:
                # Player already allocated elsewhere - skip
                allocated_players.add(player.id)
                continue
            
            # Verify team has sufficient balance
            if team.balance < bid.amount:
                print(f"Team {team.id} has insufficient balance ({team.balance}) for bid amount {bid.amount}")
                continue
                
            # Allocate player to team
            print(f"Allocating player ID {bid.player_id} to team ID {bid.team_id} for {bid.amount}")
            
            # Update team's balance
            team.balance -= bid.amount
            
            # Set the player's team
            player.team_id = team.id
            
            # Mark as allocated
            allocated_teams.add(team.id)
            allocated_players.add(player.id)
            allocation_count += 1
        
        round.is_active = False
        db.session.commit()
        print(f"Round {round_id} finalization completed. {allocation_count} allocations made.")
        track_finalization_status(round_id, "completed", f"{allocation_count} allocations made")
        return True
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error in round finalization: {str(e)}")
        traceback.print_exc()
        track_finalization_status(round_id, "failed", f"Error: {str(e)}")
        return False

@app.route('/finalize_round/<int:round_id>', methods=['POST'])
@login_required
def finalize_round(round_id):
    """Endpoint to finalize a regular auction round
    
    This endpoint now uses the consolidated auction round finalization process,
    which provides a unified approach for handling both regular and tiebreaker rounds.
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    round = Round.query.get_or_404(round_id)
    if not round.is_active:
        return jsonify({'error': 'Round already finalized'}), 400
    
    # Use the consolidated finalization function
    success = finalize_auction_round(round_id, is_tiebreaker=False)
    
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
    
    try:
        # Convert amount to integer if it's not already
        amount = int(amount)
    except ValueError:
        return jsonify({'error': 'Bid amount must be a valid number'}), 400
    
    round = Round.query.get_or_404(round_id)
    if round.is_timer_expired():
        # If timer expired, finalize the round and reject the bid
        finalize_auction_round(round_id, is_tiebreaker=False)
        return jsonify({'error': 'Round timer has expired'}), 400
    
    if amount < Config.MINIMUM_BID:
        return jsonify({'error': f'Bid must be at least {Config.MINIMUM_BID}'}), 400
    
    team = current_user.team
    if team.balance < amount:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    # Additional check: Ensure team has enough balance for all their active bids
    active_bids = Bid.query.filter_by(team_id=team.id).all()
    total_bid_amount = sum(bid.amount for bid in active_bids)
    
    # Check if existing bids + new bid would exceed team balance
    if total_bid_amount + amount > team.balance:
        return jsonify({'error': 'Insufficient balance to cover all your active bids'}), 400
    
    # Check if team has reached the maximum number of bids (20)
    total_bids = Bid.query.filter_by(team_id=team.id).count()
    if total_bids >= 20:
        return jsonify({'error': 'Maximum bid limit (20) reached for your team'}), 400
    
    # Check if the team is already involved in any active tiebreaker rounds
    active_tiebreakers = TiebreakerBid.query.join(Round, TiebreakerBid.round_id == Round.id).filter(
        TiebreakerBid.team_id == team.id,
        Round.is_active == True
    ).count()
    
    if active_tiebreakers > 0:
        return jsonify({
            'error': 'Your team is currently involved in a tiebreaker round. Please complete that first.'
        }), 400
    
    # Check if the player is already in an active tiebreaker round
    player_in_tiebreaker = Round.query.filter(
        Round.player_id == player_id,
        Round.is_active == True,
        Round.is_tiebreaker == True
    ).first() is not None
    
    if player_in_tiebreaker:
        return jsonify({
            'error': 'This player is currently involved in a tiebreaker round and cannot receive bids.'
        }), 400
    
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
    
    # Verify player doesn't already have a team
    player = Player.query.get(player_id)
    if player.team_id is not None:
        return jsonify({
            'error': f'This player is already allocated to a team and cannot receive bids.'
        }), 400
    
    try:
        bid = Bid(
            team_id=team.id,
            player_id=player_id,
            round_id=round_id,
            amount=amount
        )
        db.session.add(bid)
        db.session.commit()
        
        return jsonify({'message': 'Bid placed successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Error placing bid: {str(e)}")
        return jsonify({'error': 'An error occurred while placing your bid'}), 500

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
        finalize_auction_round(round.id, is_tiebreaker=False)
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
    
    try:
        # Convert amount to integer if it's not already
        amount = int(amount)
    except ValueError:
        return jsonify({'error': 'Bid amount must be a valid number'}), 400
    
    round = Round.query.get_or_404(round_id)
    if not round.is_tiebreaker:
        return jsonify({'error': 'This is not a tiebreaker round'}), 400
    
    if round.is_timer_expired():
        finalize_auction_round(round_id, is_tiebreaker=True)
        return jsonify({'error': 'Round timer has expired'}), 400
    
    team = current_user.team
    if team.balance < amount:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    # Additional check: Ensure team has enough balance for all their active bids 
    # Get the original bid amount from the parent round
    parent_round = Round.query.get(round.parent_round_id)
    if parent_round:
        original_bid = Bid.query.filter_by(
            round_id=parent_round.id,
            team_id=team.id,
            player_id=player_id
        ).first()
        
        # We need to make sure the team can afford ALL their active bids plus this one
        active_bids = Bid.query.filter_by(team_id=team.id).all()
        total_bid_amount = sum(bid.amount for bid in active_bids)
        
        # Use the original bid amount from the parent round as that's what will be deducted
        original_amount = original_bid.amount if original_bid else amount
        
        # Check if this would exceed team balance
        if total_bid_amount + original_amount > team.balance:
            return jsonify({'error': 'Insufficient balance to cover all your active bids'}), 400
    
    # Check if team is allowed in this tiebreaker
    existing_bid = TiebreakerBid.query.filter_by(
        team_id=team.id,
        round_id=round_id
    ).first()
    
    if not existing_bid:
        return jsonify({'error': 'Your team is not part of this tiebreaker'}), 403
    
    # Verify that player isn't already allocated
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
        
    if player.team_id is not None:
        return jsonify({'error': 'This player has already been allocated to a team'}), 400
    
    # Verify this team isn't already allocated another player globally
    team_has_player = Player.query.filter_by(team_id=team.id).first() is not None
    if team_has_player:
        return jsonify({'error': 'Your team already has a player allocated. You cannot bid on another.'}), 400
    
    try:
        # Update the bid amount
        existing_bid.amount = amount
        db.session.commit()
        
        return jsonify({'message': 'Tiebreaker bid placed successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Error placing tiebreaker bid: {str(e)}")
        return jsonify({'error': 'An error occurred while placing your tiebreaker bid'}), 500

def finalize_tiebreaker_round(round_id):
    """Finalize a tiebreaker round and allocate the player"""
    round = Round.query.get(round_id)
    if not round or not round.is_tiebreaker or not round.is_active:
        return False
    
    track_finalization_status(round_id, "started", f"tiebreaker for player ID {round.player_id}")
    
    print(f"Finalizing tiebreaker round {round_id} for player ID {round.player_id}")
    
    # Get all bids for this tiebreaker round
    bids = TiebreakerBid.query.filter_by(round_id=round_id).all()
    if not bids:
        print("No bids found in tiebreaker round")
        round.is_active = False
        db.session.commit()
        return False
    
    # Get the parent round
    parent_round = Round.query.get(round.parent_round_id)
    if not parent_round:
        print(f"Parent round {round.parent_round_id} not found")
        round.is_active = False
        db.session.commit()
        return False
    
    try:
        # Ensure we get the latest allocation state
        db.session.flush()
        
        # Get teams that already have a player allocated (global check)
        allocated_teams = set()
        allocated_players = set()
        
        # Check all players with a team assigned
        for player in Player.query.filter(Player.team_id != None).all():
            allocated_teams.add(player.team_id)
            allocated_players.add(player.id)
        
        print(f"Found {len(allocated_teams)} teams and {len(allocated_players)} players already allocated")
        
        # Filter out teams that already have a player
        eligible_bids = [bid for bid in bids if bid.team_id not in allocated_teams]
        
        # If no eligible bids left, player stays unallocated
        if not eligible_bids:
            print("No eligible bids remain after filtering allocated teams")
            round.is_active = False
            db.session.commit()
            return True
        
        # Sort eligible bids by amount (highest first)
        eligible_bids.sort(key=lambda x: x.amount, reverse=True)
        highest_bid = eligible_bids[0]
        
        # Check for another tie at the highest bid amount
        tied_bids = [bid for bid in eligible_bids if bid.amount == highest_bid.amount]
        if len(tied_bids) > 1:
            print(f"Found another tie in tiebreaker round with {len(tied_bids)} teams")
            # Create another tiebreaker round
            new_tiebreaker = Round(
                position=round.position,
                is_active=True,
                is_tiebreaker=True,
                parent_round_id=round.parent_round_id,  # Keep the original parent
                player_id=round.player_id,
                duration=180
            )
            db.session.add(new_tiebreaker)
            db.session.commit()
            
            # Add the tied teams to the new tiebreaker
            for bid in tied_bids:
                # Get the team and check its balance against the original bid amount first
                team = Team.query.get(bid.team_id)
                original_bid = Bid.query.filter_by(
                    round_id=round.parent_round_id,
                    team_id=bid.team_id,
                    player_id=round.player_id
                ).first()
                
                # Skip teams with insufficient balance for the original bid
                if original_bid and team.balance < original_bid.amount:
                    print(f"Team {team.id} has insufficient balance for subsequent tiebreaker round - skipping")
                    continue
                
                new_bid = TiebreakerBid(
                    team_id=bid.team_id,
                    player_id=bid.player_id,
                    round_id=new_tiebreaker.id,
                    amount=bid.amount  # Use original bid amount instead of 0
                )
                db.session.add(new_bid)
            
            # Commit the new tiebreaker round
            db.session.commit()
            
            track_finalization_status(round_id, "completed", f"Created new tiebreaker round {new_tiebreaker.id} for {len(tied_bids)} teams")
            
            # Check if we have any eligible bids in the new tiebreaker
            eligible_bid_count = TiebreakerBid.query.filter_by(round_id=new_tiebreaker.id).count()
            if eligible_bid_count <= 0:
                print(f"No eligible teams remain for the new tiebreaker round - canceling tiebreaker")
                # Delete the new tiebreaker round and allocate the player based on original round
                db.session.delete(new_tiebreaker)
                round.is_active = False
                db.session.commit()
                
                # Resume the parent round processing
                if parent_round:
                    resume_after_tiebreaker(parent_round.id)
                return True
        else:
            # We have a winner - allocate the player to the team with the highest bid
            team = Team.query.get(highest_bid.team_id)
            player = Player.query.get(round.player_id)
            
            # Verify team has sufficient balance
            if team.balance < highest_bid.amount:
                print(f"Team {team.id} has insufficient balance ({team.balance}) for tiebreaker bid amount {highest_bid.amount}")
                round.is_active = False
                db.session.commit()
                return True
            
            # Get the original bid from the parent round for bid history purposes
            original_bid = Bid.query.filter_by(
                round_id=round.parent_round_id,
                team_id=team.id,
                player_id=player.id
            ).first()
            
            if original_bid:
                # We'll need to modify the original bid amount to match the winning tiebreaker bid
                # This ensures the bid history shows the correct final bid amount
                original_bid.amount = highest_bid.amount
            else:
                # If there's no original bid record (rare case), create one for history
                new_bid = Bid(
                    team_id=team.id,
                    player_id=player.id,
                    round_id=round.parent_round_id,
                    amount=highest_bid.amount,
                    timestamp=datetime.utcnow()
                )
                db.session.add(new_bid)
            
            # Update team's balance
            team.balance -= highest_bid.amount
            
            # Set the player's team
            player.team_id = team.id
            
            # Mark this player and team as allocated
            allocated_teams.add(team.id)
            allocated_players.add(player.id)
            
            print(f"Successfully allocated player {player.id} to team {team.id} for {highest_bid.amount} (tiebreaker winning bid)")
        
        # Deactivate this tiebreaker round
        round.is_active = False
        db.session.commit()
        
        # Check if the parent round has any unresolved tiebreakers
        active_tiebreakers = Round.query.filter_by(
            parent_round_id=round.parent_round_id,
            is_active=True
        ).count()
        
        # If parent round has no active tiebreakers, resume its finalization
        if active_tiebreakers == 0 and not parent_round.is_active:
            print(f"All tiebreakers resolved for parent round {parent_round.id}, resuming finalization")
            # Continue with the auction process
            resume_after_tiebreaker(parent_round.id)
        
        return True
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error in tiebreaker finalization: {str(e)}")
        traceback.print_exc()
        track_finalization_status(round_id, "failed", f"Error: {str(e)}")
        return False

def resume_after_tiebreaker(round_id):
    """Resume the finalization process after tiebreakers have been resolved"""
    round = Round.query.get(round_id)
    if not round:
        return False
    
    track_finalization_status(round_id, "resumed", "after tiebreakers resolved")
    
    print(f"Resuming finalization for round {round_id} after tiebreakers")
    
    try:
        # Get latest bids (edited bids handled)
        all_bids = Bid.query.filter_by(round_id=round_id).all()
        latest_bids = {}
        for bid in all_bids:
            key = f"{bid.player_id}-{bid.team_id}"
            if key not in latest_bids or bid.timestamp > latest_bids[key].timestamp:
                latest_bids[key] = bid
        
        # Convert to list and sort by amount (highest first)
        sorted_bids = sorted(latest_bids.values(), key=lambda x: x.amount, reverse=True)
        
        # Ensure we have the latest DB state
        db.session.flush()
        
        # Find currently allocated teams and players (globally)
        allocated_teams = set()
        allocated_players = set()
        
        # Check all players with a team assigned (global check)
        for player in Player.query.filter(Player.team_id != None).all():
            allocated_teams.add(player.team_id)
            allocated_players.add(player.id)
            
        print(f"Found {len(allocated_teams)} teams and {len(allocated_players)} players already allocated globally")
        
        # Process remaining bids
        allocation_count = 0
        
        # Keep track of players that were involved in tiebreaker rounds
        tiebreaker_players = set()
        for tr in Round.query.filter_by(parent_round_id=round_id, is_tiebreaker=True).all():
            if tr.player_id:
                tiebreaker_players.add(tr.player_id)
        
        print(f"Found {len(tiebreaker_players)} players involved in tiebreaker rounds - skipping these")
        
        for bid in sorted_bids:
            # Skip if team or player already allocated
            if bid.team_id in allocated_teams or bid.player_id in allocated_players:
                continue
                
            # Skip players that were handled by tiebreaker rounds
            if bid.player_id in tiebreaker_players:
                continue
            
            # Double-check current allocation status directly from database
            player = Player.query.get(bid.player_id)
            team = Team.query.get(bid.team_id)
            
            # Skip if player or team doesn't exist or player already has a team
            if not player or not team or player.team_id is not None:
                if player and player.team_id is not None:
                    allocated_players.add(player.id)
                continue
            
            # Verify team has sufficient balance
            if team.balance < bid.amount:
                print(f"Team {team.id} has insufficient balance ({team.balance}) for bid amount {bid.amount}")
                continue
                
            # No need to check for ties - they should have been handled already
            # Allocate player to team
            print(f"Allocating player ID {bid.player_id} to team ID {bid.team_id} for {bid.amount}")
            
            # Update team's balance
            team.balance -= bid.amount
            
            # Set the player's team
            player.team_id = team.id
            
            # Mark as allocated
            allocated_teams.add(team.id)
            allocated_players.add(player.id)
            allocation_count += 1
        
        db.session.commit()
        print(f"Finalization completed for round {round_id} after tiebreakers. {allocation_count} additional allocations made.")
        track_finalization_status(round_id, "completed", f"{allocation_count} additional allocations made")
        return True
    
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error in resuming after tiebreaker: {str(e)}")
        traceback.print_exc()
        track_finalization_status(round_id, "failed", f"Error during resume: {str(e)}")
        return False

@app.route('/finalize_tiebreaker/<int:round_id>', methods=['POST'])
@login_required
def finalize_tiebreaker(round_id):
    """Endpoint to finalize a tiebreaker round
    
    This endpoint now uses the consolidated auction round finalization process,
    which provides a unified approach for handling both regular and tiebreaker rounds.
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Only admins can finalize rounds'}), 403
    
    # Use the consolidated finalization function with tiebreaker flag
    success = finalize_auction_round(round_id, is_tiebreaker=True)
    
    if success:
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
    
    # Group bids by player and team to find the latest bid for each player-team combination
    latest_bids = {}
    for bid in all_bids:
        key = f"{bid.player_id}-{bid.team_id}"
        if key not in latest_bids or bid.timestamp > latest_bids[key].timestamp:
            latest_bids[key] = bid
    
    # Find ties - group bids by player and amount
    tied_bids = {}
    for bid in latest_bids.values():
        key = f"{bid.player_id}-{bid.amount}"
        if key not in tied_bids:
            tied_bids[key] = []
        tied_bids[key].append(bid)
    
    # Mark tied bids (when multiple teams bid the same amount for the same player)
    tied_bid_ids = set()
    for key, bids in tied_bids.items():
        if len(bids) > 1:
            for bid in bids:
                tied_bid_ids.add(bid.id)
    
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
            is_tied = bid.id in tied_bid_ids
            
            # Format the timestamp for display
            created_at = bid.timestamp.strftime('%d/%m/%Y %H:%M:%S') if bid.timestamp else 'N/A'
            
            # Create bid data structure
            bid_data = {
                'player': player,
                'amount': bid.amount,
                'is_winning': is_winning,
                'is_tied': is_tied,
                'created_at': created_at
            }
            
            # Add to team bids
            team_bids[bid.team_id]['bids'].append(bid_data)
            print(f"Added bid for player {player.name} to team {team_bids[bid.team_id]['team'].name} (amount: {bid.amount}, winning: {is_winning}, tied: {is_tied})")
            
            # If this is a winning bid, add to winning bids list
            if is_winning:
                winning_bids.append({
                    'bid': bid,
                    'player': player,
                    'team': team_bids[bid.team_id]['team']
                })
    
    # Check for associated tiebreaker rounds
    tiebreaker_rounds = []
    
    # If this is a regular round, find all associated tiebreaker rounds
    if not round.is_tiebreaker:
        tiebreaker_rounds = Round.query.filter_by(parent_round_id=round.id, is_tiebreaker=True).all()
    
    # Gather data for all tiebreaker rounds
    tiebreaker_data = []
    for tb_round in tiebreaker_rounds:
        # Get player details
        player = Player.query.get(tb_round.player_id)
        
        # Get all tiebreaker bids for this round
        tb_bids = TiebreakerBid.query.filter_by(round_id=tb_round.id).all()
        
        # Process bid information
        bids_info = []
        for tb_bid in tb_bids:
            team = Team.query.get(tb_bid.team_id)
            
            # Determine if this is the winning bid
            is_winning = False
            if player and player.team_id == team.id:
                is_winning = True
                
            bids_info.append({
                'team': team,
                'amount': tb_bid.amount,
                'is_winning': is_winning
            })
        
        # Sort bids by amount (highest first)
        bids_info.sort(key=lambda x: x['amount'], reverse=True)
        
        # Add tiebreaker round data
        tiebreaker_data.append({
            'round': tb_round,
            'player': player,
            'bids': bids_info,
            'is_active': tb_round.is_active
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
        tiebreaker_data=tiebreaker_data,
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

@app.route('/admin/auction_status')
@login_required
def admin_auction_status():
    if not current_user.is_admin:
        flash("Admin access required")
        return redirect(url_for('index'))
    
    # Get all active rounds (both regular and tiebreaker)
    active_rounds = Round.query.filter_by(is_active=True).all()
    
    # Separate regular and tiebreaker rounds
    regular_rounds = [r for r in active_rounds if r.is_tiebreaker == False]
    tiebreaker_rounds = [r for r in active_rounds if r.is_tiebreaker == True]
    
    # Count players in each round
    round_data = []
    for round in regular_rounds:
        players_in_round = Player.query.filter_by(round_id=round.id).count()
        round_data.append({
            'round': round,
            'player_count': players_in_round
        })
    
    # For tiebreaker rounds, there's always just one player
    tiebreaker_data = []
    for round in tiebreaker_rounds:
        tiebreaker_data.append({
            'round': round,
            'player_count': 1  # Tiebreaker rounds always involve exactly one player
        })
    
    return render_template('admin_auction_status.html', 
                          regular_rounds=round_data,
                          tiebreaker_rounds=tiebreaker_data)

def finalize_auction_round(round_id, is_tiebreaker=False):
    """Consolidated function to handle auction round finalization.
    
    This function handles both regular rounds and tiebreaker rounds in a unified process,
    ensuring proper handling of all finalization steps including balance checks, allocation,
    and notification of results.
    
    Args:
        round_id: The ID of the round to finalize
        is_tiebreaker: Whether this is a tiebreaker round
        
    Returns:
        bool: True if finalization was successful, False otherwise
    """
    # Track the start of finalization
    status_type = "tiebreaker" if is_tiebreaker else "regular"
    track_finalization_status(round_id, "started", f"Unified {status_type} round finalization")
    
    # Get the round
    round = Round.query.get(round_id)
    if not round:
        track_finalization_status(round_id, "failed", f"Round {round_id} not found")
        return False
    
    # Check if round is active
    if not round.is_active:
        track_finalization_status(round_id, "failed", f"Round {round_id} is not active")
        return False
    
    # Verify tiebreaker status
    if is_tiebreaker != round.is_tiebreaker:
        track_finalization_status(round_id, "failed", 
                                 f"Tiebreaker mismatch: expected {is_tiebreaker}, got {round.is_tiebreaker}")
        return False

    try:
        # Handle different finalization paths based on round type
        if is_tiebreaker:
            return process_tiebreaker_finalization(round)
        else:
            return process_regular_finalization(round)
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error in unified round finalization: {str(e)}")
        traceback.print_exc()
        track_finalization_status(round_id, "failed", f"Error: {str(e)}")
        return False

def process_regular_finalization(round):
    """Process the finalization of a regular auction round.
    
    This follows a systematic approach:
    1. Get all bids and sort by amount (highest first)
    2. Process bids in order, checking for ties
    3. For tied bids, create tiebreaker rounds and pause finalization IMMEDIATELY
    4. After allocating a player, remove both player and team from consideration
    5. Continue until all bids are processed or all players/teams are allocated
    
    Args:
        round: The Round object to finalize
        
    Returns:
        bool: True if finalization was successful, False otherwise
    """
    print(f"Starting finalization for round {round.id} (position: {round.position})")
    
    # Get all bids for this round
    all_bids = Bid.query.filter_by(round_id=round.id).all()
    
    # Validate all active bids to ensure teams have sufficient balance
    is_valid, invalid_bids = validate_active_bids(round.id)
    if not is_valid:
        print(f"WARNING: Found {len(invalid_bids)} invalid bids due to insufficient team balance")
        for invalid in invalid_bids:
            print(f"  Team {invalid['team_name']} (ID: {invalid['team_id']}) has insufficient balance ({invalid['balance']}) for bid amount {invalid['amount']}")
    
    # Group bids by player and team to find the latest bid for each player-team combination
    # This handles edited bids by keeping only the latest bid amount for each team-player pair
    latest_bids = {}
    for bid in all_bids:
        key = f"{bid.player_id}-{bid.team_id}"
        if key not in latest_bids or bid.timestamp > latest_bids[key].timestamp:
            latest_bids[key] = bid
    
    # Convert to list and sort by amount (highest first)
    sorted_bids = sorted(latest_bids.values(), key=lambda x: x.amount, reverse=True)
    
    print(f"Found {len(sorted_bids)} unique bids after handling edited values")
    
    # Ensure we get the latest allocation state from the database
    db.session.flush()
    
    # Keep track of allocated teams and players to prevent duplicates
    allocated_teams = set()
    allocated_players = set()
    
    # Pre-load current allocations to ensure we don't create conflicts
    # Get all players that already have a team assigned (globally, not just this round)
    for player in Player.query.filter(Player.team_id != None).all():
        allocated_players.add(player.id)
        allocated_teams.add(player.team_id)
    
    print(f"Pre-loaded {len(allocated_players)} allocated players and {len(allocated_teams)} allocated teams")
    
    # Track ties that need tiebreaker rounds
    ties_to_resolve = []
    
    # Process bids in descending order, checking for ties
    i = 0
    while i < len(sorted_bids):
        current_bid = sorted_bids[i]
        
        # Skip if team or player already allocated
        if current_bid.team_id in allocated_teams or current_bid.player_id in allocated_players:
            i += 1
            continue
            
        # Check for ties (same amount for same player)
        tied_bids = []
        j = i
        while j < len(sorted_bids) and sorted_bids[j].amount == current_bid.amount and sorted_bids[j].player_id == current_bid.player_id:
            if sorted_bids[j].team_id not in allocated_teams:
                tied_bids.append(sorted_bids[j])
            j += 1
            
        # Process ties
        if len(tied_bids) > 1:
            print(f"Found tie: {len(tied_bids)} teams bid {current_bid.amount} for player ID {current_bid.player_id}")
            # Create a tiebreaker round
            player = Player.query.get(current_bid.player_id)
            tiebreaker_round = Round(
                position=round.position,
                is_active=True,
                is_tiebreaker=True,
                parent_round_id=round.id,
                player_id=current_bid.player_id,
                duration=180  # 3 minutes for tiebreaker
            )
            db.session.add(tiebreaker_round)
            db.session.flush()  # Get the ID without committing
            
            # Add the tied teams to the tiebreaker round
            for bid in tied_bids:
                # Get the team and check its balance against the original bid amount first
                team = Team.query.get(bid.team_id)
                
                # Skip teams with insufficient balance for the original bid
                if team.balance < bid.amount:
                    print(f"Team {team.id} has insufficient balance for subsequent tiebreaker round - skipping")
                    continue
                
                # Use the original bid amount as starting point for the tiebreaker
                tiebreaker_bid = TiebreakerBid(
                    team_id=bid.team_id,
                    player_id=bid.player_id,
                    round_id=tiebreaker_round.id,
                    amount=bid.amount  # Use original bid amount instead of 0
                )
                db.session.add(tiebreaker_bid)
                
            # Store tie information for later processing
            ties_to_resolve.append({
                'tiebreaker_round_id': tiebreaker_round.id,
                'player_id': current_bid.player_id,
                'bid_amount': current_bid.amount,
                'tied_teams': [bid.team_id for bid in tied_bids]
            })
            
            # Reserve this player to prevent other allocations
            allocated_players.add(current_bid.player_id)
            
            # IMPORTANT: If we found a tie, we must pause the auction round immediately
            # without processing any more allocations, even for different players
            print(f"Tie found, pausing all allocations for round {round.id} immediately")
            break
            
            # Skip all these tied bids
            i = j
        else:
            # No tie, just a single bid - allocate the player
            bid = tied_bids[0] if tied_bids else current_bid
            player = Player.query.get(bid.player_id)
            team = Team.query.get(bid.team_id)
            
            # Verify team has sufficient balance
            if team.balance < bid.amount:
                print(f"Team {team.id} has insufficient balance ({team.balance}) for bid amount {bid.amount}")
                i += 1
                continue
                
            # Allocate player to team
            print(f"Allocating player ID {bid.player_id} to team ID {bid.team_id} for {bid.amount}")
            
            # Update team's balance
            team.balance -= bid.amount
            
            # Set the player's team
            player.team_id = team.id
            
            # Mark as allocated
            allocated_teams.add(team.id)
            allocated_players.add(player.id)
            
            # Move to next bid
            i += 1
    
    # If we have ties to resolve, we need to pause the main finalization
    if ties_to_resolve:
        print(f"Round {round.id} has {len(ties_to_resolve)} ties to resolve. Pausing main finalization.")
        round.is_active = False  # Deactivate the main round
        
        # Set a flag to indicate that this round is waiting for tiebreakers
        round.status = "waiting_for_tiebreakers"
        
        db.session.commit()
        track_finalization_status(round.id, "paused", f"Created {len(ties_to_resolve)} tiebreaker rounds")
        return True
    
    # No ties found, complete the finalization
    round.is_active = False
    round.status = "completed"
    db.session.commit()
    
    print(f"Round {round.id} finalization completed.")
    track_finalization_status(round.id, "completed", f"Finalization completed")
    return True

def process_tiebreaker_finalization(round_id):
    """Process the finalization of a tiebreaker round.
    
    This allocates the player based on the highest tiebreaker bid and 
    updates the original bid in the parent round for record-keeping.
    
    Args:
        round_id: ID of the tiebreaker round to finalize
        
    Returns:
        bool: True if finalization was successful
    """
    print(f"Finalizing tiebreaker round {round_id}")
    track_finalization_status(round_id, "started", "Starting tiebreaker finalization")
    
    # Get tiebreaker round info
    round = Round.query.get(round_id)
    if not round or not round.is_tiebreaker:
        print(f"Error: Round {round_id} is not a valid tiebreaker round")
        track_finalization_status(round_id, "failed", "Not a valid tiebreaker round")
        return False
    
    # Get the parent round
    parent_round = Round.query.get(round.parent_round_id)
    if not parent_round:
        print(f"Error: Parent round {round.parent_round_id} not found")
        track_finalization_status(round_id, "failed", "Parent round not found")
        return False
    
    # Get the player this tiebreaker is for
    player = Player.query.get(round.player_id)
    if not player:
        print(f"Error: Player {round.player_id} not found")
        track_finalization_status(round_id, "failed", "Player not found")
        return False
    
    # Check if player is already allocated
    if player.team_id is not None:
        print(f"Warning: Player {player.id} is already allocated to team {player.team_id}")
        
        # Mark round as completed
        round.is_active = False
        round.status = "completed"
        db.session.commit()
        
        track_finalization_status(round_id, "skipped", "Player already allocated")
        return True
    
    # Get all tiebreaker bids
    bids = TiebreakerBid.query.filter_by(round_id=round_id).all()
    if not bids:
        print(f"Error: No bids found for tiebreaker round {round_id}")
        track_finalization_status(round_id, "failed", "No bids found")
        return False
    
    # Find highest bid
    highest_bid = max(bids, key=lambda x: x.amount)
    winning_team = Team.query.get(highest_bid.team_id)
    
    if not winning_team:
        print(f"Error: Team {highest_bid.team_id} not found")
        track_finalization_status(round_id, "failed", "Winning team not found")
        return False
    
    # Check if team has enough balance
    if winning_team.balance < highest_bid.amount:
        print(f"Error: Team {winning_team.id} has insufficient balance for bid {highest_bid.amount}")
        track_finalization_status(round_id, "failed", "Insufficient team balance")
        return False
    
    # Look for the original bid in the parent round (for bid history)
    original_bid = Bid.query.filter_by(
        round_id=parent_round.id,
        team_id=highest_bid.team_id,
        player_id=player.id
    ).first()
    
    # Update the bid history (original bid)
    if original_bid:
        print(f"Updating original bid {original_bid.id} with new amount {highest_bid.amount}")
        original_bid.amount = highest_bid.amount
    else:
        # Create a new bid entry if one doesn't exist (shouldn't normally happen)
        print(f"Creating new bid record in parent round for tiebreaker winner")
        original_bid = Bid(
            round_id=parent_round.id,
            team_id=highest_bid.team_id,
            player_id=player.id,
            amount=highest_bid.amount,
            timestamp=datetime.now()
        )
        db.session.add(original_bid)
    
    # Update team balance
    winning_team.balance -= highest_bid.amount
    
    # Allocate the player to the winning team
    player.team_id = winning_team.id
    
    # Mark the round as completed
    round.is_active = False
    round.status = "completed"
    
    # Save all changes
    db.session.commit()
    
    print(f"Successfully allocated player {player.id} to team {winning_team.id} for {highest_bid.amount}")
    track_finalization_status(round_id, "completed", f"Player allocated to team {winning_team.id}")
    
    # Check if all tiebreakers for the parent round are now completed
    active_tiebreakers = Round.query.filter_by(
        parent_round_id=parent_round.id,
        is_active=True
    ).count()
    
    if active_tiebreakers == 0:
        print(f"All tiebreakers for round {parent_round.id} completed. Resuming main round.")
        # Resume the parent round finalization
        resume_auction_process(parent_round.id)
    
    return True

def resume_auction_process(round_id):
    """Resume auction process for a round that was waiting for tiebreakers.
    
    This function is called when all tiebreakers for a round have been resolved.
    It processes the remaining non-tied bids and finalizes the round.
    
    Args:
        round_id: ID of the round to resume
        
    Returns:
        bool: True if resumption was successful
    """
    print(f"Resuming auction process for round {round_id}")
    track_finalization_status(round_id, "resuming", "Resuming after tiebreakers")
    
    # Get the round
    round = Round.query.get(round_id)
    if not round:
        print(f"Error: Round {round_id} not found")
        return False
    
    # Verify this round is waiting for tiebreakers
    if round.status != "waiting_for_tiebreakers":
        print(f"Error: Round {round_id} is not waiting for tiebreakers (status: {round.status})")
        return False
    
    # Check if all tiebreakers are completed
    active_tiebreakers = Round.query.filter_by(
        parent_round_id=round_id,
        is_active=True
    ).count()
    
    if active_tiebreakers > 0:
        print(f"Error: Round {round_id} still has {active_tiebreakers} active tiebreakers")
        return False
    
    # Get all bids for this round
    bids = Bid.query.filter_by(round_id=round_id).all()
    
    # Group bids by player_id and team_id to find the latest bid for each player from each team
    latest_bids = {}
    for bid in bids:
        key = f"{bid.player_id}_{bid.team_id}"
        if key not in latest_bids or bid.timestamp > latest_bids[key].timestamp:
            latest_bids[key] = bid
    
    # Convert back to a list
    current_bids = list(latest_bids.values())
    
    # Group bids by player_id
    player_bids = {}
    for bid in current_bids:
        if bid.player_id not in player_bids:
            player_bids[bid.player_id] = []
        player_bids[bid.player_id].append(bid)
    
    # Process each player's bids in descending order by amount
    for player_id, bids in player_bids.items():
        # Sort bids by amount (highest first)
        bids.sort(key=lambda x: x.amount, reverse=True)
        
        # Skip if already processed in a tiebreaker
        player = Player.query.get(player_id)
        if player.team_id is not None:
            print(f"Player {player_id} already allocated to team {player.team_id} - skipping")
            continue
        
        # Check for ties at the highest bid
        highest_bid = bids[0]
        tied_bids = [bid for bid in bids if bid.amount == highest_bid.amount]
        
        if len(tied_bids) > 1:
            print(f"Warning: Found new tie for player {player_id} with {len(tied_bids)} teams at {highest_bid.amount}")
            
            # This should not happen as ties should have been handled previously,
            # but we'll handle it just in case by creating a new tiebreaker
            new_tiebreaker = Round(
                position=round.position,
                is_active=True,
                is_tiebreaker=True,
                parent_round_id=round_id,
                player_id=player_id,
                duration=180,
                status="active"
            )
            db.session.add(new_tiebreaker)
            db.session.commit()
            
            print(f"Created new tiebreaker round {new_tiebreaker.id} for player {player_id}")
            
            # Add the tied teams to the new tiebreaker
            for bid in tied_bids:
                team = Team.query.get(bid.team_id)
                if team.balance < bid.amount:
                    print(f"Team {team.id} has insufficient balance for tiebreaker - skipping")
                    continue
                    
                new_bid = TiebreakerBid(
                    team_id=bid.team_id,
                    player_id=player_id,
                    round_id=new_tiebreaker.id,
                    amount=bid.amount
                )
                db.session.add(new_bid)
            
            db.session.commit()
            
            # Update round status to indicate we're waiting for tiebreakers again
            round.status = "waiting_for_tiebreakers"
            db.session.commit()
            
            track_finalization_status(round_id, "paused", f"New tiebreaker {new_tiebreaker.id} created for player {player_id}")
            return True
        else:
            # We have a winner - allocate the player
            team = Team.query.get(highest_bid.team_id)
            
            # Verify team has sufficient balance
            if team.balance < highest_bid.amount:
                print(f"Team {team.id} has insufficient balance for bid {highest_bid.amount} - skipping allocation")
                continue
            
            # Allocate the player to the team
            player.team_id = team.id
            
            # Update team's balance
            team.balance -= highest_bid.amount
            
            print(f"Allocated player {player_id} to team {team.id} for {highest_bid.amount}")
            
            # Commit changes to prevent race conditions
            db.session.commit()
    
    # Mark round as completed
    round.is_active = False
    round.status = "completed"
    db.session.commit()
    
    # Check if this was the last auction round
    if round.position == get_auction_round_count():
        print("All auction rounds completed. Finalizing auction.")
        # Perform any final auction cleanup or reporting here
        # ...
    
    track_finalization_status(round_id, "completed", "Round finalized successfully after tiebreakers")
    return True

def process_final_allocations(round, sorted_bids, allocated_teams, allocated_players, tiebreaker_players=None):
    """Process final allocations for a round
    
    Args:
        round: The Round object
        sorted_bids: List of bids sorted by amount (highest first)
        allocated_teams: Set of team IDs that already have allocations
        allocated_players: Set of player IDs that are already allocated
        tiebreaker_players: Optional set of player IDs that were involved in tiebreaker rounds
        
    Returns:
        int: Number of allocations made
    """
    if tiebreaker_players is None:
        tiebreaker_players = set()
        
    allocation_count = 0
    
    for bid in sorted_bids:
        # Skip if team or player already allocated
        if bid.team_id in allocated_teams or bid.player_id in allocated_players:
            continue
            
        # Skip players that were handled by tiebreaker rounds
        if bid.player_id in tiebreaker_players:
            continue
            
        # Double-check current allocation status directly from database
        player = Player.query.get(bid.player_id)
        team = Team.query.get(bid.team_id)
        
        # Skip if player or team doesn't exist or player already has a team
        if not player or not team or player.team_id is not None:
            if player and player.team_id is not None:
                allocated_players.add(player.id)
            continue
        
        # Verify team has sufficient balance
        if team.balance < bid.amount:
            print(f"Team {team.id} has insufficient balance ({team.balance}) for bid amount {bid.amount}")
            continue
            
        # Allocate player to team
        print(f"Allocating player ID {bid.player_id} to team ID {bid.team_id} for {bid.amount}")
        
        # Update team's balance
        team.balance -= bid.amount
        
        # Set the player's team
        player.team_id = team.id
        
        # Mark as allocated
        allocated_teams.add(team.id)
        allocated_players.add(player.id)
        allocation_count += 1
        
    return allocation_count

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory, session, make_response, Response
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Team, Player, Round, Bid, Tiebreaker, TeamTiebreaker, PasswordResetRequest, AuctionSettings, BulkBidTiebreaker, BulkBidRound, BulkBid, TeamBulkTiebreaker
from models import TeamMember, Category, Match, PlayerMatchup, TeamStats, PlayerStats, StarredPlayer
from config import Config
from werkzeug.security import generate_password_hash
import json
from datetime import datetime, timedelta, timezone
import sqlite3
import pandas as pd
import io
from flask_migrate import Migrate
import os
import base64
import uuid
from sqlalchemy import func
import time
from team_management_routes import team_management
from bs4 import BeautifulSoup
import re
from github_service import github_service

app = Flask(__name__)
app.config.from_object(Config)

# Apply SQLAlchemy engine options from config
if hasattr(Config, 'SQLALCHEMY_ENGINE_OPTIONS'):
    for key, value in Config.SQLALCHEMY_ENGINE_OPTIONS.items():
        app.config[f'SQLALCHEMY_{key.upper()}'] = value

# Register blueprints
app.register_blueprint(team_management, url_prefix='/team_management')


db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Add template global functions
@app.template_global()
def get_team_logo_url(team):
    """Template global function to safely get team logo URL"""
    if not team:
        return None
    try:
        # Use the same logic as Team.get_logo_url() method for consistency
        return team.get_logo_url()
    except Exception as e:
        # Fallback for any errors - return None to show default placeholder
        print(f"Error getting team logo URL: {e}")
        return None

# Runtime database initialization check
def check_and_init_database():
    """Check if database needs initialization at runtime and do it if needed."""
    try:
        # Check if initialization was skipped during build
        if os.path.exists('/tmp/db_init_skipped'):
            print("Database initialization was skipped during build. Attempting runtime initialization...")
            
            # Import init_database function
            from init_db import init_database
            
            # Try to initialize now
            try:
                init_database()
                # Remove the flag file if successful
                os.remove('/tmp/db_init_skipped')
                print("Runtime database initialization completed successfully!")
            except Exception as e:
                print(f"Runtime database initialization failed: {e}")
                # Keep the flag file so we try again on next startup
                pass
        
        # Always check if we have basic tables (safety check)
        with app.app_context():
            from models import User
            # Simple check - if this works, database is accessible
            User.query.first()
    
    except Exception as e:
        print(f"Database check failed: {e}")
        # We'll continue running - the app might still work for some functions
        pass

# Perform runtime database check
check_and_init_database()

# Add a before_request handler to prevent browser back button for authenticated users
@app.before_request
def before_request():
    # Force authentication check to happen early (this triggers load_user if needed)
    # This ensures remember token authentication happens before we check if user is authenticated
    user_authenticated = current_user.is_authenticated
    
    # Check if authenticated user is trying to access public pages
    if user_authenticated:
        public_routes = ['index', 'login', 'register', 'reset_password_request', 'reset_password_form']
        if request.endpoint in public_routes:
            return redirect(url_for('dashboard'))

# Add an after_request handler to set cache control headers and improve accessibility
@app.after_request
def add_header(response):
    # Prevent caching for authenticated users
    if current_user.is_authenticated:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, post-check=0, pre-check=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    
    # Add accessibility improvements for HTML responses
    if response.content_type.startswith('text/html'):
        try:
            html = response.get_data(as_text=True)
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. Ensure all images have alt text
            for img in soup.find_all('img'):
                if not img.get('alt'):
                    img['alt'] = ''  # Empty alt for decorative images
            
            # 2. Ensure all buttons have accessible labels
            for button in soup.find_all('button'):
                if not button.get('aria-label') and not button.text.strip():
                    # If button has an SVG icon, add descriptive label
                    if button.find('svg'):
                        button['aria-label'] = 'Button'
            
            # 3. Add skip to content link for keyboard users if not present
            if not soup.find(id='skip-to-content'):
                skip_link = soup.new_tag('a')
                skip_link['id'] = 'skip-to-content'
                skip_link['href'] = '#main-content'
                skip_link['class'] = 'sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:z-50 focus:p-4 focus:bg-white focus:text-primary'
                skip_link.string = 'Skip to main content'
                
                # Add to beginning of body
                if soup.body:
                    soup.body.insert(0, skip_link)
            
            # 4. Add focus styles to interactive elements without them
            for elem in soup.select('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'):
                # Fix: Handle the case where class might be a string
                elem_classes = elem.get('class', [])
                if isinstance(elem_classes, str):
                    elem_classes = elem_classes.split()
                
                if not any(cls.startswith('focus:') for cls in elem_classes):
                    elem_classes.append('focus-outline')
                    elem['class'] = elem_classes
            
            # 5. Ensure all form elements have associated labels
            for input_elem in soup.find_all(['input', 'select', 'textarea']):
                input_id = input_elem.get('id')
                if input_id and not soup.find('label', attrs={'for': input_id}):
                    # Try to find label within parent elements
                    parent = input_elem.parent
                    for i in range(3):  # Check up to 3 levels up
                        if parent and parent.name == 'label':
                            if not parent.get('for'):
                                parent['for'] = input_id
                            break
                        if parent:
                            parent = parent.parent
            
            # 6. Add role="main" to main content container if not present
            main_content = soup.find(class_=re.compile('(main|container)'))
            if main_content and not main_content.get('role'):
                main_content['role'] = 'main'
                if not main_content.get('id'):
                    main_content['id'] = 'main-content'
            
            # Update response data with improved HTML
            response.set_data(str(soup))
            
        except Exception as e:
            # Log error but don't break the response
            print(f"Error enhancing accessibility: {e}")
    
    return response

@login_manager.user_loader
def load_user(user_id):
    # This function is called by Flask-Login to load a user from the session
    # It can receive either a user ID from the session or a remember token
    
    # First try to load the user by ID (normal session case)
    try:
        user = User.query.get(int(user_id))
        if user:
            return user
    except (ValueError, TypeError):
        # user_id might be invalid, fall through to remember token check
        pass
    
    # If user not found by ID, check for remember token in cookies
    remember_token = request.cookies.get('remember_token')
    if remember_token:
        # Try to find and validate user by remember token
        user = User.get_by_remember_token(remember_token)
        if user:
            # Return the user - Flask-Login will handle the session
            return user
    
    return None

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static/js', 'service-worker.js', mimetype='application/javascript')

@app.route('/offline')
def offline():
    return send_from_directory('static', 'offline.html')

@app.route('/uploads/logos/<filename>')
def uploaded_logo(filename):
    """Serve uploaded team logo files"""
    try:
        return send_from_directory(
            os.path.join(app.root_path, 'static', 'uploads', 'logos'),
            filename
        )
    except:
        # Return a default/placeholder image if logo not found
        # You can create a placeholder image or return a 404
        return send_from_directory('static/img', 'default-team-logo.png')

@app.route('/')
def index():
    # Redirect authenticated users to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Set no-cache headers for unauthenticated users
    response = make_response(render_template('index.html'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, post-check=0, pre-check=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # Check if user is either an admin or has been approved
            if user.is_admin or user.is_approved:
                # Login the user
                login_user(user, remember=False)  # We'll handle remember me manually with secure tokens
                
                # Create a response object for redirect
                response = make_response(redirect(url_for('dashboard')))
                
                # If remember me is checked, generate and store a secure token
                if remember:
                    # Generate a new remember token
                    token = user.generate_remember_token(days=30)
                    # Save the changes to the database
                    db.session.commit()
                    
                    # Calculate expiry date for persistent cookie (GMT format for better compatibility)
                    from datetime import datetime, timedelta
                    import time
                    expires = datetime.utcnow() + timedelta(days=30)
                    expires_timestamp = int(time.mktime(expires.timetuple()))
                    
                    # Set a persistent cookie with the token
                    # Using both expires and max_age for maximum compatibility
                    response.set_cookie(
                        'remember_token', 
                        token, 
                        expires=expires,          # Explicit expiry date for persistence
                        max_age=30*24*60*60,     # 30 days in seconds (backup)
                        httponly=True,           # XSS protection
                        samesite='Lax',          # Cross-site compatibility
                        secure=request.is_secure,# HTTPS only if using secure connection
                        path='/',                # Available across entire site
                        domain=None              # Let browser determine domain
                    )
                
                return response
            else:
                flash('Your account is pending approval. Please contact an administrator.')
                return render_template('login.html')
        flash('Invalid username or password')
    
    # Set no-cache headers
    response = make_response(render_template('login.html'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, post-check=0, pre-check=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect authenticated users to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
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
            
            # Handle team logo upload
            logo_url = None
            if 'team_logo' in request.files:
                logo_file = request.files['team_logo']
                if logo_file and logo_file.filename != '':
                    # Check if file is an image
                    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                    file_extension = logo_file.filename.rsplit('.', 1)[1].lower() if '.' in logo_file.filename else ''
                    
                    if file_extension in allowed_extensions:
                        try:
                            # Create uploads directory if it doesn't exist
                            upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'logos')
                            os.makedirs(upload_dir, exist_ok=True)
                            
                            # Generate unique filename to avoid conflicts
                            filename = secure_filename(logo_file.filename)
                            unique_filename = f"{uuid.uuid4().hex}_{filename}"
                            file_path = os.path.join(upload_dir, unique_filename)
                            
                            # Save the file
                            logo_file.save(file_path)
                            
                            # Store relative path for database
                            logo_url = f"uploads/logos/{unique_filename}"
                            
                        except Exception as e:
                            # If file upload fails, continue without logo but show warning
                            flash('Team logo could not be uploaded, but registration was successful', 'warning')
                    else:
                        flash('Invalid logo file format. Please use PNG, JPG, JPEG, GIF, or WEBP', 'warning')
            
            # Set the logo URL on the team
            team.logo_url = logo_url
            db.session.add(team)
        
        db.session.commit()
        return redirect(url_for('login'))
    
    # Set no-cache headers
    response = make_response(render_template('register.html'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, post-check=0, pre-check=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/dashboard')
@login_required
def dashboard():
    # Verify we have a valid session - enhance security
    if not current_user.is_authenticated:
        session.clear()
        return redirect(url_for('login'))
    
    # Check if user is a new user (no bids placed yet)
    user_is_new = False
    if current_user.team:
        bid_count = Bid.query.filter_by(team_id=current_user.team.id).count()
        user_is_new = bid_count == 0

    # Check if any active rounds have expired
    active_rounds = Round.query.filter_by(is_active=True).all()
    for round in active_rounds:
        if round.is_timer_expired():
            finalize_round_internal(round.id)
    
    # Check if user just won a player in a tiebreaker
    player_won = request.args.get('player_won')
    if player_won:
        flash(f'Congratulations! You won the bid for {player_won}!', 'success')
    
    # Refresh the data after potentially finalizing rounds
    if current_user.is_admin:
        teams = Team.query.all()
        
        # Get pending users (users that are not approved and not admins)
        pending_users = User.query.filter(User.is_approved == False, User.is_admin == False).all()
        
        # Get pending password reset requests
        pending_resets = PasswordResetRequest.query.filter_by(status='pending').all()
        
        # Get active bulk bid round if any
        active_bulk_round = BulkBidRound.query.filter_by(is_active=True).first()
        
        # Get player selection stats
        total_player_count = Player.query.count()
        eligible_player_count = Player.query.filter_by(is_auction_eligible=True).count()
        
        # Make response with strong cache headers
        response = make_response(render_template('admin_dashboard.html', 
                              teams=teams,
                              pending_users=pending_users,
                              pending_resets=pending_resets,
                              active_bulk_round=active_bulk_round,
                              total_player_count=total_player_count,
                              eligible_player_count=eligible_player_count,
                              config=Config))
        
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, post-check=0, pre-check=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    # For team users
    active_rounds = Round.query.filter_by(is_active=True).all()
    rounds = Round.query.all()
    
    # Get active bulk bid round if any
    active_bulk_round = BulkBidRound.query.filter_by(is_active=True).first()
    
    # Get auction settings for budget planning
    auction_settings = AuctionSettings.get_settings()
    
    # Get completed rounds count
    completed_rounds_count = Round.query.filter_by(is_active=False).count()
    
    # Get completed rounds for display
    completed_rounds = Round.query.filter_by(is_active=False).all()
    
    # Get tiebreakers for this team
    team_tiebreakers = TeamTiebreaker.query.join(Tiebreaker).filter(
        TeamTiebreaker.team_id == current_user.team.id,
        Tiebreaker.resolved == False
    ).all()
    
    # Get bulk tiebreakers for this team
    team_bulk_tiebreakers = TeamBulkTiebreaker.query.join(
        BulkBidTiebreaker, TeamBulkTiebreaker.tiebreaker_id == BulkBidTiebreaker.id
    ).filter(
        TeamBulkTiebreaker.team_id == current_user.team.id,
        TeamBulkTiebreaker.is_active == True,
        BulkBidTiebreaker.resolved == False
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
    
    # Make response with strong cache headers
    response = make_response(render_template('team_dashboard.html', 
                          active_rounds=active_rounds, 
                          rounds=rounds,
                          active_bulk_round=active_bulk_round,
                          team_tiebreakers=team_tiebreakers,
                          team_bulk_tiebreakers=team_bulk_tiebreakers,
                          bid_counts=bid_counts,
                          round_results=round_results,
                          auction_settings=auction_settings,
                          completed_rounds_count=completed_rounds_count,
                          completed_rounds=completed_rounds))
                          
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, post-check=0, pre-check=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Unified profile editing - allows users to edit both user account and team information"""
    if current_user.is_admin:
        flash('Admin users do not have team profiles to edit', 'info')
        # Redirect admin users to a different profile edit page if needed
        return redirect(url_for('dashboard'))
    
    if not current_user.team:
        flash('You need to have a team to edit profile', 'error')
        return redirect(url_for('dashboard'))
    
    team = current_user.team
    
    if request.method == 'POST':
        # Verify current password first for any changes
        current_password = request.form.get('current_password')
        if not current_password or not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('edit_profile'))
        
        # Handle username change
        new_username = request.form.get('username', '').strip()
        if new_username and new_username != current_user.username:
            # Check if username is already taken
            if User.query.filter(User.username == new_username, User.id != current_user.id).first():
                flash('Username already exists', 'error')
                return redirect(url_for('edit_profile'))
            
            # Prevent changing to 'admin' unless user is already admin
            if new_username.lower() == 'admin' and not current_user.is_admin:
                flash('Cannot use reserved username', 'error')
                return redirect(url_for('edit_profile'))
            
            current_user.username = new_username
            app.logger.info(f'User {current_user.id} changed username to {new_username}')
        
        # Handle team name change
        new_team_name = request.form.get('team_name', '').strip()
        if new_team_name and new_team_name != team.name:
            # Check if team name is already taken
            existing_team = Team.query.filter_by(name=new_team_name).first()
            if existing_team and existing_team.id != team.id:
                flash('Team name already taken', 'error')
                return redirect(url_for('edit_profile'))
            team.name = new_team_name
            app.logger.info(f'Team {team.id} name changed to {new_team_name}')
        
        # Handle password change
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if new_password:
            # Check password change restrictions
            if not current_user.can_change_password():
                time_remaining = current_user.time_until_password_change()
                hours = int(time_remaining.total_seconds() // 3600)
                minutes = int((time_remaining.total_seconds() % 3600) // 60)
                flash(f'You can only change your password once per day. Try again in {hours}h {minutes}m', 'error')
                return redirect(url_for('edit_profile'))
            
            # Validate password confirmation
            if new_password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('edit_profile'))
            
            # Validate password strength
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return redirect(url_for('edit_profile'))
            
            # Set new password (this also updates last_password_change)
            current_user.set_password(new_password)
            app.logger.info(f'User {current_user.id} ({current_user.username}) changed password')
            
            # Clear remember tokens when password is changed for security
            current_user.clear_remember_token()
        
        # Handle logo upload
        logo_updated = False
        if 'team_logo' in request.files:
            logo_file = request.files['team_logo']
            if logo_file and logo_file.filename != '':
                # Check if file is an image
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                file_extension = logo_file.filename.rsplit('.', 1)[1].lower() if '.' in logo_file.filename else ''
                
                if file_extension in allowed_extensions:
                    try:
                        # Read the logo file content
                        logo_content = logo_file.read()
                        
                        # Try GitHub upload first if configured
                        if github_service.is_configured():
                            # Delete old GitHub logo if exists
                            if team.logo_storage_type == 'github' and team.logo_url:
                                # Extract info from current logo to delete
                                old_extension = team.logo_url.split('.')[-1] if '.' in team.logo_url else 'png'
                                github_service.delete_team_logo(team.id, team.name, old_extension)
                            
                            # Upload to GitHub
                            github_result = github_service.upload_team_logo(
                                team.id, 
                                team.name, 
                                logo_content, 
                                logo_file.filename
                            )
                            
                            if github_result and github_result.get('success'):
                                # Store GitHub URL and metadata
                                team.logo_url = github_result['download_url']
                                team.logo_storage_type = 'github'
                                team.github_logo_sha = github_result.get('sha')
                                logo_updated = True
                            else:
                                # GitHub upload failed, fall back to local storage
                                raise Exception("GitHub upload failed")
                        else:
                            # GitHub not configured, use local storage
                            raise Exception("GitHub not configured")
                    
                    except Exception as github_error:
                        # Fall back to local storage
                        try:
                            # Reset file pointer for local upload
                            logo_file.seek(0)
                            
                            # Create uploads directory if it doesn't exist
                            upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'logos')
                            os.makedirs(upload_dir, exist_ok=True)
                            
                            # Delete old local logo if exists
                            if team.logo_storage_type == 'local' and team.logo_url:
                                old_logo_path = os.path.join(app.root_path, 'static', team.logo_url)
                                if os.path.exists(old_logo_path):
                                    try:
                                        os.remove(old_logo_path)
                                    except:
                                        pass  # Ignore errors when deleting old logo
                            
                            # Generate unique filename to avoid conflicts
                            filename = secure_filename(logo_file.filename)
                            unique_filename = f"{uuid.uuid4().hex}_{filename}"
                            file_path = os.path.join(upload_dir, unique_filename)
                            
                            # Save the file locally
                            logo_file.save(file_path)
                            
                            # Store local path and metadata
                            team.logo_url = f"uploads/logos/{unique_filename}"
                            team.logo_storage_type = 'local'
                            team.github_logo_sha = None  # Clear GitHub metadata
                            logo_updated = True
                            
                        except Exception as local_error:
                            flash('Logo could not be uploaded', 'error')
                else:
                    flash('Invalid logo file format. Please use PNG, JPG, JPEG, GIF, or WEBP', 'error')
        
        try:
            db.session.commit()
            
            if new_password:
                flash('Profile updated successfully! Please log in again for security.', 'success')
                # Log out user after password change for security
                logout_user()
                response = make_response(redirect(url_for('login')))
                # Clear remember token cookie
                response.set_cookie('remember_token', '', expires=0, httponly=True, samesite='Lax')
                return response
            else:
                success_message = 'Profile updated successfully!'
                if logo_updated:
                    success_message += ' Team logo has been updated.'
                flash(success_message, 'success')
                return redirect(url_for('dashboard'))
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error updating profile for user {current_user.id}: {e}')
            flash('Error updating profile. Please try again.', 'error')
            return redirect(url_for('edit_profile'))
    
    # Calculate password change availability
    can_change_password = current_user.can_change_password()
    time_until_change = None
    if not can_change_password:
        time_remaining = current_user.time_until_password_change()
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)
        time_until_change = f"{hours}h {minutes}m"
    
    # Add timestamp for cache busting
    import time
    cache_buster = int(time.time())
    
    # Set comprehensive no-cache headers for security and live updates
    response = make_response(render_template('edit_profile.html', 
                          team=team,
                          can_change_password=can_change_password,
                          time_until_change=time_until_change,
                          last_password_change=current_user.last_password_change,
                          cache_buster=cache_buster))
    
    # Comprehensive cache prevention headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, post-check=0, pre-check=0, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"  # Expired date
    response.headers["Last-Modified"] = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers["ETag"] = f'"edit-profile-{current_user.id}-{cache_buster}"'
    response.headers["Vary"] = "*"  # Vary on all possible headers
    
    return response

@app.route('/start_round', methods=['POST'])
@login_required
def start_round():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    position = request.json.get('position')
    duration = request.json.get('duration', 300)  # Default to 5 minutes (300 seconds)
    max_bids_per_team = request.json.get('max_bids_per_team', 5)  # Default to 5 bids per team
    
    # Check if position is valid - could be a base position or a position group
    if not position:
        return jsonify({'error': 'Invalid position'}), 400
    
    # Check if it's a position group (e.g. CF-1)
    is_position_group = '-' in position
    if is_position_group:
        position_parts = position.split('-')
        if len(position_parts) != 2 or position_parts[0] not in Config.POSITIONS:
            return jsonify({'error': 'Invalid position group format'}), 400
        base_position = position_parts[0] 
    else:
        # Regular position (not a group)
        if position not in Config.POSITIONS:
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
    
    # Get auction settings
    settings = AuctionSettings.get_settings()
    
    # Check if we've reached the maximum number of rounds
    completed_rounds_count = Round.query.filter_by(is_active=False).count()
    if completed_rounds_count >= settings.max_rounds:
        return jsonify({
            'error': f'Maximum number of rounds ({settings.max_rounds}) has been reached. No more rounds can be started.'
        }), 400
    
    # Calculate remaining rounds (including this one)
    remaining_rounds = settings.max_rounds - completed_rounds_count
    
    # Check if teams have sufficient balance for remaining rounds
    min_required_balance = settings.min_balance_per_round * remaining_rounds
    
    # Get all approved teams
    teams = Team.query.filter(Team.user.has(is_approved=True)).all()
    
    # Track teams with insufficient balance
    insufficient_balance_teams = []
    for team in teams:
        if team.balance < min_required_balance:
            insufficient_balance_teams.append({
                'name': team.name,
                'balance': team.balance, 
                'required': min_required_balance
            })
    
    if insufficient_balance_teams:
        return jsonify({
            'error': 'Some teams have insufficient balance for the remaining rounds',
            'teams': insufficient_balance_teams,
            'min_required_balance': min_required_balance,
            'remaining_rounds': remaining_rounds
        }), 400
    
    # Create new round with timer
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(seconds=duration)
    
    round = Round(
        position=position, 
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        max_bids_per_team=max_bids_per_team
    )
    db.session.add(round)
    db.session.flush()  # Get the round ID
    
    # Add players to the round based on position or position group
    if is_position_group:
        # Position group (e.g., CF-1) - filter by position_group
        players = Player.query.filter_by(position_group=position, team_id=None, is_auction_eligible=True).all()
    else:
        # Regular position (e.g., CF) - filter by position
        players = Player.query.filter_by(position=position, team_id=None, is_auction_eligible=True).all()
    
    for player in players:
        player.round_id = round.id
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'round_id': round.id,
        'message': f'Round for {position} started successfully',
        'remaining_rounds': remaining_rounds - 1  # Subtract 1 to account for current round
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
        if duration < 300:  # Minimum duration of 5 minutes (300 seconds)
            return jsonify({'error': 'Duration must be at least 5 minutes (300 seconds)'}), 400
        # No maximum limit, allowing admin to set any reasonable duration
    except ValueError:
        return jsonify({'error': 'Invalid duration value'}), 400
    
    # Extend the round by adding duration to end_time instead of resetting start_time
    if round.end_time:
        round.end_time = round.end_time + timedelta(seconds=duration)
    else:
        # Fallback: if no end_time exists, create it from current time + duration
        round.end_time = datetime.utcnow() + timedelta(seconds=duration)
    
    # Update the stored duration for backward compatibility
    round.duration = round.calculated_duration
    db.session.commit()
    
    return jsonify({
        'message': 'Round timer extended successfully',
        'duration_added': duration,
        'new_end_time': round.end_time.isoformat(),
        'total_duration': round.calculated_duration,
        'remaining_time': round.get_remaining_time()
    })

@app.route('/check_round_status/<int:round_id>')
@login_required
def check_round_status(round_id):
    # Optimized query with select_related for better performance
    round = Round.query.options(db.selectinload(Round.tiebreakers)).get_or_404(round_id)
    
    if not round.is_active:
        # Optimized tiebreaker check for non-admin users
        if not current_user.is_admin and current_user.team:
            # Use a more efficient query with proper indexing
            active_tiebreaker = db.session.query(Tiebreaker)\
                .join(TeamTiebreaker, Tiebreaker.id == TeamTiebreaker.tiebreaker_id)\
                .filter(
                    Tiebreaker.round_id == round_id,
                    Tiebreaker.resolved == False,
                    TeamTiebreaker.team_id == current_user.team.id
                ).first()
            
            if active_tiebreaker:
                return jsonify({
                    'active': False,
                    'message': 'Round finalized with tiebreaker',
                    'redirect_to': f'/tiebreaker/{active_tiebreaker.id}',
                    'tiebreaker_id': active_tiebreaker.id
                })
        
        return jsonify({'active': False, 'message': 'Round is already finalized'})
    
    # Cache the timer check result to avoid repeated calculations
    expired = round.is_timer_expired()
    if expired:
        # Finalize the round if expired
        result = finalize_round_internal(round_id)
        
        # Check the result to see if a tiebreaker was created
        if isinstance(result, dict):
            status = result.get('status')
            if status == 'tiebreaker_needed' and not current_user.is_admin and current_user.team:
                tiebreaker_id = result.get('tiebreaker_id')
                # Optimized tiebreaker check
                team_in_tiebreaker = TeamTiebreaker.query.filter(
                    TeamTiebreaker.tiebreaker_id == tiebreaker_id,
                    TeamTiebreaker.team_id == current_user.team.id
                ).first()
                
                if team_in_tiebreaker:
                    return jsonify({
                        'active': False,
                        'message': 'Round ended, tiebreaker needed',
                        'redirect_to': f'/tiebreaker/{tiebreaker_id}',
                        'tiebreaker_id': tiebreaker_id
                    })
            elif status == 'tiebreaker_pending' and not current_user.is_admin and current_user.team:
                # Batch check existing tiebreakers for better performance
                existing_tiebreakers = result.get('tiebreakers', [])
                if existing_tiebreakers:
                    team_tiebreaker = TeamTiebreaker.query.filter(
                        TeamTiebreaker.tiebreaker_id.in_(existing_tiebreakers),
                        TeamTiebreaker.team_id == current_user.team.id
                    ).first()
                    
                    if team_tiebreaker:
                        return jsonify({
                            'active': False,
                            'message': 'Round ended, existing tiebreaker pending',
                            'redirect_to': f'/tiebreaker/{team_tiebreaker.tiebreaker_id}',
                            'tiebreaker_id': team_tiebreaker.tiebreaker_id
                        })
        
        return jsonify({'active': False, 'message': 'Round timer expired and has been finalized'})
    
    # Calculate remaining time using end_time (cached calculation)
    remaining = round.get_remaining_time()
    
    data = {
        'active': True,
        'remaining': remaining,
        'duration': round.calculated_duration,
        'start_time': round.start_time.isoformat() if round.start_time else None,
        'end_time': round.end_time.isoformat() if round.end_time else None
    }
    return jsonify(data)

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
    
    # Get all bids for this round
    all_bids = Bid.query.filter_by(round_id=round_id).all()
    
    # Count bids per team
    team_bid_counts = {}
    for bid in all_bids:
        team_bid_counts[bid.team_id] = team_bid_counts.get(bid.team_id, 0) + 1
    
    # Only consider teams that placed exactly the required number of bids
    valid_team_ids = [team_id for team_id, count in team_bid_counts.items() 
                      if count == round.max_bids_per_team]
    
    # Filter bids to only include those from valid teams
    valid_bids = [bid for bid in all_bids if bid.team_id in valid_team_ids]
    
    # Start processing only the valid bids
    return process_bids_with_tiebreaker_check(round_id, valid_bids)

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
            
            # Check if adding this player would exceed team's player limit
            team_player_count = Player.query.filter_by(team_id=team.id).count()
            if team_player_count >= Config.MAX_PLAYERS_PER_TEAM:
                # Skip this bid as team is already at max capacity
                bids.remove(highest_bid)
                continue
            
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
    
    # Notifications have been removed
            
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
    
    return jsonify({'message': 'Bid placed successfully', 'bid': bid.to_dict()})

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
    
    # Store details before deleting
    player_id = bid.player_id
    round_id = bid.round_id
    
    # Check if the round is still active
    if not bid.round.is_active:
        return jsonify({'error': 'Cannot delete bid from a finalized round'}), 400
    
    db.session.delete(bid)
    db.session.commit()
    
    return jsonify({'message': 'Bid deleted successfully', 'bid_id': bid_id, 'player_id': player_id, 'round_id': round_id})

@app.route('/logout')
@login_required
def logout():
    # Get the username before logging out for the flash message
    username = current_user.username
    
    # Clear the remember token if it exists
    if hasattr(current_user, 'clear_remember_token'):
        current_user.clear_remember_token()
        db.session.commit()
    
    # Log the user out using Flask-Login
    logout_user()
    
    # Clear session data
    session.clear()
    
    # Flash message to confirm logout
    flash(f'You have been logged out, {username}.')
    
    # Create response for redirect
    response = make_response(redirect(url_for('index')))
    
    # Remove the remember_token cookie
    response.delete_cookie('remember_token')
    
    # Tell service worker to clear cache
    response.headers['Clear-Site-Data'] = '"cache", "cookies"'
    
    return response

@app.route('/tiebreaker/<int:tiebreaker_id>', methods=['GET'])
@login_required
def get_tiebreaker(tiebreaker_id):
    tiebreaker = Tiebreaker.query.get_or_404(tiebreaker_id)
    
    if current_user.is_admin:
        # Admin view
        team_tiebreakers = TeamTiebreaker.query.filter_by(tiebreaker_id=tiebreaker_id).all()
        teams = [team_tiebreaker.team for team_tiebreaker in team_tiebreakers]
        player = Player.query.get(tiebreaker.player_id)
        
        # Count how many teams have submitted bids
        teams_submitted = sum(1 for tt in team_tiebreakers if tt.new_amount is not None)
        
        return render_template('tiebreaker_admin.html', 
                             tiebreaker=tiebreaker, 
                             teams=teams,
                             team_tiebreakers=team_tiebreakers,
                             player=player,
                             teams_submitted=teams_submitted)
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

@app.route('/api/bulk_tiebreaker_status/<int:tiebreaker_id>')
@login_required
def api_bulk_tiebreaker_status(tiebreaker_id):
    """API endpoint for live updates of bulk tiebreaker status"""
    tiebreaker = BulkBidTiebreaker.query.get_or_404(tiebreaker_id)
    
    # Get the player this tiebreaker is for
    player = Player.query.get(tiebreaker.player_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    # Get all active teams in this tiebreaker
    team_tiebreakers = TeamBulkTiebreaker.query.filter_by(
        tiebreaker_id=tiebreaker_id,
        is_active=True
    ).all()
    
    active_teams = []
    for team_tb in team_tiebreakers:
        team = Team.query.get(team_tb.team_id)
        if team:
            # Get the last bid for this team
            last_bid = team_tb.last_bid if team_tb.last_bid else None
            last_bid_time = team_tb.last_bid_time.strftime('%H:%M:%S') if team_tb.last_bid_time else None
            
            active_teams.append({
                'team_id': team.id,
                'team_name': team.name,
                'last_bid': last_bid,
                'last_bid_time': last_bid_time
            })
    
    # Get current user's team balance if they're part of this tiebreaker
    team_balance = None
    if current_user.team:
        user_team_tiebreaker = TeamBulkTiebreaker.query.filter_by(
            tiebreaker_id=tiebreaker_id,
            team_id=current_user.team.id,
            is_active=True
        ).first()
        if user_team_tiebreaker:
            team_balance = current_user.team.balance
    
    # Check if there's a next tiebreaker for the current user
    next_tiebreaker_id = None
    if tiebreaker.resolved and current_user.team:
        next_tiebreaker = TeamBulkTiebreaker.query.join(
            BulkBidTiebreaker, TeamBulkTiebreaker.tiebreaker_id == BulkBidTiebreaker.id
        ).filter(
            TeamBulkTiebreaker.team_id == current_user.team.id,
            TeamBulkTiebreaker.is_active == True,
            BulkBidTiebreaker.resolved == False,
            BulkBidTiebreaker.id != tiebreaker_id
        ).first()
        if next_tiebreaker:
            next_tiebreaker_id = next_tiebreaker.tiebreaker_id
    
    # Determine winner if resolved
    winner_team_id = None
    if tiebreaker.resolved:
        # Find the team with the highest last_bid
        highest_bidder = TeamBulkTiebreaker.query.filter_by(
            tiebreaker_id=tiebreaker_id
        ).order_by(TeamBulkTiebreaker.last_bid.desc()).first()
        if highest_bidder:
            winner_team_id = highest_bidder.team_id
    
    return jsonify({
        'resolved': tiebreaker.resolved,
        'current_amount': tiebreaker.current_amount,
        'active_teams': active_teams,
        'team_balance': team_balance,
        'next_tiebreaker_id': next_tiebreaker_id,
        'winner_team_id': winner_team_id,
        'player_name': player.name
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
    
    # Allow access if user is admin OR coming from database page OR the player belongs to their team
    if not current_user.is_admin and not from_players_database and (current_user.team is None or player not in current_user.team.players):
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
        'team_id': player.team_id,
        'is_auction_eligible': player.is_auction_eligible
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
    group = request.args.get('group', '')
    search_query = request.args.get('q', '')
    eligibility_filter = request.args.get('eligibility', 'eligible')  # Default to showing eligible players only
    
    query = Player.query
    
    # Apply eligibility filter
    if eligibility_filter == 'eligible':
        query = query.filter_by(is_auction_eligible=True)
    
    # Apply position filter
    if position:
        query = query.filter_by(position=position)
    
    # Apply position group filter
    if group:
        query = query.filter_by(position_group=group)
    
    # Apply search filter
    if search_query:
        query = query.filter(Player.name.ilike(f'%{search_query}%'))
    
    # Paginate results
    players_pagination = query.order_by(Player.name).paginate(page=page, per_page=20)
    
    return render_template('admin_players.html', 
                          players=players_pagination.items,
                          players_pagination=players_pagination,
                          current_position=position,
                          current_group=group,
                          search_query=search_query,
                          eligibility_filter=eligibility_filter,
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
        overall_rating=overall_rating,
        is_auction_eligible=True  # Set new players as eligible by default
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
    player.acquisition_value = data.get('acquisition_value', player.acquisition_value)
    
    # Get new team_id
    new_team_id = data.get('team_id', player.team_id)
    
    # If team is changing and new team is not None
    if new_team_id is not None and new_team_id != player.team_id:
        # Check if adding this player would exceed the team's maximum player limit
        team = Team.query.get(new_team_id)
        if team:
            current_player_count = Player.query.filter_by(team_id=new_team_id).count()
            if current_player_count >= Config.MAX_PLAYERS_PER_TEAM:
                return jsonify({'error': f'Team already has maximum number of players ({Config.MAX_PLAYERS_PER_TEAM})'})
    
    # Set the team_id
    player.team_id = new_team_id
    
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
    
    # Get cancelled teams (teams that didn't place exactly the required number of bids)
    team_bid_counts = {}
    for bid in bids:
        team_bid_counts[bid.team_id] = team_bid_counts.get(bid.team_id, 0) + 1
    
    cancelled_teams = []
    for team_id, count in team_bid_counts.items():
        if count != round.max_bids_per_team:
            team = Team.query.get(team_id)
            cancelled_teams.append({
                'team': team,
                'bid_count': count,
                'required_count': round.max_bids_per_team
            })
    
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
                          cancelled_teams=cancelled_teams,
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
                        'Playing Style': player.playing_style,
                        'player_id': player.player_id,
                        'team_id': player.team_id,
                        'is_auction_eligible': player.is_auction_eligible
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

@app.route('/admin/teams_update')
@login_required
def admin_teams_update():
    if not current_user.is_admin or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Unauthorized'}), 403
    
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
            'id': team.id,
            'name': team.name,
            'balance': team.balance,
            'total_players': len(players),
            'position_counts': position_counts,
            'total_team_value': total_team_value,
            'active_bids_count': active_bids_count,
            'completed_bids_count': completed_bids_count,
            'has_user': has_user,
            'username': username
        })
    
    # Render the teams list as HTML
    teams_html = render_template('partials/teams_list.html', 
                               teams=teams_data,
                               config=Config)
    
    return jsonify({
        'teams_count': len(teams),
        'teams_html': teams_html
    })

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

@app.route('/admin/users_update')
@login_required
def admin_users_update():
    if not current_user.is_admin or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get all users
    users = User.query.all()
    
    # Calculate statistics
    pending_approvals = sum(1 for user in users if not user.is_approved and not user.is_admin)
    admin_count = sum(1 for user in users if user.is_admin)
    
    # Render user table and cards
    desktop_html = render_template('partials/users_table.html', users=users)
    mobile_html = render_template('partials/users_cards.html', users=users)
    
    return jsonify({
        'total_users': len(users),
        'pending_approvals': pending_approvals,
        'admin_count': admin_count,
        'desktop_html': desktop_html,
        'mobile_html': mobile_html
    })

@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if not current_user.is_admin:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Unauthorized'}), 403
        flash('You do not have permission to perform this action')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Don't approve admin users
    if user.is_admin:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Admin users do not need approval'}), 400
        flash('Admin users do not need approval')
        return redirect(url_for('admin_users'))
        
    user.is_approved = True
    db.session.commit()
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': f'User {user.username} has been approved'})
    
    flash(f'User {user.username} has been approved')
    return redirect(url_for('admin_users'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Unauthorized'}), 403
        flash('You do not have permission to perform this action')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'You cannot delete yourself'}), 400
        flash('You cannot delete yourself')
        return redirect(url_for('admin_users'))
    
    try:
        # Delete associated password reset requests first
        PasswordResetRequest.query.filter_by(user_id=user.id).delete()
        
        # Delete the user's team if it exists
        if user.team:
            db.session.delete(user.team)
        
        # Delete the user
        username = user.username  # Store username before deletion
        db.session.delete(user)
        db.session.commit()
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'message': f'User {username} has been deleted'})
        
        flash(f'User {username} has been deleted')
        return redirect(url_for('admin_users'))
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': f'Error deleting user: {str(e)}'}), 500
        flash(f'Error deleting user: {str(e)}', 'error')
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

@app.route('/admin/team/<int:team_id>')
@login_required
def admin_team_details(team_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page')
        return redirect(url_for('dashboard'))
    
    # Get the team and its details
    team = Team.query.get_or_404(team_id)
    
    # Get team stats
    team_stats = {}
    
    # Get players for this team
    players = Player.query.filter_by(team_id=team.id).all()
    
    # Calculate total team value and get position counts
    total_value = sum(player.acquisition_value for player in players if player.acquisition_value)
    
    # Position counts and average ratings
    position_counts = {position: 0 for position in Config.POSITIONS}
    position_values = {position: 0 for position in Config.POSITIONS}
    position_ratings = {position: 0 for position in Config.POSITIONS}
    
    for player in players:
        if player.position in position_counts:
            position_counts[player.position] += 1
            position_values[player.position] += player.acquisition_value or 0
            position_ratings[player.position] += player.overall_rating or 0
    
    # Calculate average ratings for each position
    position_avg_ratings = {}
    for position in Config.POSITIONS:
        if position_counts[position] > 0:
            position_avg_ratings[position] = round(position_ratings[position] / position_counts[position], 1)
        else:
            position_avg_ratings[position] = 0
    
    # Calculate team statistics
    avg_rating = round(sum(player.overall_rating for player in players if player.overall_rating) / len(players), 1) if players else 0
    highest_value = max((player.acquisition_value for player in players if player.acquisition_value), default=0)
    avg_player_value = round(total_value / len(players)) if players else 0
    
    # Get bid information
    active_bids = Bid.query.join(Player).filter(
        Bid.team_id == team.id,
        Player.round_id != None,
        Player.team_id != team.id
    ).count()
    
    total_bids = Bid.query.filter_by(team_id=team.id).count()
    successful_bids = len([p for p in players if p.acquisition_value is not None])
    bid_success_rate = round((successful_bids / total_bids) * 100) if total_bids > 0 else 0
    
    # Get top players (limited to 5)
    top_players = sorted(players, key=lambda p: p.overall_rating or 0, reverse=True)[:5]
    
    # Combine everything into team_stats
    team_stats = {
        'total_players': len(players),
        'total_value': total_value,
        'avg_rating': avg_rating,
        'highest_value': highest_value,
        'avg_player_value': avg_player_value,
        'position_counts': position_counts,
        'position_avg_ratings': position_avg_ratings,
        'active_bids': active_bids,
        'bid_success_rate': bid_success_rate,
        'top_players': top_players
    }
    
    return render_template('admin_team_details.html', team=team, team_stats=team_stats, config=Config)

@app.route('/admin/update_team/<int:team_id>', methods=['POST'])
@login_required
def admin_update_team(team_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action')
        return redirect(url_for('dashboard'))
    
    team = Team.query.get_or_404(team_id)
    
    # Get form data
    name = request.form.get('name')
    
    # Validate data
    if not name:
        flash('Team name is required', 'error')
        return redirect(url_for('admin_team_details', team_id=team_id))
    
    # Check if name already exists for another team
    existing_team = Team.query.filter_by(name=name).first()
    if existing_team and existing_team.id != team_id:
        flash('Another team with this name already exists', 'error')
        return redirect(url_for('admin_team_details', team_id=team_id))
    
    # Update team details
    team.name = name
    
    try:
        db.session.commit()
        flash('Team details updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating team: {str(e)}', 'error')
    
    return redirect(url_for('admin_team_details', team_id=team_id))

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
    query = Player.query.filter_by(is_auction_eligible=True)  # Only show eligible players
    
    # Apply search filter if provided
    if search_query:
        query = query.filter(Player.name.ilike(f'%{search_query}%'))
    
    # Apply position filter if provided
    if current_position:
        if current_position in Config.POSITION_GROUPS:
            # Filter by position group
            query = query.filter(Player.position_group == current_position)
        else:
            # Filter by normal position
            query = query.filter(Player.position == current_position)
    
    # Apply playing style filter if provided
    if current_playing_style:
        query = query.filter(Player.playing_style == current_playing_style)
    
    # Get starred players for the current user
    starred_player_ids = []
    if current_user.team:
        starred_players = StarredPlayer.query.filter_by(team_id=current_user.team.id).all()
        starred_player_ids = [sp.player_id for sp in starred_players]
    
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
    if not current_user.team:
        return jsonify({'success': False, 'message': 'You do not have a team'}), 400
    
    # Check if player exists
    player = Player.query.get_or_404(player_id)
    
    # Check if player is already starred
    existing_star = StarredPlayer.query.filter_by(
        team_id=current_user.team.id,
        player_id=player_id
    ).first()
    
    if existing_star:
        return jsonify({'success': True, 'message': 'Player was already starred'}), 200
    
    # Add to starred players
    new_star = StarredPlayer(
        team_id=current_user.team.id,
        player_id=player_id
    )
    
    try:
        db.session.add(new_star)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Player starred successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/unstar_player/<int:player_id>', methods=['POST'])
@login_required
def unstar_player(player_id):
    """Remove a player from the user's starred players list"""
    if not current_user.team:
        return jsonify({'success': False, 'message': 'You do not have a team'}), 400
    
    # Find the starred player entry
    starred_player = StarredPlayer.query.filter_by(
        team_id=current_user.team.id,
        player_id=player_id
    ).first()
    
    if not starred_player:
        return jsonify({'success': True, 'message': 'Player was not starred'}), 200
    
    try:
        db.session.delete(starred_player)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Player unstarred successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/team/profile')
@login_required
def team_profile():
    """
    Display the team profile page with team information, stats, and achievements.
    """
    if current_user.is_admin:
        flash('Admin users do not have team profiles', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.team:
        flash('You do not have a team', 'error')
        return redirect(url_for('dashboard'))
    
    # Get team data
    team = current_user.team
    
    # Calculate team statistics
    total_spent = sum(player.acquisition_value or 0 for player in team.players)
    remaining_balance = team.balance
    
    # Count players by position
    position_counts = {}
    for position in Config.POSITIONS:
        position_counts[position] = sum(1 for player in team.players if player.position == position)
    
    # Get team match statistics from TeamStats if available
    team_stats = TeamStats.query.filter_by(team_id=team.id).first()
    
    # Calculate achievements/badges
    achievements = []
    
    # First Team Achievement - if user was among first 5 teams registered
    if team.id <= 5:
        achievements.append({
            'name': 'Early Adopter',
            'description': 'Among the first 5 teams to join',
            'icon': 'star',
            'color': 'gold'
        })
    
    # Big Spender Achievement - if spent more than 10000
    if total_spent > 10000:
        achievements.append({
            'name': 'Big Spender',
            'description': 'Spent over £10,000 in auctions',
            'icon': 'currency-pound',
            'color': 'green'
        })
    
    # Squad Builder Achievement - if has 15+ players
    if len(team.players) >= 15:
        achievements.append({
            'name': 'Squad Builder',
            'description': 'Built a squad of 15+ players',
            'icon': 'users',
            'color': 'blue'
        })
    
    # Balanced Team Achievement - if has at least 1 player in each position
    has_all_positions = all(position_counts.get(pos, 0) > 0 for pos in ['GK', 'CB', 'CMF', 'CF'])
    if has_all_positions:
        achievements.append({
            'name': 'Balanced Squad',
            'description': 'Has players in all key positions',
            'icon': 'shield-check',
            'color': 'purple'
        })
    
    # Get recent acquisitions (last 5 players)
    recent_players = sorted(team.players, 
                           key=lambda p: p.id, 
                           reverse=True)[:5]
    
    # Get top rated players
    top_players = sorted(team.players, 
                        key=lambda p: p.overall_rating or 0, 
                        reverse=True)[:5]
    
    # Get manager/user info
    manager_name = current_user.username
    
    # Count total bids placed
    total_bids = Bid.query.filter_by(team_id=team.id).count()
    
    # Count won bids (players acquired)
    won_bids = len(team.players)
    
    return render_template('team_profile.html',
                         team=team,
                         total_spent=total_spent,
                         remaining_balance=remaining_balance,
                         position_counts=position_counts,
                         team_stats=team_stats,
                         achievements=achievements,
                         recent_players=recent_players,
                         top_players=top_players,
                         manager_name=manager_name,
                         total_bids=total_bids,
                         won_bids=won_bids,
                         config=Config)


@app.route('/team_transfers')
@login_required
def team_transfers():
    """
    Display the complete transfer market history for all teams.
    Shows all completed player transfers with filtering and analytics.
    """
    if current_user.is_admin:
        flash('Admin users should use the admin panel to view transfers', 'info')
        return redirect(url_for('dashboard'))
    
    if not current_user.team:
        flash('You must have a team to view transfer history', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all teams for filter dropdown
    teams = Team.query.all()
    
    return render_template('team_transfers.html', 
                          teams=teams,
                          config=Config)

@app.route('/api/transfers')
@login_required
def api_transfers():
    """
    API endpoint to get all transfer data for the Transfer Market History page.
    Returns JSON with all completed transfers.
    """
    transfers = []
    
    # Get all players with teams (completed transfers)
    transferred_players = Player.query.filter(Player.team_id != None).all()
    
    for player in transferred_players:
        # Get the transfer details
        transfer_data = {
            'id': player.id,
            'player_name': player.name,
            'position': player.position,
            'to_team': player.team.name if player.team else 'Unknown',
            'to_team_id': player.team_id,
            'price': player.acquisition_value or 0,
            'from_team': None,  # We don't track previous teams in current model
            'date': None,  # We'll use bid timestamp or a default
            'type': 'Auction',  # Default type
            'round': None
        }
        
        # Try to find the winning bid to get more details
        winning_bid = Bid.query.filter_by(
            player_id=player.id,
            team_id=player.team_id
        ).first()
        
        if winning_bid:
            transfer_data['date'] = winning_bid.timestamp.isoformat() if winning_bid.timestamp else datetime.utcnow().isoformat()
            transfer_data['price'] = winning_bid.amount
            if winning_bid.round:
                transfer_data['round'] = winning_bid.round.position
                
            # Get competing bids for this player in the same round
            if winning_bid.round_id:
                competing_bids = Bid.query.filter(
                    Bid.player_id == player.id,
                    Bid.round_id == winning_bid.round_id,
                    Bid.team_id != player.team_id
                ).all()
                
                transfer_data['competing_bids'] = [
                    {
                        'team': bid.team.name,
                        'amount': bid.amount
                    } for bid in competing_bids
                ]
        else:
            # Check if it was a bulk bid transfer
            bulk_bid = BulkBid.query.filter_by(
                player_id=player.id,
                team_id=player.team_id,
                is_resolved=True
            ).first()
            
            if bulk_bid:
                transfer_data['date'] = bulk_bid.timestamp.isoformat() if bulk_bid.timestamp else datetime.utcnow().isoformat()
                transfer_data['type'] = 'Bulk'
                if bulk_bid.bulk_round:
                    transfer_data['price'] = bulk_bid.bulk_round.base_price
            else:
                # Use a default date if no bid found
                transfer_data['date'] = datetime.utcnow().isoformat()
        
        transfers.append(transfer_data)
    
    # Sort by date (newest first)
    transfers.sort(key=lambda x: x['date'], reverse=True)
    
    return jsonify({'transfers': transfers})

@app.route('/team_bids')
@login_required
def team_bids():
    """
    Display a team's bidding history and statistics.
    This page shows current and past bids for the current user's team.
    """
    # Get active rounds for the "Place New Bid" button
    active_rounds = Round.query.filter_by(is_active=True).all()
    
    # Get tiebreakers for this team
    team_tiebreakers = TeamTiebreaker.query.join(Tiebreaker).filter(
        TeamTiebreaker.team_id == current_user.team.id,
        Tiebreaker.resolved == False
    ).all()
    
    # Get bulk tiebreakers for this team
    team_bulk_tiebreakers = TeamBulkTiebreaker.query.join(
        BulkBidTiebreaker, TeamBulkTiebreaker.tiebreaker_id == BulkBidTiebreaker.id
    ).filter(
        TeamBulkTiebreaker.team_id == current_user.team.id,
        TeamBulkTiebreaker.is_active == True,
        BulkBidTiebreaker.resolved == False
    ).all()
    
    return render_template('team_bids.html',
                          active_rounds=active_rounds,
                          team_tiebreakers=team_tiebreakers,
                          team_bulk_tiebreakers=team_bulk_tiebreakers)

@app.route('/team_round')
@login_required
def team_round():
    # Check if user has any active tiebreakers
    from models import TeamTiebreaker, Tiebreaker
    
    if current_user.is_authenticated and hasattr(current_user, 'team') and current_user.team:
        # Check for any active bulk bid tiebreakers first
        team_bulk_tiebreakers = TeamBulkTiebreaker.query.join(
            BulkBidTiebreaker, TeamBulkTiebreaker.tiebreaker_id == BulkBidTiebreaker.id
        ).filter(
            TeamBulkTiebreaker.team_id == current_user.team.id,
            TeamBulkTiebreaker.is_active == True,
            BulkBidTiebreaker.resolved == False
        ).all()
        
        if team_bulk_tiebreakers:
            tiebreaker = BulkBidTiebreaker.query.get(team_bulk_tiebreakers[0].tiebreaker_id)
            return redirect(url_for('team_bulk_tiebreaker', tiebreaker_id=tiebreaker.id))
        
        # Check for regular tiebreakers
        team_tiebreakers = TeamTiebreaker.query.join(
            Tiebreaker, TeamTiebreaker.tiebreaker_id == Tiebreaker.id
        ).filter(
            TeamTiebreaker.team_id == current_user.team.id,
            Tiebreaker.resolved == False
        ).all()
        
        if team_tiebreakers:
            tiebreaker_id = team_tiebreakers[0].tiebreaker_id
            tiebreaker = Tiebreaker.query.get(tiebreaker_id)
            player = Player.query.get(tiebreaker.player_id)
            
            return render_template('tiebreaker_team.html',
                                  tiebreaker=tiebreaker,
                                  team_tiebreaker=team_tiebreakers[0],
                                  player=player)
        
        # Only show active rounds if no tiebreakers are pending
        active_rounds = Round.query.filter_by(is_active=True).all()
        
        # Get auction settings
        settings = AuctionSettings.get_settings()
        
        # Get completed rounds count
        completed_rounds_count = Round.query.filter_by(is_active=False).count()
        
        # Check for active bulk bid rounds
        active_bulk_round = BulkBidRound.query.filter_by(is_active=True).first()
        
        # Get Config for minimum bid amount
        from config import Config
        
        # Get starred players for this team
        starred_player_ids = []
        if current_user.team:
            starred_players = StarredPlayer.query.filter_by(team_id=current_user.team.id).all()
            starred_player_ids = [sp.player_id for sp in starred_players]
        
        return render_template('team_round.html',
                              active_rounds=active_rounds,
                              active_bulk_round=active_bulk_round,
                              Config=Config,
                              auction_settings=AuctionSettings,
                              completed_rounds_count=completed_rounds_count,
                              starred_player_ids=starred_player_ids)

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


@app.route('/admin/auction_settings', methods=['GET', 'POST'])
@login_required
def admin_auction_settings():
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))
    
    settings = AuctionSettings.get_settings()
    
    if request.method == 'POST':
        try:
            max_rounds = int(request.form.get('max_rounds', 25))
            min_balance_per_round = int(request.form.get('min_balance_per_round', 30))
            
            if max_rounds < 1:
                flash('Maximum rounds must be at least 1', 'error')
            elif min_balance_per_round < 0:
                flash('Minimum balance per round cannot be negative', 'error')
            else:
                settings.max_rounds = max_rounds
                settings.min_balance_per_round = min_balance_per_round
                db.session.commit()
                flash('Auction settings updated successfully', 'success')
        except ValueError:
            flash('Invalid input values', 'error')
    
    # Get counts for context
    total_rounds = Round.query.count()
    completed_rounds = Round.query.filter_by(is_active=False).count()
    remaining_rounds = settings.max_rounds - completed_rounds
    
    return render_template('admin_auction_settings.html', 
                          settings=settings,
                          total_rounds=total_rounds,
                          completed_rounds=completed_rounds,
                          remaining_rounds=remaining_rounds)

@app.route('/admin/auction_settings_update')
@login_required
def admin_auction_settings_update():
    if not current_user.is_admin or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get current auction settings
    settings = AuctionSettings.get_settings()
    
    # Get counts for context
    total_rounds = Round.query.count()
    completed_rounds = Round.query.filter_by(is_active=False).count()
    remaining_rounds = settings.max_rounds - completed_rounds
    
    # Return JSON with settings and counts
    return jsonify({
        'settings': {
            'max_rounds': settings.max_rounds,
            'min_balance_per_round': settings.min_balance_per_round
        },
        'total_rounds': total_rounds,
        'completed_rounds': completed_rounds,
        'remaining_rounds': remaining_rounds
    })

@app.route('/budget')
@login_required
def budget_planner():
    if not current_user.team:
        flash('You must have a team to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get auction settings
    auction_settings = AuctionSettings.get_settings()
    
    # Get completed rounds count
    completed_rounds_count = Round.query.filter_by(is_active=False).count()
    
    # Get active rounds
    active_rounds = Round.query.filter_by(is_active=True).all()
    
    # Calculate remaining rounds
    remaining_rounds = auction_settings.max_rounds - completed_rounds_count
    
    # Get team's current players by position
    players_by_position = {}
    for player in current_user.team.players:
        if player.position not in players_by_position:
            players_by_position[player.position] = []
        players_by_position[player.position].append(player)
    
    # Get team's bid history
    bid_history = Bid.query.filter_by(team_id=current_user.team.id).order_by(Bid.timestamp.desc()).all()
    
    # Calculate spending by position
    spending_by_position = {}
    for position in Config.POSITIONS:
        spending = sum(p.acquisition_value or 0 for p in current_user.team.players if p.position == position)
        spending_by_position[position] = spending
    
    # Calculate average bid amounts by position from all teams
    position_averages = {}
    for position in Config.POSITIONS:
        avg_result = db.session.query(func.avg(Player.acquisition_value)).filter(
            Player.position == position,
            Player.acquisition_value != None
        ).scalar()
        position_averages[position] = int(avg_result) if avg_result else 0
    
    # Get recent round results for budget tracking
    recent_rounds = Round.query.filter_by(is_active=False).order_by(Round.id.desc()).limit(5).all()
    
    # Calculate budget recommendations
    budget_recommendations = calculate_budget_recommendations(
        current_user.team.balance,
        remaining_rounds,
        auction_settings.min_balance_per_round,
        players_by_position,
        position_averages
    )
    
    return render_template('budget_planner.html',
                          auction_settings=auction_settings,
                          completed_rounds_count=completed_rounds_count,
                          remaining_rounds=remaining_rounds,
                          active_rounds=active_rounds,
                          players_by_position=players_by_position,
                          bid_history=bid_history,
                          spending_by_position=spending_by_position,
                          position_averages=position_averages,
                          recent_rounds=recent_rounds,
                          budget_recommendations=budget_recommendations,
                          config=Config)

def calculate_budget_recommendations(balance, remaining_rounds, min_per_round, players_by_position, position_averages):
    """Calculate budget recommendations based on team needs and market data"""
    recommendations = {}
    
    # Calculate safe spending amount for next round
    if remaining_rounds > 0:
        safe_reserve = min_per_round * (remaining_rounds - 1)
        safe_spending = max(0, balance - safe_reserve)
        recommendations['safe_spending'] = safe_spending
        recommendations['max_bid'] = int(safe_spending * 0.8)  # Recommend keeping 20% buffer
    else:
        recommendations['safe_spending'] = balance
        recommendations['max_bid'] = balance
    
    # Recommend positions to focus on based on gaps
    position_needs = []
    for position in Config.POSITIONS:
        current_count = len(players_by_position.get(position, []))
        
        # High Priority - Essential positions that MUST be filled
        if position in ['GK'] and current_count < 1:
            position_needs.append({'position': position, 'priority': 'High', 'suggested_budget': position_averages.get(position, 80)})
        elif position in ['CB', 'CF'] and current_count < 2:
            position_needs.append({'position': position, 'priority': 'High', 'suggested_budget': position_averages.get(position, 70)})
        
        # Medium Priority - Important positions for team balance  
        elif position in ['RB', 'LB', 'DMF', 'CMF', 'AMF'] and current_count < 1:
            position_needs.append({'position': position, 'priority': 'Medium', 'suggested_budget': position_averages.get(position, 60)})
        elif position in ['LMF', 'RMF', 'LWF', 'RWF', 'SS'] and current_count < 1:
            position_needs.append({'position': position, 'priority': 'Medium', 'suggested_budget': position_averages.get(position, 50)})
        
        # Depth Options - Adding squad depth
        elif position in ['CB', 'CF'] and current_count < 3 and current_count >= 2:
            position_needs.append({'position': position, 'priority': 'Low', 'suggested_budget': position_averages.get(position, 40)})
        elif position in ['RB', 'LB', 'DMF', 'CMF'] and current_count < 2 and current_count >= 1:
            position_needs.append({'position': position, 'priority': 'Low', 'suggested_budget': position_averages.get(position, 35)})
    
    recommendations['position_needs'] = position_needs
    
    # Calculate optimal bid distribution
    if remaining_rounds > 0:
        avg_per_round = safe_spending / remaining_rounds if remaining_rounds > 0 else safe_spending
        recommendations['avg_per_round'] = int(avg_per_round)
    
    return recommendations

@app.route('/team_bulk_round')
@login_required
def team_bulk_round():
    if not current_user.team:
        flash('You must have a team to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check for any active bulk bid tiebreakers first
    team_bulk_tiebreakers = TeamBulkTiebreaker.query.join(
        BulkBidTiebreaker, TeamBulkTiebreaker.tiebreaker_id == BulkBidTiebreaker.id
    ).filter(
        TeamBulkTiebreaker.team_id == current_user.team.id,
        TeamBulkTiebreaker.is_active == True,
        BulkBidTiebreaker.resolved == False
    ).all()
    
    if team_bulk_tiebreakers:
        tiebreaker = BulkBidTiebreaker.query.get(team_bulk_tiebreakers[0].tiebreaker_id)
        return redirect(url_for('team_bulk_tiebreaker', tiebreaker_id=tiebreaker.id))
    
    # Get active bulk bid round
    active_bulk_round = BulkBidRound.query.filter_by(is_active=True).first()
    
    if not active_bulk_round:
        flash('No active bulk bid round available.', 'info')
        return redirect(url_for('dashboard'))
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)  # Default 20 players per page
    position_filter = request.args.get('position', '')
    search_query = request.args.get('search', '')
    
    # Validate per_page parameter (prevent abuse)
    per_page = min(max(per_page, 5), 100)  # Between 5 and 100 players per page
    
    # Performance optimization: Use a single query with joins and aggregates
    # Get team player count and bid count in one query
    team_stats = db.session.query(
        func.count(Player.id).label('player_count')
    ).filter(
        Player.team_id == current_user.team.id
    ).first()
    
    # Get bid count for this round
    bid_count = BulkBid.query.filter_by(
        team_id=current_user.team.id,
        round_id=active_bulk_round.id
    ).count()
    
    # Calculate available slots
    max_players_per_team = 25  # Each team can have a maximum of 25 players
    team_player_count = team_stats.player_count if team_stats.player_count else 0
    available_slots = max_players_per_team - team_player_count - bid_count
    
    # Get all available players with pagination and filters
    players_query = Player.query.filter(
        Player.team_id == None,
        Player.is_auction_eligible == True
    )
    
    # Apply position filter if specified
    if position_filter:
        players_query = players_query.filter(Player.position == position_filter)
    
    # Apply search filter if specified
    if search_query:
        players_query = players_query.filter(
            Player.name.ilike(f'%{search_query}%')
        )
    
    # Order by overall rating (highest first) and paginate
    players_pagination = players_query.order_by(
        Player.overall_rating.desc().nullslast(),
        Player.name.asc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Group paginated players by position for display
    players_by_position = {}
    for player in players_pagination.items:
        if player.position not in players_by_position:
            players_by_position[player.position] = []
        
        # Convert player to dict for consistency with template
        player_dict = {
            'id': player.id,
            'name': player.name,
            'position': player.position,
            'team_name': player.team_name,
            'overall_rating': player.overall_rating,
            'playing_style': player.playing_style
        }
        players_by_position[player.position].append(player_dict)
    
    # Get position counts for sidebar/filter display
    position_counts = {}
    if not position_filter and not search_query:
        # Only calculate position counts if no filters applied (for performance)
        position_count_query = db.session.query(
            Player.position,
            func.count(Player.id).label('count')
        ).filter(
            Player.team_id == None,
            Player.is_auction_eligible == True
        ).group_by(Player.position).all()
        
        position_counts = {position: count for position, count in position_count_query}
    
    # Get existing bids for this team in this round with minimal data
    team_bids = db.session.query(
        BulkBid.id,
        BulkBid.player_id,
        Player.name.label('player_name'),
        Player.position,
        Player.overall_rating
    ).join(
        Player, BulkBid.player_id == Player.id
    ).filter(
        BulkBid.team_id == current_user.team.id,
        BulkBid.round_id == active_bulk_round.id
    ).all()
    
    return render_template('team_bulk_round.html',
                          bulk_round=active_bulk_round,
                          players_by_position=players_by_position,
                          players_pagination=players_pagination,
                          position_counts=position_counts,
                          team_bids=team_bids,
                          available_slots=available_slots,
                          current_page=page,
                          per_page=per_page,
                          position_filter=position_filter,
                          search_query=search_query,
                          config=Config)

@app.route('/place_bulk_bid', methods=['POST'])
@login_required
def place_bulk_bid():
    if not current_user.team:
        return jsonify({'error': 'You must have a team to place bids.'}), 400
    
    data = request.json
    player_id = data.get('player_id')
    round_id = data.get('round_id')
    
    if not player_id or not round_id:
        return jsonify({'error': 'Missing required fields.'}), 400
    
    # Validate the round is active
    bulk_round = BulkBidRound.query.get_or_404(round_id)
    if not bulk_round.is_active:
        return jsonify({'error': 'This round is no longer active.'}), 400
    
    # Validate the player exists and is not already assigned
    player = Player.query.get_or_404(player_id)
    if player.team_id:
        return jsonify({'error': 'This player is already assigned to a team.'}), 400
    
    # Check if the team has enough balance for the base price
    if current_user.team.balance < bulk_round.base_price:
        return jsonify({'error': 'Your team does not have enough balance.'}), 400
    
    # Calculate available slot count (remaining slots for the team)
    team_player_count = Player.query.filter_by(team_id=current_user.team.id).count()
    max_players_per_team = 25  # Each team can have a maximum of 25 players
    
    # Count existing bids in this round
    existing_bids_count = BulkBid.query.filter_by(
        team_id=current_user.team.id,
        round_id=bulk_round.id
    ).count()
    
    # Total slots available taking into account current players and bids
    available_slots = max_players_per_team - team_player_count - existing_bids_count
    
    if available_slots <= 0:
        return jsonify({'error': 'You have reached the maximum number of bids for this round.'}), 400
    
    # Check if the team already has a bid for this player in this round
    existing_bid = BulkBid.query.filter_by(
        team_id=current_user.team.id,
        player_id=player_id,
        round_id=round_id
    ).first()
    
    if existing_bid:
        return jsonify({'error': 'You have already placed a bid for this player.'}), 400
    
    # Create the new bid
    new_bid = BulkBid(
        team_id=current_user.team.id,
        player_id=player_id,
        round_id=round_id
    )
    
    db.session.add(new_bid)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Bid placed successfully.',
        'bid_id': new_bid.id,
        'player_id': player_id
    })

@app.route('/delete_bulk_bid/<int:bid_id>', methods=['DELETE'])
@login_required
def delete_bulk_bid(bid_id):
    if not current_user.team:
        return jsonify({'error': 'You must have a team to delete bids.'}), 400
    
    bid = BulkBid.query.get_or_404(bid_id)
    
    if bid.team_id != current_user.team.id:
        return jsonify({'error': 'You can only delete your own bids.'}), 403
    
    if not bid.bulk_round.is_active:
        return jsonify({'error': 'This round is no longer active.'}), 400
    
    # Store player_id before deleting the bid
    player_id = bid.player_id
    
    db.session.delete(bid)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Bid deleted successfully.',
        'player_id': player_id
    })

@app.route('/test_bulk_timer')
@login_required
def test_bulk_timer():
    """Test page for debugging bulk timer"""
    return render_template('test_bulk_timer.html')

@app.route('/check_bulk_round_status/<int:round_id>')
@login_required
def check_bulk_round_status(round_id):
    bulk_round = BulkBidRound.query.get_or_404(round_id)
    
    # Debug logging
    print(f"[DEBUG] Checking bulk round {round_id}:")
    print(f"  - is_active: {bulk_round.is_active}")
    print(f"  - start_time: {bulk_round.start_time}")
    print(f"  - duration: {bulk_round.duration}")
    print(f"  - status: {bulk_round.status}")
    
    if not bulk_round.is_active:
        print(f"[DEBUG] Round {round_id} is not active, returning False")
        return jsonify({'active': False})
    
    # Make sure start_time exists
    if not bulk_round.start_time:
        print(f"[DEBUG] Round {round_id} has no start_time, setting to now")
        # If start_time is None, set it to now
        bulk_round.start_time = datetime.utcnow()
        db.session.commit()
        print(f"[DEBUG] Round {round_id} start_time set to {bulk_round.start_time}")
    
    # Calculate elapsed and remaining time
    now = datetime.utcnow()
    elapsed = (now - bulk_round.start_time).total_seconds()
    remaining = bulk_round.duration - elapsed
    
    print(f"[DEBUG] Time calculations for round {round_id}:")
    print(f"  - now: {now}")
    print(f"  - elapsed: {elapsed} seconds")
    print(f"  - remaining: {remaining} seconds")
    
    # Check if timer has expired
    if remaining <= 0:
        print(f"[DEBUG] Round {round_id} timer expired, deactivating")
        # Timer expired, deactivate the round
        bulk_round.is_active = False
        bulk_round.status = "completed"
        db.session.commit()
        return jsonify({'active': False, 'expired': True})
    
    # Return the remaining time
    data = {
        'active': True,
        'remaining': remaining,
        'duration': bulk_round.duration,
        'start_time': bulk_round.start_time.isoformat() if bulk_round.start_time else None
    }
    
    print(f"[DEBUG] Returning data for round {round_id}: {data}")
    return jsonify(data)

@app.route('/team_bulk_tiebreaker/<int:tiebreaker_id>')
@login_required
def team_bulk_tiebreaker(tiebreaker_id):
    if not current_user.team:
        flash('You must have a team to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    tiebreaker = BulkBidTiebreaker.query.get_or_404(tiebreaker_id)
    
    # Check if the team is part of this tiebreaker
    team_tiebreaker = TeamBulkTiebreaker.query.filter_by(
        tiebreaker_id=tiebreaker_id,
        team_id=current_user.team.id,
        is_active=True
    ).first()
    
    if not team_tiebreaker:
        flash('You are not part of this tiebreaker.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all active teams in this tiebreaker
    active_teams = TeamBulkTiebreaker.query.filter_by(
        tiebreaker_id=tiebreaker_id,
        is_active=True
    ).all()
    
    return render_template('team_bulk_tiebreaker.html',
                          tiebreaker=tiebreaker,
                          team_tiebreaker=team_tiebreaker,
                          active_teams=active_teams,
                          player=tiebreaker.player)

@app.route('/place_bulk_tiebreaker_bid', methods=['POST'])
@login_required
def place_bulk_tiebreaker_bid():
    if not current_user.team:
        return jsonify({'error': 'You must have a team to place bids.'}), 400
    
    data = request.json
    tiebreaker_id = data.get('tiebreaker_id')
    amount = data.get('amount')
    
    if not tiebreaker_id or not amount:
        return jsonify({'error': 'Missing required fields.'}), 400
    
    try:
        amount = int(amount)
    except ValueError:
        return jsonify({'error': 'Bid amount must be a number.'}), 400
    
    tiebreaker = BulkBidTiebreaker.query.get_or_404(tiebreaker_id)
    
    if tiebreaker.resolved:
        return jsonify({'error': 'This tiebreaker is already resolved.'}), 400
    
    # Validate team is part of the tiebreaker
    team_tiebreaker = TeamBulkTiebreaker.query.filter_by(
        tiebreaker_id=tiebreaker_id,
        team_id=current_user.team.id,
        is_active=True
    ).first()
    
    if not team_tiebreaker:
        return jsonify({'error': 'You are not part of this tiebreaker.'}), 400
    
    # Check minimum bid amount
    if amount <= tiebreaker.current_amount:
        return jsonify({'error': f'Bid amount must be greater than {tiebreaker.current_amount}.'}), 400
    
    # Check if team has enough balance
    if current_user.team.balance < amount:
        return jsonify({'error': 'Your team does not have enough balance.'}), 400
    
    # Update the current amount and last bid info
    tiebreaker.current_amount = amount
    team_tiebreaker.last_bid = amount
    team_tiebreaker.last_bid_time = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Bid placed successfully.', 
        'new_amount': amount
    })

@app.route('/withdraw_from_bulk_tiebreaker', methods=['POST'])
@login_required
def withdraw_from_bulk_tiebreaker():
    if not current_user.team:
        return jsonify({'error': 'You must have a team to perform this action.'}), 400
    
    data = request.json
    tiebreaker_id = data.get('tiebreaker_id')
    
    if not tiebreaker_id:
        return jsonify({'error': 'Missing tiebreaker ID.'}), 400
    
    tiebreaker = BulkBidTiebreaker.query.get_or_404(tiebreaker_id)
    
    # Check if tiebreaker is already resolved
    if tiebreaker.resolved:
        return jsonify({'error': 'This tiebreaker is already resolved.'}), 400
    
    # Validate user is part of the tiebreaker
    team_tiebreaker = TeamBulkTiebreaker.query.filter_by(
        tiebreaker_id=tiebreaker_id,
        team_id=current_user.team.id,
        is_active=True
    ).first()
    
    if not team_tiebreaker:
        return jsonify({'error': 'You are not part of this tiebreaker or have already withdrawn.'}), 400
    
    # Check if this team has the highest bid
    active_teams = TeamBulkTiebreaker.query.filter_by(
        tiebreaker_id=tiebreaker_id,
        is_active=True
    ).all()
    
    highest_bid = 0
    highest_bidder_id = None
    
    for active_team in active_teams:
        if active_team.last_bid and active_team.last_bid > highest_bid:
            highest_bid = active_team.last_bid
            highest_bidder_id = active_team.team_id
    
    # If there's a highest bidder and it's this team, don't allow withdrawal
    if highest_bidder_id and highest_bidder_id == current_user.team.id:
        return jsonify({'error': 'You currently have the highest bid and cannot withdraw from this tiebreaker.'}), 400
    
    # Mark the team as inactive in the tiebreaker
    team_tiebreaker.is_active = False
    db.session.commit()
    
    # Check if there's only one team left active
    remaining_active_teams = [team for team in active_teams if team.team_id != current_user.team.id and team.is_active]
    
    if len(remaining_active_teams) == 1:
        # Resolve the tiebreaker with the remaining team as the winner
        tiebreaker.resolved = True
        tiebreaker.winner_team_id = remaining_active_teams[0].team_id
        
        # Find the original bid and mark it as resolved
        bulk_bid = BulkBid.query.filter_by(
            player_id=tiebreaker.player_id,
            team_id=remaining_active_teams[0].team_id,
            round_id=tiebreaker.bulk_round_id
        ).first()
        
        if bulk_bid:
            bulk_bid.is_resolved = True
            
            # Get the player and winning team
            player = Player.query.get(tiebreaker.player_id)
            winning_team = Team.query.get(remaining_active_teams[0].team_id)
            
            # Assign player to winning team
            player.team_id = winning_team.id
            
            # Use the highest bid amount as the acquisition value
            # First check if the winner has placed any bids
            final_value = remaining_active_teams[0].last_bid if remaining_active_teams[0].last_bid else tiebreaker.current_amount
            player.acquisition_value = final_value
            
            # Deduct amount from team balance
            winning_team.balance -= final_value
        
        db.session.commit()
    
    return jsonify({'success': True, 'message': 'Withdrawn from tiebreaker successfully.'})

# Admin routes for Bulk Bid Rounds
@app.route('/admin/start_bulk_round', methods=['POST'])
@login_required
def admin_start_bulk_round():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    data = request.form
    duration = data.get('duration', 300)
    base_price = data.get('base_price', 10)
    
    try:
        duration = int(duration)
        base_price = int(base_price)
    except ValueError:
        flash('Duration and base price must be numbers.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Check if there's an active bulk round already
    active_round = BulkBidRound.query.filter_by(is_active=True).first()
    
    if active_round:
        flash('There is already an active bulk bid round.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Create new bulk round with explicit start_time
    new_round = BulkBidRound(
        duration=duration,
        base_price=base_price,
        start_time=datetime.utcnow(),
        is_active=True,
        status='active'
    )
    
    db.session.add(new_round)
    db.session.commit()
    
    flash('Bulk bid round started successfully.', 'success')
    return redirect(url_for('admin_bulk_round', round_id=new_round.id))

@app.route('/admin/bulk_round/<int:round_id>')
@login_required
def admin_bulk_round(round_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    bulk_round = BulkBidRound.query.get_or_404(round_id)
    
    # Get all bids in this round
    bids = BulkBid.query.filter_by(round_id=round_id).all()
    
    # Group bids by player
    bids_by_player = {}
    for bid in bids:
        if bid.player_id not in bids_by_player:
            bids_by_player[bid.player_id] = {
                'player': bid.player,
                'bids': []
            }
        bids_by_player[bid.player_id]['bids'].append(bid)
    
    # Group bids by team
    bids_by_team = {}
    for bid in bids:
        if bid.team_id not in bids_by_team:
            bids_by_team[bid.team_id] = {
                'team': bid.team,
                'bids': []
            }
        bids_by_team[bid.team_id]['bids'].append(bid)
    
    # Get all active tiebreakers
    tiebreakers = BulkBidTiebreaker.query.filter_by(
        bulk_round_id=round_id,
        resolved=False
    ).all()
    
    return render_template('admin_bulk_round.html',
                          bulk_round=bulk_round,
                          bids_by_player=bids_by_player,
                          bids_by_team=bids_by_team,
                          tiebreakers=tiebreakers)

@app.route('/admin/bulk_round_update/<int:round_id>')
@login_required
def admin_bulk_round_update(round_id):
    if not current_user.is_admin or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Unauthorized'}), 403
    
    bulk_round = BulkBidRound.query.get_or_404(round_id)
    
    # Get status information
    if bulk_round.is_active:
        elapsed = (datetime.utcnow() - bulk_round.start_time).total_seconds()
        remaining = max(bulk_round.duration - elapsed, 0)
        status = {
            'active': True,
            'remaining': remaining
        }
    else:
        status = {
            'active': False
        }
    
    # Get all bids in this round
    bids = BulkBid.query.filter_by(round_id=round_id).all()
    
    # Group bids by player
    bids_by_player = {}
    for bid in bids:
        if bid.player_id not in bids_by_player:
            bids_by_player[bid.player_id] = {
                'player': bid.player,
                'bids': []
            }
        bids_by_player[bid.player_id]['bids'].append(bid)
    
    # Group bids by team
    bids_by_team = {}
    for bid in bids:
        if bid.team_id not in bids_by_team:
            bids_by_team[bid.team_id] = {
                'team': bid.team,
                'bids': []
            }
        bids_by_team[bid.team_id]['bids'].append(bid)
    
    # Get all active tiebreakers
    tiebreakers = BulkBidTiebreaker.query.filter_by(
        bulk_round_id=round_id,
        resolved=False
    ).all()
    
    # Serialize the data for JSON response
    tiebreaker_data = []
    for t in tiebreakers:
        team_count = TeamBulkTiebreaker.query.filter_by(tiebreaker_id=t.id, is_active=True).count()
        tiebreaker_data.append({
            'id': t.id,
            'player_id': t.player_id,
            'player_name': t.player.name,
            'position': t.player.position,
            'current_amount': t.current_amount,
            'team_count': team_count
        })
    
    # Serialize player data
    player_data = {}
    for player_id, data in bids_by_player.items():
        player = data['player']
        status = ''
        
        if player.team_id:
            status = 'assigned'
        elif player_id in [t.player_id for t in tiebreakers]:
            status = 'in_tiebreaker'
        elif len(data['bids']) == 1:
            status = 'single_bid'
        else:
            status = 'multiple_bids'
            
        player_data[player_id] = {
            'id': player.id,
            'name': player.name,
            'position': player.position,
            'overall_rating': player.overall_rating,
            'bid_count': len(data['bids']),
            'status': status
        }
    
    # Serialize team data
    team_data = {}
    for team_id, data in bids_by_team.items():
        team = data['team']
        bid_list = []
        
        for bid in data['bids']:
            bid_status = ''
            if bid.player.team_id and bid.player.team_id != team.id:
                bid_status = 'lost'
            elif bid.is_resolved and bid.player.team_id == team.id:
                bid_status = 'won'
            elif bid.player_id in [t.player_id for t in tiebreakers]:
                bid_status = 'in_tiebreaker'
            else:
                bid_status = 'pending'
                
            bid_list.append({
                'id': bid.id,
                'player_id': bid.player_id,
                'player_name': bid.player.name,
                'position': bid.player.position,
                'status': bid_status
            })
        
        team_data[team_id] = {
            'id': team.id,
            'name': team.name,
            'bid_count': len(data['bids']),
            'bids': bid_list
        }
    
    return jsonify({
        'status': status,
        'round_info': {
            'id': bulk_round.id,
            'base_price': bulk_round.base_price,
            'start_time': bulk_round.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': bulk_round.status
        },
        'tiebreakers': tiebreaker_data,
        'bid_count': len(bids),
        'player_count': len(bids_by_player),
        'team_count': len(bids_by_team),
        'players': player_data,
        'teams': team_data
    })

@app.route('/admin/update_bulk_round_timer/<int:round_id>', methods=['POST'])
@login_required
def admin_update_bulk_round_timer(round_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 401
    
    bulk_round = BulkBidRound.query.get_or_404(round_id)
    
    if not bulk_round.is_active:
        return jsonify({'error': 'This round is not active.'}), 400
    
    data = request.json
    duration = data.get('duration')
    
    try:
        duration = int(duration)
    except (ValueError, TypeError):
        return jsonify({'error': 'Duration must be a number.'}), 400
    
    bulk_round.duration = bulk_round.duration + duration
    db.session.commit()
    
    return jsonify({'success': True, 'new_duration': bulk_round.duration})

@app.route('/admin/finalize_bulk_round/<int:round_id>', methods=['POST'])
@login_required
def admin_finalize_bulk_round(round_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    bulk_round = BulkBidRound.query.get_or_404(round_id)
    
    if not bulk_round.is_active:
        flash('This round is already finalized.', 'error')
        return redirect(url_for('admin_bulk_round', round_id=round_id))
    
    # Set the round as inactive and processing
    bulk_round.is_active = False
    bulk_round.status = "processing"
    db.session.commit()
    
    # Process all bids in this round
    bids = BulkBid.query.filter_by(round_id=round_id).all()
    
    # Group bids by player
    players_with_bids = {}
    for bid in bids:
        if bid.player_id not in players_with_bids:
            players_with_bids[bid.player_id] = []
        players_with_bids[bid.player_id].append(bid)
    
    # Process each player
    for player_id, player_bids in players_with_bids.items():
        if len(player_bids) == 1:
            # Only one team bid for this player, assign directly
            bid = player_bids[0]
            player = Player.query.get(player_id)
            
            # Deduct team balance
            team = Team.query.get(bid.team_id)
            team.balance -= bulk_round.base_price
            
            # Assign player to team
            player.team_id = bid.team_id
            player.acquisition_value = bulk_round.base_price
            
            # Mark bid as resolved
            bid.is_resolved = True
            
            db.session.commit()
        elif len(player_bids) > 1:
            # Multiple teams bid for this player, create a tiebreaker
            player = Player.query.get(player_id)
            
            # Create tiebreaker
            tiebreaker = BulkBidTiebreaker(
                player_id=player_id,
                bulk_round_id=round_id,
                current_amount=bulk_round.base_price
            )
            db.session.add(tiebreaker)
            db.session.flush()  # To get the tiebreaker ID
            
            # Create team tiebreakers
            for bid in player_bids:
                team_tiebreaker = TeamBulkTiebreaker(
                    tiebreaker_id=tiebreaker.id,
                    team_id=bid.team_id
                )
                db.session.add(team_tiebreaker)
                
                # Mark bid as having a tie
                bid.has_tie = True
            
            db.session.commit()
    
    # Set the round as completed
    bulk_round.status = "completed"
    db.session.commit()
    
    flash('Bulk bid round finalized successfully.', 'success')
    return redirect(url_for('admin_bulk_round', round_id=round_id))

@app.route('/admin/bulk_rounds')
@login_required
def admin_bulk_rounds():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all bulk rounds, ordered by most recent first
    bulk_rounds = BulkBidRound.query.order_by(BulkBidRound.start_time.desc()).all()
    
    # Group by status
    active_rounds = []
    completed_rounds = []
    
    for round in bulk_rounds:
        if round.is_active:
            active_rounds.append(round)
        else:
            completed_rounds.append(round)
    
    # Get stats for each round
    round_stats = {}
    for round in bulk_rounds:
        # Count total bids
        total_bids = BulkBid.query.filter_by(round_id=round.id).count()
        
        # Count players acquired directly (no tiebreaker)
        direct_assignments = BulkBid.query.filter_by(
            round_id=round.id,
            is_resolved=True
        ).count()
        
        # Count tiebreakers
        tiebreakers = BulkBidTiebreaker.query.filter_by(
            bulk_round_id=round.id
        ).count()
        
        # Count resolved tiebreakers
        resolved_tiebreakers = BulkBidTiebreaker.query.filter_by(
            bulk_round_id=round.id,
            resolved=True
        ).count()
        
        round_stats[round.id] = {
            'total_bids': total_bids,
            'direct_assignments': direct_assignments,
            'tiebreakers': tiebreakers,
            'resolved_tiebreakers': resolved_tiebreakers,
            'pending_tiebreakers': tiebreakers - resolved_tiebreakers
        }
    
    return render_template('admin_bulk_rounds.html',
                          active_rounds=active_rounds,
                          completed_rounds=completed_rounds,
                          round_stats=round_stats)

@app.route('/admin/bulk_tiebreakers')
@login_required
def admin_bulk_tiebreakers():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all active tiebreakers
    tiebreakers = BulkBidTiebreaker.query.filter_by(resolved=False).all()
    
    # Group by round
    tiebreakers_by_round = {}
    
    for tiebreaker in tiebreakers:
        if tiebreaker.bulk_round_id not in tiebreakers_by_round:
            tiebreakers_by_round[tiebreaker.bulk_round_id] = {
                'round': tiebreaker.bulk_round,
                'tiebreakers': []
            }
        tiebreakers_by_round[tiebreaker.bulk_round_id]['tiebreakers'].append(tiebreaker)
    
    # Gather details for each tiebreaker
    tiebreaker_details = {}
    for tiebreaker in tiebreakers:
        team_tiebreakers = TeamBulkTiebreaker.query.filter_by(
            tiebreaker_id=tiebreaker.id, 
            is_active=True
        ).all()
        
        highest_bid = 0
        highest_bidder = None
        
        for tt in team_tiebreakers:
            if tt.last_bid and tt.last_bid > highest_bid:
                highest_bid = tt.last_bid
                highest_bidder = tt.team
        
        tiebreaker_details[tiebreaker.id] = {
            'teams': team_tiebreakers,
            'highest_bid': highest_bid,
            'highest_bidder': highest_bidder
        }
    
    return render_template('admin_bulk_tiebreakers.html', 
                          tiebreakers_by_round=tiebreakers_by_round,
                          tiebreaker_details=tiebreaker_details)

@app.route('/admin/bulk_tiebreakers_stream')
@login_required
def admin_bulk_tiebreakers_stream():
    """Server-Sent Events endpoint for real-time bulk tiebreaker updates"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    def generate():
        """Generator function for SSE stream"""
        last_data_hash = None
        
        while True:
            try:
                # Get all active tiebreakers
                tiebreakers = BulkBidTiebreaker.query.filter_by(resolved=False).all()
                
                # Group by round
                tiebreakers_by_round = {}
                
                for tiebreaker in tiebreakers:
                    if tiebreaker.bulk_round_id not in tiebreakers_by_round:
                        tiebreakers_by_round[tiebreaker.bulk_round_id] = {
                            'round': {
                                'id': tiebreaker.bulk_round.id,
                                'is_active': tiebreaker.bulk_round.is_active,
                                'status': tiebreaker.bulk_round.status,
                                'start_time': tiebreaker.bulk_round.start_time.strftime('%Y-%m-%d')
                            },
                            'tiebreakers': []
                        }
                    
                    # Get team tiebreakers
                    team_tiebreakers = TeamBulkTiebreaker.query.filter_by(
                        tiebreaker_id=tiebreaker.id, 
                        is_active=True
                    ).all()
                    
                    highest_bid = 0
                    highest_bidder = None
                    
                    team_data = []
                    for tt in team_tiebreakers:
                        if tt.last_bid and tt.last_bid > highest_bid:
                            highest_bid = tt.last_bid
                            highest_bidder = tt.team
                        
                        team_data.append({
                            'id': tt.team.id,
                            'name': tt.team.name,
                            'last_bid': tt.last_bid if tt.last_bid else 0
                        })
                    
                    tiebreaker_data = {
                        'id': tiebreaker.id,
                        'player_id': tiebreaker.player_id,
                        'player_name': tiebreaker.player.name,
                        'player_position': tiebreaker.player.position,
                        'player_team_name': tiebreaker.player.team_name,
                        'player_overall_rating': tiebreaker.player.overall_rating,
                        'current_amount': tiebreaker.current_amount,
                        'teams': team_data,
                        'highest_bid': highest_bid,
                        'highest_bidder': {'id': highest_bidder.id, 'name': highest_bidder.name} if highest_bidder else None
                    }
                    
                    tiebreakers_by_round[tiebreaker.bulk_round_id]['tiebreakers'].append(tiebreaker_data)
                
                # Convert to a list format for JSON response
                response_data = [
                    {
                        'round_id': round_id,
                        'round_data': round_data
                    } for round_id, round_data in tiebreakers_by_round.items()
                ]
                
                # Create a hash of the data to detect changes
                import hashlib
                data_str = json.dumps(response_data, sort_keys=True)
                data_hash = hashlib.md5(data_str.encode()).hexdigest()
                
                # Only send update if data has changed
                if data_hash != last_data_hash:
                    last_data_hash = data_hash
                    
                    event_data = json.dumps({
                        'tiebreakers_count': len(tiebreakers),
                        'rounds_count': len(tiebreakers_by_round),
                        'tiebreakers_by_round': response_data,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
                    yield f"data: {event_data}\n\n"
                
                # Sleep for a short interval before checking again
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                # Send error event
                error_data = json.dumps({'error': str(e)})
                yield f"data: {error_data}\n\n"
                break
    
    return Response(generate(), mimetype="text/event-stream")


@app.route('/admin/bulk_tiebreakers_update')
@login_required
def admin_bulk_tiebreakers_update():
    if not current_user.is_admin or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get all active tiebreakers
    tiebreakers = BulkBidTiebreaker.query.filter_by(resolved=False).all()
    
    # Group by round
    tiebreakers_by_round = {}
    
    for tiebreaker in tiebreakers:
        if tiebreaker.bulk_round_id not in tiebreakers_by_round:
            tiebreakers_by_round[tiebreaker.bulk_round_id] = {
                'round': {
                    'id': tiebreaker.bulk_round.id,
                    'is_active': tiebreaker.bulk_round.is_active,
                    'status': tiebreaker.bulk_round.status,
                    'start_time': tiebreaker.bulk_round.start_time.strftime('%Y-%m-%d')
                },
                'tiebreakers': []
            }
        
        # Get team tiebreakers
        team_tiebreakers = TeamBulkTiebreaker.query.filter_by(
            tiebreaker_id=tiebreaker.id, 
            is_active=True
        ).all()
        
        highest_bid = 0
        highest_bidder = None
        
        team_data = []
        for tt in team_tiebreakers:
            if tt.last_bid and tt.last_bid > highest_bid:
                highest_bid = tt.last_bid
                highest_bidder = tt.team
            
            team_data.append({
                'id': tt.team.id,
                'name': tt.team.name,
                'last_bid': tt.last_bid if tt.last_bid else 0
            })
        
        tiebreaker_data = {
            'id': tiebreaker.id,
            'player_id': tiebreaker.player_id,
            'player_name': tiebreaker.player.name,
            'player_position': tiebreaker.player.position,
            'player_team_name': tiebreaker.player.team_name,
            'player_overall_rating': tiebreaker.player.overall_rating,
            'current_amount': tiebreaker.current_amount,
            'teams': team_data,
            'highest_bid': highest_bid,
            'highest_bidder': {'id': highest_bidder.id, 'name': highest_bidder.name} if highest_bidder else None
        }
        
        tiebreakers_by_round[tiebreaker.bulk_round_id]['tiebreakers'].append(tiebreaker_data)
    
    # Convert to a list format for JSON response
    response_data = [
        {
            'round_id': round_id,
            'round_data': round_data
        } for round_id, round_data in tiebreakers_by_round.items()
    ]
    
    return jsonify({
        'tiebreakers_count': len(tiebreakers),
        'rounds_count': len(tiebreakers_by_round),
        'tiebreakers_by_round': response_data
    })

@app.route('/admin/resolve_bulk_tiebreaker/<int:tiebreaker_id>', methods=['POST'])
@login_required
def admin_resolve_bulk_tiebreaker(tiebreaker_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    tiebreaker = BulkBidTiebreaker.query.get_or_404(tiebreaker_id)
    
    if tiebreaker.resolved:
        flash('This tiebreaker is already resolved.', 'error')
        return redirect(url_for('admin_bulk_tiebreakers'))
    
    # Get all active teams in this tiebreaker
    active_teams = TeamBulkTiebreaker.query.filter_by(
        tiebreaker_id=tiebreaker_id,
        is_active=True
    ).all()
    
    if not active_teams:
        flash('No active teams found in this tiebreaker.', 'error')
        return redirect(url_for('admin_bulk_tiebreakers'))
    
    # Find highest bidder
    highest_bid = 0
    highest_bidder_id = None
    
    for team_tiebreaker in active_teams:
        if team_tiebreaker.last_bid and team_tiebreaker.last_bid > highest_bid:
            highest_bid = team_tiebreaker.last_bid
            highest_bidder_id = team_tiebreaker.team_id
    
    if highest_bidder_id:
        # Set the winner
        tiebreaker.winner_team_id = highest_bidder_id
        
        # Find the original bid and mark it as resolved
        bulk_bid = BulkBid.query.filter_by(
            player_id=tiebreaker.player_id,
            team_id=highest_bidder_id,
            round_id=tiebreaker.bulk_round_id
        ).first()
        
        if bulk_bid:
            bulk_bid.is_resolved = True
            
            # Get the player and winning team
            player = Player.query.get(tiebreaker.player_id)
            winning_team = Team.query.get(highest_bidder_id)
            
            # Assign player to winning team
            player.team_id = winning_team.id
            
            # Use the highest bid as the acquisition value
            final_value = highest_bid if highest_bid > 0 else tiebreaker.current_amount
            player.acquisition_value = final_value
            
            # Deduct amount from team balance
            winning_team.balance -= final_value
            
            # Mark as resolved
            tiebreaker.resolved = True
            
            db.session.commit()
            flash(f'Tiebreaker resolved. Player {player.name} assigned to {winning_team.name} for £{player.acquisition_value}.', 'success')
        else:
            flash('Could not find the original bid. Tiebreaker not resolved.', 'error')
    else:
        # If no highest bidder (all teams joined but none placed a bid), 
        # assign to a random team to prevent deadlock
        if active_teams:
            random_team = active_teams[0]
            tiebreaker.winner_team_id = random_team.team_id
            
            # Find the original bid and mark it as resolved
            bulk_bid = BulkBid.query.filter_by(
                player_id=tiebreaker.player_id,
                team_id=random_team.team_id,
                round_id=tiebreaker.bulk_round_id
            ).first()
            
            if bulk_bid:
                bulk_bid.is_resolved = True
                
                # Get the player and assigned team
                player = Player.query.get(tiebreaker.player_id)
                team = Team.query.get(random_team.team_id)
                
                # Assign player to team
                player.team_id = team.id
                
                # Use the base price as the acquisition value
                player.acquisition_value = tiebreaker.current_amount
                
                # Deduct amount from team balance
                team.balance -= tiebreaker.current_amount
                
                # Mark as resolved
                tiebreaker.resolved = True
                
                db.session.commit()
                flash(f'Tiebreaker resolved with no bids. Player {player.name} randomly assigned to {team.name} for £{tiebreaker.current_amount}.', 'success')
            else:
                flash('Could not find the original bid. Tiebreaker not resolved.', 'error')
        else:
            flash('No active teams found in this tiebreaker.', 'error')
    
    return redirect(url_for('admin_bulk_tiebreakers'))

@app.route('/team/bulk_tiebreaker_stream/<int:tiebreaker_id>')
@login_required
def team_bulk_tiebreaker_stream(tiebreaker_id):
    """Server-Sent Events endpoint for real-time team bulk tiebreaker updates"""
    if current_user.is_admin or not current_user.team:
        return jsonify({'error': 'Unauthorized'}), 403
    
    tiebreaker = BulkBidTiebreaker.query.get_or_404(tiebreaker_id)
    
    # Check if the team is part of this tiebreaker
    team_tiebreaker = TeamBulkTiebreaker.query.filter_by(
        tiebreaker_id=tiebreaker_id,
        team_id=current_user.team.id,
        is_active=True
    ).first()
    
    if not team_tiebreaker:
        return jsonify({'error': 'Unauthorized'}), 403
    
    def generate():
        """Generator function for SSE stream"""
        last_data_hash = None
        
        while True:
            try:
                # Get current tiebreaker data
                current_tiebreaker = BulkBidTiebreaker.query.get(tiebreaker_id)
                if not current_tiebreaker:
                    break
                
                # If tiebreaker is resolved, send final update and break
                if current_tiebreaker.resolved:
                    # Find next tiebreaker for the team if exists
                    next_tiebreaker_id = None
                    next_team_tiebreaker = TeamBulkTiebreaker.query.join(
                        BulkBidTiebreaker, TeamBulkTiebreaker.tiebreaker_id == BulkBidTiebreaker.id
                    ).filter(
                        TeamBulkTiebreaker.team_id == current_user.team.id,
                        TeamBulkTiebreaker.is_active == True,
                        BulkBidTiebreaker.resolved == False,
                        BulkBidTiebreaker.id != tiebreaker_id
                    ).first()
                    
                    if next_team_tiebreaker:
                        next_tiebreaker_id = next_team_tiebreaker.tiebreaker_id
                    
                    final_data = json.dumps({
                        'resolved': True,
                        'winner_team_id': current_tiebreaker.winner_team_id,
                        'next_tiebreaker_id': next_tiebreaker_id,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    yield f"data: {final_data}\n\n"
                    break
                
                # Get all active teams in this tiebreaker
                team_tiebreakers = TeamBulkTiebreaker.query.filter_by(
                    tiebreaker_id=tiebreaker_id,
                    is_active=True
                ).all()
                
                active_teams = []
                for team_tb in team_tiebreakers:
                    team = Team.query.get(team_tb.team_id)
                    if team:
                        # Get the last bid for this team
                        last_bid = team_tb.last_bid if team_tb.last_bid else None
                        last_bid_time = team_tb.last_bid_time.strftime('%H:%M:%S') if team_tb.last_bid_time else None
                        
                        active_teams.append({
                            'team_id': team.id,
                            'team_name': team.name,
                            'last_bid': last_bid,
                            'last_bid_time': last_bid_time
                        })
                
                # Get current user's team balance
                team_balance = current_user.team.balance
                
                # Create current data package
                current_data = {
                    'resolved': False,
                    'current_amount': current_tiebreaker.current_amount,
                    'active_teams': active_teams,
                    'team_balance': team_balance,
                    'player_name': current_tiebreaker.player.name,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Create hash to detect changes
                import hashlib
                data_str = json.dumps(current_data, sort_keys=True)
                data_hash = hashlib.md5(data_str.encode()).hexdigest()
                
                # Only send update if data has changed
                if data_hash != last_data_hash:
                    last_data_hash = data_hash
                    yield f"data: {json.dumps(current_data)}\n\n"
                
                # Sleep for a short interval before checking again
                time.sleep(0.5)  # Check every 500ms for very fast updates
                
            except Exception as e:
                # Send error event
                error_data = json.dumps({'error': str(e)})
                yield f"data: {error_data}\n\n"
                break
    
    return Response(generate(), mimetype="text/event-stream", headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control'
    })

@app.route('/check_bulk_tiebreaker_status/<int:tiebreaker_id>')
@login_required
def check_bulk_tiebreaker_status(tiebreaker_id):
    tiebreaker = BulkBidTiebreaker.query.get_or_404(tiebreaker_id)
    
    # If the tiebreaker is resolved, check if there are other active tiebreakers for this team
    next_tiebreaker = None
    if tiebreaker.resolved and current_user.team:
        # Find next active tiebreaker for this team
        next_team_tiebreaker = TeamBulkTiebreaker.query.join(
            BulkBidTiebreaker, TeamBulkTiebreaker.tiebreaker_id == BulkBidTiebreaker.id
        ).filter(
            TeamBulkTiebreaker.team_id == current_user.team.id,
            TeamBulkTiebreaker.is_active == True,
            BulkBidTiebreaker.resolved == False,
            BulkBidTiebreaker.id != tiebreaker_id
        ).first()
        
        if next_team_tiebreaker:
            next_tiebreaker = next_team_tiebreaker.tiebreaker_id
    
    # Return tiebreaker status information
    return jsonify({
        'resolved': tiebreaker.resolved,
        'winner_team_id': tiebreaker.winner_team_id if tiebreaker.resolved else None,
        'next_tiebreaker_id': next_tiebreaker
    })

@app.route('/admin/delete_bulk_round/<int:round_id>', methods=['POST'])
@login_required
def admin_delete_bulk_round(round_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    bulk_round = BulkBidRound.query.get_or_404(round_id)
    
    if bulk_round.is_active:
        return jsonify({'error': 'Cannot delete an active bulk round. Please finalize it first.'}), 400
    
    try:
        released_players = 0
        refunded_amount = 0
        
        # Find all bids in this round
        bulk_bids = BulkBid.query.filter_by(round_id=round_id).all()
        
        # Group bids by player
        bid_players = {}
        for bid in bulk_bids:
            if bid.player_id not in bid_players:
                bid_players[bid.player_id] = []
            bid_players[bid.player_id].append(bid)
        
        # Find all players that were allocated through this round
        for player_id, bids in bid_players.items():
            player = Player.query.get(player_id)
            if player and player.team_id:
                # Check if any of the bids matches the player's team
                team_match = False
                for bid in bids:
                    if bid.team_id == player.team_id:
                        team_match = True
                        break
                
                if team_match:
                    # Found a player allocated through this round
                    # Refund the team
                    team = Team.query.get(player.team_id)
                    if team and player.acquisition_value:
                        team.balance += player.acquisition_value
                        refunded_amount += player.acquisition_value
                    
                    # Reset player's team and acquisition value
                    player.team_id = None
                    player.acquisition_value = None
                    released_players += 1
        
        # Delete all tiebreakers for this round
        tiebreakers = BulkBidTiebreaker.query.filter_by(bulk_round_id=round_id).all()
        for tiebreaker in tiebreakers:
            TeamBulkTiebreaker.query.filter_by(tiebreaker_id=tiebreaker.id).delete()
        BulkBidTiebreaker.query.filter_by(bulk_round_id=round_id).delete()
        
        # Delete all bids for this round
        BulkBid.query.filter_by(round_id=round_id).delete()
        
        # Delete the round
        db.session.delete(bulk_round)
        db.session.commit()
        
        return jsonify({
            'message': 'Bulk bid round deleted successfully',
            'released_players': released_players,
            'refunded_amount': refunded_amount
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete bulk round: {str(e)}'}), 500

@app.route('/team_squad/<int:team_id>')
@login_required
def team_squad(team_id):
    """
    View another team's squad details.
    All logged-in users can access this route to see other teams' players.
    """
    # Get the requested team
    team = Team.query.get_or_404(team_id)
    
    # Get team players with optional filters
    position_filter = request.args.get('position', 'all')
    sort_by = request.args.get('sort', 'rating')
    
    # Get the team's players
    players = Player.query.filter_by(team_id=team_id).all()
    
    # Apply position filter if needed
    if position_filter != 'all':
        players = [p for p in players if p.position == position_filter]
    
    # Apply sorting
    if sort_by == 'rating':
        players = sorted(players, key=lambda p: p.overall_rating or 0, reverse=True)
    elif sort_by == 'cost':
        players = sorted(players, key=lambda p: p.acquisition_value or 0, reverse=True)
    elif sort_by == 'position':
        players = sorted(players, key=lambda p: p.position)
    else:  # Default: sort by name
        players = sorted(players, key=lambda p: p.name)
    
    # Calculate position counts
    position_counts = {position: 0 for position in Config.POSITIONS}
    for player in players:
        if player.position in position_counts:
            position_counts[player.position] += 1
    
    # Calculate total team value
    total_team_value = sum(player.acquisition_value or 0 for player in players)
    
    return render_template('team_squad.html', 
                          team=team,
                          players=players, 
                          position_counts=position_counts,
                          total_team_value=total_team_value,
                          current_position=position_filter,
                          sort_by=sort_by,
                          config=Config)

@app.route('/team/compare')
@login_required
def team_compare():
    """
    Team Comparison Tool - Compare two teams side by side
    """
    # Get all teams for the selection dropdowns
    teams = Team.query.all()
    
    # Get team IDs from query parameters
    team1_id = request.args.get('team1', type=int)
    team2_id = request.args.get('team2', type=int)
    
    # Initialize comparison data
    team1 = None
    team2 = None
    team1_stats = None
    team2_stats = None
    team1_positions = {}
    team2_positions = {}
    h2h_results = []
    h2h_stats = {'team1_wins': 0, 'team2_wins': 0}
    
    if team1_id and team2_id and team1_id != team2_id:
        # Get the teams
        team1 = Team.query.get_or_404(team1_id)
        team2 = Team.query.get_or_404(team2_id)
        
        # Get players for both teams
        team1_players = Player.query.filter_by(team_id=team1_id).all()
        team2_players = Player.query.filter_by(team_id=team2_id).all()
        
        # Calculate team statistics
        def calculate_team_stats(team, players):
            total_spent = sum(p.acquisition_value or 0 for p in players)
            player_count = len(players)
            avg_rating = sum(p.overall_rating or 0 for p in players) / player_count if player_count > 0 else 0
            avg_player_cost = total_spent / player_count if player_count > 0 else 0
            
            return {
                'balance': team.balance,
                'total_spent': total_spent,
                'player_count': player_count,
                'avg_rating': avg_rating,
                'avg_player_cost': avg_player_cost
            }
        
        team1_stats = calculate_team_stats(team1, team1_players)
        team2_stats = calculate_team_stats(team2, team2_players)
        
        # Calculate position breakdown for both teams
        for position in Config.POSITIONS:
            # Team 1 position stats
            position_players1 = [p for p in team1_players if p.position == position]
            team1_positions[position] = {
                'count': len(position_players1),
                'avg_rating': sum(p.overall_rating or 0 for p in position_players1) / len(position_players1) if position_players1 else 0
            }
            
            # Team 2 position stats
            position_players2 = [p for p in team2_players if p.position == position]
            team2_positions[position] = {
                'count': len(position_players2),
                'avg_rating': sum(p.overall_rating or 0 for p in position_players2) / len(position_players2) if position_players2 else 0
            }
        
        # Get head-to-head auction results
        # Find players where both teams bid
        from sqlalchemy import and_, or_
        
        # Get all completed rounds
        completed_rounds = Round.query.filter_by(is_active=False).all()
        
        for round in completed_rounds:
            # Get bids from both teams in this round
            team1_bids = Bid.query.filter_by(team_id=team1_id, round_id=round.id).all()
            team2_bids = Bid.query.filter_by(team_id=team2_id, round_id=round.id).all()
            
            # Find common players both teams bid on
            team1_player_ids = {bid.player_id for bid in team1_bids}
            team2_player_ids = {bid.player_id for bid in team2_bids}
            common_player_ids = team1_player_ids.intersection(team2_player_ids)
            
            for player_id in common_player_ids:
                player = Player.query.get(player_id)
                if player and player.team_id in [team1_id, team2_id]:
                    # This player was won by one of these two teams
                    team1_bid = next((b for b in team1_bids if b.player_id == player_id), None)
                    team2_bid = next((b for b in team2_bids if b.player_id == player_id), None)
                    
                    winner_id = player.team_id
                    winner_name = team1.name if winner_id == team1_id else team2.name
                    winning_bid = team1_bid.amount if winner_id == team1_id else team2_bid.amount
                    
                    h2h_results.append({
                        'player_name': player.name,
                        'position': player.position,
                        'winner_id': winner_id,
                        'winner_name': winner_name,
                        'winning_bid': winning_bid
                    })
                    
                    if winner_id == team1_id:
                        h2h_stats['team1_wins'] += 1
                    else:
                        h2h_stats['team2_wins'] += 1
    
    return render_template('team_compare.html',
                          teams=teams,
                          team1=team1,
                          team2=team2,
                          team1_stats=team1_stats,
                          team2_stats=team2_stats,
                          team1_positions=team1_positions,
                          team2_positions=team2_positions,
                          h2h_results=h2h_results,
                          h2h_stats=h2h_stats,
                          config=Config)

@app.route('/teams')
@login_required
def all_teams():
    """
    List all teams with basic statistics for regular users.
    This allows users to navigate to specific team squads.
    """
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
        total_team_value = sum(player.acquisition_value or 0 for player in players)
        
        teams_data.append({
            'team': team,
            'total_players': len(players),
            'position_counts': position_counts,
            'total_team_value': total_team_value
        })
    
    return render_template('team_list.html', teams=teams_data, config=Config)

@app.route('/admin/player_selection')
@login_required
def admin_player_selection():
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    position_filter = request.args.get('position', 'all')
    search_query = request.args.get('q', '')
    eligibility_filter = request.args.get('eligibility', 'all')
    sort_by = request.args.get('sort', 'name')
    
    # Limit per_page to reasonable values
    per_page = max(10, min(per_page, 200))
    
    # Build base query
    query = Player.query
    
    # Apply position filter
    if position_filter != 'all':
        query = query.filter_by(position=position_filter)
    
    # Apply eligibility filter
    if eligibility_filter == 'eligible':
        query = query.filter_by(is_auction_eligible=True)
    elif eligibility_filter == 'not_eligible':
        query = query.filter_by(is_auction_eligible=False)
    
    # Apply search filter
    if search_query:
        query = query.filter(Player.name.ilike(f'%{search_query}%'))
    
    # Apply sorting
    if sort_by == 'rating':
        query = query.order_by(Player.overall_rating.desc().nulls_last())
    elif sort_by == 'position':
        query = query.order_by(Player.position, Player.name)
    elif sort_by == 'team':
        query = query.outerjoin(Team).order_by(Team.name.nulls_last(), Player.name)
    else:  # Default: name
        query = query.order_by(Player.name)
    
    # Paginate results
    players_pagination = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # Get position statistics efficiently using database aggregation
    from sqlalchemy import func
    position_stats = {}
    
    for position in Config.POSITIONS:
        # Get total and selected count for each position in one query
        stats = db.session.query(
            func.count(Player.id).label('total'),
            func.sum(func.cast(Player.is_auction_eligible, db.Integer)).label('selected')
        ).filter(Player.position == position).first()
        
        position_stats[position] = {
            'total': stats.total or 0,
            'selected': stats.selected or 0
        }
    
    # Get players by position for position tabs (limited for performance)
    players_by_position = {}
    for position in Config.POSITIONS:
        # Only load first 100 players per position for tabs
        players_in_position = Player.query.filter_by(position=position).order_by(Player.name).limit(100).all()
        players_by_position[position] = players_in_position
    
    # Get total counts for display
    total_players = Player.query.count()
    total_eligible = Player.query.filter_by(is_auction_eligible=True).count()
    
    return render_template('admin_player_selection.html',
                          players_pagination=players_pagination,
                          players_by_position=players_by_position,
                          position_stats=position_stats,
                          total_players=total_players,
                          total_eligible=total_eligible,
                          current_position=position_filter,
                          current_search=search_query,
                          current_eligibility=eligibility_filter,
                          current_sort=sort_by,
                          current_per_page=per_page,
                          config=Config)

@app.route('/admin/update_player_eligibility', methods=['POST'])
@login_required
def admin_update_player_eligibility():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.json
    player_id = data.get('player_id')
    is_eligible = data.get('is_eligible', False)
    
    if not player_id:
        return jsonify({'success': False, 'error': 'Player ID is required'}), 400
    
    try:
        player = Player.query.get_or_404(player_id)
        player.is_auction_eligible = is_eligible
        db.session.commit()
        
        message = f"Player {player.name} has been {'added to' if is_eligible else 'removed from'} auction list"
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/export_player_selection')
@login_required
def admin_export_player_selection():
    if not current_user.is_admin:
        flash('You do not have permission to access this feature', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Create a BytesIO object to store the Excel file
        output = io.BytesIO()
        
        # Create Excel writer object
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Prepare data for each position
            for position in Config.POSITIONS:
                players = Player.query.filter_by(position=position, is_auction_eligible=True).order_by(Player.overall_rating.desc()).all()
                
                # Convert to DataFrame
                data = []
                for player in players:
                    data.append({
                        'Name': player.name,
                        'Position': player.position,
                        'Rating': player.overall_rating,
                        'Nationality': player.nationality,
                        'Team': player.team_name
                    })
                
                if not data:
                    continue  # Skip if no players in this position
                
                df = pd.DataFrame(data)
                
                # Write to sheet
                df.to_excel(writer, sheet_name=position, index=False)
                
                # Auto-adjust columns width
                worksheet = writer.sheets[position]
                for i, col in enumerate(df.columns):
                    column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, column_width)
        
        # Prepare the response
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'player_selection_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    except Exception as e:
        flash(f'Error exporting player selection: {str(e)}', 'error')
        return redirect(url_for('admin_player_selection'))

@app.route('/admin/divide_position_groups', methods=['POST'])
@login_required
def admin_divide_position_groups():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    position = request.json.get('position')
    if not position or position not in Config.POSITIONS:
        return jsonify({'success': False, 'error': 'Invalid position'}), 400
    
    try:
        # Get all eligible players for this position
        players = Player.query.filter_by(position=position, is_auction_eligible=True).all()
        
        if not players:
            return jsonify({
                'success': False, 
                'error': f'No eligible players found for position {position}'
            }), 404
        
        # Sort players by overall rating (from highest to lowest)
        players.sort(key=lambda x: x.overall_rating if x.overall_rating else 0, reverse=True)
        
        # Divide players into two equally skilled groups
        group1 = []
        group2 = []
        
        # Snake draft pattern to ensure fairness
        for i, player in enumerate(players):
            if i % 4 in [0, 3]:  # 1st and 4th players go to group 1
                player.position_group = f"{position}-1"
                group1.append(player)
            else:  # 2nd and 3rd players go to group 2
                player.position_group = f"{position}-2"
                group2.append(player)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Divided {len(players)} {position} players into two groups',
            'group1_count': len(group1),
            'group2_count': len(group2)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/swap_position_group', methods=['POST'])
@login_required
def admin_swap_position_group():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    player_id = request.json.get('player_id')
    if not player_id:
        return jsonify({'success': False, 'error': 'Player ID is required'}), 400
    
    try:
        player = Player.query.get_or_404(player_id)
        
        if not player.position_group:
            return jsonify({
                'success': False, 
                'error': 'Player is not assigned to any position group'
            }), 400
        
        # Swap the group (e.g., from CF-1 to CF-2 or vice versa)
        position_base = player.position_group.split('-')[0]
        group_num = player.position_group.split('-')[1]
        
        # Toggle group number
        new_group_num = '2' if group_num == '1' else '1'
        player.position_group = f"{position_base}-{new_group_num}"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Player {player.name} moved to group {player.position_group}',
            'new_group': player.position_group
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/start_group_round', methods=['POST'])
@login_required
def admin_start_group_round():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    position_group = request.json.get('position_group')
    duration = request.json.get('duration', 300)  # Default to 5 minutes (300 seconds)
    max_bids_per_team = request.json.get('max_bids_per_team', 5)  # Default to 5 bids per team
    
    if not position_group:
        return jsonify({'error': 'Invalid position group'}), 400
    
    # Extract base position from position group (e.g., "CF" from "CF-1")
    position_parts = position_group.split('-')
    if len(position_parts) != 2 or position_parts[0] not in Config.POSITIONS:
        return jsonify({'error': 'Invalid position group format'}), 400
    
    position_base = position_parts[0]
    group_num = position_parts[1]
    
    try:
        duration = int(duration)
        if duration < 30:  # Minimum duration of 30 seconds
            return jsonify({'error': 'Duration must be at least 30 seconds'}), 400
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
    
    # Get auction settings
    settings = AuctionSettings.get_settings()
    
    # Check if we've reached the maximum number of rounds
    completed_rounds_count = Round.query.filter_by(is_active=False).count()
    if completed_rounds_count >= settings.max_rounds:
        return jsonify({
            'error': f'Maximum number of rounds ({settings.max_rounds}) has been reached. No more rounds can be started.'
        }), 400
    
    # Calculate remaining rounds (including this one)
    remaining_rounds = settings.max_rounds - completed_rounds_count
    
    # Check if teams have sufficient balance for remaining rounds
    min_required_balance = settings.min_balance_per_round * remaining_rounds
    
    # Get all approved teams
    teams = Team.query.filter(Team.user.has(is_approved=True)).all()
    
    # Track teams with insufficient balance
    insufficient_balance_teams = []
    for team in teams:
        if team.balance < min_required_balance:
            insufficient_balance_teams.append({
                'name': team.name,
                'balance': team.balance, 
                'required': min_required_balance
            })
    
    if insufficient_balance_teams:
        return jsonify({
            'error': 'Some teams have insufficient balance for the remaining rounds',
            'teams': insufficient_balance_teams,
            'min_required_balance': min_required_balance,
            'remaining_rounds': remaining_rounds
        }), 400
    
    # Create new round with timer
    round = Round(
        position=position_group,  # Use full position group (e.g., "CF-1")
        start_time=datetime.utcnow(),
        duration=duration,
        max_bids_per_team=max_bids_per_team
    )
    db.session.add(round)
    db.session.flush()  # Get the round ID
    
    # Add players of the specified position group to the round
    players = Player.query.filter_by(position_group=position_group, team_id=None, is_auction_eligible=True).all()
    for player in players:
        player.round_id = round.id
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'round_id': round.id,
        'message': f'Round for position group {position_group} started successfully',
        'remaining_rounds': remaining_rounds - 1  # Subtract 1 to account for current round
    })

@app.route('/admin/position_group_players')
@login_required
def admin_position_group_players():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    position = request.args.get('position')
    if not position or position not in Config.POSITIONS:
        return jsonify({'success': False, 'error': 'Invalid position'}), 400
    
    try:
        # Get all eligible players for this position
        players = Player.query.filter_by(position=position, is_auction_eligible=True).all()
        
        player_data = []
        for player in players:
            player_data.append({
                'id': player.id,
                'name': player.name,
                'position': player.position,
                'position_group': player.position_group,
                'overall_rating': player.overall_rating,
                'team_name': player.team_name
            })
        
        return jsonify({
            'success': True,
            'players': player_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/position_groups')
@login_required
def admin_position_groups():
    if not current_user.is_admin:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('admin_position_groups.html', config=Config)

@app.route('/admin/rounds_update')
@login_required
def admin_rounds_update():
    if not current_user.is_admin or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get all relevant data for round management
    teams = Team.query.all()
    active_rounds = Round.query.filter_by(is_active=True).all()
    rounds = Round.query.all()
    active_tiebreakers = Tiebreaker.query.filter_by(resolved=False).all()
    
    # Render the active rounds HTML partial
    active_rounds_html = render_template('partials/active_rounds.html', 
                                        active_rounds=active_rounds)
    
    # Render tiebreakers HTML if there are any active tiebreakers
    tiebreakers_html = None
    if active_tiebreakers:
        tiebreakers_html = render_template('partials/active_tiebreakers.html', 
                                          active_tiebreakers=active_tiebreakers)
    
    completed_rounds_html = render_template('partials/completed_rounds.html', 
                                           rounds=rounds)
    
    # Return JSON with the HTML snippets for dynamic updates
    return jsonify({
        'active_count': len(active_rounds),
        'total_count': len(rounds),
        'tiebreakers_count': len(active_tiebreakers),
        'activeRoundsHtml': active_rounds_html,
        'tiebreakersHtml': tiebreakers_html,
        'completedRoundsHtml': completed_rounds_html
    })

@app.route('/team_dashboard_update')
@login_required
def team_dashboard_update():
    """Check for dashboard updates including new rounds and bulk rounds for team users"""
    if current_user.is_admin:
        return jsonify({'error': 'This endpoint is for team users only'}), 403
    
    # Get active rounds
    active_rounds = Round.query.filter_by(is_active=True).all()
    
    # Get team tiebreakers
    team_tiebreakers = []
    team_bulk_tiebreakers = []
    if current_user.team:
        team_tiebreakers = TeamTiebreaker.query.join(Tiebreaker).filter(
            TeamTiebreaker.team_id == current_user.team.id,
            Tiebreaker.resolved == False
        ).all()
        
        team_bulk_tiebreakers = TeamBulkTiebreaker.query.join(
            BulkBidTiebreaker, TeamBulkTiebreaker.tiebreaker_id == BulkBidTiebreaker.id
        ).filter(
            TeamBulkTiebreaker.team_id == current_user.team.id,
            TeamBulkTiebreaker.is_active == True,
            BulkBidTiebreaker.resolved == False
        ).all()
    
    # Get active bulk round
    active_bulk_round = BulkBidRound.query.filter_by(is_active=True).first()
    
    # Check if any rounds have just started (within last 10 seconds)
    just_started_rounds = []
    for round in active_rounds:
        if round.start_time:
            time_since_start = (datetime.utcnow() - round.start_time).total_seconds()
            if time_since_start <= 10:  # Round started within last 10 seconds
                just_started_rounds.append({
                    'id': round.id,
                    'position': round.position,
                    'duration': round.duration,
                    'max_bids': round.max_bids_per_team
                })
    
    # Check if bulk round has just started or ended
    bulk_round_status_changed = False
    bulk_round_just_started = False
    bulk_round_just_ended = False
    
    if active_bulk_round:
        # Check if bulk round just started (within last 10 seconds)
        if active_bulk_round.start_time:
            time_since_start = (datetime.utcnow() - active_bulk_round.start_time).total_seconds()
            if time_since_start <= 10:
                bulk_round_just_started = True
                bulk_round_status_changed = True
    else:
        # Check if a bulk round just ended by looking for recently completed ones
        # Since BulkBidRound doesn't have end_time, check for recently deactivated rounds
        recently_completed_bulk_round = BulkBidRound.query.filter(
            BulkBidRound.is_active == False,
            BulkBidRound.start_time != None
        ).order_by(BulkBidRound.start_time.desc()).first()
        
        if recently_completed_bulk_round and recently_completed_bulk_round.start_time:
            # Calculate end time based on start_time + duration
            estimated_end_time = recently_completed_bulk_round.start_time + timedelta(seconds=recently_completed_bulk_round.duration)
            time_since_end = (datetime.utcnow() - estimated_end_time).total_seconds()
            if time_since_end <= 10:
                bulk_round_just_ended = True
                bulk_round_status_changed = True
    
    # Prepare bulk round data for client
    bulk_round_data = None
    if active_bulk_round:
        bulk_round_data = {
            'id': active_bulk_round.id,
            'base_price': active_bulk_round.base_price,
            'start_time': active_bulk_round.start_time.strftime('%Y-%m-%d %H:%M:%S') if active_bulk_round.start_time else None,
            'duration': active_bulk_round.duration if hasattr(active_bulk_round, 'duration') else None,
            'just_started': bulk_round_just_started
        }
    
    # Determine if page needs refresh
    needs_refresh = (
        len(just_started_rounds) > 0 or 
        len(team_tiebreakers) > 0 or 
        len(team_bulk_tiebreakers) > 0 or 
        bulk_round_status_changed
    )
    
    return jsonify({
        'active_rounds_count': len(active_rounds),
        'team_tiebreakers_count': len(team_tiebreakers),
        'team_bulk_tiebreakers_count': len(team_bulk_tiebreakers),
        'has_active_bulk_round': active_bulk_round is not None,
        'active_bulk_round': bulk_round_data,
        'bulk_round_just_started': bulk_round_just_started,
        'bulk_round_just_ended': bulk_round_just_ended,
        'bulk_round_status_changed': bulk_round_status_changed,
        'just_started_rounds': just_started_rounds,
        'needs_refresh': needs_refresh
    })

@app.route('/admin/dashboard_update')
@login_required
def admin_dashboard_update():
    if not current_user.is_admin or not request.headers.get('X-Requested-With') == 'XMLHttpRequest': 
        return jsonify({'error': 'Unauthorized'}), 403

    # Get all teams
    teams = Team.query.all()

    # Get pending users (users that are not approved and not admins)
    pending_users = User.query.filter(User.is_approved == False, User.is_admin == False).all()

    # Get pending password reset requests
    pending_resets = PasswordResetRequest.query.filter_by(status='pending').all()

    # Get active bulk bid round if any
    active_bulk_round = BulkBidRound.query.filter_by(is_active=True).first()

    # Get player selection stats
    total_player_count = Player.query.count()
    eligible_player_count = Player.query.filter_by(is_auction_eligible=True).count()
    
    # Get active rounds count
    active_rounds_count = Round.query.filter_by(is_active=True).count()

    # Prepare bulk round data if active
    bulk_round_data = None
    if active_bulk_round:
        bulk_round_data = {
            'id': active_bulk_round.id,
            'base_price': active_bulk_round.base_price,
            'start_time': active_bulk_round.start_time.strftime('%Y-%m-%d %H:%M:%S')
        }

    # Prepare team data for updates
    teams_data = {}
    for team in teams:
        teams_data[team.id] = {
            'balance': team.balance,
            'player_count': len(team.players)
        }

    return jsonify({
        'pending_users': len(pending_users),
        'pending_resets': len(pending_resets),
        'total_player_count': total_player_count,
        'eligible_player_count': eligible_player_count,
        'active_rounds_count': active_rounds_count,
        'has_active_bulk_round': active_bulk_round is not None,
        'active_bulk_round': bulk_round_data,
        'teams_data': teams_data
    })

# Team Matches routes (read-only for team users)
@app.route('/team/matches')
@login_required
def team_matches():
    """Display a list of matches for team users (read-only)"""
    # Only allow team users to access
    if current_user.is_admin:
        return redirect(url_for('team_management.match_list'))
    
    # Check if user has a team
    if not current_user.team:
        flash('You need to have a team to view matches.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Get team's completed matches (where team is either home or away)
    completed_matches = Match.query.filter(
        ((Match.home_team_id == current_user.team.id) | (Match.away_team_id == current_user.team.id)) &
        (Match.is_completed == True)
    ).order_by(Match.match_date.desc()).all()
    
    # Get team's upcoming matches (where team is either home or away)
    upcoming_matches = Match.query.filter(
        ((Match.home_team_id == current_user.team.id) | (Match.away_team_id == current_user.team.id)) &
        (Match.is_completed == False)
    ).order_by(Match.match_date.asc()).all()
    
    return render_template(
        'team_matches.html',
        completed_matches=completed_matches,
        upcoming_matches=upcoming_matches
    )

@app.route('/team/match/<int:match_id>')
@login_required
def team_match_detail(match_id):
    """Display match details for team users (read-only)"""
    # Only allow team users to access
    if current_user.is_admin:
        return redirect(url_for('team_management.match_detail', id=match_id))
    
    # Check if user has a team
    if not current_user.team:
        flash('You need to have a team to view match details.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Get the match
    match = Match.query.get_or_404(match_id)
    
    # Make sure the match belongs to the team
    if match.home_team_id != current_user.team.id and match.away_team_id != current_user.team.id:
        flash('You do not have permission to view this match.', 'danger')
        return redirect(url_for('team_matches'))
    
    # Get player matchups for this match
    player_matchups = PlayerMatchup.query.filter_by(match_id=match_id).all()
    
    return render_template(
        'team_match_detail.html',
        match=match,
        player_matchups=player_matchups
    )

@app.route('/admin/database', methods=['GET'])
@login_required
def admin_database():
    if not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    player_count = Player.query.count()
    
    # Get player count by position for a quick summary
    position_counts = {}
    if player_count > 0:
        position_results = db.session.query(
            Player.position, 
            func.count(Player.id)
        ).group_by(Player.position).all()
        
        for position, count in position_results:
            position_counts[position] = count
    
    # Check for SQLite database file
    sqlite_paths = [
        'efootball_real.db',
        '/opt/render/project/src/efootball_real.db',
        '/opt/render/project/src/data/efootball_real.db'
    ]
    
    db_exists = False
    db_path = None
    
    for path in sqlite_paths:
        if os.path.exists(path):
            db_exists = True
            db_path = path
            break
    
    # If SQLite DB exists, get the count of players in it
    sqlite_player_count = 0
    if db_exists:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM players_all")
            sqlite_player_count = cursor.fetchone()[0]
            conn.close()
        except:
            # If there's an error, we'll just show 0
            pass
    
    return render_template('admin_database.html', 
                          player_count=player_count,
                          position_counts=position_counts,
                          db_exists=db_exists,
                          db_path=db_path,
                          sqlite_player_count=sqlite_player_count)

@app.route('/admin/import_players', methods=['POST'])
@login_required
def admin_import_players():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check for SQLite database file
    sqlite_paths = [
        'efootball_real.db',
        '/opt/render/project/src/efootball_real.db',
        '/opt/render/project/src/data/efootball_real.db'
    ]
    
    db_path = None
    for path in sqlite_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        return jsonify({'error': 'SQLite database not found'})
    
    try:
        # Get current player count to determine if we're doing a fresh import or adding players
        current_player_count = Player.query.count()
        operation_type = "Fresh import" if current_player_count == 0 else "Adding players"
        
        # Connect to SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the 'players_all' table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players_all'")
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': "'players_all' table not found in the database"})
        
        # Count how many players we're going to import
        cursor.execute("SELECT COUNT(*) FROM players_all")
        total_players = cursor.fetchone()[0]
        
        # Get player data
        cursor.execute("""
            SELECT player_name, position, team_name, nationality,
                offensive_awareness, ball_control, dribbling, tight_possession,
                low_pass, lofted_pass, finishing, heading, set_piece_taking,
                curl, speed, acceleration, kicking_power, jumping,
                physical_contact, balance, stamina, defensive_awareness,
                tackling, aggression, defensive_engagement, gk_awareness,
                gk_catching, gk_parrying, gk_reflexes, gk_reach,
                overall_rating, playing_style, player_id
            FROM players_all
        """)
        
        player_count = 0
        batch_size = 100
        batch = []
        
        for row in cursor.fetchall():
            # Skip if this player_id already exists in the database
            existing_player = Player.query.filter_by(player_id=row[32]).first()
            if existing_player:
                continue
                
            player = Player(
                name=row[0],
                position=row[1],
                team_name=row[2],
                nationality=row[3],
                offensive_awareness=row[4],
                ball_control=row[5],
                dribbling=row[6],
                tight_possession=row[7],
                low_pass=row[8],
                lofted_pass=row[9],
                finishing=row[10],
                heading=row[11],
                set_piece_taking=row[12],
                curl=row[13],
                speed=row[14],
                acceleration=row[15],
                kicking_power=row[16],
                jumping=row[17],
                physical_contact=row[18],
                balance=row[19],
                stamina=row[20],
                defensive_awareness=row[21],
                tackling=row[22],
                aggression=row[23],
                defensive_engagement=row[24],
                gk_awareness=row[25],
                gk_catching=row[26],
                gk_parrying=row[27],
                gk_reflexes=row[28],
                gk_reach=row[29],
                overall_rating=row[30],
                playing_style=row[31],
                player_id=row[32]
            )
            batch.append(player)
            player_count += 1
            
            # Process in batches to avoid memory issues
            if len(batch) >= batch_size:
                db.session.add_all(batch)
                db.session.commit()
                batch = []
        
        # Add remaining players
        if batch:
            db.session.add_all(batch)
            db.session.commit()
        
        conn.close()
        
        # Determine success message based on how many players were added
        if player_count == 0:
            if current_player_count > 0:
                message = f"No new players were imported. All {total_players} players from the SQLite database already exist in the system."
            else:
                message = "No players were imported. The SQLite database may not contain valid player data."
        else:
            message = f"{operation_type}: Successfully imported {player_count} players out of {total_players} in the SQLite database."
        
        return jsonify({'success': message, 'count': player_count, 'total_available': total_players})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error importing players: {str(e)}'})

@app.route('/admin/upload_sqlite', methods=['POST'])
@login_required
def admin_upload_sqlite():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'sqlite_db' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    
    file = request.files['sqlite_db']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    if not file.filename.endswith('.db'):
        return jsonify({'error': 'File must be a SQLite database (.db)'})
    
    # Determine where to save the file
    render_data_dir = '/opt/render/project/src/data'
    if os.path.exists(render_data_dir):
        target_path = os.path.join(render_data_dir, 'efootball_real.db')
    else:
        target_path = 'efootball_real.db'
    
    try:
        file.save(target_path)
        return jsonify({'success': f'Database uploaded successfully to {target_path}'})
    except Exception as e:
        return jsonify({'error': f'Error saving file: {str(e)}'})

@app.route('/admin/delete_all_players', methods=['POST'])
@login_required
def admin_delete_all_players():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Check for active rounds that might reference players
        active_rounds = Round.query.filter_by(is_active=True).all()
        if active_rounds:
            return jsonify({'error': 'Cannot delete players while there are active rounds. Please finalize or delete all active rounds first.'})
        
        # Check for active bulk rounds
        active_bulk_rounds = BulkBidRound.query.filter_by(is_active=True).all()
        if active_bulk_rounds:
            return jsonify({'error': 'Cannot delete players while there are active bulk rounds. Please finalize or delete all active bulk rounds first.'})
        
        # Count players before deletion
        player_count = Player.query.count()
        
        # Delete all related bids first to avoid foreign key constraints
        Bid.query.delete()
        db.session.commit()
        
        # Delete tiebreakers that reference players
        TeamTiebreaker.query.delete()
        db.session.commit()
        
        Tiebreaker.query.delete()
        db.session.commit()
        
        # Delete bulk bids and tiebreakers
        TeamBulkTiebreaker.query.delete()
        db.session.commit()
        
        BulkBidTiebreaker.query.delete()
        db.session.commit()
        
        BulkBid.query.delete()
        db.session.commit()
        
        # Delete starred players references
        StarredPlayer.query.delete()
        db.session.commit()
        
        # Finally delete all players
        Player.query.delete()
        db.session.commit()
        
        return jsonify({'success': f'Successfully deleted {player_count} players and all related bids and tiebreakers'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error deleting players: {str(e)}'})

@app.route('/admin/create_backup', methods=['POST'])
@login_required
def admin_create_backup():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Create a JSON serializable backup of the database
        backup_data = {
            'metadata': {
                'created_at': datetime.utcnow().isoformat(),
                'version': '1.0',
                'app_name': 'Football Auction'
            },
            'data': {}
        }
        
        # Back up Players
        players_data = []
        for player in Player.query.all():
            player_dict = {column.name: getattr(player, column.name) for column in player.__table__.columns}
            # Convert datetime objects to ISO strings for JSON serialization
            for key, value in player_dict.items():
                if isinstance(value, datetime):
                    player_dict[key] = value.isoformat()
            players_data.append(player_dict)
        backup_data['data']['players'] = players_data
        
        # Back up Teams
        teams_data = []
        for team in Team.query.all():
            team_dict = {column.name: getattr(team, column.name) for column in team.__table__.columns}
            for key, value in team_dict.items():
                if isinstance(value, datetime):
                    team_dict[key] = value.isoformat()
            teams_data.append(team_dict)
        backup_data['data']['teams'] = teams_data
        
        # Back up Users
        users_data = []
        for user in User.query.all():
            user_dict = {column.name: getattr(user, column.name) for column in user.__table__.columns}
            for key, value in user_dict.items():
                if isinstance(value, datetime):
                    user_dict[key] = value.isoformat()
            users_data.append(user_dict)
        backup_data['data']['users'] = users_data
        
        # Back up other essential tables
        # Rounds
        rounds_data = []
        for round in Round.query.all():
            round_dict = {column.name: getattr(round, column.name) for column in round.__table__.columns}
            for key, value in round_dict.items():
                if isinstance(value, datetime):
                    round_dict[key] = value.isoformat()
            rounds_data.append(round_dict)
        backup_data['data']['rounds'] = rounds_data
        
        # Bids
        bids_data = []
        for bid in Bid.query.all():
            bid_dict = {column.name: getattr(bid, column.name) for column in bid.__table__.columns}
            for key, value in bid_dict.items():
                if isinstance(value, datetime):
                    bid_dict[key] = value.isoformat()
            bids_data.append(bid_dict)
        backup_data['data']['bids'] = bids_data
        
        # Create response with the backup file
        response = make_response(json.dumps(backup_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=efootball_auction_backup_{datetime.utcnow().strftime("%Y%m%d")}.json'
        return response
    
    except Exception as e:
        return jsonify({'error': f'Error creating backup: {str(e)}'}), 500

@app.route('/admin/restore_backup', methods=['POST'])
@login_required
def admin_restore_backup():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'backup_file' not in request.files:
        return jsonify({'error': 'No backup file provided'})
    
    file = request.files['backup_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    if not file.filename.endswith('.json'):
        return jsonify({'error': 'File must be a JSON backup'})
    
    try:
        # Read and parse JSON data
        backup_data = json.loads(file.read().decode('utf-8'))
        
        # Validate backup format
        if 'metadata' not in backup_data or 'data' not in backup_data:
            return jsonify({'error': 'Invalid backup format'})
        
        # Check for active rounds/operations
        active_rounds = Round.query.filter_by(is_active=True).all()
        if active_rounds:
            return jsonify({'error': 'Cannot restore while there are active rounds. Please finalize or delete all active rounds first.'})
        
        active_bulk_rounds = BulkBidRound.query.filter_by(is_active=True).all()
        if active_bulk_rounds:
            return jsonify({'error': 'Cannot restore while there are active bulk rounds. Please finalize or delete all active bulk rounds first.'})
        
        # Begin the restore process in a transaction
        try:
            # Clear existing data (in proper order to avoid foreign key constraints)
            # Note: This is a destructive operation!
            Bid.query.delete()
            db.session.commit()
            
            TeamTiebreaker.query.delete()
            db.session.commit()
            
            Tiebreaker.query.delete()
            db.session.commit()
            
            TeamBulkTiebreaker.query.delete()
            db.session.commit()
            
            BulkBidTiebreaker.query.delete()
            db.session.commit()
            
            BulkBid.query.delete()
            db.session.commit()
            
            StarredPlayer.query.delete()
            db.session.commit()
            
            Player.query.delete()
            db.session.commit()
            
            Round.query.delete()
            db.session.commit()
            
            # Preserve the admin user for safety
            admin_user = User.query.filter_by(is_admin=True).first()
            admin_id = admin_user.id if admin_user else None
            
            # Now restore the data
            # Restore Players
            if 'players' in backup_data['data']:
                for player_data in backup_data['data']['players']:
                    player = Player()
                    for key, value in player_data.items():
                        if key != 'id':  # Don't restore IDs directly
                            # Handle datetime conversion if needed
                            if key.endswith('_at') and value:
                                try:
                                    value = datetime.fromisoformat(value)
                                except:
                                    pass
                            setattr(player, key, value)
                    db.session.add(player)
                db.session.commit()
            
            # Restore Teams
            if 'teams' in backup_data['data']:
                for team_data in backup_data['data']['teams']:
                    # Skip if team already exists (by ID)
                    if Team.query.get(team_data.get('id')):
                        continue
                    
                    team = Team()
                    for key, value in team_data.items():
                        if key != 'id' or not Team.query.get(value):  # Only set ID if not exists
                            if key.endswith('_at') and value:
                                try:
                                    value = datetime.fromisoformat(value)
                                except:
                                    pass
                            setattr(team, key, value)
                    db.session.add(team)
                db.session.commit()
            
            # Restore Users (except existing admin)
            if 'users' in backup_data['data']:
                for user_data in backup_data['data']['users']:
                    # Skip if this is the admin user we want to preserve
                    if admin_id and user_data.get('id') == admin_id:
                        continue
                    
                    # Skip if user already exists
                    if User.query.get(user_data.get('id')):
                        continue
                    
                    user = User()
                    for key, value in user_data.items():
                        if key != 'id' or not User.query.get(value):
                            if key.endswith('_at') and value:
                                try:
                                    value = datetime.fromisoformat(value)
                                except:
                                    pass
                            setattr(user, key, value)
                    db.session.add(user)
                db.session.commit()
            
            # Restore Rounds
            if 'rounds' in backup_data['data']:
                for round_data in backup_data['data']['rounds']:
                    round = Round()
                    for key, value in round_data.items():
                        if key != 'id':
                            if key.endswith('_at') and value:
                                try:
                                    value = datetime.fromisoformat(value)
                                except:
                                    pass
                            setattr(round, key, value)
                    db.session.add(round)
                db.session.commit()
            
            # Restore Bids
            if 'bids' in backup_data['data']:
                for bid_data in backup_data['data']['bids']:
                    bid = Bid()
                    for key, value in bid_data.items():
                        if key != 'id':
                            if key.endswith('_at') and value:
                                try:
                                    value = datetime.fromisoformat(value)
                                except:
                                    pass
                            setattr(bid, key, value)
                    db.session.add(bid)
                db.session.commit()
            
            return jsonify({'success': 'Database restored successfully from backup'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Error during restore process: {str(e)}'})
    
    except Exception as e:
        return jsonify({'error': f'Error processing backup file: {str(e)}'})

@app.route('/admin/filter_players', methods=['POST'])
@login_required
def admin_filter_players():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    position = data.get('position')
    min_rating = data.get('min_rating')
    max_rating = data.get('max_rating')
    
    # Build query with filters
    query = Player.query
    
    if position:
        query = query.filter(Player.position == position)
    
    if min_rating:
        query = query.filter(Player.overall_rating >= int(min_rating))
    
    if max_rating:
        query = query.filter(Player.overall_rating <= int(max_rating))
    
    # Execute query and format results
    try:
        players = query.all()
        result = []
        
        for player in players:
            player_data = {
                'id': player.id,
                'name': player.name,
                'position': player.position,
                'team_name': player.team_name,
                'overall_rating': player.overall_rating
            }
            result.append(player_data)
        
        return jsonify({
            'players': result,
            'count': len(result)
        })
    
    except Exception as e:
        return jsonify({'error': f'Error filtering players: {str(e)}'}), 500

@app.route('/admin/export_filtered_players', methods=['POST'])
@login_required
def admin_export_filtered_players():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    position = data.get('position')
    min_rating = data.get('min_rating')
    max_rating = data.get('max_rating')
    
    # Build query with filters
    query = Player.query
    
    if position:
        query = query.filter(Player.position == position)
    
    if min_rating:
        query = query.filter(Player.overall_rating >= int(min_rating))
    
    if max_rating:
        query = query.filter(Player.overall_rating <= int(max_rating))
    
    try:
        # Get players and create a dataframe
        players = query.all()
        
        # Create in-memory Excel file
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Convert player data to DataFrame
            players_data = []
            for player in players:
                player_dict = {
                    'ID': player.id,
                    'Name': player.name,
                    'Position': player.position,
                    'Team': player.team_name,
                    'Nationality': player.nationality,
                    'Rating': player.overall_rating,
                    'Playing Style': player.playing_style,
                    'Player ID': player.player_id,
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
                }
                # Add goalkeeper stats if applicable
                if player.position == 'GK':
                    player_dict.update({
                        'GK Awareness': player.gk_awareness,
                        'GK Catching': player.gk_catching,
                        'GK Parrying': player.gk_parrying,
                        'GK Reflexes': player.gk_reflexes,
                        'GK Reach': player.gk_reach
                    })
                
                players_data.append(player_dict)
            
            # Create DataFrame and write to Excel
            df = pd.DataFrame(players_data)
            df.to_excel(writer, sheet_name='Players', index=False)
            
            # Get the worksheet and set column widths
            worksheet = writer.sheets['Players']
            for i, col in enumerate(df.columns):
                # Set column width based on maximum length of column data
                max_len = max([
                    len(str(col)),  # Column header
                    df[col].astype(str).str.len().max()  # Column data
                ]) + 2  # Add padding
                worksheet.set_column(i, i, max_len)
        
        # Reset file pointer
        output.seek(0)
        
        # Create response
        filter_text = f"_{position}" if position else ""
        rating_text = f"_rating_{min_rating or '0'}-{max_rating or '99'}" if min_rating or max_rating else ""
        filename = f"players{filter_text}{rating_text}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        return jsonify({'error': f'Error exporting players: {str(e)}'}), 500

@app.route('/admin/delete_filtered_players', methods=['POST'])
@login_required
def admin_delete_filtered_players():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    position = data.get('position')
    min_rating = data.get('min_rating')
    max_rating = data.get('max_rating')
    
    # Require at least one filter for safety
    if not position and not min_rating and not max_rating:
        return jsonify({'error': 'At least one filter must be specified for deletion'})
    
    # Build query with filters
    query = Player.query
    
    if position:
        query = query.filter(Player.position == position)
    
    if min_rating:
        query = query.filter(Player.overall_rating >= int(min_rating))
    
    if max_rating:
        query = query.filter(Player.overall_rating <= int(max_rating))
    
    try:
        # Check for active rounds first
        active_rounds = Round.query.filter_by(is_active=True).all()
        if active_rounds:
            return jsonify({'error': 'Cannot delete players while there are active rounds. Please finalize or delete all active rounds first.'})
        
        # Check for active bulk rounds
        active_bulk_rounds = BulkBidRound.query.filter_by(is_active=True).all()
        if active_bulk_rounds:
            return jsonify({'error': 'Cannot delete players while there are active bulk rounds. Please finalize or delete all active bulk rounds first.'})
        
        # Get players to delete
        players = query.all()
        player_count = len(players)
        
        if player_count == 0:
            return jsonify({'success': 'No players match the filter criteria'})
        
        # Get player IDs
        player_ids = [player.id for player in players]
        
        # Delete related data first (to avoid foreign key constraint errors)
        Bid.query.filter(Bid.player_id.in_(player_ids)).delete(synchronize_session=False)
        db.session.commit()
        
        StarredPlayer.query.filter(StarredPlayer.player_id.in_(player_ids)).delete(synchronize_session=False)
        db.session.commit()
        
        # Find tiebreakers related to these players
        tiebreakers = Tiebreaker.query.filter(Tiebreaker.player_id.in_(player_ids)).all()
        tiebreaker_ids = [t.id for t in tiebreakers]
        
        if tiebreaker_ids:
            TeamTiebreaker.query.filter(TeamTiebreaker.tiebreaker_id.in_(tiebreaker_ids)).delete(synchronize_session=False)
            db.session.commit()
            
            Tiebreaker.query.filter(Tiebreaker.id.in_(tiebreaker_ids)).delete(synchronize_session=False)
            db.session.commit()
        
        # Find bulk tiebreakers related to these players
        bulk_tiebreakers = BulkBidTiebreaker.query.filter(BulkBidTiebreaker.player_id.in_(player_ids)).all()
        bulk_tiebreaker_ids = [t.id for t in bulk_tiebreakers]
        
        if bulk_tiebreaker_ids:
            TeamBulkTiebreaker.query.filter(TeamBulkTiebreaker.tiebreaker_id.in_(bulk_tiebreaker_ids)).delete(synchronize_session=False)
            db.session.commit()
            
            BulkBidTiebreaker.query.filter(BulkBidTiebreaker.id.in_(bulk_tiebreaker_ids)).delete(synchronize_session=False)
            db.session.commit()
        
        # Delete bulk bids
        BulkBid.query.filter(BulkBid.player_id.in_(player_ids)).delete(synchronize_session=False)
        db.session.commit()
        
        # Finally delete the players
        query.delete(synchronize_session=False)
        db.session.commit()
        
        return jsonify({'success': f'Successfully deleted {player_count} players and related data'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error deleting players: {str(e)}'}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 
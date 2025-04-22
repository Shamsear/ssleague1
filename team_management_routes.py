from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models import db, Team, TeamMember, Category, Match, PlayerMatchup, TeamStats, PlayerStats
from datetime import datetime
from sqlalchemy import func, desc, or_

team_management = Blueprint('team_management', __name__)

# Dashboard route
@team_management.route('/dashboard')
@login_required
def dashboard():
    # Get all teams
    teams = Team.query.all()
    
    # Get recent matches (last 6)
    recent_matches = Match.query.order_by(Match.created_at.desc()).limit(6).all()
    
    return render_template('team_management/dashboard.html',
                          teams=teams,
                          recent_matches=recent_matches)

# Helper function to get the match points based on player categories
def calculate_match_points(home_category, away_category, result='win'):
    # If names are passed instead of Category objects, get the actual Category objects
    if isinstance(home_category, str):
        home_category_obj = Category.query.filter(func.lower(Category.name) == home_category).first()
        if not home_category_obj:
            # Default points if category not found
            return 3 if result == 'win' else 1 if result == 'draw' else 0
    else:
        home_category_obj = home_category
        
    if isinstance(away_category, str):
        away_category_obj = Category.query.filter(func.lower(Category.name) == away_category).first()
        if not away_category_obj:
            # Default points if category not found
            return 3 if result == 'win' else 1 if result == 'draw' else 0
    else:
        away_category_obj = away_category
    
    # Now calculate points using the Category objects
    difference = abs(home_category_obj.priority - away_category_obj.priority)
    
    if result == 'win':
        if difference == 0:
            return home_category_obj.points_same_category
        elif difference == 1:
            return home_category_obj.points_one_level_diff
        elif difference == 2:
            return home_category_obj.points_two_level_diff
        else:
            return home_category_obj.points_three_level_diff
    elif result == 'draw':
        if difference == 0:
            return home_category_obj.draw_same_category
        elif difference == 1:
            return home_category_obj.draw_one_level_diff
        elif difference == 2:
            return home_category_obj.draw_two_level_diff
        else:
            return home_category_obj.draw_three_level_diff
    elif result == 'loss':
        if difference == 0:
            return home_category_obj.loss_same_category
        elif difference == 1:
            return home_category_obj.loss_one_level_diff
        elif difference == 2:
            return home_category_obj.loss_two_level_diff
        else:
            return home_category_obj.loss_three_level_diff
    else:
        return 0

# Categories routes
@team_management.route('/categories')
@login_required
def category_list():
    categories = Category.query.order_by(Category.priority).all()
    return render_template('team_management/categories.html', categories=categories)

@team_management.route('/categories/new', methods=['GET', 'POST'])
@login_required
def new_category():
    if not current_user.is_admin:
        abort(403)
        
    if request.method == 'POST':
        name = request.form.get('name')
        color = request.form.get('color')
        priority = request.form.get('priority')
        points_same = request.form.get('points_same_category', 8, type=int)
        points_one = request.form.get('points_one_level_diff', 7, type=int)
        points_two = request.form.get('points_two_level_diff', 6, type=int)
        points_three = request.form.get('points_three_level_diff', 5, type=int)
        
        # Get draw points
        draw_same = request.form.get('draw_same_category', 4, type=int)
        draw_one = request.form.get('draw_one_level_diff', 3, type=int)
        draw_two = request.form.get('draw_two_level_diff', 3, type=int)
        draw_three = request.form.get('draw_three_level_diff', 2, type=int)
        
        # Get loss points
        loss_same = request.form.get('loss_same_category', 1, type=int)
        loss_one = request.form.get('loss_one_level_diff', 1, type=int)
        loss_two = request.form.get('loss_two_level_diff', 1, type=int)
        loss_three = request.form.get('loss_three_level_diff', 0, type=int)
        
        category = Category(
            name=name,
            color=color,
            priority=priority,
            points_same_category=points_same,
            points_one_level_diff=points_one,
            points_two_level_diff=points_two,
            points_three_level_diff=points_three,
            draw_same_category=draw_same,
            draw_one_level_diff=draw_one,
            draw_two_level_diff=draw_two,
            draw_three_level_diff=draw_three,
            loss_same_category=loss_same,
            loss_one_level_diff=loss_one,
            loss_two_level_diff=loss_two,
            loss_three_level_diff=loss_three
        )
        
        db.session.add(category)
        db.session.commit()
        flash('Category created successfully', 'success')
        return redirect(url_for('team_management.category_list'))
        
    return render_template('team_management/category_form.html')

@team_management.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    if not current_user.is_admin:
        abort(403)
        
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.color = request.form.get('color')
        category.priority = request.form.get('priority')
        category.points_same_category = request.form.get('points_same_category', 8, type=int)
        category.points_one_level_diff = request.form.get('points_one_level_diff', 7, type=int)
        category.points_two_level_diff = request.form.get('points_two_level_diff', 6, type=int)
        category.points_three_level_diff = request.form.get('points_three_level_diff', 5, type=int)
        
        # Add draw points
        category.draw_same_category = request.form.get('draw_same_category', 4, type=int)
        category.draw_one_level_diff = request.form.get('draw_one_level_diff', 3, type=int)
        category.draw_two_level_diff = request.form.get('draw_two_level_diff', 3, type=int)
        category.draw_three_level_diff = request.form.get('draw_three_level_diff', 2, type=int)
        
        # Add loss points
        category.loss_same_category = request.form.get('loss_same_category', 1, type=int)
        category.loss_one_level_diff = request.form.get('loss_one_level_diff', 1, type=int)
        category.loss_two_level_diff = request.form.get('loss_two_level_diff', 1, type=int)
        category.loss_three_level_diff = request.form.get('loss_three_level_diff', 0, type=int)
        
        db.session.commit()
        
        # Completely reset all player and team stats before recalculating
        player_stats = PlayerStats.query.all()
        for ps in player_stats:
            ps.played = 0
            ps.wins = 0
            ps.draws = 0
            ps.losses = 0
            ps.goals_scored = 0
            ps.goals_conceded = 0
            ps.clean_sheets = 0
            ps.points = 0
        
        team_stats = TeamStats.query.all()
        for ts in team_stats:
            ts.played = 0
            ts.wins = 0
            ts.draws = 0
            ts.losses = 0
            ts.goals_for = 0
            ts.goals_against = 0
            ts.points = 0
            
        db.session.commit()
        
        # Recalculate points for all completed matches
        completed_matches = Match.query.filter_by(is_completed=True).all()
        for match in completed_matches:
            update_player_and_team_stats(match.id)
            
        # No need for a second goal difference calculation here as it's already done in update_player_and_team_stats
        
        flash('Category updated successfully and stats recalculated', 'success')
        return redirect(url_for('team_management.category_list'))
        
    return render_template('team_management/category_form.html', category=category)

@team_management.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    if not current_user.is_admin:
        abort(403)
        
    category = Category.query.get_or_404(id)
    
    # Check if the category has any team members
    if category.team_members:
        flash('Cannot delete category with associated team members', 'danger')
        return redirect(url_for('team_management.category_list'))
    
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully', 'success')
    return redirect(url_for('team_management.category_list'))

# Team Members routes
@team_management.route('/team_members')
@login_required
def team_member_list():
    # Admin can see all team members, users can only see their own team
    if current_user.is_admin:
        team_members = TeamMember.query.all()
        teams = Team.query.all()
    else:
        if not current_user.team:
            flash('You need to have a team first', 'warning')
            return redirect(url_for('dashboard'))
            
        team_members = TeamMember.query.filter_by(team_id=current_user.team.id).all()
        teams = [current_user.team]
    
    categories = Category.query.order_by(Category.priority).all()
    return render_template('team_management/team_members.html', 
                           team_members=team_members, 
                           teams=teams, 
                           categories=categories)

@team_management.route('/team_members/new', methods=['GET', 'POST'])
@login_required
def new_team_member():
    # Only admin can add team members to any team, users can only add to their own team
    if current_user.is_admin:
        teams = Team.query.all()
    else:
        if not current_user.team:
            flash('You need to have a team first', 'warning')
            return redirect(url_for('dashboard'))
            
        teams = [current_user.team]
    
    categories = Category.query.order_by(Category.priority).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        team_id = request.form.get('team_id', type=int)
        category_id = request.form.get('category_id', type=int)
        photo_url = request.form.get('photo_url')
        
        # Validate that user can add to this team
        if not current_user.is_admin and current_user.team.id != team_id:
            abort(403)
        
        team_member = TeamMember(
            name=name,
            team_id=team_id,
            category_id=category_id,
            photo_url=photo_url
        )
        
        db.session.add(team_member)
        
        # Create player stats record
        player_stats = PlayerStats(team_member=team_member)
        db.session.add(player_stats)
        
        db.session.commit()
        flash('Team member added successfully', 'success')
        return redirect(url_for('team_management.team_member_list'))
        
    return render_template('team_management/team_member_form.html', 
                           teams=teams, 
                           categories=categories)

@team_management.route('/team_members/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_team_member(id):
    team_member = TeamMember.query.get_or_404(id)
    
    # Check permissions - only admin or the team owner can edit
    if not current_user.is_admin and (not current_user.team or current_user.team.id != team_member.team_id):
        abort(403)
    
    if current_user.is_admin:
        teams = Team.query.all()
    else:
        teams = [current_user.team]
    
    categories = Category.query.order_by(Category.priority).all()
    
    if request.method == 'POST':
        team_member.name = request.form.get('name')
        
        # Admin can change the team
        if current_user.is_admin:
            team_member.team_id = request.form.get('team_id', type=int)
            
        team_member.category_id = request.form.get('category_id', type=int)
        team_member.photo_url = request.form.get('photo_url')
        
        db.session.commit()
        flash('Team member updated successfully', 'success')
        return redirect(url_for('team_management.team_member_list'))
        
    return render_template('team_management/team_member_form.html', 
                           team_member=team_member,
                           teams=teams, 
                           categories=categories)

@team_management.route('/team_members/<int:id>/delete', methods=['POST'])
@login_required
def delete_team_member(id):
    team_member = TeamMember.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_admin and (not current_user.team or current_user.team.id != team_member.team_id):
        abort(403)
    
    # Check if member is involved in any matches
    has_matches = PlayerMatchup.query.filter(
        or_(
            PlayerMatchup.home_player_id == id,
            PlayerMatchup.away_player_id == id
        )
    ).first() is not None
    
    if has_matches:
        flash('Cannot delete team member who has participated in matches', 'danger')
        return redirect(url_for('team_management.team_member_list'))
    
    # Delete associated player stats
    if team_member.player_stats:
        db.session.delete(team_member.player_stats)
        
    db.session.delete(team_member)
    db.session.commit()
    flash('Team member deleted successfully', 'success')
    return redirect(url_for('team_management.team_member_list'))

# Matches routes
@team_management.route('/matches')
@login_required
def match_list():
    matches = Match.query.order_by(Match.round_number, Match.match_number).all()
    return render_template('team_management/matches.html', matches=matches)

@team_management.route('/matches/new', methods=['GET', 'POST'])
@login_required
def new_match():
    if not current_user.is_admin:
        abort(403)
        
    teams = Team.query.all()
    
    if request.method == 'POST':
        home_team_id = request.form.get('home_team_id', type=int)
        away_team_id = request.form.get('away_team_id', type=int)
        round_number = request.form.get('round_number', type=int)
        match_number = request.form.get('match_number', type=int)
        match_date_str = request.form.get('match_date')
        
        # Validate teams are different
        if home_team_id == away_team_id:
            flash('Home and away teams must be different', 'danger')
            return render_template('team_management/match_form.html', teams=teams, now=datetime.utcnow())
        
        # Parse date if provided
        match_date = None
        if match_date_str:
            try:
                match_date = datetime.strptime(match_date_str, '%Y-%m-%d')
            except ValueError:
                match_date = datetime.utcnow()
        else:
            match_date = datetime.utcnow()
        
        match = Match(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            round_number=round_number,
            match_number=match_number,
            match_date=match_date
        )
        
        db.session.add(match)
        db.session.commit()
        flash('Match created successfully', 'success')
        return redirect(url_for('team_management.match_detail', id=match.id))
        
    return render_template('team_management/match_form.html', teams=teams, now=datetime.utcnow())

@team_management.route('/matches/<int:id>')
@login_required
def match_detail(id):
    match = Match.query.get_or_404(id)
    
    # Get all player matchups for this match
    player_matchups = PlayerMatchup.query.filter_by(match_id=id).all()
    
    # Get available players from both teams for creating new matchups
    home_team_members = TeamMember.query.filter_by(team_id=match.home_team_id).all()
    away_team_members = TeamMember.query.filter_by(team_id=match.away_team_id).all()
    
    # Filter out players already in matchups
    used_home_player_ids = [m.home_player_id for m in player_matchups]
    used_away_player_ids = [m.away_player_id for m in player_matchups]
    
    available_home_players = [p for p in home_team_members if p.id not in used_home_player_ids]
    available_away_players = [p for p in away_team_members if p.id not in used_away_player_ids]
    
    return render_template('team_management/match_detail.html', 
                           match=match, 
                           player_matchups=player_matchups,
                           available_home_players=available_home_players,
                           available_away_players=available_away_players)

@team_management.route('/matches/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_match(id):
    if not current_user.is_admin:
        abort(403)
        
    match = Match.query.get_or_404(id)
    teams = Team.query.all()
    
    if request.method == 'POST':
        home_team_id = request.form.get('home_team_id', type=int)
        away_team_id = request.form.get('away_team_id', type=int)
        round_number = request.form.get('round_number', type=int)
        match_number = request.form.get('match_number', type=int)
        match_date_str = request.form.get('match_date')
        is_completed = 'is_completed' in request.form
        
        # Validate teams are different
        if home_team_id == away_team_id:
            flash('Home and away teams must be different', 'danger')
            return render_template('team_management/match_form.html', match=match, teams=teams, now=datetime.utcnow())
        
        # Parse date if provided
        if match_date_str:
            try:
                match.match_date = datetime.strptime(match_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        match.home_team_id = home_team_id
        match.away_team_id = away_team_id
        match.round_number = round_number
        match.match_number = match_number
        match.is_completed = is_completed
        
        db.session.commit()
        flash('Match updated successfully', 'success')
        return redirect(url_for('team_management.match_detail', id=match.id))
        
    return render_template('team_management/match_form.html', match=match, teams=teams, now=datetime.utcnow())

@team_management.route('/matches/<int:id>/delete', methods=['POST'])
@login_required
def delete_match(id):
    if not current_user.is_admin:
        abort(403)
        
    match = Match.query.get_or_404(id)
    
    # Completely reset all player and team stats
    player_stats_all = PlayerStats.query.all()
    for ps in player_stats_all:
        ps.played = 0
        ps.wins = 0
        ps.draws = 0
        ps.losses = 0
        ps.goals_scored = 0
        ps.goals_conceded = 0
        ps.clean_sheets = 0
        ps.points = 0
    
    # Reset team stats too
    team_stats = TeamStats.query.all()
    for ts in team_stats:
        ts.played = 0
        ts.wins = 0
        ts.draws = 0
        ts.losses = 0
        ts.goals_for = 0
        ts.goals_against = 0
        ts.points = 0
    
    db.session.commit()
    
    # Recalculate stats for all remaining completed matches
    completed_matches = Match.query.filter_by(is_completed=True).all()
    for match in completed_matches:
        update_player_and_team_stats(match.id)
    
    # No need for additional point calculation as it's done in update_player_and_team_stats
    
    # Delete all player matchups first
    PlayerMatchup.query.filter_by(match_id=id).delete()
    
    # Delete the match
    db.session.delete(match)
    db.session.commit()
    
    flash('Match deleted successfully', 'success')
    return redirect(url_for('team_management.match_list'))

# Player Matchup routes
@team_management.route('/matches/<int:match_id>/matchups/new', methods=['POST'])
@login_required
def add_player_matchup(match_id):
    if not current_user.is_admin:
        abort(403)
        
    match = Match.query.get_or_404(match_id)
    
    home_player_id = request.form.get('home_player_id', type=int)
    away_player_id = request.form.get('away_player_id', type=int)
    
    # Validate players exist and belong to the correct teams
    home_player = TeamMember.query.get_or_404(home_player_id)
    away_player = TeamMember.query.get_or_404(away_player_id)
    
    if home_player.team_id != match.home_team_id or away_player.team_id != match.away_team_id:
        flash('Players must belong to the correct teams', 'danger')
        return redirect(url_for('team_management.match_detail', id=match_id))
    
    # Check if players are already in another matchup for this match
    existing_home = PlayerMatchup.query.filter_by(match_id=match_id, home_player_id=home_player_id).first()
    existing_away = PlayerMatchup.query.filter_by(match_id=match_id, away_player_id=away_player_id).first()
    
    if existing_home or existing_away:
        flash('One or both players are already in a matchup for this match', 'danger')
        return redirect(url_for('team_management.match_detail', id=match_id))
    
    matchup = PlayerMatchup(
        match_id=match_id,
        home_player_id=home_player_id,
        away_player_id=away_player_id
    )
    
    db.session.add(matchup)
    db.session.commit()
    flash('Player matchup added successfully', 'success')
    return redirect(url_for('team_management.match_detail', id=match_id))

@team_management.route('/player_matchups/<int:id>/update', methods=['POST'])
@login_required
def update_player_matchup(id):
    if not current_user.is_admin:
        abort(403)
        
    matchup = PlayerMatchup.query.get_or_404(id)
    
    home_goals = request.form.get('home_goals', 0, type=int)
    away_goals = request.form.get('away_goals', 0, type=int)
    
    # Update the matchup
    old_home_goals = matchup.home_goals
    old_away_goals = matchup.away_goals
    
    matchup.home_goals = home_goals
    matchup.away_goals = away_goals
    
    # Update the match score
    match = matchup.match
    match.home_score = match.home_score - old_home_goals + home_goals
    match.away_score = match.away_score - old_away_goals + away_goals
    
    # If the match is completed, update player and team stats
    if match.is_completed:
        update_player_and_team_stats(match.id)
    
    db.session.commit()
    flash('Player matchup updated successfully', 'success')
    return redirect(url_for('team_management.match_detail', id=matchup.match_id))

@team_management.route('/player_matchups/<int:id>/delete', methods=['POST'])
@login_required
def delete_player_matchup(id):
    if not current_user.is_admin:
        abort(403)
        
    matchup = PlayerMatchup.query.get_or_404(id)
    match_id = matchup.match_id
    
    # Update match score
    match = matchup.match
    match.home_score -= matchup.home_goals
    match.away_score -= matchup.away_goals
    
    db.session.delete(matchup)
    db.session.commit()
    
    # If the match is completed, update stats after deleting the matchup
    if match.is_completed:
        update_player_and_team_stats(match_id)
        db.session.commit()
    
    flash('Player matchup deleted successfully', 'success')
    return redirect(url_for('team_management.match_detail', id=match_id))

@team_management.route('/matches/<int:id>/complete', methods=['POST'])
@login_required
def complete_match(id):
    if not current_user.is_admin:
        abort(403)
        
    match = Match.query.get_or_404(id)
    
    if match.is_completed:
        flash('Match is already completed', 'info')
        return redirect(url_for('team_management.match_detail', id=id))
    
    match.is_completed = True
    db.session.commit()
    
    # Update player and team stats
    update_player_and_team_stats(id)
    
    flash('Match completed successfully', 'success')
    return redirect(url_for('team_management.match_detail', id=id))

@team_management.route('/matches/<int:match_id>/select_potm', methods=['POST'])
@login_required
def select_potm(match_id):
    if not current_user.is_admin:
        abort(403)
        
    match = Match.query.get_or_404(match_id)
    
    # Only completed matches can have a POTM
    if not match.is_completed:
        flash('Only completed matches can have a Player of the Match', 'danger')
        return redirect(url_for('team_management.match_detail', id=match_id))
    
    player_id = request.form.get('player_id', type=int)
    if not player_id:
        flash('No player selected', 'danger')
        return redirect(url_for('team_management.match_detail', id=match_id))
    
    # Verify the player participated in this match
    player = TeamMember.query.get_or_404(player_id)
    participated = False
    
    for matchup in match.player_matchups:
        if matchup.home_player_id == player_id or matchup.away_player_id == player_id:
            participated = True
            break
    
    if not participated:
        flash('Selected player did not participate in this match', 'danger')
        return redirect(url_for('team_management.match_detail', id=match_id))
    
    # Set the player as POTM
    match.potm_id = player_id
    db.session.commit()
    
    flash(f'{player.name} has been selected as Player of the Match!', 'success')
    return redirect(url_for('team_management.match_detail', id=match_id))

# Helper function to update player and team stats when a match is completed
def update_player_and_team_stats(match_id):
    match = Match.query.get(match_id)
    if not match:
        return
    
    # Get or create team stats
    home_stats = TeamStats.query.filter_by(team_id=match.home_team_id).first()
    if not home_stats:
        home_stats = TeamStats(
            team_id=match.home_team_id,
            played=0,
            wins=0,
            draws=0,
            losses=0,
            goals_for=0,
            goals_against=0,
            points=0
        )
        db.session.add(home_stats)
        # Flush the session to ensure the object is created in the database
        db.session.flush()
    
    away_stats = TeamStats.query.filter_by(team_id=match.away_team_id).first()
    if not away_stats:
        away_stats = TeamStats(
            team_id=match.away_team_id,
            played=0,
            wins=0,
            draws=0,
            losses=0,
            goals_for=0,
            goals_against=0,
            points=0
        )
        db.session.add(away_stats)
        # Flush the session to ensure the object is created in the database
        db.session.flush()
    
    # Determine match result
    if match.home_score > match.away_score:
        # Home team wins
        home_result = "win"
        away_result = "loss"
    elif match.home_score < match.away_score:
        # Away team wins
        home_result = "loss"
        away_result = "win"
    else:
        # Draw
        home_result = "draw"
        away_result = "draw"
    
    # Update team stats
    home_stats.played += 1
    away_stats.played += 1
    
    if home_result == "win":
        home_stats.wins += 1
        away_stats.losses += 1
    elif home_result == "loss":
        home_stats.losses += 1
        away_stats.wins += 1
    else:
        home_stats.draws += 1
        away_stats.draws += 1
    
    home_stats.goals_for += match.home_score
    home_stats.goals_against += match.away_score
    
    away_stats.goals_for += match.away_score
    away_stats.goals_against += match.home_score
    
    # Calculate points based on categories
    player_matchups = PlayerMatchup.query.filter_by(match_id=match_id).all()
    
    # Process player matchups for this match
    for matchup in player_matchups:
        home_player = matchup.home_player
        away_player = matchup.away_player
        
        if not home_player or not away_player:
            continue
        
        # Get or create player stats
        home_player_stats = home_player.player_stats
        if not home_player_stats:
            home_player_stats = PlayerStats(
                team_member_id=home_player.id,
                played=0,
                wins=0,
                draws=0,
                losses=0,
                goals_scored=0,
                goals_conceded=0,
                clean_sheets=0,
                points=0
            )
            db.session.add(home_player_stats)
            db.session.flush()
            
        away_player_stats = away_player.player_stats
        if not away_player_stats:
            away_player_stats = PlayerStats(
                team_member_id=away_player.id,
                played=0,
                wins=0,
                draws=0,
                losses=0,
                goals_scored=0,
                goals_conceded=0,
                clean_sheets=0,
                points=0
            )
            db.session.add(away_player_stats)
            db.session.flush()
        
        # Calculate player results
        home_result, away_result = matchup.calculate_result()
        
        # Update player stats
        home_player_stats.played += 1
        away_player_stats.played += 1
        
        if home_result == "win":
            home_player_stats.wins += 1
            away_player_stats.losses += 1
        elif home_result == "loss":
            home_player_stats.losses += 1
            away_player_stats.wins += 1
        else:
            home_player_stats.draws += 1
            away_player_stats.draws += 1
        
        home_player_stats.goals_scored += matchup.home_goals
        home_player_stats.goals_conceded += matchup.away_goals
        
        away_player_stats.goals_scored += matchup.away_goals
        away_player_stats.goals_conceded += matchup.home_goals
        
        # Clean sheets
        if matchup.away_goals == 0:
            home_player_stats.clean_sheets += 1
        if matchup.home_goals == 0:
            away_player_stats.clean_sheets += 1
        
        # Calculate and add points based on categories and match result
        if home_result == "win":
            home_points = calculate_match_points(home_player.category, away_player.category, 'win')
            away_points = calculate_match_points(away_player.category, home_player.category, 'loss')
            home_player_stats.points += home_points
            away_player_stats.points += away_points
            
            # Debug output
            print(f"Match {match_id} - {home_player.name} (WIN) vs {away_player.name} (LOSS): {home_points} vs {away_points} category points")
            
        elif home_result == "draw":
            home_points = calculate_match_points(home_player.category, away_player.category, 'draw')
            away_points = calculate_match_points(away_player.category, home_player.category, 'draw')
            home_player_stats.points += home_points
            away_player_stats.points += away_points
            
            # Debug output
            print(f"Match {match_id} - {home_player.name} (DRAW) vs {away_player.name} (DRAW): {home_points} vs {away_points} category points")
            
        else:  # away win
            home_points = calculate_match_points(home_player.category, away_player.category, 'loss')
            away_points = calculate_match_points(away_player.category, home_player.category, 'win')
            home_player_stats.points += home_points
            away_player_stats.points += away_points
            
            # Debug output
            print(f"Match {match_id} - {home_player.name} (LOSS) vs {away_player.name} (WIN): {home_points} vs {away_points} category points")
    
    # Commit first pass calculations
    db.session.commit()
    
    # Second pass: Add goal difference bonus points
    player_stats_all = PlayerStats.query.all()
    for ps in player_stats_all:
        # Get original category points before adding goal difference bonus
        category_points = ps.points
        
        # Calculate goal difference bonus
        goal_difference = ps.goals_scored - ps.goals_conceded
        goal_difference_points = goal_difference / 2
        
        # Add debug output for Shamsear specifically
        if ps.team_member and ps.team_member.name == "Shamsear":
            print(f"Shamsear stats - category points: {category_points}, GD: {goal_difference}, GD/2: {goal_difference_points}")
        
        # Round properly: 0.5 and above rounds up, below 0.5 rounds down
        if goal_difference_points >= 0:
            goal_diff_rounded = int(goal_difference_points + 0.5)
        else:
            goal_diff_rounded = int(goal_difference_points - 0.5)
            
        # More debug for Shamsear
        if ps.team_member and ps.team_member.name == "Shamsear":
            print(f"Shamsear rounded GD points: {goal_diff_rounded}, final points: {category_points + goal_diff_rounded}")
            
        # Add the goal difference bonus to get final points
        ps.points = category_points + goal_diff_rounded
        
        player = TeamMember.query.get(ps.team_member_id)
        if player:
            print(f"UPDATE STATS - Player {player.name}: Category Points={category_points}, " +
                  f"Goals={ps.goals_scored}, Conceded={ps.goals_conceded}, " +
                  f"Goal Diff={goal_difference}, Goal Diff Bonus={goal_diff_rounded}, " +
                  f"Total Points={ps.points}")
    
    db.session.commit()
    
    # Calculate total team points from wins/draws
    home_stats.points = (home_stats.wins * 3) + home_stats.draws
    away_stats.points = (away_stats.wins * 3) + away_stats.draws
    
    db.session.commit()

# Leaderboard routes
@team_management.route('/team_leaderboard')
@login_required
def team_leaderboard():
    team_stats = TeamStats.query.join(Team).order_by(
        TeamStats.points.desc(),
        (TeamStats.goals_for - TeamStats.goals_against).desc(),
        TeamStats.goals_for.desc()
    ).all()
    
    return render_template('team_management/team_leaderboard.html', team_stats=team_stats)

@team_management.route('/team_detail/<string:team_name>')
@login_required
def team_detail(team_name):
    # Find the team by name
    team = Team.query.filter_by(name=team_name).first_or_404()
    
    # Get team statistics
    team_stats = TeamStats.query.filter_by(team_id=team.id).first_or_404()
    
    # Get team's position in the league table
    position_query = db.session.query(
        TeamStats.team_id,
        db.func.row_number().over(
            order_by=[
                TeamStats.points.desc(),
                (TeamStats.goals_for - TeamStats.goals_against).desc(),
                TeamStats.goals_for.desc()
            ]
        ).label('position')
    ).subquery()
    
    team_position = db.session.query(position_query.c.position).filter(
        position_query.c.team_id == team.id
    ).scalar() or 0
    
    # Get recent matches (last 5)
    recent_matches = Match.query.filter(
        db.or_(
            Match.home_team_id == team.id,
            Match.away_team_id == team.id
        ),
        Match.is_completed == True
    ).order_by(Match.match_date.desc()).limit(5).all()
    
    # Format the recent matches data
    recent_matches_data = []
    for match in recent_matches:
        is_home = match.home_team_id == team.id
        opponent = match.away_team if is_home else match.home_team
        team_goals = match.home_score if is_home else match.away_score
        opponent_goals = match.away_score if is_home else match.home_score
        
        # Determine result
        if team_goals > opponent_goals:
            result = 'win'
        elif team_goals < opponent_goals:
            result = 'loss'
        else:
            result = 'draw'
            
        # Get some basic match stats
        total_shots = 0
        possession = 50  # Default value
        corners = 0
        
        # In a real application, you would get this from the match data
        # For now, we'll use placeholder values
        if is_home:
            possession = 55
            total_shots = 12
            corners = 5
        else:
            possession = 45
            total_shots = 8
            corners = 3
            
        match_data = {
            'date': match.match_date.strftime('%b %d, %Y'),
            'opponent': opponent.name,
            'result': result,
            'team_goals': team_goals,
            'opponent_goals': opponent_goals,
            'stats': {
                'possession': possession,
                'shots': total_shots,
                'corners': corners
            }
        }
        
        recent_matches_data.append(match_data)
    
    # Get form data (last 5 matches results: W, D, L)
    form_data = []
    for match in recent_matches:
        is_home = match.home_team_id == team.id
        team_goals = match.home_score if is_home else match.away_score
        opponent_goals = match.away_score if is_home else match.home_score
        
        if team_goals > opponent_goals:
            form_data.append('W')
        elif team_goals < opponent_goals:
            form_data.append('L')
        else:
            form_data.append('D')
    
    # Get home and away record
    home_matches = Match.query.filter(
        Match.home_team_id == team.id,
        Match.is_completed == True
    ).all()
    
    away_matches = Match.query.filter(
        Match.away_team_id == team.id,
        Match.is_completed == True
    ).all()
    
    home_record = {
        'wins': 0,
        'draws': 0,
        'losses': 0,
        'total': 0  # Add a total count to avoid division by zero
    }
    
    away_record = {
        'wins': 0,
        'draws': 0,
        'losses': 0,
        'total': 0  # Add a total count to avoid division by zero
    }
    
    for match in home_matches:
        home_record['total'] += 1
        if match.home_score > match.away_score:
            home_record['wins'] += 1
        elif match.home_score < match.away_score:
            home_record['losses'] += 1
        else:
            home_record['draws'] += 1
            
    for match in away_matches:
        away_record['total'] += 1
        if match.away_score > match.home_score:
            away_record['wins'] += 1
        elif match.away_score < match.home_score:
            away_record['losses'] += 1
        else:
            away_record['draws'] += 1
    
    # Get top players from this team
    top_players = db.session.query(
        TeamMember, PlayerStats
    ).join(
        PlayerStats, TeamMember.id == PlayerStats.team_member_id
    ).filter(
        TeamMember.team_id == team.id,
        PlayerStats.played > 0
    ).order_by(
        PlayerStats.points.desc()
    ).limit(10).all()
    
    top_players_data = []
    for player, stats in top_players:
        player_data = {
            'id': player.id,  # Include the player ID for the detail link
            'name': player.name,
            'position': player.category.name,  # Using category as position
            'games_played': stats.played,
            'goals': stats.goals_scored,
            'rating': round((stats.points / stats.played) * 2, 1) if stats.played > 0 else 0  # Prevent division by zero
        }
        top_players_data.append(player_data)
    
    # Get all team members with their stats
    all_players = db.session.query(
        TeamMember, PlayerStats
    ).outerjoin(
        PlayerStats, TeamMember.id == PlayerStats.team_member_id
    ).filter(
        TeamMember.team_id == team.id
    ).all()
    
    all_players_data = []
    for player, player_stats in all_players:
        if player_stats:
            # If player has stats
            player_data = {
                'id': player.id,
                'name': player.name,
                'position': player.category.name,  # Using category as position
                'games_played': stats.played,
                'goals': stats.goals_scored,
                'points': player_stats.points
            }
        else:
            # If player has no stats
            player_data = {
                'id': player.id,
                'name': player.name,
                'position': player.category.name,  # Using category as position
                'games_played': 0,
                'goals': 0,
                'rating': 0
            }
        all_players_data.append(player_data)
    
    # Calculate additional statistics
    shooting_accuracy = 45  # Default placeholder - in a real app this would come from data
    possession = 52  # Default placeholder
    
    # Prevent division by zero for clean sheets calculation
    clean_sheets = 0
    if team_stats.played > 0:
        clean_sheets = int(team_stats.played - (team_stats.losses + team_stats.draws) / 2)  # Estimate
    
    # Prepare the team data object to send to the template
    team_data = {
        'name': team.name,
        'position': team_position,
        'played': team_stats.played,
        'points': team_stats.points,
        'wins': team_stats.wins,
        'draws': team_stats.draws,
        'losses': team_stats.losses,
        'goals_for': team_stats.goals_for,
        'goals_against': team_stats.goals_against,
        'goal_difference': team_stats.goals_for - team_stats.goals_against,
        'recent_form': form_data,
        'recent_matches': recent_matches_data,
        'home_record': home_record,
        'away_record': away_record,
        'top_players': top_players_data,
        'clean_sheets': clean_sheets,
        'shooting_accuracy': shooting_accuracy,
        'possession': possession,
        'last_updated': datetime.now().strftime('%b %d, %Y at %I:%M %p'),
        'all_players': all_players_data
    }
    
    return render_template('team_management/team_detail.html', team=team_data)

@team_management.route('/player_leaderboard')
@login_required
def player_leaderboard():
    # First recalculate all player stats
    player_stats = PlayerStats.query.all()
    completed_matches = Match.query.filter_by(is_completed=True).all()
    
    # Reset all player stats to zero
    for ps in player_stats:
        ps.points = 0
        ps.wins = 0
        ps.draws = 0
        ps.losses = 0
        ps.goals_scored = 0
        ps.goals_conceded = 0
        ps.clean_sheets = 0
        ps.played = 0
    
    db.session.commit()  # Commit the reset to ensure it takes effect
    
    # First pass: Recalculate basic stats and category points from completed matches
    for match in completed_matches:
        match_obj = Match.query.get(match.id)
        if not match_obj:
            continue
            
        # Process player matchups for this match
        for matchup in match_obj.player_matchups:
            home_player = matchup.home_player
            away_player = matchup.away_player
            
            if not home_player or not away_player:
                continue
                
            # Get player stats
            home_player_stats = home_player.player_stats
            away_player_stats = away_player.player_stats
            
            if not home_player_stats or not away_player_stats:
                continue
                
            # Update played games
            home_player_stats.played += 1
            away_player_stats.played += 1
            
            # Update goals
            home_player_stats.goals_scored += matchup.home_goals
            home_player_stats.goals_conceded += matchup.away_goals
            away_player_stats.goals_scored += matchup.away_goals
            away_player_stats.goals_conceded += matchup.home_goals
            
            # Update clean sheets
            if matchup.away_goals == 0:
                home_player_stats.clean_sheets += 1
            if matchup.home_goals == 0:
                away_player_stats.clean_sheets += 1
                
            # Calculate result
            home_result, away_result = matchup.calculate_result()
            
            # Update win/draw/loss counts
            if home_result == "win":
                home_player_stats.wins += 1
                away_player_stats.losses += 1
            elif home_result == "draw":
                home_player_stats.draws += 1
                away_player_stats.draws += 1
            else:  # Away wins
                home_player_stats.losses += 1
                away_player_stats.wins += 1
                
            # Add category points
            if home_result == "win":
                home_points = calculate_match_points(home_player.category, away_player.category, 'win')
                away_points = calculate_match_points(away_player.category, home_player.category, 'loss')
                home_player_stats.points += home_points
                away_player_stats.points += away_points
            elif home_result == "draw":
                home_points = calculate_match_points(home_player.category, away_player.category, 'draw')
                away_points = calculate_match_points(away_player.category, home_player.category, 'draw')
                home_player_stats.points += home_points
                away_player_stats.points += away_points
            else:  # Away wins
                home_points = calculate_match_points(home_player.category, away_player.category, 'loss')
                away_points = calculate_match_points(away_player.category, home_player.category, 'win')
                home_player_stats.points += home_points
                away_player_stats.points += away_points
                
    # Commit first pass calculations
    db.session.commit()
    
    # Second pass: Add goal difference bonus points
    for ps in player_stats:
        # Get original category points before adding goal difference bonus
        category_points = ps.points
        
        # Calculate goal difference bonus
        goal_difference = ps.goals_scored - ps.goals_conceded
        goal_difference_points = goal_difference / 2
        
        # Handle negative goal differences properly
        if goal_difference_points >= 0:
            goal_diff_rounded = int(goal_difference_points + 0.5)
        else:
            goal_diff_rounded = int(goal_difference_points - 0.5)
            
        # Add the goal difference bonus to get final points
        ps.points = category_points + goal_diff_rounded
        
        # Debug output
        player = TeamMember.query.get(ps.team_member_id)
        if player:
            print(f"PLAYER LEADERBOARD - {player.name}: Category Points={category_points}, " +
                  f"Goals={ps.goals_scored}, Conceded={ps.goals_conceded}, " +
                  f"Goal Diff={goal_difference}, Goal Diff Bonus={goal_diff_rounded}, " +
                  f"Total Points={ps.points}")
    
    db.session.commit()
    
    # Get all realplayers with their categories for the category-wise leaderboard section
    realplayers = db.session.query(
        TeamMember, Category, Team, PlayerStats
    ).join(
        Category, TeamMember.category_id == Category.id
    ).join(
        Team, TeamMember.team_id == Team.id
    ).outerjoin(
        PlayerStats, TeamMember.id == PlayerStats.team_member_id
    ).all()
    
    # Prepare realplayer data with category colors and stats
    realplayer_list = []
    for player, category, team, stats in realplayers:
        # Map category name to color
        category_color_map = {
            'red': '#ef4444',
            'black': '#1f2937',
            'blue': '#3b82f6',
            'orange': '#f97316',
            'white': '#f3f4f6'
        }
        
        # Default values if stats are None
        matches_played = 0
        goals = 0
        
        if stats:
            matches_played = stats.played 
            goals = stats.goals_scored
            
        realplayer_list.append({
            'id': player.id,
            'name': player.name,
            'category': category.name.lower(),
            'category_color': category_color_map.get(category.name.lower(), '#6b7280'),
            'team': team.name,
            'photo_url': player.photo_url,
            'matches_played': matches_played,
            'wins': stats.wins,
            'draws': stats.draws,
            'losses': stats.losses,
            'goals': goals,
            'goals_conceded': stats.goals_conceded,
            'goal_difference': stats.goals_scored - stats.goals_conceded,
            'points': stats.points
        })
    
    # Get top goalscorers for Golden Boot
    top_goalscorers = db.session.query(
        TeamMember, Category, Team, PlayerStats
    ).join(
        Category, TeamMember.category_id == Category.id
    ).join(
        Team, TeamMember.team_id == Team.id
    ).join(
        PlayerStats, TeamMember.id == PlayerStats.team_member_id
    ).filter(
        PlayerStats.played > 0
    ).order_by(
        PlayerStats.goals_scored.desc(),
        PlayerStats.played
    ).limit(10).all()
    
    # Format top goalscorers data
    top_goalscorers_list = []
    for player, category, team, stats in top_goalscorers:
        category_color_map = {
            'red': '#ef4444',
            'black': '#1f2937',
            'blue': '#3b82f6',
            'orange': '#f97316',
            'white': '#f3f4f6'
        }
        
        top_goalscorers_list.append({
            'id': player.id,
            'name': player.name,
            'category': category.name.lower(),
            'category_color': category_color_map.get(category.name.lower(), '#6b7280'),
            'team': team.name,
            'photo_url': player.photo_url,
            'matches_played': stats.played,
            'goals': stats.goals_scored
        })
    
    # Get top defenders for Golden Glove (players with lowest goals conceded)
    top_defenders = db.session.query(
        TeamMember, Category, Team, PlayerStats
    ).join(
        Category, TeamMember.category_id == Category.id
    ).join(
        Team, TeamMember.team_id == Team.id
    ).join(
        PlayerStats, TeamMember.id == PlayerStats.team_member_id
    ).filter(
        PlayerStats.played > 0
    ).order_by(
        PlayerStats.goals_conceded,
        PlayerStats.clean_sheets.desc()
    ).limit(10).all()
    
    # Format top defenders data
    top_defenders_list = []
    for player, category, team, stats in top_defenders:
        category_color_map = {
            'red': '#ef4444',
            'black': '#1f2937',
            'blue': '#3b82f6',
            'orange': '#f97316',
            'white': '#f3f4f6'
        }
        
        top_defenders_list.append({
            'id': player.id,
            'name': player.name,
            'category': category.name.lower(),
            'category_color': category_color_map.get(category.name.lower(), '#6b7280'),
            'team': team.name,
            'photo_url': player.photo_url,
            'matches_played': stats.played,
            'goals_conceded': stats.goals_conceded,
            'clean_sheets': stats.clean_sheets
        })
    
    # Get best overall players for Golden Ball (based on rating calculated from all stats)
    best_players_query = db.session.query(
        TeamMember, Category, Team, PlayerStats,
        db.func.count(Match.id).label('potm_count')
    ).join(
        Category, TeamMember.category_id == Category.id
    ).join(
        Team, TeamMember.team_id == Team.id
    ).join(
        PlayerStats, TeamMember.id == PlayerStats.team_member_id
    ).outerjoin(
        Match, Match.potm_id == TeamMember.id
    ).filter(
        PlayerStats.played > 0
    ).group_by(
        TeamMember.id, Category.id, Team.id, PlayerStats.id
    )
    
    # Apply sorting by a calculated rating formula
    best_players = best_players_query.all()
    
    # Calculate rating for each player and add to list
    best_players_list = []
    for player, category, team, stats, potm_count in best_players:
        # Formula for overall rating (simple example - can be adjusted)
        # 50% points + 20% goals + 15% goal difference + 15% potm
        points_factor = stats.points * 0.5
        goals_factor = stats.goals_scored * 0.2
        goal_diff_factor = (stats.goals_scored - stats.goals_conceded) * 0.15
        potm_factor = potm_count * 0.15
        
        rating = points_factor + goals_factor + goal_diff_factor + potm_factor
        
        category_color_map = {
            'red': '#ef4444',
            'black': '#1f2937',
            'blue': '#3b82f6',
            'orange': '#f97316',
            'white': '#f3f4f6'
        }
        
        best_players_list.append({
            'id': player.id,
            'name': player.name,
            'category': category.name.lower(),
            'category_color': category_color_map.get(category.name.lower(), '#6b7280'),
            'team': team.name,
            'photo_url': player.photo_url,
            'matches_played': stats.played,
            'wins': stats.wins,
            'draws': stats.draws,
            'losses': stats.losses,
            'goals': stats.goals_scored,
            'goals_conceded': stats.goals_conceded,
            'goal_difference': stats.goals_scored - stats.goals_conceded,
            'points': stats.points,
            'potm_count': potm_count,
            'rating': rating
        })
    
    # Sort the best players by rating
    best_players_list = sorted(best_players_list, key=lambda x: x['rating'], reverse=True)[:10]
    
    # Get round by round performance data (Rounds 1-7, 8-14, 15-21, 22+)
    # Group matches by round
    round_ranges = [
        (1, 7),   # Rounds 1-7
        (8, 14),  # Rounds 8-14
        (15, 21), # Rounds 15-21
        (22, 999) # Rounds 22+
    ]
    
    # Initialize data structure for each round range
    round_stats = {
        'round1': [],  # Rounds 1-7
        'round2': [],  # Rounds 8-14
        'round3': [],  # Rounds 15-21
        'round4': []   # Rounds 22+
    }
    
    # Get all completed matches
    for i, (start_round, end_round) in enumerate(round_ranges):
        round_key = f'round{i+1}'
        
        # Get matches in this round range
        round_matches = Match.query.filter(
            Match.round_number.between(start_round, end_round),
            Match.is_completed == True
    ).all()
    
        # Collect all player matchups in this round
        player_performance = {}
        
        for match in round_matches:
            for matchup in match.player_matchups:
                # Process home player
                if matchup.home_player_id not in player_performance:
                    home_player = matchup.home_player
                    player_performance[matchup.home_player_id] = {
                        'player': home_player,
                        'team': home_player.team,
                        'category': home_player.category,
                        'matches': 0,
                        'goals': 0,
                        'assists': 0,  # Placeholder as assists aren't tracked yet
                        'tackles': 0,  # Placeholder as tackles aren't tracked yet
                        'rating': 0,   # Will calculate based on goals and match results
                        'wins': 0,
                        'draws': 0,
                        'losses': 0
                    }
                
                # Process away player
                if matchup.away_player_id not in player_performance:
                    away_player = matchup.away_player
                    player_performance[matchup.away_player_id] = {
                        'player': away_player,
                        'team': away_player.team,
                        'category': away_player.category,
                        'matches': 0,
                        'goals': 0,
                        'assists': 0,  # Placeholder
                        'tackles': 0,  # Placeholder
                        'rating': 0,
                        'wins': 0,
                        'draws': 0,
                        'losses': 0
                    }
                
                # Update stats for home player
                home_perf = player_performance[matchup.home_player_id]
                home_perf['matches'] += 1
                home_perf['goals'] += matchup.home_goals
                
                # Update stats for away player
                away_perf = player_performance[matchup.away_player_id]
                away_perf['matches'] += 1
                away_perf['goals'] += matchup.away_goals
                
                # Update win/draw/loss records
                home_result, away_result = matchup.calculate_result()
                if home_result == 'win':
                    home_perf['wins'] += 1
                    away_perf['losses'] += 1
                elif home_result == 'draw':
                    home_perf['draws'] += 1
                    away_perf['draws'] += 1
                else:  # away win
                    home_perf['losses'] += 1
                    away_perf['wins'] += 1
                
                # Calculate simple rating (can be enhanced)
                # 3 points for win, 1 for draw, 1 per goal
                home_perf['rating'] = (home_perf['wins'] * 3) + home_perf['draws'] + (home_perf['goals'] * 0.5)
                away_perf['rating'] = (away_perf['wins'] * 3) + away_perf['draws'] + (away_perf['goals'] * 0.5)
                
                # POTM bonus
                if match.potm_id == matchup.home_player_id:
                    home_perf['rating'] += 2
                elif match.potm_id == matchup.away_player_id:
                    away_perf['rating'] += 2
        
        # Convert to list and sort by rating
        player_list = []
        for player_id, perf in player_performance.items():
            player = perf['player']
            category = perf['category']
            team = perf['team']
            
            # Map category to color
            category_color_map = {
                'red': '#ef4444',
                'black': '#1f2937',
                'blue': '#3b82f6',
                'orange': '#f97316',
                'white': '#f3f4f6'
            }
            
            # Calculate goal conceded and goal difference for this round
            goals_conceded = 0
            for match in round_matches:
                for matchup in match.player_matchups:
                    if matchup.home_player_id == player_id:
                        goals_conceded += matchup.away_goals
                    elif matchup.away_player_id == player_id:
                        goals_conceded += matchup.home_goals
            
            goal_difference = perf['goals'] - goals_conceded
            
            # Count POTM awards in this round
            potm_count = Match.query.filter(
                Match.round_number.between(start_round, end_round),
                Match.is_completed == True,
                Match.potm_id == player_id
            ).count()
            
            # Calculate points for this round (3 for win, 1 for draw)
            points = (perf['wins'] * 3) + perf['draws']
            
            player_list.append({
                'id': player.id,
                'name': player.name,
                'category': category.name.lower(),
                'category_color': category_color_map.get(category.name.lower(), '#6b7280'),
                'team': team.name,
                'photo_url': player.photo_url,
                'matches': perf['matches'],
                'wins': perf['wins'],
                'draws': perf['draws'],
                'losses': perf['losses'],
                'goals': perf['goals'],
                'goals_conceded': goals_conceded,
                'goal_difference': goal_difference,
                'potm_count': potm_count,
                'points': points,
                'assists': perf['assists'],
                'tackles': perf['tackles'],
                'rating': round(perf['rating'], 1)
            })
        
        # Sort by rating (descending)
        sorted_players = sorted(player_list, key=lambda x: x['rating'], reverse=True)
        
        # Store in the appropriate round stats
        round_stats[round_key] = sorted_players
    
    # Check if player_id parameter is provided for specific player view
    player_id = request.args.get('player_id', type=int)
    if player_id:
        # Fetch specific player data
        player = TeamMember.query.get_or_404(player_id)
        player_stats = player.player_stats
        
        if not player_stats:
            flash('No stats available for this player', 'info')
            return redirect(url_for('team_management.team_member_list'))
        
        # Get all matchups involving this player
        player_matchups = PlayerMatchup.query.filter(
            db.or_(
                PlayerMatchup.home_player_id == player_id,
                PlayerMatchup.away_player_id == player_id
            )
        ).join(Match).filter(Match.is_completed == True).order_by(Match.match_date.desc()).all()
        
        # Prepare match history
        match_history = []
        for matchup in player_matchups:
            match = matchup.match
            is_home = matchup.home_player_id == player_id
            
            opponent = matchup.away_player if is_home else matchup.home_player
            player_goals = matchup.home_goals if is_home else matchup.away_goals
            opponent_goals = matchup.away_goals if is_home else matchup.home_goals
            
            result = ""
            if player_goals > opponent_goals:
                result = "win"
            elif player_goals < opponent_goals:
                result = "loss"
            else:
                result = "draw"
            
            # Calculate points for each matchup
            points = 0
            if result == "win":
                # Calculate points based on categories
                points = calculate_match_points(
                    player.category.name.lower(), 
                    opponent.category.name.lower(), 
                    'win'
                )
            elif result == "draw":
                points = calculate_match_points(
                    player.category.name.lower(), 
                    opponent.category.name.lower(), 
                    'draw'
                )
            
            match_history.append({
                'match_date': match.match_date,
                'round': match.round_number,
                'match_number': match.match_number,
                'opponent': opponent.name,
                'opponent_team': opponent.team.name,
                'opponent_category': opponent.category.name,
                'player_goals': player_goals,
                'opponent_goals': opponent_goals,
                'result': result,
                'is_potm': match.potm_id == player_id,
                'points': points
            })
        
        # Calculate additional stats
        total_matches = player_stats.played
        win_percentage = (player_stats.wins / total_matches * 100) if total_matches > 0 else 0
        clean_sheet_percentage = (player_stats.clean_sheets / total_matches * 100) if total_matches > 0 else 0
        goals_per_match = player_stats.goals_scored / total_matches if total_matches > 0 else 0
        
        # Get round specific performance for this player
        round_performance = {}
        for round_key, players in round_stats.items():
            for p in players:
                if p['id'] == player_id:
                    round_performance[round_key] = p
                    break
        
        # Count POTMs
        potm_count = Match.query.filter_by(potm_id=player_id).count()
        
        # Get player ranking in overall leaderboard
        player_ranking = PlayerStats.query.order_by(
            PlayerStats.points.desc(), 
            PlayerStats.goals_scored.desc()
        ).all()
        
        ranking = 0
        for i, ps in enumerate(player_ranking):
            if ps.team_member_id == player_id:
                ranking = i + 1
                break
        
        # Category color mapping
        category_color_map = {
            'red': '#ef4444',
            'black': '#1f2937',
            'blue': '#3b82f6',
            'orange': '#f97316',
            'white': '#f3f4f6'
        }
        
        # Create player detail object
        player_detail = {
            'id': player.id,
            'name': player.name,
            'team': player.team.name,
            'category': player.category.name.lower(),
            'category_color': category_color_map.get(player.category.name.lower(), '#6b7280'),
            'photo_url': player.photo_url,
            'points': player_stats.points,
            'played': player_stats.played,
            'wins': player_stats.wins,
            'draws': player_stats.draws,
            'losses': player_stats.losses,
            'goals_scored': player_stats.goals_scored,
            'goals_conceded': player_stats.goals_conceded,
            'clean_sheets': player_stats.clean_sheets,
            'win_percentage': round(win_percentage, 1),
            'clean_sheet_percentage': round(clean_sheet_percentage, 1),
            'goals_per_match': round(goals_per_match, 2),
            'potm_count': potm_count,
            'ranking': ranking,
            'round_performance': round_performance
        }
        
        return render_template('team_management/player_detail.html', 
                              player=player_detail,
                              match_history=match_history)
    
    return render_template('team_management/player_leaderboard.html', 
                          realplayers=realplayer_list,
                          top_goalscorers=top_goalscorers_list,
                          top_defenders=top_defenders_list,
                          best_realplayers=best_players_list,
                          round1_stats=round_stats['round1'],
                          round2_stats=round_stats['round2'],
                          round3_stats=round_stats['round3'],
                          round4_stats=round_stats['round4'])
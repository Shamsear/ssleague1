from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Team, Player, Round, Bid, db
from datetime import datetime
from socket_events import broadcast_bid_update

auction_bp = Blueprint('auction', __name__)

@auction_bp.route('/place_bid', methods=['POST'])
@login_required
def place_bid():
    data = request.json
    player_id = data.get('player_id')
    round_id = data.get('round_id')
    amount = data.get('amount')
    
    if not all([player_id, round_id, amount]):
        return jsonify({'success': False, 'message': 'Missing required data'}), 400
    
    # Check if the user is authorized to bid
    team = Team.query.filter_by(user_id=current_user.id).first()
    if not team:
        return jsonify({'success': False, 'message': 'Team not found'}), 404
    
    current_round = Round.query.get(round_id)
    if not current_round or current_round.status != 'active':
        return jsonify({'success': False, 'message': 'Round is not active'}), 400
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'message': 'Player not found'}), 404
    
    # Check if the amount is valid (must be greater than current highest bid)
    highest_bid = Bid.query.filter_by(player_id=player_id, round_id=round_id).order_by(Bid.amount.desc()).first()
    min_bid = highest_bid.amount + 1 if highest_bid else player.base_price
    
    if amount < min_bid:
        return jsonify({'success': False, 'message': f'Bid must be at least {min_bid}'}), 400
    
    # Check if team has enough budget
    total_spent = db.session.query(db.func.sum(Bid.amount)).filter(
        Bid.team_id == team.id,
        Bid.is_winning == True
    ).scalar() or 0
    
    remaining_budget = team.budget - total_spent
    if amount > remaining_budget:
        return jsonify({'success': False, 'message': 'Not enough budget'}), 400
    
    # Create new bid
    new_bid = Bid(
        player_id=player_id,
        team_id=team.id,
        round_id=round_id,
        amount=amount,
        timestamp=datetime.now(),
        is_winning=True
    )
    
    # Set previous winning bid (if any) to is_winning=False
    if highest_bid:
        highest_bid.is_winning = False
    
    db.session.add(new_bid)
    db.session.commit()
    
    # Broadcast bid update to all clients in the auction room
    from app import socketio
    broadcast_bid_update(socketio, round_id, player_id, team.id, amount)
    
    return jsonify({
        'success': True, 
        'message': 'Bid placed successfully',
        'bid': {
            'id': new_bid.id,
            'amount': new_bid.amount,
            'team_id': new_bid.team_id,
            'team_name': team.name
        }
    })
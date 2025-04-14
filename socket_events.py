from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user
from flask import request
import logging

logger = logging.getLogger(__name__)

# Initialize SocketIO instance
socketio = SocketIO()

# Dictionary to track online users - key is user_id, value is list of sessions
online_users = {}
# Room for administrators
admin_room = 'admin_room'
# Room for general broadcast
broadcast_room = 'broadcast_room'

def init_app(app):
    """Initialize the Socket.IO extension with the Flask app"""
    socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')
    return socketio

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    if not current_user.is_authenticated:
        return False  # Reject connection if user is not authenticated
    
    user_id = current_user.id
    session_id = request.sid
    
    # Add user to their personal room (for direct messaging)
    join_room(f'user_{user_id}')
    
    # Add admins to admin room
    if current_user.is_admin:
        join_room(admin_room)
    
    # Everyone joins broadcast room
    join_room(broadcast_room)
    
    # Track online status
    if user_id in online_users:
        online_users[user_id].append(session_id)
    else:
        online_users[user_id] = [session_id]
    
    # Notify admins about user connection
    if current_user.is_admin:
        emit('admin_notification', {
            'message': f'Admin {current_user.username} connected'
        }, room=admin_room)
    else:
        emit('admin_notification', {
            'message': f'User {current_user.username} connected',
            'user_id': user_id
        }, room=admin_room)
    
    # Send initial status to user
    emit('connection_status', {
        'status': 'connected',
        'username': current_user.username,
        'is_admin': current_user.is_admin
    })
    
    logger.info(f"Client connected: {request.sid}")
    
    return True

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    if not current_user.is_authenticated:
        return
    
    user_id = current_user.id
    session_id = request.sid
    
    # Remove session from tracking
    if user_id in online_users:
        if session_id in online_users[user_id]:
            online_users[user_id].remove(session_id)
        
        # If no more sessions, user is fully offline
        if not online_users[user_id]:
            del online_users[user_id]
            
            # Notify admins about disconnect
            emit('admin_notification', {
                'message': f'User {current_user.username} disconnected',
                'user_id': user_id
            }, room=admin_room)

    logger.info(f"Client disconnected: {request.sid}")

# Event handlers for real-time auction updates

@socketio.on('join_auction')
def handle_join_auction(data):
    """
    Handle client joining an auction room for a specific round
    """
    if 'round_id' not in data:
        logger.error("Invalid join_auction request: missing round_id")
        return
            
    round_id = data['round_id']
    room = f"auction_room_{round_id}"
    join_room(room)
    logger.info(f"Client {request.sid} joined auction room for round {round_id}")
    
    emit('auction_message', {
        'message': f'You are now receiving live updates for auction round {round_id}'
    })

@socketio.on('leave_auction')
def handle_leave_auction(data):
    """
    Handle client leaving an auction room
    """
    if 'round_id' not in data:
        logger.error("Invalid leave_auction request: missing round_id")
        return
            
    round_id = data['round_id']
    room = f"auction_room_{round_id}"
    leave_room(room)
    logger.info(f"Client {request.sid} left auction room for round {round_id}")

# Public functions to be called from app.py

def broadcast_round_start(socketio: SocketIO, round_id):
    """
    Broadcast round start event to all clients in the auction room
    """
    room = f"auction_room_{round_id}"
    socketio.emit('round_start', {'round_id': round_id}, room=room)
    logger.info(f"Broadcast round_start event for round {round_id}")

def broadcast_round_end(socketio: SocketIO, round_id):
    """
    Broadcast round end event to all clients in the auction room
    """
    room = f"auction_room_{round_id}"
    socketio.emit('round_end', {'round_id': round_id}, room=room)
    logger.info(f"Broadcast round_end event for round {round_id}")

def broadcast_bid_update(socketio: SocketIO, round_id, player_id, team_id, amount):
    """
    Broadcast bid update to all clients in the auction room
    """
    room = f"auction_room_{round_id}"
    socketio.emit('auction_update', {
        'type': 'new_bid',
        'round_id': round_id,
        'player_id': player_id,
        'team_id': team_id,
        'amount': amount
    }, room=room)
    logger.info(f"Broadcast bid update for player {player_id} in round {round_id}")

def broadcast_timer_update(socketio: SocketIO, round_id, remaining_seconds):
    """
    Broadcast timer update to all clients in the auction room
    """
    room = f"auction_room_{round_id}"
    socketio.emit('timer_update', {
        'round_id': round_id,
        'remaining_seconds': remaining_seconds
    }, room=room)
    logger.info(f"Broadcast timer update for round {round_id}: {remaining_seconds}s remaining")

def broadcast_auction_update(round_id, update_data):
    """Broadcast auction update to users in specific auction room"""
    socketio.emit('auction_update', update_data, room=f'auction_{round_id}')

def send_personal_notification(user_id, notification_data):
    """Send personal notification to specific user"""
    socketio.emit('personal_notification', notification_data, room=f'user_{user_id}')

def broadcast_to_admins(data):
    """Send message to all admins"""
    socketio.emit('admin_update', data, room=admin_room)

def broadcast_tiebreaker_start(tiebreaker_data):
    """Broadcast tiebreaker start event"""
    round_id = tiebreaker_data.get('round_id')
    # Send to general broadcast room
    socketio.emit('tiebreaker_start', tiebreaker_data, room=broadcast_room)
    # Also send to specific auction room if available
    if round_id:
        socketio.emit('tiebreaker_start', tiebreaker_data, room=f'auction_{round_id}')

def broadcast_tiebreaker_end(tiebreaker_data):
    """Broadcast tiebreaker end event"""
    round_id = tiebreaker_data.get('round_id')
    # Send to general broadcast room
    socketio.emit('tiebreaker_end', tiebreaker_data, room=broadcast_room)
    # Also send to specific auction room if available
    if round_id:
        socketio.emit('tiebreaker_end', tiebreaker_data, room=f'auction_{round_id}')

def broadcast_player_allocation(player_data):
    """Broadcast player allocation to a team"""
    socketio.emit('player_allocated', player_data, room=broadcast_room) 
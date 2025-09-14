from flask import current_app
from models import db, TelegramUser, NotificationLog, NotificationSettings
from telegram_service import get_telegram_bot
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

class NotificationService:
    """
    Service for managing and sending notifications to users via Telegram
    """
    
    def __init__(self):
        self.telegram_bot = get_telegram_bot()
    
    def send_user_action_notification(self, user_action: str, actor_user_id: int, 
                                    details: Dict[str, Any] = None, 
                                    notification_type: str = 'admin_actions'):
        """
        Send notification about a user action to all subscribed users
        
        Args:
            user_action: Description of the action performed
            actor_user_id: ID of user who performed the action
            details: Additional details about the action
            notification_type: Type of notification for filtering subscribers
        """
        if not self.telegram_bot:
            logger.warning("Telegram bot not available, skipping notification")
            return
        
        # Get the actor user
        from models import User
        actor_user = User.query.get(actor_user_id)
        if not actor_user:
            logger.error(f"Actor user {actor_user_id} not found")
            return
        
        # Get users who want this type of notification
        telegram_users = TelegramUser.get_users_for_notification_type(notification_type)
        
        if not telegram_users:
            logger.info(f"No users subscribed to {notification_type} notifications")
            return
        
        # Format the message
        message = self.telegram_bot.format_user_action_message(
            user=actor_user.username,
            action=user_action,
            details=details
        )
        
        # Send to all subscribed users
        sent_count = 0
        for tg_user in telegram_users:
            try:
                # Create log entry
                log = NotificationLog.create_log(
                    telegram_user_id=tg_user.id,
                    notification_type=notification_type,
                    message=message,
                    user_action=user_action,
                    actor_user_id=actor_user_id,
                    message_data=details
                )
                
                # Queue the notification
                notification_data = {
                    'type': 'message',
                    'chat_id': tg_user.telegram_chat_id,
                    'text': message,
                    'parse_mode': 'HTML',
                    'disable_notification': False
                }
                
                self.telegram_bot.queue_notification(notification_data)
                log.mark_sent()
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send notification to user {tg_user.user_id}: {e}")
                if 'log' in locals():
                    log.mark_failed(str(e))
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info(f"Queued {sent_count} notifications for action: {user_action}")
        except Exception as e:
            logger.error(f"Failed to commit notification logs: {e}")
            db.session.rollback()
    
    def send_system_alert(self, alert_type: str, message: str, severity: str = "info",
                         notification_type: str = 'system_alerts'):
        """
        Send system alert to all subscribed users
        
        Args:
            alert_type: Type of alert (e.g., "Database Error", "Performance Warning")
            message: Alert message
            severity: Severity level (critical, warning, info, success)
            notification_type: Type of notification for filtering subscribers
        """
        if not self.telegram_bot:
            logger.warning("Telegram bot not available, skipping alert")
            return
        
        # Get users who want this type of notification
        telegram_users = TelegramUser.get_users_for_notification_type(notification_type)
        
        if not telegram_users:
            logger.info(f"No users subscribed to {notification_type} notifications")
            return
        
        # Format the message
        formatted_message = self.telegram_bot.format_system_alert_message(
            alert_type=alert_type,
            message=message,
            severity=severity
        )
        
        # Send to all subscribed users
        sent_count = 0
        for tg_user in telegram_users:
            try:
                # Create log entry
                log = NotificationLog.create_log(
                    telegram_user_id=tg_user.id,
                    notification_type=notification_type,
                    message=formatted_message,
                    user_action=f"System Alert: {alert_type}",
                    message_data={'alert_type': alert_type, 'severity': severity}
                )
                
                # Queue the notification
                notification_data = {
                    'type': 'message',
                    'chat_id': tg_user.telegram_chat_id,
                    'text': formatted_message,
                    'parse_mode': 'HTML',
                    'disable_notification': severity not in ['critical', 'warning']
                }
                
                self.telegram_bot.queue_notification(notification_data)
                log.mark_sent()
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send alert to user {tg_user.user_id}: {e}")
                if 'log' in locals():
                    log.mark_failed(str(e))
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info(f"Queued {sent_count} system alerts: {alert_type}")
        except Exception as e:
            logger.error(f"Failed to commit alert logs: {e}")
            db.session.rollback()
    
    def send_auction_notification(self, action: str, round_info: Dict[str, Any] = None,
                                player_info: Dict[str, Any] = None, team_info: Dict[str, Any] = None):
        """
        Send auction-related notifications
        
        Args:
            action: Type of auction action (start, end, bid_placed, tiebreaker, etc.)
            round_info: Information about the auction round
            player_info: Information about the player involved
            team_info: Information about the team involved
        """
        if not self.telegram_bot:
            logger.warning("Telegram bot not available, skipping auction notification")
            return
        
        # Map actions to notification types
        action_type_map = {
            'auction_start': 'auction_start',
            'auction_end': 'auction_end',
            'bid_placed': 'bids',
            'tiebreaker_start': 'bids',
            'tiebreaker_end': 'bids',
            'player_acquired': 'bids'
        }
        
        notification_type = action_type_map.get(action, 'system_alerts')
        
        # Get users who want this type of notification
        telegram_users = TelegramUser.get_users_for_notification_type(notification_type)
        
        if not telegram_users:
            logger.info(f"No users subscribed to {notification_type} notifications")
            return
        
        # Build the message
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        message = f"🏆 <b>Auction Update</b>\n\n"
        message += f"⚡ <b>Action:</b> {action.replace('_', ' ').title()}\n"
        message += f"🕐 <b>Time:</b> {timestamp}\n\n"
        
        if round_info:
            message += f"🎯 <b>Round Info:</b>\n"
            for key, value in round_info.items():
                message += f"  • <b>{key.replace('_', ' ').title()}:</b> {value}\n"
            message += "\\n"
        
        if player_info:
            message += f"⭐ <b>Player Info:</b>\n"
            for key, value in player_info.items():
                message += f"  • <b>{key.replace('_', ' ').title()}:</b> {value}\n"
            message += "\\n"
        
        if team_info:
            message += f"🏟️ <b>Team Info:</b>\n"
            for key, value in team_info.items():
                message += f"  • <b>{key.replace('_', ' ').title()}:</b> {value}\n"
        
        # Send to all subscribed users
        sent_count = 0
        details = {
            'round_info': round_info,
            'player_info': player_info,
            'team_info': team_info
        }
        
        for tg_user in telegram_users:
            try:
                # Create log entry
                log = NotificationLog.create_log(
                    telegram_user_id=tg_user.id,
                    notification_type=notification_type,
                    message=message,
                    user_action=f"Auction: {action}",
                    message_data=details
                )
                
                # Queue the notification
                notification_data = {
                    'type': 'message',
                    'chat_id': tg_user.telegram_chat_id,
                    'text': message,
                    'parse_mode': 'HTML',
                    'disable_notification': action not in ['auction_start', 'auction_end']
                }
                
                self.telegram_bot.queue_notification(notification_data)
                log.mark_sent()
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send auction notification to user {tg_user.user_id}: {e}")
                if 'log' in locals():
                    log.mark_failed(str(e))
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info(f"Queued {sent_count} auction notifications: {action}")
        except Exception as e:
            logger.error(f"Failed to commit auction notification logs: {e}")
            db.session.rollback()
    
    def register_telegram_user(self, user_id: int, chat_id: str, username: str = None,
                             first_name: str = None, last_name: str = None):
        """
        Register a new Telegram user or update existing one
        
        Args:
            user_id: Internal app user ID
            chat_id: Telegram chat ID
            username: Telegram username
            first_name: First name
            last_name: Last name
        """
        try:
            # Check if user already exists
            existing_user = TelegramUser.query.filter_by(user_id=user_id).first()
            
            if existing_user:
                # Update existing user
                existing_user.telegram_chat_id = str(chat_id)
                existing_user.telegram_username = username
                existing_user.first_name = first_name
                existing_user.last_name = last_name
                existing_user.is_active = True
                existing_user.updated_at = datetime.now(timezone.utc)
                logger.info(f"Updated Telegram user for user_id {user_id}")
            else:
                # Create new user
                new_user = TelegramUser(
                    user_id=user_id,
                    telegram_chat_id=str(chat_id),
                    telegram_username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                db.session.add(new_user)
                logger.info(f"Created new Telegram user for user_id {user_id}")
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to register Telegram user: {e}")
            db.session.rollback()
            return False
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        try:
            total_users = TelegramUser.query.count()
            active_users = TelegramUser.query.filter_by(is_active=True).count()
            
            # Get notification counts by status
            from sqlalchemy import func
            status_counts = db.session.query(
                NotificationLog.status,
                func.count(NotificationLog.id)
            ).group_by(NotificationLog.status).all()
            
            status_dict = {status: count for status, count in status_counts}
            
            # Get notification counts by type
            type_counts = db.session.query(
                NotificationLog.notification_type,
                func.count(NotificationLog.id)
            ).group_by(NotificationLog.notification_type).all()
            
            type_dict = {ntype: count for ntype, count in type_counts}
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': total_users - active_users,
                'status_counts': status_dict,
                'type_counts': type_dict,
                'bot_enabled': self.telegram_bot is not None
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return {}

# Global notification service instance
notification_service = None

def init_notification_service():
    """Initialize the global notification service"""
    global notification_service
    notification_service = NotificationService()
    logger.info("Notification service initialized")
    return notification_service

def get_notification_service() -> Optional[NotificationService]:
    """Get the global notification service instance"""
    return notification_service

# Decorator for tracking user actions
def track_user_action(action_description: str, notification_type: str = 'admin_actions', 
                     include_details: bool = True):
    """
    Decorator to automatically track user actions and send notifications
    
    Args:
        action_description: Description of the action being tracked
        notification_type: Type of notification to send
        include_details: Whether to include request details in the notification
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)
            
            try:
                # Get current user
                from flask_login import current_user
                from flask import request
                
                if current_user.is_authenticated and notification_service:
                    details = None
                    if include_details:
                        details = {
                            'endpoint': request.endpoint or 'unknown',
                            'method': request.method,
                            'url': request.url,
                            'user_agent': request.headers.get('User-Agent', 'unknown')[:100]
                        }
                        
                        # Add form data if it's a POST request (excluding sensitive fields)
                        if request.method == 'POST' and request.form:
                            form_data = {}
                            sensitive_fields = ['password', 'token', 'secret']
                            for key, value in request.form.items():
                                if not any(sensitive in key.lower() for sensitive in sensitive_fields):
                                    form_data[key] = str(value)[:100]  # Limit length
                            if form_data:
                                details['form_data'] = form_data
                    
                    # Send notification
                    notification_service.send_user_action_notification(
                        user_action=action_description,
                        actor_user_id=current_user.id,
                        details=details,
                        notification_type=notification_type
                    )
            
            except Exception as e:
                logger.error(f"Failed to track user action '{action_description}': {e}")
            
            return result
        return wrapper
    return decorator
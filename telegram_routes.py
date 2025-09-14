from flask import Blueprint, request, jsonify, current_app
from models import db, User, TelegramUser, NotificationSettings
from telegram_service import get_telegram_bot
from notification_service import get_notification_service
import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Create blueprint for Telegram routes
telegram_bp = Blueprint('telegram', __name__, url_prefix='/telegram')

def handle_telegram_message(update: Dict[str, Any]):
    """Handle incoming Telegram messages"""
    try:
        message = update.get('message', {})
        chat = message.get('chat', {})
        from_user = message.get('from', {})
        text = message.get('text', '')
        
        chat_id = str(chat.get('id'))
        username = from_user.get('username')
        first_name = from_user.get('first_name', '')
        last_name = from_user.get('last_name', '')
        
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            logger.error("Telegram bot not available")
            return
        
        # Handle commands with interactive buttons
        if text.startswith('/start') or text.startswith('/menu'):
            # Check if /start has parameters for deep linking
            start_param = None
            if text.startswith('/start ') and len(text.split()) > 1:
                start_param = text.split(' ', 1)[1]
            handle_start_command(chat_id, username, first_name, last_name, start_param)
        elif text.startswith('/help'):
            handle_help_command(chat_id)
        elif text.startswith('/link'):
            handle_link_command(chat_id, text, username, first_name, last_name)
        elif text.startswith('/status'):
            handle_status_command(chat_id)
        elif text.startswith('/notifications'):
            handle_notifications_command(chat_id, text)
        elif text.startswith('/unlink'):
            handle_unlink_command(chat_id)
        elif text.startswith('/stats'):
            handle_stats_command(chat_id)
        else:
            # Show main menu for unknown commands
            show_main_menu(chat_id, "❓ Unknown command. Here's the main menu:")
    
    except Exception as e:
        logger.error(f"Error handling Telegram message: {e}")

def handle_telegram_callback_query(update: Dict[str, Any]):
    """Handle incoming Telegram callback queries from inline keyboards"""
    try:
        callback_query = update.get('callback_query', {})
        message = callback_query.get('message', {})
        chat = message.get('chat', {})
        from_user = callback_query.get('from', {})
        data = callback_query.get('data', '')
        callback_query_id = callback_query.get('id')
        
        chat_id = str(chat.get('id'))
        message_id = message.get('message_id')
        username = from_user.get('username')
        first_name = from_user.get('first_name', '')
        last_name = from_user.get('last_name', '')
        
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            logger.error("Telegram bot not available")
            return
        
        # Handle different callback actions
        if data.startswith('menu_'):
            handle_menu_callback(chat_id, message_id, data, callback_query_id)
        elif data.startswith('notif_'):
            handle_notification_callback(chat_id, message_id, data, callback_query_id, username, first_name, last_name)
        elif data.startswith('confirm_') or data.startswith('cancel_'):
            handle_confirmation_callback(chat_id, message_id, data, callback_query_id)
        elif data == 'noop':
            # No operation - just answer the callback
            telegram_bot.answer_callback_query(callback_query_id)
        else:
            # Unknown callback data
            telegram_bot.answer_callback_query(callback_query_id, "❓ Unknown action")
    
    except Exception as e:
        logger.error(f"Error handling Telegram callback query: {e}")

def show_main_menu(chat_id: str, message_text: str = None):
    """Show the main interactive menu"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    if not message_text:
        message_text = "🏠 <b>Main Menu</b>\n\nChoose an option:"
    
    reply_markup = telegram_bot.create_main_menu_buttons()
    
    telegram_bot.send_message(
        chat_id=chat_id,
        text=message_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

def handle_menu_callback(chat_id: str, message_id: int, data: str, callback_query_id: str):
    """Handle main menu callback actions"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    action = data.replace('menu_', '')
    
    if action == 'main':
        # Return to main menu
        new_text = "🏠 <b>Main Menu</b>\n\nChoose an option:"
        reply_markup = telegram_bot.create_main_menu_buttons()
        
        telegram_bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=new_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
    elif action == 'status':
        handle_status_callback(chat_id, message_id, callback_query_id)
        
    elif action == 'notifications':
        handle_notifications_menu_callback(chat_id, message_id, callback_query_id)
        
    elif action == 'stats':
        handle_stats_callback(chat_id, message_id, callback_query_id)
        
    elif action == 'help':
        handle_help_callback(chat_id, message_id, callback_query_id)
        
    elif action == 'link':
        handle_link_callback(chat_id, message_id, callback_query_id)
        
    elif action == 'unlink':
        handle_unlink_callback(chat_id, message_id, callback_query_id)
    
    telegram_bot.answer_callback_query(callback_query_id)

def handle_start_command(chat_id: str, username: str, first_name: str, last_name: str, start_param: str = None):
    """Handle /start command with interactive buttons and deep linking support"""
    telegram_bot = get_telegram_bot()
    notification_service = get_notification_service()
    
    if not telegram_bot:
        return
    
    # Handle deep linking for automatic account linking
    if start_param and start_param.startswith('link_'):
        handle_deep_link_auto_connect(chat_id, username, first_name, last_name, start_param)
        return
    
    # Check if user is already linked
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    
    if tg_user:
        # User is already linked - show personalized welcome
        welcome_message = f"""
🤖 <b>Welcome back, {first_name}!</b>

You're linked to account: <b>{tg_user.user.username}</b>
🔔 Notifications: {'✅ Enabled' if tg_user.is_active else '❌ Disabled'}

<b>Quick Actions:</b>
📊 Check your notification status
🔔 Manage notification preferences
📈 View statistics (admin only)
        """
    else:
        # User not linked - show welcome with link instructions
        welcome_message = f"""
🤖 <b>Welcome to the Auction App Bot!</b>

Hello {first_name}! I'll send you notifications about all app activities.

<b>To get started:</b>
🔗 Link your account using the button in your profile
🔔 Or use: <code>/link your_username</code>

<b>Quick Actions:</b>
📊 Check your notification status
🔔 Manage notification preferences
📈 View statistics (admin only)
        """
    
    reply_markup = telegram_bot.create_main_menu_buttons()
    
    telegram_bot.send_message(
        chat_id=chat_id,
        text=welcome_message.strip(),
        parse_mode='HTML',
        reply_markup=reply_markup
    )

def handle_deep_link_auto_connect(chat_id: str, username: str, first_name: str, last_name: str, start_param: str):
    """Handle automatic account linking from deep link"""
    telegram_bot = get_telegram_bot()
    notification_service = get_notification_service()
    
    if not telegram_bot or not notification_service:
        return
    
    try:
        # Extract token from start parameter
        token = start_param.replace('link_', '')
        
        # Validate the token
        validation_result = telegram_bot.validate_link_token(token)
        
        if not validation_result.get('valid'):
            error_msg = validation_result.get('error', 'Invalid link')
            telegram_bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>Link Failed</b>\n\n{error_msg}\n\nPlease request a new link from your profile or use <code>/link your_username</code> manually.",
                parse_mode='HTML',
                reply_markup=telegram_bot.create_main_menu_buttons()
            )
            return
        
        # Extract user info from validated token
        app_user_id = validation_result['user_id']
        app_username = validation_result['username']
        
        # Find user in app database
        user = User.query.get(app_user_id)
        if not user or user.username != app_username:
            telegram_bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>Account Not Found</b>\n\nThe linked account '{app_username}' was not found. It may have been deleted or modified.\n\nPlease contact support if this error persists.",
                parse_mode='HTML',
                reply_markup=telegram_bot.create_main_menu_buttons()
            )
            return
        
        # Check if user is already linked to another Telegram account
        existing_link = TelegramUser.query.filter_by(user_id=user.id).first()
        if existing_link and existing_link.telegram_chat_id != chat_id:
            telegram_bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>Already Linked</b>\n\nAccount '{app_username}' is already linked to another Telegram account.\n\nIf you believe this is an error, please contact support.",
                parse_mode='HTML',
                reply_markup=telegram_bot.create_main_menu_buttons()
            )
            return
        
        # Check if this Telegram account is already linked to another user
        existing_telegram = TelegramUser.get_by_chat_id(chat_id)
        if existing_telegram and existing_telegram.user_id != user.id:
            telegram_bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>Account Conflict</b>\n\nYour Telegram is already linked to '{existing_telegram.user.username}'.\n\nUse /unlink first if you want to link to a different account.",
                parse_mode='HTML',
                reply_markup=telegram_bot.create_main_menu_buttons()
            )
            return
        
        # Perform the automatic linking
        success = notification_service.register_telegram_user(
            user_id=user.id,
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        if success:
            # Success message with celebration
            success_message = f"""
✨ <b>Account Linked Successfully!</b> ✨

Your Telegram is now connected to:
👤 <b>Username:</b> {app_username}
🔔 <b>Notifications:</b> ✅ Enabled

🎉 <b>You're all set!</b> You'll now receive:
• Login activity alerts
• Auction notifications  
• Team updates
• System announcements

<i>Welcome to the notification system!</i>
            """
            
            # Create buttons for immediate actions
            quick_buttons = {
                "inline_keyboard": [
                    [{"text": "📊 View Status", "callback_data": "menu_status"}],
                    [{"text": "🔔 Manage Notifications", "callback_data": "menu_notifications"}],
                    [{"text": "🏠 Main Menu", "callback_data": "menu_main"}]
                ]
            }
            
            telegram_bot.send_message(
                chat_id=chat_id,
                text=success_message.strip(),
                parse_mode='HTML',
                reply_markup=quick_buttons
            )
            
            # Send notification to admin about successful auto-link
            try:
                notification_service.send_user_action_notification(
                    user_action=f"User auto-linked Telegram via deep link",
                    actor_user_id=user.id,
                    details={
                        'telegram_username': username,
                        'telegram_chat_id': chat_id,
                        'first_name': first_name,
                        'last_name': last_name,
                        'link_method': 'deep_link_auto'
                    },
                    notification_type='admin_actions'
                )
            except Exception as e:
                logger.error(f"Failed to send auto-link notification: {e}")
        else:
            telegram_bot.send_message(
                chat_id=chat_id,
                text="❌ <b>Link Failed</b>\n\nThere was an error linking your account. Please try again or contact support.",
                parse_mode='HTML',
                reply_markup=telegram_bot.create_main_menu_buttons()
            )
            
    except Exception as e:
        logger.error(f"Error in deep link auto-connect: {e}")
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ <b>Link Error</b>\n\nAn unexpected error occurred while linking your account. Please try again later.",
            parse_mode='HTML',
            reply_markup=telegram_bot.create_main_menu_buttons()
        )

def handle_help_command(chat_id: str):
    """Handle /help command"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    help_message = """
🤖 <b>Auction App Bot - Help</b>

<b>Commands:</b>
• <code>/start</code> - Welcome message and setup
• <code>/help</code> - Show this help message
• <code>/link &lt;username&gt;</code> - Link Telegram to app account
• <code>/status</code> - Check notification settings
• <code>/notifications on|off [type]</code> - Manage preferences
• <code>/unlink</code> - Unlink your account
• <code>/stats</code> - View notification statistics

<b>Notification Types:</b>
• <code>login</code> - User login activities
• <code>bids</code> - Auction bids and results
• <code>auction_start</code> - Auction round starts
• <code>auction_end</code> - Auction round ends
• <code>team_changes</code> - Team modifications
• <code>admin_actions</code> - Administrative actions
• <code>system_alerts</code> - System notifications

<b>Examples:</b>
• <code>/link john123</code> - Link account
• <code>/notifications off bids</code> - Disable bid notifications
• <code>/notifications on</code> - Enable all notifications
    """
    
    telegram_bot.send_message(
        chat_id=chat_id,
        text=help_message.strip(),
        parse_mode='HTML'
    )

def handle_link_command(chat_id: str, text: str, username: str, first_name: str, last_name: str):
    """Handle /link username command"""
    telegram_bot = get_telegram_bot()
    notification_service = get_notification_service()
    
    if not telegram_bot or not notification_service:
        return
    
    parts = text.split()
    if len(parts) != 2:
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Usage: <code>/link your_app_username</code>",
            parse_mode='HTML'
        )
        return
    
    app_username = parts[1].strip()
    
    # Find user in app database
    user = User.query.filter_by(username=app_username).first()
    if not user:
        telegram_bot.send_message(
            chat_id=chat_id,
            text=f"❌ User '{app_username}' not found in the app. Please check your username.",
            parse_mode='HTML'
        )
        return
    
    # Check if user is already linked
    existing_link = TelegramUser.query.filter_by(user_id=user.id).first()
    if existing_link and existing_link.telegram_chat_id != chat_id:
        telegram_bot.send_message(
            chat_id=chat_id,
            text=f"❌ User '{app_username}' is already linked to another Telegram account.",
            parse_mode='HTML'
        )
        return
    
    # Register or update the Telegram user
    success = notification_service.register_telegram_user(
        user_id=user.id,
        chat_id=chat_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    
    if success:
        telegram_bot.send_message(
            chat_id=chat_id,
            text=f"✅ Successfully linked your Telegram to app user '<b>{app_username}</b>'!\\n\\n"
                 f"You'll now receive notifications about app activities. "
                 f"Use <code>/status</code> to check your settings.",
            parse_mode='HTML'
        )
        
        # Send notification to admin about new link
        try:
            notification_service.send_user_action_notification(
                user_action=f"User linked Telegram account",
                actor_user_id=user.id,
                details={
                    'telegram_username': username,
                    'telegram_chat_id': chat_id,
                    'first_name': first_name,
                    'last_name': last_name
                },
                notification_type='admin_actions'
            )
        except Exception as e:
            logger.error(f"Failed to send link notification: {e}")
    else:
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Failed to link your account. Please try again later.",
            parse_mode='HTML'
        )

def handle_status_command(chat_id: str):
    """Handle /status command"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    # Find Telegram user
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    if not tg_user:
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Your Telegram is not linked to any app account. Use <code>/link username</code> to link it.",
            parse_mode='HTML'
        )
        return
    
    # Show current settings
    status_message = f"""
📊 <b>Notification Status</b>

<b>Account:</b> {tg_user.user.username}
<b>Status:</b> {'✅ Active' if tg_user.is_active else '❌ Inactive'}

<b>Notification Preferences:</b>
• Login: {'✅' if tg_user.notify_login else '❌'}
• Bids: {'✅' if tg_user.notify_bids else '❌'}  
• Auction Start: {'✅' if tg_user.notify_auction_start else '❌'}
• Auction End: {'✅' if tg_user.notify_auction_end else '❌'}
• Team Changes: {'✅' if tg_user.notify_team_changes else '❌'}
• Admin Actions: {'✅' if tg_user.notify_admin_actions else '❌'}
• System Alerts: {'✅' if tg_user.notify_system_alerts else '❌'}

Use <code>/notifications</code> to change preferences.
    """
    
    telegram_bot.send_message(
        chat_id=chat_id,
        text=status_message.strip(),
        parse_mode='HTML'
    )

def handle_notifications_command(chat_id: str, text: str):
    """Handle /notifications command"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    # Find Telegram user
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    if not tg_user:
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Your Telegram is not linked to any app account. Use <code>/link username</code> to link it.",
            parse_mode='HTML'
        )
        return
    
    parts = text.split()
    if len(parts) == 1:
        # Show help for notifications command
        help_text = """
🔔 <b>Notification Settings</b>

<b>Usage:</b>
• <code>/notifications on</code> - Enable all notifications
• <code>/notifications off</code> - Disable all notifications  
• <code>/notifications on [type]</code> - Enable specific type
• <code>/notifications off [type]</code> - Disable specific type

<b>Available types:</b>
• <code>login</code> - User login activities
• <code>bids</code> - Auction bids and results
• <code>auction_start</code> - Auction round starts
• <code>auction_end</code> - Auction round ends
• <code>team_changes</code> - Team modifications
• <code>admin_actions</code> - Administrative actions
• <code>system_alerts</code> - System notifications

<b>Examples:</b>
• <code>/notifications off bids</code> - Disable bid notifications
• <code>/notifications on login</code> - Enable login notifications
        """
        telegram_bot.send_message(
            chat_id=chat_id,
            text=help_text.strip(),
            parse_mode='HTML'
        )
        return
    
    if len(parts) < 2 or parts[1] not in ['on', 'off']:
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Usage: <code>/notifications on|off [type]</code>",
            parse_mode='HTML'
        )
        return
    
    enable = parts[1] == 'on'
    notification_type = parts[2] if len(parts) > 2 else None
    
    # Map notification types to database fields
    type_mapping = {
        'login': 'notify_login',
        'bids': 'notify_bids',
        'auction_start': 'notify_auction_start',
        'auction_end': 'notify_auction_end',
        'team_changes': 'notify_team_changes',
        'admin_actions': 'notify_admin_actions',
        'system_alerts': 'notify_system_alerts'
    }
    
    try:
        if notification_type:
            # Update specific notification type
            if notification_type not in type_mapping:
                telegram_bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Unknown notification type '{notification_type}'. Use <code>/notifications</code> for help.",
                    parse_mode='HTML'
                )
                return
            
            setattr(tg_user, type_mapping[notification_type], enable)
            action = "enabled" if enable else "disabled"
            
            telegram_bot.send_message(
                chat_id=chat_id,
                text=f"✅ {notification_type.replace('_', ' ').title()} notifications {action}.",
                parse_mode='HTML'
            )
        else:
            # Update all notification types
            for field in type_mapping.values():
                setattr(tg_user, field, enable)
            
            action = "enabled" if enable else "disabled"
            telegram_bot.send_message(
                chat_id=chat_id,
                text=f"✅ All notifications {action}.",
                parse_mode='HTML'
            )
        
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        db.session.rollback()
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Failed to update notification settings. Please try again.",
            parse_mode='HTML'
        )

def handle_unlink_command(chat_id: str):
    """Handle /unlink command"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    # Find Telegram user
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    if not tg_user:
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Your Telegram is not linked to any app account.",
            parse_mode='HTML'
        )
        return
    
    try:
        username = tg_user.user.username
        user_id = tg_user.user.id
        telegram_user_id = tg_user.id
        
        # Send notification to admin BEFORE unlinking (while TelegramUser still exists)
        try:
            notification_service = get_notification_service()
            if notification_service:
                # Create a special admin notification about the unlink
                from models import NotificationLog, User
                admin_users = User.query.filter_by(is_admin=True).all()
                for admin_user in admin_users:
                    admin_tg_user = TelegramUser.query.filter_by(user_id=admin_user.id, is_active=True).first()
                    if admin_tg_user and admin_tg_user.notify_admin_actions:
                        message = f"🔗❌ <b>User Unlinked Telegram</b>\n\n👤 <b>User:</b> {username}\n📱 <b>Chat ID:</b> {chat_id}\n🕒 <b>Time:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                        
                        # Log the notification
                        log_entry = NotificationLog.create_log(
                            telegram_user_id=admin_tg_user.id,
                            notification_type='admin_actions',
                            message=message,
                            user_action='User unlinked Telegram account',
                            actor_user_id=user_id,
                            message_data=json.dumps({
                                'telegram_chat_id': chat_id,
                                'unlinked_username': username
                            })
                        )
                        
                        # Send the actual Telegram message
                        success = telegram_bot.send_message(
                            chat_id=admin_tg_user.telegram_chat_id,
                            text=message,
                            parse_mode='HTML'
                        )
                        
                        if success:
                            log_entry.mark_sent()
                        else:
                            log_entry.mark_failed("Failed to send message")
                        
                        db.session.add(log_entry)
                        
        except Exception as e:
            logger.error(f"Failed to send unlink notification: {e}")
        
        # Now remove the Telegram user (this will cascade to logs if configured properly)
        db.session.delete(tg_user)
        db.session.commit()
        
        telegram_bot.send_message(
            chat_id=chat_id,
            text=f"✅ Successfully unlinked from app user '<b>{username}</b>'. You will no longer receive notifications.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error unlinking user: {e}")
        db.session.rollback()
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Failed to unlink your account. Please try again.",
            parse_mode='HTML'
        )

def handle_stats_command(chat_id: str):
    """Handle /stats command"""
    telegram_bot = get_telegram_bot()
    notification_service = get_notification_service()
    
    if not telegram_bot or not notification_service:
        return
    
    # Check if user is linked and has admin access
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    if not tg_user:
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Your Telegram is not linked to any app account. Use <code>/link username</code> to link it.",
            parse_mode='HTML'
        )
        return
    
    if not tg_user.user.is_admin:
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Only administrators can view statistics.",
            parse_mode='HTML'
        )
        return
    
    try:
        stats = notification_service.get_notification_stats()
        
        stats_message = f"""
📊 <b>Notification Statistics</b>

<b>Users:</b>
• Total: {stats.get('total_users', 0)}
• Active: {stats.get('active_users', 0)}
• Inactive: {stats.get('inactive_users', 0)}

<b>Notifications by Status:</b>
"""
        
        status_counts = stats.get('status_counts', {})
        for status, count in status_counts.items():
            stats_message += f"• {status.title()}: {count}\\n"
        
        stats_message += "\\n<b>Notifications by Type:</b>\\n"
        type_counts = stats.get('type_counts', {})
        for ntype, count in type_counts.items():
            stats_message += f"• {ntype.replace('_', ' ').title()}: {count}\\n"
        
        stats_message += f"\\n<b>Bot Status:</b> {'✅ Enabled' if stats.get('bot_enabled') else '❌ Disabled'}"
        
        telegram_bot.send_message(
            chat_id=chat_id,
            text=stats_message.strip(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        telegram_bot.send_message(
            chat_id=chat_id,
            text="❌ Failed to retrieve statistics. Please try again.",
            parse_mode='HTML'
        )

@telegram_bp.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Handle incoming Telegram webhook requests"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        update = request.get_json()
        
        if not update:
            return jsonify({'error': 'Empty request body'}), 400
        
        # Handle the update
        if 'message' in update:
            handle_telegram_message(update)
        elif 'callback_query' in update:
            handle_telegram_callback_query(update)
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@telegram_bp.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    """Set the webhook URL for the Telegram bot (admin only)"""
    try:
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            if request.method == 'GET':
                return f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Telegram Webhook Setup - Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                        .error {{ color: #dc3545; background: #f8d7da; padding: 15px; border-radius: 5px; }}
                    </style>
                </head>
                <body>
                    <h1>❌ Telegram Bot Not Available</h1>
                    <div class="error">The Telegram bot service is not currently available. Please check the server configuration.</div>
                </body>
                </html>
                '''
            return jsonify({'error': 'Telegram bot not available'}), 503
        
        webhook_url = current_app.config.get('TELEGRAM_WEBHOOK_URL')
        if not webhook_url:
            error_msg = 'TELEGRAM_WEBHOOK_URL not configured'
            if request.method == 'GET':
                return f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Telegram Webhook Setup - Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                        .error {{ color: #dc3545; background: #f8d7da; padding: 15px; border-radius: 5px; }}
                    </style>
                </head>
                <body>
                    <h1>❌ Configuration Error</h1>
                    <div class="error">{error_msg}</div>
                </body>
                </html>
                '''
            return jsonify({'error': error_msg}), 400
        
        success = telegram_bot.set_webhook(webhook_url)
        
        if success:
            if request.method == 'GET':
                return f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Telegram Webhook Setup - Success</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                        .success {{ color: #155724; background: #d4edda; padding: 15px; border-radius: 5px; }}
                        .info {{ color: #0c5460; background: #d1ecf1; padding: 15px; border-radius: 5px; margin-top: 15px; }}
                        .btn {{ display: inline-block; background: #007bff; color: white; padding: 10px 20px; 
                                text-decoration: none; border-radius: 5px; margin-top: 15px; }}
                        .btn:hover {{ background: #0056b3; }}
                    </style>
                </head>
                <body>
                    <h1>✅ Webhook Set Successfully!</h1>
                    <div class="success">
                        <strong>Webhook URL:</strong> {webhook_url}<br>
                        <strong>Status:</strong> Active
                    </div>
                    <div class="info">
                        <strong>What this means:</strong><br>
                        • Your Telegram bot is now ready to receive messages<br>
                        • Users can interact with @ssleaguebot<br>
                        • Real-time notifications will be delivered<br>
                        • Bot commands will work properly
                    </div>
                    <a href="/telegram/webhook_info" class="btn">Check Webhook Status</a>
                    <a href="/admin/notifications/" class="btn">Admin Panel</a>
                </body>
                </html>
                '''
            return jsonify({'success': True, 'webhook_url': webhook_url})
        else:
            error_msg = 'Failed to set webhook - please check your configuration'
            if request.method == 'GET':
                return f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Telegram Webhook Setup - Failed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                        .error {{ color: #dc3545; background: #f8d7da; padding: 15px; border-radius: 5px; }}
                    </style>
                </head>
                <body>
                    <h1>❌ Webhook Setup Failed</h1>
                    <div class="error">{error_msg}</div>
                </body>
                </html>
                '''
            return jsonify({'error': error_msg}), 500
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        error_msg = f'Error setting webhook: {str(e)}'
        if request.method == 'GET':
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Telegram Webhook Setup - Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                    .error {{ color: #dc3545; background: #f8d7da; padding: 15px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>❌ Setup Error</h1>
                <div class="error">{error_msg}</div>
            </body>
            </html>
            '''
        return jsonify({'error': str(e)}), 500

@telegram_bp.route('/webhook_info', methods=['GET'])
def webhook_info():
    """Get current webhook information"""
    try:
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            if request.headers.get('Accept', '').startswith('text/html'):
                return '''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Telegram Webhook Info - Error</title>
                    <style>
                        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                        .error { color: #dc3545; background: #f8d7da; padding: 15px; border-radius: 5px; }
                    </style>
                </head>
                <body>
                    <h1>❌ Telegram Bot Not Available</h1>
                    <div class="error">The Telegram bot service is not currently available.</div>
                </body>
                </html>
                '''
            return jsonify({'error': 'Telegram bot not available'}), 503
        
        info = telegram_bot.get_webhook_info()
        
        # Return HTML for browser requests, JSON for API requests
        if request.headers.get('Accept', '').startswith('text/html'):
            result = info.get('result', {})
            webhook_url = result.get('url', 'Not set')
            pending_updates = result.get('pending_update_count', 0)
            has_custom_cert = result.get('has_custom_certificate', False)
            last_error_date = result.get('last_error_date')
            last_error_message = result.get('last_error_message', '')
            
            # Format last error date if exists
            error_info = ''
            if last_error_date:
                import datetime
                error_time = datetime.datetime.fromtimestamp(last_error_date)
                error_info = f'''
                <div class="warning">
                    <strong>⚠️ Last Error:</strong><br>
                    <strong>Time:</strong> {error_time}<br>
                    <strong>Message:</strong> {last_error_message}
                </div>
                '''
            
            # Determine status color
            status_class = 'success' if webhook_url != 'Not set' and not last_error_date else 'warning' if webhook_url != 'Not set' else 'error'
            status_icon = '✅' if webhook_url != 'Not set' and not last_error_date else '⚠️' if webhook_url != 'Not set' else '❌'
            
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Telegram Webhook Information</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                    .success {{ color: #155724; background: #d4edda; padding: 15px; border-radius: 5px; }}
                    .warning {{ color: #856404; background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 15px; }}
                    .error {{ color: #dc3545; background: #f8d7da; padding: 15px; border-radius: 5px; }}
                    .info {{ color: #0c5460; background: #d1ecf1; padding: 15px; border-radius: 5px; margin-top: 15px; }}
                    .btn {{ display: inline-block; background: #007bff; color: white; padding: 10px 20px; 
                            text-decoration: none; border-radius: 5px; margin: 10px 5px 0 0; }}
                    .btn:hover {{ background: #0056b3; }}
                    .btn-success {{ background: #28a745; }}
                    .btn-success:hover {{ background: #1e7e34; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                    th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <h1>{status_icon} Telegram Webhook Status</h1>
                
                <div class="{status_class}">
                    <strong>Current Status:</strong> {"Active" if webhook_url != 'Not set' else "Not Configured"}
                </div>
                
                <table>
                    <tr><th>Property</th><th>Value</th></tr>
                    <tr><td><strong>Webhook URL</strong></td><td>{webhook_url}</td></tr>
                    <tr><td><strong>Pending Updates</strong></td><td>{pending_updates}</td></tr>
                    <tr><td><strong>Custom Certificate</strong></td><td>{"Yes" if has_custom_cert else "No"}</td></tr>
                    <tr><td><strong>Bot Username</strong></td><td>@ssleaguebot</td></tr>
                </table>
                
                {error_info}
                
                <div class="info">
                    <strong>What this means:</strong><br>
                    {'• ✅ Webhook is active and ready to receive messages' if webhook_url != 'Not set' else '• ❌ Webhook is not configured - bot will not receive messages'}<br>
                    {'• ✅ Users can interact with the bot' if webhook_url != 'Not set' else '• ❌ Bot commands will not work'}<br>
                    {'• ✅ Notifications will be delivered' if webhook_url != 'Not set' else '• ❌ Notifications cannot be sent'}
                </div>
                
                <a href="/telegram/set_webhook" class="btn btn-success">Set Webhook</a>
                <a href="/admin/notifications/" class="btn">Admin Panel</a>
                <a href="#" onclick="location.reload()" class="btn">Refresh</a>
            </body>
            </html>
            '''
        
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        if request.headers.get('Accept', '').startswith('text/html'):
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Telegram Webhook Info - Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                    .error {{ color: #dc3545; background: #f8d7da; padding: 15px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>❌ Error Getting Webhook Info</h1>
                <div class="error">{str(e)}</div>
            </body>
            </html>
            '''
        return jsonify({'error': str(e)}), 500

# Interactive Button Callback Handlers

def handle_status_callback(chat_id: str, message_id: int, callback_query_id: str):
    """Handle status button callback"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    # Find Telegram user
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    if not tg_user:
        new_text = "❌ <b>Account Not Linked</b>\n\nYour Telegram is not linked to any app account.\nUse the 'Link Account' button to connect it."
        reply_markup = telegram_bot.create_main_menu_buttons()
    else:
        # Show current settings with back button
        status_message = f"""
📊 <b>Notification Status</b>

<b>Account:</b> {tg_user.user.username}
<b>Status:</b> {'✅ Active' if tg_user.is_active else '❌ Inactive'}

<b>Notification Preferences:</b>
• Login: {'✅' if tg_user.notify_login else '❌'}
• Bids: {'✅' if tg_user.notify_bids else '❌'}  
• Auction Start: {'✅' if tg_user.notify_auction_start else '❌'}
• Auction End: {'✅' if tg_user.notify_auction_end else '❌'}
• Team Changes: {'✅' if tg_user.notify_team_changes else '❌'}
• Admin Actions: {'✅' if tg_user.notify_admin_actions else '❌'}
• System Alerts: {'✅' if tg_user.notify_system_alerts else '❌'}
        """
        new_text = status_message.strip()
        reply_markup = {"inline_keyboard": [[
            {"text": "🔔 Manage Notifications", "callback_data": "menu_notifications"},
            {"text": "🏠 Back to Menu", "callback_data": "menu_main"}
        ]]}
    
    telegram_bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=new_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    telegram_bot.answer_callback_query(callback_query_id)

def handle_notifications_menu_callback(chat_id: str, message_id: int, callback_query_id: str):
    """Handle notifications menu button callback"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    # Find Telegram user
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    if not tg_user:
        new_text = "❌ <b>Account Not Linked</b>\n\nYour Telegram is not linked to any app account.\nPlease link your account first."
        reply_markup = telegram_bot.create_main_menu_buttons()
    else:
        new_text = "🔔 <b>Notification Settings</b>\n\nChoose what to manage:"
        reply_markup = telegram_bot.create_notification_settings_buttons()
    
    telegram_bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=new_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    telegram_bot.answer_callback_query(callback_query_id)

def handle_notification_callback(chat_id: str, message_id: int, data: str, callback_query_id: str, username: str, first_name: str, last_name: str):
    """Handle notification setting callbacks"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    # Find Telegram user
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    if not tg_user:
        telegram_bot.answer_callback_query(callback_query_id, "❌ Account not linked")
        return
    
    action = data.replace('notif_', '')
    
    try:
        if action == 'enable_all':
            # Enable all notifications
            tg_user.notify_login = True
            tg_user.notify_bids = True
            tg_user.notify_auction_start = True
            tg_user.notify_auction_end = True
            tg_user.notify_team_changes = True
            tg_user.notify_admin_actions = True
            tg_user.notify_system_alerts = True
            db.session.commit()
            telegram_bot.answer_callback_query(callback_query_id, "✅ All notifications enabled!")
            
        elif action == 'disable_all':
            # Disable all notifications
            tg_user.notify_login = False
            tg_user.notify_bids = False
            tg_user.notify_auction_start = False
            tg_user.notify_auction_end = False
            tg_user.notify_team_changes = False
            tg_user.notify_admin_actions = False
            tg_user.notify_system_alerts = False
            db.session.commit()
            telegram_bot.answer_callback_query(callback_query_id, "❌ All notifications disabled!")
            
        elif action.startswith('toggle_'):
            # Toggle specific notification type
            toggle_type = action.replace('toggle_', '')
            type_mapping = {
                'login': 'notify_login',
                'bids': 'notify_bids',
                'auctions': 'notify_auction_start',  # Toggle both auction start and end
                'teams': 'notify_team_changes',
                'admin': 'notify_admin_actions',
                'alerts': 'notify_system_alerts'
            }
            
            if toggle_type in type_mapping:
                field = type_mapping[toggle_type]
                current_value = getattr(tg_user, field)
                setattr(tg_user, field, not current_value)
                
                # For auctions, toggle both start and end
                if toggle_type == 'auctions':
                    setattr(tg_user, 'notify_auction_end', not current_value)
                
                db.session.commit()
                status = "enabled" if not current_value else "disabled"
                telegram_bot.answer_callback_query(
                    callback_query_id, 
                    f"{'✅' if not current_value else '❌'} {toggle_type.title()} notifications {status}!"
                )
        
        # Refresh the notification settings menu
        new_text = "🔔 <b>Notification Settings</b>\n\nChoose what to manage:"
        reply_markup = telegram_bot.create_notification_settings_buttons()
        
        telegram_bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=new_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        db.session.rollback()
        telegram_bot.answer_callback_query(callback_query_id, "❌ Failed to update settings")

def handle_stats_callback(chat_id: str, message_id: int, callback_query_id: str):
    """Handle stats button callback"""
    telegram_bot = get_telegram_bot()
    notification_service = get_notification_service()
    
    if not telegram_bot or not notification_service:
        return
    
    # Check if user is linked and has admin access
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    if not tg_user:
        new_text = "❌ <b>Account Not Linked</b>\n\nYour Telegram is not linked to any app account."
        reply_markup = telegram_bot.create_main_menu_buttons()
    elif not tg_user.user.is_admin:
        new_text = "❌ <b>Access Denied</b>\n\nOnly administrators can view statistics."
        reply_markup = {"inline_keyboard": [[{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]]}
    else:
        try:
            stats = notification_service.get_notification_stats()
            
            stats_message = f"""
📊 <b>Notification Statistics</b>

<b>Users:</b>
• Total: {stats.get('total_users', 0)}
• Active: {stats.get('active_users', 0)}
• Inactive: {stats.get('inactive_users', 0)}

<b>Notifications by Status:</b>
            """
            
            status_counts = stats.get('status_counts', {})
            for status, count in status_counts.items():
                stats_message += f"• {status.title()}: {count}\n"
            
            stats_message += "\n<b>Notifications by Type:</b>\n"
            type_counts = stats.get('type_counts', {})
            for ntype, count in type_counts.items():
                stats_message += f"• {ntype.replace('_', ' ').title()}: {count}\n"
            
            stats_message += f"\n<b>Bot Status:</b> {'✅ Enabled' if stats.get('bot_enabled') else '❌ Disabled'}"
            
            new_text = stats_message.strip()
            reply_markup = {"inline_keyboard": [[{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]]}
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            new_text = "❌ <b>Error</b>\n\nFailed to retrieve statistics. Please try again."
            reply_markup = {"inline_keyboard": [[{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]]}
    
    telegram_bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=new_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    telegram_bot.answer_callback_query(callback_query_id)

def handle_help_callback(chat_id: str, message_id: int, callback_query_id: str):
    """Handle help button callback"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    help_message = """
ℹ️ <b>Auction App Bot - Help</b>

<b>Features:</b>
• 🔗 Link your Telegram to your app account
• 🔔 Receive real-time notifications
• ⚙️ Customize notification preferences
• 📊 Check your account status
• 📈 View statistics (admin only)

<b>Notification Types:</b>
• 🔄 Login activities
• 🏆 Auction bids and results
• 🎯 Auction start/end events
• 👥 Team modifications
• ⚙️ Administrative actions
• ⚠️ System alerts

<b>Getting Started:</b>
1. Click 'Link Account' to connect your app username
2. Configure your preferences in 'Notifications'
3. You'll receive real-time updates!
    """
    
    reply_markup = {"inline_keyboard": [[{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]]}
    
    telegram_bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=help_message.strip(),
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    telegram_bot.answer_callback_query(callback_query_id)

def handle_link_callback(chat_id: str, message_id: int, callback_query_id: str):
    """Handle link account button callback"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    link_message = """
🔗 <b>Link Your Account</b>

To link your Telegram to your app account, send me a message in this format:

<code>/link your_app_username</code>

<b>Example:</b>
<code>/link john123</code>

Replace 'john123' with your actual app username.
    """
    
    reply_markup = {"inline_keyboard": [[{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]]}
    
    telegram_bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=link_message.strip(),
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    telegram_bot.answer_callback_query(callback_query_id)

def handle_unlink_callback(chat_id: str, message_id: int, callback_query_id: str):
    """Handle unlink account button callback"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    # Find Telegram user
    tg_user = TelegramUser.get_by_chat_id(chat_id)
    if not tg_user:
        new_text = "❌ <b>Account Not Linked</b>\n\nYour Telegram is not linked to any app account."
        reply_markup = telegram_bot.create_main_menu_buttons()
    else:
        new_text = f"🔓 <b>Unlink Account</b>\n\nAre you sure you want to unlink from '<b>{tg_user.user.username}</b>'?\n\nYou will stop receiving notifications."
        reply_markup = {"inline_keyboard": [
            [{"text": "✅ Yes, Unlink", "callback_data": "confirm_unlink"}],
            [{"text": "❌ Cancel", "callback_data": "cancel_unlink"}],
            [{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]
        ]}
    
    telegram_bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=new_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    telegram_bot.answer_callback_query(callback_query_id)

def handle_confirmation_callback(chat_id: str, message_id: int, data: str, callback_query_id: str):
    """Handle confirmation callbacks (Yes/No actions)"""
    telegram_bot = get_telegram_bot()
    if not telegram_bot:
        return
    
    if data == "confirm_unlink":
        # Unlink the account
        tg_user = TelegramUser.get_by_chat_id(chat_id)
        if tg_user:
            try:
                username = tg_user.user.username
                user_id = tg_user.user.id
                
                # Send notification to admin BEFORE unlinking (while TelegramUser still exists)
                try:
                    notification_service = get_notification_service()
                    if notification_service:
                        # Create a special admin notification about the unlink
                        from models import NotificationLog, User
                        admin_users = User.query.filter_by(is_admin=True).all()
                        for admin_user in admin_users:
                            admin_tg_user = TelegramUser.query.filter_by(user_id=admin_user.id, is_active=True).first()
                            if admin_tg_user and admin_tg_user.notify_admin_actions:
                                message = f"🔗❌ <b>User Unlinked Telegram</b>\n\n👤 <b>User:</b> {username}\n📱 <b>Chat ID:</b> {chat_id}\n🕒 <b>Time:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                                
                                # Log the notification
                                log_entry = NotificationLog.create_log(
                                    telegram_user_id=admin_tg_user.id,
                                    notification_type='admin_actions',
                                    message=message,
                                    user_action='User unlinked Telegram account (interactive)',
                                    actor_user_id=user_id,
                                    message_data=json.dumps({
                                        'telegram_chat_id': chat_id,
                                        'unlinked_username': username
                                    })
                                )
                                
                                # Send the actual Telegram message
                                success = telegram_bot.send_message(
                                    chat_id=admin_tg_user.telegram_chat_id,
                                    text=message,
                                    parse_mode='HTML'
                                )
                                
                                if success:
                                    log_entry.mark_sent()
                                else:
                                    log_entry.mark_failed("Failed to send message")
                                
                                db.session.add(log_entry)
                                
                except Exception as e:
                    logger.error(f"Failed to send unlink notification: {e}")
                
                # Now remove the Telegram user
                db.session.delete(tg_user)
                db.session.commit()
                
                new_text = f"✅ <b>Account Unlinked</b>\n\nSuccessfully unlinked from app user '<b>{username}</b>'.\nYou will no longer receive notifications."
                    
            except Exception as e:
                logger.error(f"Error unlinking user: {e}")
                db.session.rollback()
                new_text = "❌ <b>Unlink Failed</b>\n\nFailed to unlink your account. Please try again."
        else:
            new_text = "❌ <b>Account Not Found</b>\n\nNo linked account found."
        
        reply_markup = telegram_bot.create_main_menu_buttons()
        telegram_bot.answer_callback_query(callback_query_id, "Account unlinked!" if "Successfully" in new_text else "Failed to unlink")
        
    elif data == "cancel_unlink":
        new_text = "🔓 <b>Unlink Cancelled</b>\n\nYour account remains linked."
        reply_markup = telegram_bot.create_main_menu_buttons()
        telegram_bot.answer_callback_query(callback_query_id, "Cancelled")
    else:
        # Unknown confirmation action
        new_text = "❓ <b>Unknown Action</b>\n\nSomething went wrong."
        reply_markup = telegram_bot.create_main_menu_buttons()
        telegram_bot.answer_callback_query(callback_query_id, "Unknown action")
    
    telegram_bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=new_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

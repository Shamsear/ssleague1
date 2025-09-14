import requests
import json
import asyncio
import logging
import secrets
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from flask import current_app
import threading
import time
import queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBotService:
    """
    Telegram Bot Service for sending notifications to users
    """
    
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or current_app.config.get('TELEGRAM_BOT_TOKEN')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.webhook_url = current_app.config.get('TELEGRAM_WEBHOOK_URL')
        
        # Notification queue for async processing
        self.notification_queue = queue.Queue()
        self.is_processing = False
        
        # Start background worker
        self._start_background_worker()
    
    def _start_background_worker(self):
        """Start background thread to process notification queue"""
        if not self.is_processing:
            self.is_processing = True
            worker_thread = threading.Thread(target=self._process_notifications, daemon=True)
            worker_thread.start()
            logger.info("Telegram notification worker started")
    
    def _process_notifications(self):
        """Background worker to process notification queue"""
        while self.is_processing:
            try:
                # Get notification from queue (blocks for up to 1 second)
                notification = self.notification_queue.get(timeout=1)
                self._send_notification_sync(notification)
                self.notification_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
                continue
    
    def verify_bot_token(self) -> bool:
        """Verify if the bot token is valid"""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to verify bot token: {e}")
            return False
    
    def set_webhook(self, webhook_url: str) -> bool:
        """Set webhook URL for the bot"""
        try:
            data = {'url': webhook_url}
            response = requests.post(f"{self.base_url}/setWebhook", json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            return False
    
    def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook information"""
        try:
            response = requests.get(f"{self.base_url}/getWebhookInfo", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Failed to get webhook info: {e}")
            return {}
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = 'HTML', 
                    reply_markup: Dict = None, disable_notification: bool = False) -> bool:
        """Send a message to a specific chat"""
        try:
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_notification': disable_notification
            }
            
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            
            response = requests.post(f"{self.base_url}/sendMessage", json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send message to {chat_id}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return False
    
    def send_photo(self, chat_id: str, photo_url: str, caption: str = '', 
                   parse_mode: str = 'HTML') -> bool:
        """Send a photo to a specific chat"""
        try:
            data = {
                'chat_id': chat_id,
                'photo': photo_url,
                'caption': caption,
                'parse_mode': parse_mode
            }
            
            response = requests.post(f"{self.base_url}/sendPhoto", json=data, timeout=15)
            
            if response.status_code == 200:
                logger.info(f"Photo sent successfully to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send photo to {chat_id}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending photo to {chat_id}: {e}")
            return False
    
    def send_document(self, chat_id: str, document_url: str, caption: str = '', 
                     filename: str = None) -> bool:
        """Send a document to a specific chat"""
        try:
            data = {
                'chat_id': chat_id,
                'document': document_url,
                'caption': caption
            }
            
            if filename:
                data['filename'] = filename
            
            response = requests.post(f"{self.base_url}/sendDocument", json=data, timeout=20)
            
            if response.status_code == 200:
                logger.info(f"Document sent successfully to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send document to {chat_id}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending document to {chat_id}: {e}")
            return False
    
    def get_chat_member(self, chat_id: str, user_id: str) -> Dict[str, Any]:
        """Get information about a chat member"""
        try:
            data = {
                'chat_id': chat_id,
                'user_id': user_id
            }
            
            response = requests.post(f"{self.base_url}/getChatMember", json=data, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return {}
            
        except Exception as e:
            logger.error(f"Error getting chat member info: {e}")
            return {}
    
    def queue_notification(self, notification_data: Dict[str, Any]):
        """Queue a notification for async processing"""
        try:
            self.notification_queue.put(notification_data, timeout=1)
            logger.info(f"Notification queued for processing")
        except queue.Full:
            logger.warning("Notification queue is full, dropping notification")
    
    def _send_notification_sync(self, notification_data: Dict[str, Any]):
        """Synchronously send a notification"""
        try:
            chat_id = notification_data.get('chat_id')
            message_type = notification_data.get('type', 'message')
            
            if message_type == 'message':
                self.send_message(
                    chat_id=chat_id,
                    text=notification_data.get('text', ''),
                    parse_mode=notification_data.get('parse_mode', 'HTML'),
                    reply_markup=notification_data.get('reply_markup'),
                    disable_notification=notification_data.get('disable_notification', False)
                )
            elif message_type == 'photo':
                self.send_photo(
                    chat_id=chat_id,
                    photo_url=notification_data.get('photo_url', ''),
                    caption=notification_data.get('caption', ''),
                    parse_mode=notification_data.get('parse_mode', 'HTML')
                )
            elif message_type == 'document':
                self.send_document(
                    chat_id=chat_id,
                    document_url=notification_data.get('document_url', ''),
                    caption=notification_data.get('caption', ''),
                    filename=notification_data.get('filename')
                )
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def broadcast_message(self, chat_ids: List[str], text: str, parse_mode: str = 'HTML',
                         disable_notification: bool = False) -> Dict[str, bool]:
        """Broadcast a message to multiple chats"""
        results = {}
        for chat_id in chat_ids:
            results[chat_id] = self.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_notification=disable_notification
            )
            # Small delay between messages to avoid rate limiting
            time.sleep(0.1)
        
        return results
    
    def format_user_action_message(self, user: str, action: str, details: Dict[str, Any] = None) -> str:
        """Format a user action into a notification message"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Base message
        message = f"🔔 <b>User Action Alert</b>\n\n"
        message += f"👤 <b>User:</b> {user}\n"
        message += f"⚡ <b>Action:</b> {action}\n"
        message += f"🕐 <b>Time:</b> {timestamp}\n"
        
        # Add details if provided
        if details:
            message += f"\n📋 <b>Details:</b>\n"
            for key, value in details.items():
                message += f"  • <b>{key}:</b> {value}\n"
        
        return message
    
    def format_system_alert_message(self, alert_type: str, message: str, severity: str = "info") -> str:
        """Format a system alert message"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Severity icons
        severity_icons = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️",
            "success": "✅"
        }
        
        icon = severity_icons.get(severity.lower(), "ℹ️")
        
        formatted_message = f"{icon} <b>System Alert</b>\n\n"
        formatted_message += f"🏷️ <b>Type:</b> {alert_type}\n"
        formatted_message += f"📝 <b>Message:</b> {message}\n"
        formatted_message += f"🕐 <b>Time:</b> {timestamp}\n"
        
        return formatted_message
    
    def create_inline_keyboard(self, buttons: List[List[Dict[str, str]]]) -> Dict[str, Any]:
        """Create an inline keyboard markup"""
        return {
            "inline_keyboard": buttons
        }
    
    def create_quick_reply_buttons(self, options: List[str], prefix: str = "btn") -> Dict[str, Any]:
        """Create quick reply buttons from a list of options"""
        buttons = []
        row = []
        
        for i, option in enumerate(options):
            # Add 2 buttons per row for better mobile experience
            if i > 0 and i % 2 == 0:
                buttons.append(row)
                row = []
            
            row.append({
                "text": option,
                "callback_data": f"{prefix}_{option.lower().replace(' ', '_')}"
            })
        
        if row:  # Add remaining buttons
            buttons.append(row)
        
        return self.create_inline_keyboard(buttons)
    
    def create_yes_no_buttons(self, action: str) -> Dict[str, Any]:
        """Create Yes/No confirmation buttons"""
        buttons = [[
            {"text": "✅ Yes", "callback_data": f"confirm_{action}"},
            {"text": "❌ No", "callback_data": f"cancel_{action}"}
        ]]
        return self.create_inline_keyboard(buttons)
    
    def create_navigation_buttons(self, current_page: int, total_pages: int, prefix: str = "page") -> Dict[str, Any]:
        """Create navigation buttons for paginated content"""
        buttons = []
        
        # Previous and Next buttons
        row = []
        if current_page > 1:
            row.append({"text": "◀️ Previous", "callback_data": f"{prefix}_{current_page - 1}"})
        
        row.append({"text": f"{current_page}/{total_pages}", "callback_data": "noop"})
        
        if current_page < total_pages:
            row.append({"text": "Next ▶️", "callback_data": f"{prefix}_{current_page + 1}"})
        
        if row:
            buttons.append(row)
        
        return self.create_inline_keyboard(buttons)
    
    def create_main_menu_buttons(self) -> Dict[str, Any]:
        """Create main menu buttons for the bot"""
        buttons = [
            [{"text": "📊 Status", "callback_data": "menu_status"}],
            [{"text": "🔔 Notifications", "callback_data": "menu_notifications"}],
            [{"text": "📈 Stats", "callback_data": "menu_stats"}, {"text": "ℹ️ Help", "callback_data": "menu_help"}],
            [{"text": "🔗 Link Account", "callback_data": "menu_link"}, {"text": "🔓 Unlink", "callback_data": "menu_unlink"}]
        ]
        return self.create_inline_keyboard(buttons)
    
    def create_notification_settings_buttons(self) -> Dict[str, Any]:
        """Create notification settings management buttons"""
        buttons = [
            [{"text": "✅ Enable All", "callback_data": "notif_enable_all"}],
            [{"text": "❌ Disable All", "callback_data": "notif_disable_all"}],
            [{"text": "🔄 Toggle Login", "callback_data": "notif_toggle_login"}],
            [{"text": "🏆 Toggle Bids", "callback_data": "notif_toggle_bids"}],
            [{"text": "🎯 Toggle Auctions", "callback_data": "notif_toggle_auctions"}],
            [{"text": "👥 Toggle Teams", "callback_data": "notif_toggle_teams"}],
            [{"text": "⚙️ Toggle Admin", "callback_data": "notif_toggle_admin"}],
            [{"text": "⚠️ Toggle Alerts", "callback_data": "notif_toggle_alerts"}],
            [{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]
        ]
        return self.create_inline_keyboard(buttons)
    
    def answer_callback_query(self, callback_query_id: str, text: str = None, show_alert: bool = False) -> bool:
        """Answer a callback query from an inline keyboard button"""
        try:
            data = {
                'callback_query_id': callback_query_id,
                'show_alert': show_alert
            }
            
            if text:
                data['text'] = text
            
            response = requests.post(f"{self.base_url}/answerCallbackQuery", json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Callback query answered successfully")
                return True
            else:
                logger.error(f"Failed to answer callback query: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return False
    
    def edit_message_text(self, chat_id: str, message_id: int, text: str, 
                         parse_mode: str = 'HTML', reply_markup: Dict = None) -> bool:
        """Edit an existing message text"""
        try:
            data = {
                'chat_id': chat_id,
                'message_id': message_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            
            response = requests.post(f"{self.base_url}/editMessageText", json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Message edited successfully")
                return True
            else:
                logger.error(f"Failed to edit message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return False
    
    def edit_message_reply_markup(self, chat_id: str, message_id: int, reply_markup: Dict = None) -> bool:
        """Edit only the reply markup of an existing message"""
        try:
            data = {
                'chat_id': chat_id,
                'message_id': message_id
            }
            
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            
            response = requests.post(f"{self.base_url}/editMessageReplyMarkup", json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Message reply markup edited successfully")
                return True
            else:
                logger.error(f"Failed to edit message reply markup: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error editing message reply markup: {e}")
            return False
    
    def stop_processing(self):
        """Stop the background notification processor"""
        self.is_processing = False
        logger.info("Telegram notification worker stopped")
    
    # Deep Linking Methods
    
    def generate_link_token(self, user_id: int, username: str, expires_hours: int = 24) -> str:
        """Generate a secure token for deep linking a user account"""
        try:
            # Create expiration timestamp
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
            expires_timestamp = int(expires_at.timestamp())
            
            # Create payload
            payload = f"{user_id}:{username}:{expires_timestamp}"
            
            # Generate a random salt
            salt = secrets.token_hex(16)
            
            # Create signature using bot token as secret key
            signature_input = f"{payload}:{salt}:{self.bot_token}"
            signature = hashlib.sha256(signature_input.encode()).hexdigest()[:16]
            
            # Combine everything and encode
            token_data = f"{payload}:{salt}:{signature}"
            token = base64.urlsafe_b64encode(token_data.encode()).decode().rstrip('=')
            
            logger.info(f"Generated link token for user {username} (expires in {expires_hours}h)")
            return token
            
        except Exception as e:
            logger.error(f"Error generating link token: {e}")
            return None
    
    def validate_link_token(self, token: str) -> Dict[str, Any]:
        """Validate a deep link token and extract user information"""
        try:
            # Add padding if needed and decode
            padding_needed = 4 - (len(token) % 4)
            if padding_needed != 4:
                token += '=' * padding_needed
            
            token_data = base64.urlsafe_b64decode(token).decode()
            parts = token_data.split(':')
            
            if len(parts) != 5:
                return {'valid': False, 'error': 'Invalid token format'}
            
            user_id, username, expires_timestamp, salt, signature = parts
            
            # Check expiration
            if datetime.now(timezone.utc).timestamp() > int(expires_timestamp):
                return {'valid': False, 'error': 'Token expired'}
            
            # Verify signature
            payload = f"{user_id}:{username}:{expires_timestamp}"
            signature_input = f"{payload}:{salt}:{self.bot_token}"
            expected_signature = hashlib.sha256(signature_input.encode()).hexdigest()[:16]
            
            if signature != expected_signature:
                return {'valid': False, 'error': 'Invalid signature'}
            
            logger.info(f"Validated link token for user {username}")
            return {
                'valid': True,
                'user_id': int(user_id),
                'username': username,
                'expires_at': datetime.fromtimestamp(int(expires_timestamp), timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Error validating link token: {e}")
            return {'valid': False, 'error': 'Token validation failed'}
    
    def generate_deep_link(self, user_id: int, username: str, bot_username: str = None) -> str:
        """Generate a deep link for automatic user account linking"""
        try:
            token = self.generate_link_token(user_id, username)
            if not token:
                return None
            
            # Get bot username (you'll need to set this in your config or get from getMe API)
            if not bot_username:
                bot_username = current_app.config.get('TELEGRAM_BOT_USERNAME', 'ssleaguebot')
            
            # Create the deep link URL
            deep_link = f"https://t.me/{bot_username}?start=link_{token}"
            
            logger.info(f"Generated deep link for user {username}: {deep_link}")
            return deep_link
            
        except Exception as e:
            logger.error(f"Error generating deep link: {e}")
            return None
    
    def create_link_button(self, user_id: int, username: str, bot_username: str = None) -> Dict[str, Any]:
        """Create an inline keyboard button for account linking"""
        deep_link = self.generate_deep_link(user_id, username, bot_username)
        if not deep_link:
            return None
        
        return {
            "inline_keyboard": [[
                {
                    "text": "🔗 Link Telegram Account",
                    "url": deep_link
                }
            ]]
        }

# Global instance
telegram_bot = None

def init_telegram_bot(app):
    """Initialize the Telegram bot service with the Flask app"""
    global telegram_bot
    
    bot_token = app.config.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured. Telegram notifications disabled.")
        return None
    
    telegram_bot = TelegramBotService(bot_token)
    
    # Verify bot token
    if not telegram_bot.verify_bot_token():
        logger.error("Invalid Telegram bot token. Telegram notifications disabled.")
        telegram_bot = None
        return None
    
    logger.info("Telegram bot service initialized successfully")
    return telegram_bot

def get_telegram_bot() -> Optional[TelegramBotService]:
    """Get the global Telegram bot instance"""
    return telegram_bot
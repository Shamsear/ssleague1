#!/usr/bin/env python3
"""
Telegram Bot with Interactive Buttons - Example Script

This script demonstrates how to create a Telegram bot with interactive buttons
for easy user interaction. It shows various button layouts and callback handling.

Requirements:
- Python 3.6+
- requests library
- A Telegram bot token (get from @BotFather)

Usage:
1. Replace 'YOUR_BOT_TOKEN_HERE' with your actual bot token
2. Run the script: python telegram_bot_example.py
3. Set up webhook or use polling to receive updates
"""

import requests
import json
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramBot:
    """Simple Telegram Bot with Interactive Buttons"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, chat_id: str, text: str, reply_markup: Dict = None) -> bool:
        """Send a message with optional inline keyboard"""
        try:
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            
            response = requests.post(f"{self.base_url}/sendMessage", json=data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def edit_message_text(self, chat_id: str, message_id: int, text: str, reply_markup: Dict = None) -> bool:
        """Edit an existing message"""
        try:
            data = {
                'chat_id': chat_id,
                'message_id': message_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            
            response = requests.post(f"{self.base_url}/editMessageText", json=data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return False
    
    def answer_callback_query(self, callback_query_id: str, text: str = None, show_alert: bool = False) -> bool:
        """Answer a callback query"""
        try:
            data = {
                'callback_query_id': callback_query_id,
                'show_alert': show_alert
            }
            
            if text:
                data['text'] = text
            
            response = requests.post(f"{self.base_url}/answerCallbackQuery", json=data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return False
    
    # Button Creation Methods
    
    def create_inline_keyboard(self, buttons: List[List[Dict[str, str]]]) -> Dict[str, Any]:
        """Create inline keyboard markup"""
        return {"inline_keyboard": buttons}
    
    def create_main_menu_buttons(self) -> Dict[str, Any]:
        """Create main menu buttons"""
        buttons = [
            [{"text": "📊 Status", "callback_data": "menu_status"}],
            [{"text": "🔔 Settings", "callback_data": "menu_settings"}],
            [
                {"text": "📈 Analytics", "callback_data": "menu_analytics"},
                {"text": "ℹ️ Help", "callback_data": "menu_help"}
            ],
            [{"text": "🎮 Games", "callback_data": "menu_games"}],
        ]
        return self.create_inline_keyboard(buttons)
    
    def create_settings_buttons(self) -> Dict[str, Any]:
        """Create settings menu buttons"""
        buttons = [
            [{"text": "✅ Enable All", "callback_data": "settings_enable_all"}],
            [{"text": "❌ Disable All", "callback_data": "settings_disable_all"}],
            [
                {"text": "🔄 Toggle Option 1", "callback_data": "settings_toggle_1"},
                {"text": "🔄 Toggle Option 2", "callback_data": "settings_toggle_2"}
            ],
            [{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]
        ]
        return self.create_inline_keyboard(buttons)
    
    def create_games_buttons(self) -> Dict[str, Any]:
        """Create games menu buttons"""
        buttons = [
            [
                {"text": "🎯 Trivia", "callback_data": "game_trivia"},
                {"text": "🎲 Dice", "callback_data": "game_dice"}
            ],
            [
                {"text": "🃏 Cards", "callback_data": "game_cards"},
                {"text": "🧩 Puzzle", "callback_data": "game_puzzle"}
            ],
            [{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]
        ]
        return self.create_inline_keyboard(buttons)
    
    def create_yes_no_buttons(self, action: str) -> Dict[str, Any]:
        """Create Yes/No confirmation buttons"""
        buttons = [[
            {"text": "✅ Yes", "callback_data": f"confirm_{action}"},
            {"text": "❌ No", "callback_data": f"cancel_{action}"}
        ]]
        return self.create_inline_keyboard(buttons)
    
    def create_pagination_buttons(self, current_page: int, total_pages: int, prefix: str = "page") -> Dict[str, Any]:
        """Create pagination buttons"""
        buttons = []
        
        row = []
        if current_page > 1:
            row.append({"text": "◀️ Previous", "callback_data": f"{prefix}_{current_page - 1}"})
        
        row.append({"text": f"{current_page}/{total_pages}", "callback_data": "noop"})
        
        if current_page < total_pages:
            row.append({"text": "Next ▶️", "callback_data": f"{prefix}_{current_page + 1}"})
        
        if row:
            buttons.append(row)
        
        # Add back button
        buttons.append([{"text": "🏠 Back to Menu", "callback_data": "menu_main"}])
        
        return self.create_inline_keyboard(buttons)


class BotHandler:
    """Handles bot messages and callbacks"""
    
    def __init__(self, bot: TelegramBot):
        self.bot = bot
        # Mock user settings for demonstration
        self.user_settings = {}
    
    def handle_message(self, update: Dict[str, Any]):
        """Handle incoming messages"""
        message = update.get('message', {})
        chat_id = str(message.get('chat', {}).get('id'))
        text = message.get('text', '')
        
        if text.startswith('/start'):
            self.send_welcome_message(chat_id)
        elif text.startswith('/menu'):
            self.send_main_menu(chat_id)
        elif text.startswith('/help'):
            self.send_help_message(chat_id)
        else:
            self.send_main_menu(chat_id, "❓ Unknown command. Here's the main menu:")
    
    def handle_callback_query(self, update: Dict[str, Any]):
        """Handle button callbacks"""
        callback_query = update.get('callback_query', {})
        message = callback_query.get('message', {})
        chat_id = str(message.get('chat', {}).get('id'))
        message_id = message.get('message_id')
        data = callback_query.get('data', '')
        callback_query_id = callback_query.get('id')
        
        # Route callback to appropriate handler
        if data.startswith('menu_'):
            self.handle_menu_callback(chat_id, message_id, data, callback_query_id)
        elif data.startswith('settings_'):
            self.handle_settings_callback(chat_id, message_id, data, callback_query_id)
        elif data.startswith('game_'):
            self.handle_game_callback(chat_id, message_id, data, callback_query_id)
        elif data.startswith('confirm_') or data.startswith('cancel_'):
            self.handle_confirmation_callback(chat_id, message_id, data, callback_query_id)
        elif data == 'noop':
            self.bot.answer_callback_query(callback_query_id)
        else:
            self.bot.answer_callback_query(callback_query_id, "❓ Unknown action")
    
    def send_welcome_message(self, chat_id: str):
        """Send welcome message with main menu"""
        welcome_text = """
🤖 <b>Welcome to Interactive Bot!</b>

This bot demonstrates various interactive button features:

✨ <b>Features:</b>
• Interactive menus with buttons
• Settings management
• Games and entertainment
• Pagination examples
• Confirmation dialogs

Click a button below to explore!
        """
        
        reply_markup = self.bot.create_main_menu_buttons()
        self.bot.send_message(chat_id, welcome_text.strip(), reply_markup)
    
    def send_main_menu(self, chat_id: str, message_text: str = None):
        """Send main menu"""
        if not message_text:
            message_text = "🏠 <b>Main Menu</b>\n\nChoose an option:"
        
        reply_markup = self.bot.create_main_menu_buttons()
        self.bot.send_message(chat_id, message_text, reply_markup)
    
    def send_help_message(self, chat_id: str):
        """Send help message"""
        help_text = """
ℹ️ <b>Bot Help</b>

<b>Commands:</b>
• /start - Show welcome message
• /menu - Show main menu
• /help - Show this help

<b>Navigation:</b>
• Use buttons to navigate menus
• Click "Back to Menu" to return to main menu
• Buttons show instant feedback

<b>Features Demonstrated:</b>
• 📊 Status checking
• 🔔 Settings management
• 📈 Analytics display
• 🎮 Interactive games
• ✅❌ Yes/No confirmations
• ◀️▶️ Pagination controls

Try clicking the buttons to see how they work!
        """
        
        reply_markup = self.bot.create_inline_keyboard([
            [{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]
        ])
        
        self.bot.send_message(chat_id, help_text.strip(), reply_markup)
    
    def handle_menu_callback(self, chat_id: str, message_id: int, data: str, callback_query_id: str):
        """Handle main menu callbacks"""
        action = data.replace('menu_', '')
        
        if action == 'main':
            new_text = "🏠 <b>Main Menu</b>\n\nChoose an option:"
            reply_markup = self.bot.create_main_menu_buttons()
            
        elif action == 'status':
            new_text = """
📊 <b>System Status</b>

🟢 <b>Bot Status:</b> Online
🟢 <b>Database:</b> Connected
🟢 <b>API:</b> Responsive
🟡 <b>Cache:</b> 85% Full
🟢 <b>Memory:</b> 342MB / 1GB

<b>Statistics:</b>
• Active Users: 1,247
• Messages Today: 5,832
• Uptime: 99.8%

<i>All systems operational!</i>
            """
            reply_markup = self.bot.create_inline_keyboard([
                [{"text": "🔄 Refresh", "callback_data": "menu_status"}],
                [{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]
            ])
            
        elif action == 'settings':
            new_text = "🔔 <b>Settings</b>\n\nManage your preferences:"
            reply_markup = self.bot.create_settings_buttons()
            
        elif action == 'analytics':
            new_text = """
📈 <b>Analytics Dashboard</b>

<b>Usage Statistics:</b>
• Page 1 of 3 •

📅 <b>Today:</b>
• Messages: 1,234 (+15%)
• Active Users: 456 (+8%)
• Button Clicks: 789 (+22%)

📊 <b>This Week:</b>
• Total Messages: 8,901
• Peak Hour: 3:00 PM
• Most Popular: Games Menu
            """
            reply_markup = self.bot.create_pagination_buttons(1, 3, "analytics")
            
        elif action == 'games':
            new_text = "🎮 <b>Games & Entertainment</b>\n\nChoose a game to play:"
            reply_markup = self.bot.create_games_buttons()
            
        elif action == 'help':
            new_text = """
ℹ️ <b>Quick Help</b>

<b>Navigation Tips:</b>
• Use buttons to navigate
• Look for the 🏠 button to return to main menu
• Icons help identify button functions

<b>Button Types:</b>
• 📊 📈 📉 - Data and statistics
• 🔔 ⚙️ 🔧 - Settings and configuration  
• 🎮 🎯 🎲 - Games and entertainment
• ✅ ❌ - Confirmations
• ◀️ ▶️ - Navigation

<b>Feedback:</b>
Buttons provide instant visual feedback when pressed!
            """
            reply_markup = self.bot.create_inline_keyboard([
                [{"text": "📖 Full Help", "callback_data": "help_full"}],
                [{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]
            ])
        
        else:
            new_text = "❓ Unknown menu option"
            reply_markup = self.bot.create_main_menu_buttons()
        
        self.bot.edit_message_text(chat_id, message_id, new_text, reply_markup)
        self.bot.answer_callback_query(callback_query_id)
    
    def handle_settings_callback(self, chat_id: str, message_id: int, data: str, callback_query_id: str):
        """Handle settings callbacks"""
        action = data.replace('settings_', '')
        
        # Initialize user settings if not exists
        if chat_id not in self.user_settings:
            self.user_settings[chat_id] = {
                'option_1': True,
                'option_2': False,
                'notifications': True
            }
        
        settings = self.user_settings[chat_id]
        
        if action == 'enable_all':
            settings.update({'option_1': True, 'option_2': True, 'notifications': True})
            self.bot.answer_callback_query(callback_query_id, "✅ All settings enabled!")
            
        elif action == 'disable_all':
            settings.update({'option_1': False, 'option_2': False, 'notifications': False})
            self.bot.answer_callback_query(callback_query_id, "❌ All settings disabled!")
            
        elif action == 'toggle_1':
            settings['option_1'] = not settings['option_1']
            status = "enabled" if settings['option_1'] else "disabled"
            self.bot.answer_callback_query(callback_query_id, f"Option 1 {status}!")
            
        elif action == 'toggle_2':
            settings['option_2'] = not settings['option_2']
            status = "enabled" if settings['option_2'] else "disabled"
            self.bot.answer_callback_query(callback_query_id, f"Option 2 {status}!")
        
        # Update the settings display
        new_text = f"""
🔔 <b>Settings</b>

<b>Current Configuration:</b>
• Option 1: {'✅ Enabled' if settings['option_1'] else '❌ Disabled'}
• Option 2: {'✅ Enabled' if settings['option_2'] else '❌ Disabled'}
• Notifications: {'✅ Enabled' if settings['notifications'] else '❌ Disabled'}

<b>Quick Actions:</b>
        """
        
        reply_markup = self.bot.create_settings_buttons()
        self.bot.edit_message_text(chat_id, message_id, new_text, reply_markup)
    
    def handle_game_callback(self, chat_id: str, message_id: int, data: str, callback_query_id: str):
        """Handle game callbacks"""
        game = data.replace('game_', '')
        
        game_responses = {
            'trivia': {
                'text': "🎯 <b>Trivia Game</b>\n\n❓ What is the capital of France?\n\nA) London\nB) Berlin\nC) Paris\nD) Madrid",
                'buttons': [
                    [{"text": "A) London", "callback_data": "trivia_wrong"}, {"text": "B) Berlin", "callback_data": "trivia_wrong"}],
                    [{"text": "C) Paris", "callback_data": "trivia_correct"}, {"text": "D) Madrid", "callback_data": "trivia_wrong"}],
                    [{"text": "🏠 Back to Games", "callback_data": "menu_games"}]
                ]
            },
            'dice': {
                'text': "🎲 <b>Dice Game</b>\n\n🎰 Roll the dice and see what you get!\n\n🎲 Result: ⚄ (5)\n\n🎉 Nice roll!",
                'buttons': [
                    [{"text": "🎲 Roll Again", "callback_data": "game_dice"}],
                    [{"text": "🏠 Back to Games", "callback_data": "menu_games"}]
                ]
            },
            'cards': {
                'text': "🃏 <b>Card Game</b>\n\n🃏 Your card: King of Hearts ♥️\n\n👑 Excellent draw!",
                'buttons': [
                    [{"text": "🃏 Draw Card", "callback_data": "game_cards"}],
                    [{"text": "🏠 Back to Games", "callback_data": "menu_games"}]
                ]
            },
            'puzzle': {
                'text': "🧩 <b>Word Puzzle</b>\n\n🔤 Solve this: _ E L E G R A M\n\nHint: Communication app\n\nAnswer: T E L E G R A M ✅",
                'buttons': [
                    [{"text": "🧩 New Puzzle", "callback_data": "game_puzzle"}],
                    [{"text": "🏠 Back to Games", "callback_data": "menu_games"}]
                ]
            }
        }
        
        if game in game_responses:
            response = game_responses[game]
            reply_markup = self.bot.create_inline_keyboard(response['buttons'])
            self.bot.edit_message_text(chat_id, message_id, response['text'], reply_markup)
            self.bot.answer_callback_query(callback_query_id, f"🎮 {game.title()} loaded!")
        else:
            self.bot.answer_callback_query(callback_query_id, "❓ Unknown game")
    
    def handle_confirmation_callback(self, chat_id: str, message_id: int, data: str, callback_query_id: str):
        """Handle confirmation callbacks"""
        if data.startswith('confirm_'):
            action = data.replace('confirm_', '')
            self.bot.answer_callback_query(callback_query_id, f"✅ {action.title()} confirmed!")
            new_text = f"✅ <b>Action Confirmed</b>\n\nYou confirmed: {action.title()}"
            
        elif data.startswith('cancel_'):
            action = data.replace('cancel_', '')
            self.bot.answer_callback_query(callback_query_id, f"❌ {action.title()} cancelled!")
            new_text = f"❌ <b>Action Cancelled</b>\n\nYou cancelled: {action.title()}"
        
        else:
            self.bot.answer_callback_query(callback_query_id, "❓ Unknown action")
            new_text = "❓ <b>Unknown Action</b>"
        
        reply_markup = self.bot.create_inline_keyboard([
            [{"text": "🏠 Back to Menu", "callback_data": "menu_main"}]
        ])
        
        self.bot.edit_message_text(chat_id, message_id, new_text, reply_markup)


def main():
    """Main function to demonstrate the bot"""
    # Replace with your actual bot token
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please replace 'YOUR_BOT_TOKEN_HERE' with your actual bot token!")
        print("Get one from @BotFather on Telegram")
        return
    
    bot = TelegramBot(BOT_TOKEN)
    handler = BotHandler(bot)
    
    print("🤖 Telegram Bot with Interactive Buttons - Example")
    print("=" * 50)
    print()
    print("This script demonstrates:")
    print("✅ Interactive button menus")
    print("✅ Callback query handling")
    print("✅ Dynamic button updates")
    print("✅ Settings management")
    print("✅ Games and entertainment")
    print("✅ Confirmation dialogs")
    print("✅ Pagination controls")
    print()
    print("To test the bot:")
    print("1. Set up a webhook to receive updates")
    print("2. Or use long polling (not included in this example)")
    print("3. Send updates to handler.handle_message() or handler.handle_callback_query()")
    print()
    print("Example update processing:")
    
    # Example update (you would normally receive this from Telegram)
    example_update = {
        "message": {
            "chat": {"id": 12345},
            "text": "/start",
            "from": {"username": "example_user"}
        }
    }
    
    print("Processing example /start command...")
    handler.handle_message(example_update)
    print("✅ Example processed! Check your bot for the welcome message.")


if __name__ == "__main__":
    main()
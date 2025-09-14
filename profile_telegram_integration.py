#!/usr/bin/env python3
"""
Profile Telegram Integration Example

This file shows how to integrate Telegram deep linking into user profiles
so users can automatically link their accounts with one click.

This includes both backend API endpoints and frontend integration examples.
"""

from flask import Blueprint, request, jsonify, render_template_string
from telegram_service import get_telegram_bot
from models import db, User, TelegramUser
import logging

logger = logging.getLogger(__name__)

# Create blueprint for profile integration
profile_telegram_bp = Blueprint('profile_telegram', __name__, url_prefix='/profile')

@profile_telegram_bp.route('/telegram/link/<int:user_id>')
def get_telegram_link(user_id):
    """
    API endpoint to generate a Telegram deep link for a user
    Use this in your profile page to show the "Link Telegram" button
    """
    try:
        # Find the user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if already linked
        existing_link = TelegramUser.query.filter_by(user_id=user.id).first()
        if existing_link:
            return jsonify({
                'linked': True,
                'telegram_username': existing_link.telegram_username,
                'telegram_chat_id': existing_link.telegram_chat_id,
                'is_active': existing_link.is_active,
                'message': 'Account already linked to Telegram'
            })
        
        # Get Telegram bot service
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            return jsonify({'error': 'Telegram bot not available'}), 503
        
        # Generate deep link
        deep_link = telegram_bot.generate_deep_link(user.id, user.username)
        if not deep_link:
            return jsonify({'error': 'Failed to generate link'}), 500
        
        return jsonify({
            'linked': False,
            'deep_link': deep_link,
            'expires_hours': 24,
            'message': 'Click the link to connect your Telegram account'
        })
        
    except Exception as e:
        logger.error(f"Error generating Telegram link for user {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@profile_telegram_bp.route('/telegram/status/<int:user_id>')
def get_telegram_status(user_id):
    """
    API endpoint to check Telegram linking status for a user
    Use this to show current status in the profile
    """
    try:
        # Find the user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if linked
        tg_user = TelegramUser.query.filter_by(user_id=user.id).first()
        
        if tg_user:
            return jsonify({
                'linked': True,
                'telegram_username': tg_user.telegram_username,
                'telegram_first_name': tg_user.telegram_first_name,
                'telegram_last_name': tg_user.telegram_last_name,
                'is_active': tg_user.is_active,
                'notifications': {
                    'login': tg_user.notify_login,
                    'bids': tg_user.notify_bids,
                    'auction_start': tg_user.notify_auction_start,
                    'auction_end': tg_user.notify_auction_end,
                    'team_changes': tg_user.notify_team_changes,
                    'admin_actions': tg_user.notify_admin_actions,
                    'system_alerts': tg_user.notify_system_alerts
                },
                'linked_at': tg_user.created_at.isoformat() if tg_user.created_at else None
            })
        else:
            return jsonify({
                'linked': False,
                'message': 'Telegram account not linked'
            })
            
    except Exception as e:
        logger.error(f"Error getting Telegram status for user {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@profile_telegram_bp.route('/telegram/unlink/<int:user_id>', methods=['POST'])
def unlink_telegram(user_id):
    """
    API endpoint to unlink Telegram account
    Use this for the "Unlink Telegram" button in profile
    """
    try:
        # Find the user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Find linked Telegram account
        tg_user = TelegramUser.query.filter_by(user_id=user.id).first()
        if not tg_user:
            return jsonify({'error': 'No Telegram account linked'}), 400
        
        # Store info for response
        telegram_username = tg_user.telegram_username
        
        # Remove the link
        db.session.delete(tg_user)
        db.session.commit()
        
        logger.info(f"Unlinked Telegram account for user {user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully unlinked Telegram account @{telegram_username}',
            'unlinked_username': telegram_username
        })
        
    except Exception as e:
        logger.error(f"Error unlinking Telegram for user {user_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# Frontend Integration Examples

@profile_telegram_bp.route('/example/profile/<int:user_id>')
def example_profile_page(user_id):
    """
    Example profile page showing how to integrate Telegram linking
    This is just a demonstration - adapt to your existing profile template
    """
    user = User.query.get_or_404(user_id)
    
    # Example HTML template with JavaScript integration
    template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ user.username }}'s Profile</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .telegram-section { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .telegram-button { 
            display: inline-block; padding: 12px 24px; background: #0088cc; color: white; 
            text-decoration: none; border-radius: 6px; border: none; cursor: pointer;
            font-size: 16px; transition: background-color 0.3s;
        }
        .telegram-button:hover { background: #006ba3; }
        .telegram-button:disabled { background: #ccc; cursor: not-allowed; }
        .telegram-status { padding: 10px; border-radius: 4px; margin: 10px 0; }
        .linked { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .not-linked { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .loading { color: #666; }
    </style>
</head>
<body>
    <h1>👤 {{ user.username }}'s Profile</h1>
    
    <!-- Other profile information -->
    <div>
        <h3>📧 Account Information</h3>
        <p><strong>Username:</strong> {{ user.username }}</p>
        <p><strong>Email:</strong> {{ user.email }}</p>
        <p><strong>Joined:</strong> {{ user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A' }}</p>
    </div>
    
    <!-- Telegram Integration Section -->
    <div class="telegram-section">
        <h3>📱 Telegram Notifications</h3>
        <p>Link your Telegram account to receive real-time notifications about auctions, bids, and system updates.</p>
        
        <div id="telegram-status" class="loading">
            🔄 Loading Telegram status...
        </div>
        
        <div id="telegram-actions" style="display: none;">
            <!-- Dynamic content will be inserted here -->
        </div>
    </div>

    <script>
        const userId = {{ user.id }};
        
        // Load Telegram status on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadTelegramStatus();
        });
        
        async function loadTelegramStatus() {
            try {
                const response = await fetch(`/profile/telegram/status/${userId}`);
                const data = await response.json();
                
                const statusDiv = document.getElementById('telegram-status');
                const actionsDiv = document.getElementById('telegram-actions');
                
                if (data.error) {
                    statusDiv.innerHTML = `
                        <div class="error">
                            ❌ Error: ${data.error}
                        </div>
                    `;
                    return;
                }
                
                if (data.linked) {
                    // User has linked Telegram account
                    statusDiv.innerHTML = `
                        <div class="linked">
                            ✅ <strong>Connected to Telegram</strong><br>
                            📱 Account: @${data.telegram_username || 'N/A'}<br>
                            👤 Name: ${data.telegram_first_name || ''} ${data.telegram_last_name || ''}<br>
                            🔔 Status: ${data.is_active ? 'Active' : 'Inactive'}
                        </div>
                    `;
                    
                    actionsDiv.innerHTML = `
                        <button onclick="unlinkTelegram()" class="telegram-button" style="background: #dc3545;">
                            🔓 Unlink Telegram Account
                        </button>
                        <button onclick="window.open('https://t.me/ssleaguebot', '_blank')" class="telegram-button" style="background: #28a745; margin-left: 10px;">
                            💬 Open Bot Chat
                        </button>
                    `;
                    
                    // Show notification preferences
                    const notifications = data.notifications;
                    let notifStatus = '<h4>🔔 Notification Settings:</h4><ul>';
                    notifStatus += `<li>Login Alerts: ${notifications.login ? '✅' : '❌'}</li>`;
                    notifStatus += `<li>Bid Notifications: ${notifications.bids ? '✅' : '❌'}</li>`;
                    notifStatus += `<li>Auction Alerts: ${notifications.auction_start ? '✅' : '❌'}</li>`;
                    notifStatus += `<li>Team Updates: ${notifications.team_changes ? '✅' : '❌'}</li>`;
                    notifStatus += `<li>Admin Actions: ${notifications.admin_actions ? '✅' : '❌'}</li>`;
                    notifStatus += `<li>System Alerts: ${notifications.system_alerts ? '✅' : '❌'}</li>`;
                    notifStatus += '</ul><p><em>Manage these settings in the Telegram bot chat.</em></p>';
                    
                    actionsDiv.innerHTML += notifStatus;
                } else {
                    // User hasn't linked Telegram account
                    statusDiv.innerHTML = `
                        <div class="not-linked">
                            ❌ <strong>Telegram Not Connected</strong><br>
                            Link your Telegram account to receive instant notifications.
                        </div>
                    `;
                    
                    actionsDiv.innerHTML = `
                        <button onclick="generateTelegramLink()" class="telegram-button" id="link-btn">
                            🔗 Link Telegram Account
                        </button>
                        <div id="link-instructions" style="display: none; margin-top: 15px; padding: 15px; background: #e7f3ff; border-radius: 6px;">
                            <p><strong>📱 How to link your account:</strong></p>
                            <ol>
                                <li>Click the "Link Account" button below</li>
                                <li>It will open Telegram and start a chat with the bot</li>
                                <li>Your account will be automatically linked!</li>
                            </ol>
                            <p><em>The link expires in 24 hours for security.</em></p>
                        </div>
                    `;
                }
                
                actionsDiv.style.display = 'block';
                
            } catch (error) {
                document.getElementById('telegram-status').innerHTML = `
                    <div class="error">
                        ❌ Failed to load Telegram status: ${error.message}
                    </div>
                `;
            }
        }
        
        async function generateTelegramLink() {
            const linkBtn = document.getElementById('link-btn');
            const originalText = linkBtn.innerHTML;
            
            try {
                linkBtn.innerHTML = '🔄 Generating Link...';
                linkBtn.disabled = true;
                
                const response = await fetch(`/profile/telegram/link/${userId}`);
                const data = await response.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                if (data.linked) {
                    alert('Your account is already linked to Telegram!');
                    loadTelegramStatus(); // Refresh the page
                    return;
                }
                
                // Show instructions and create link button
                document.getElementById('link-instructions').style.display = 'block';
                
                linkBtn.innerHTML = `
                    <a href="${data.deep_link}" target="_blank" style="color: white; text-decoration: none;">
                        🚀 Open Telegram & Link Account
                    </a>
                `;
                linkBtn.disabled = false;
                
                // Add a refresh button
                linkBtn.insertAdjacentHTML('afterend', `
                    <button onclick="loadTelegramStatus()" class="telegram-button" style="background: #17a2b8; margin-left: 10px;">
                        🔄 Check Status
                    </button>
                `);
                
            } catch (error) {
                alert('Failed to generate link: ' + error.message);
                linkBtn.innerHTML = originalText;
                linkBtn.disabled = false;
            }
        }
        
        async function unlinkTelegram() {
            if (!confirm('Are you sure you want to unlink your Telegram account? You will stop receiving notifications.')) {
                return;
            }
            
            try {
                const response = await fetch(`/profile/telegram/unlink/${userId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                alert('Successfully unlinked Telegram account: @' + data.unlinked_username);
                loadTelegramStatus(); // Refresh the display
                
            } catch (error) {
                alert('Failed to unlink account: ' + error.message);
            }
        }
    </script>
</body>
</html>
    """
    
    return render_template_string(template, user=user)

# Helper function for other parts of your application
def get_user_telegram_link_button_html(user_id, username):
    """
    Generate HTML for a Telegram link button that can be embedded anywhere
    
    Usage in your templates:
    {{ get_user_telegram_link_button_html(current_user.id, current_user.username) | safe }}
    """
    return f"""
    <div class="telegram-link-widget" data-user-id="{user_id}">
        <button onclick="openTelegramLink({user_id})" class="btn btn-primary">
            📱 Link Telegram
        </button>
        <script>
        async function openTelegramLink(userId) {{
            try {{
                const response = await fetch('/profile/telegram/link/' + userId);
                const data = await response.json();
                if (data.deep_link) {{
                    window.open(data.deep_link, '_blank');
                }} else if (data.linked) {{
                    alert('Your account is already linked to Telegram!');
                }} else {{
                    alert('Error: ' + (data.error || 'Failed to generate link'));
                }}
            }} catch (error) {{
                alert('Failed to generate Telegram link');
            }}
        }}
        </script>
    </div>
    """

# Configuration helper
def setup_telegram_config():
    """
    Example configuration for your Flask app
    Add these to your config file or environment variables
    """
    config_example = """
    # Add these to your Flask configuration:
    
    # Your Telegram bot token from @BotFather
    TELEGRAM_BOT_TOKEN = "1234567890:ABCDEFghijklmnopqrstuvwxyz123456789"
    
    # Your bot username (without @)
    TELEGRAM_BOT_USERNAME = "ssleaguebot"  # or whatever your bot username is
    
    # Webhook URL for receiving Telegram updates
    TELEGRAM_WEBHOOK_URL = "https://yourdomain.com/telegram/webhook"
    
    # Optional: Customize deep link expiration (default: 24 hours)
    TELEGRAM_LINK_EXPIRES_HOURS = 24
    """
    return config_example

if __name__ == "__main__":
    print("Telegram Profile Integration Example")
    print("=" * 50)
    print()
    print("This file contains:")
    print("✅ API endpoints for Telegram linking")
    print("✅ Frontend integration examples")
    print("✅ Complete profile page with JavaScript")
    print("✅ Helper functions for templates")
    print()
    print("Configuration needed:")
    print(setup_telegram_config())
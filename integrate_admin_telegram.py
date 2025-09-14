# Instructions for integrating the Telegram Admin Dashboard into your Flask app

"""
To integrate the Telegram Admin Dashboard into your Flask application:

1. Copy the admin_telegram_routes.py file to your project directory
2. Copy the templates/admin/ directory to your templates folder
3. Add the following imports and registration to your main app.py file:
"""

# Add this import at the top of your app.py file
from admin_telegram_routes import admin_telegram_bp

# Register the blueprint in your Flask app (add this after creating your app)
app.register_blueprint(admin_telegram_bp)

"""
4. Make sure you have the required dependencies in your models:
   - User model with is_admin property
   - TelegramUser model with all the fields shown in the routes
   - NotificationLog model for tracking sent notifications
   - NotificationSettings model for storing configuration

5. Ensure your base.html template includes Bootstrap 5 and FontAwesome icons:
   - Bootstrap 5 CSS and JS
   - FontAwesome icons
   - jQuery (for some interactive features)

6. Add navigation links to your admin section. Example:
"""

admin_nav_example = """
<!-- Add this to your admin navigation menu -->
{% if current_user.is_admin %}
<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="telegramDropdown" role="button" 
       data-bs-toggle="dropdown" aria-expanded="false">
        <i class="fas fa-paper-plane"></i> Telegram
    </a>
    <ul class="dropdown-menu" aria-labelledby="telegramDropdown">
        <li><a class="dropdown-item" href="{{ url_for('admin_telegram.telegram_dashboard') }}">
            <i class="fas fa-tachometer-alt"></i> Dashboard
        </a></li>
        <li><a class="dropdown-item" href="{{ url_for('admin_telegram.telegram_users') }}">
            <i class="fas fa-users"></i> Manage Users
        </a></li>
        <li><a class="dropdown-item" href="{{ url_for('admin_telegram.telegram_settings') }}">
            <i class="fas fa-cog"></i> Settings
        </a></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item" href="#" onclick="showTestNotificationModal()">
            <i class="fas fa-paper-plane"></i> Send Test Notification
        </a></li>
    </ul>
</li>
{% endif %}
"""

"""
7. Features included in this admin dashboard:

MAIN DASHBOARD (/admin/telegram/):
- Real-time statistics (total users, linked users, notifications sent, etc.)
- Bot status monitoring
- Recent notifications feed
- User notification preferences breakdown
- Quick actions (send test notifications, manage users)
- Auto-refresh functionality

USER MANAGEMENT (/admin/telegram/users):
- List all Telegram-linked users with detailed information
- Search and filter capabilities (by status, notification preferences)
- View user's Telegram info (username, chat ID, link date)
- See notification preferences for each user
- Count of notifications sent to each user
- Bulk actions (toggle status, unlink multiple users)
- Individual user actions (view notifications, toggle status, unlink)
- Pagination for large user lists

USER NOTIFICATION HISTORY (/admin/telegram/user/<id>/notifications):
- Detailed notification history for individual users
- User profile information and status
- Notification preferences overview
- Statistics (total, sent, failed, today's notifications)
- Detailed notification logs with metadata
- Send test notifications to specific users
- Quick user management actions

SETTINGS PAGE (/admin/telegram/settings):
- Configuration status overview (bot token, webhook, etc.)
- Bot information and webhook status
- Tabbed settings interface:
  - General Settings (global toggles, retry settings)
  - Notification Types (default preferences for new users)
  - Advanced Settings (HTML formatting, rate limiting, templates)
- Webhook testing functionality
- Dangerous actions (reset settings, clear logs, unlink all users)

API ENDPOINTS:
- POST /admin/telegram/test-notification - Send test notifications
- POST /admin/telegram/user/<id>/toggle-status - Toggle user active status
- POST /admin/telegram/user/<id>/unlink - Unlink user's Telegram account
- GET /admin/telegram/stats/api - Get real-time statistics for dashboard
- POST /admin/telegram/settings - Save configuration settings

8. Security Features:
- All routes require login and admin privileges
- CSRF protection through form tokens
- Confirmation dialogs for destructive actions
- Rate limiting considerations
- Proper error handling and logging

9. UI/UX Features:
- Responsive design with Bootstrap 5
- Loading states and progress indicators
- Toast notifications for user feedback
- Modals for test notifications and confirmations
- Auto-refresh dashboard with toggle
- Sorting and filtering capabilities
- Pagination for large datasets
- Search functionality
- Bulk selection and actions

10. Make sure your notification service and telegram bot service are properly configured:
    - get_telegram_bot() function should return a working bot instance
    - get_notification_service() function should return notification service
    - TelegramUser.get_users_for_notification_type() method should exist
    - NotificationLog.create_log() method should work properly

This provides a complete admin interface for managing your Telegram notification system!
"""
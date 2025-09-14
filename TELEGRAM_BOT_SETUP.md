# Telegram Bot Setup Guide

This guide will help you set up and configure the Telegram bot for your auction app to send real-time notifications to users about all app activities.

## 🚀 Quick Start

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "Auction App Bot")
4. Choose a username (e.g., "auction_app_bot")
5. Save the bot token that BotFather gives you

### 2. Configure Environment Variables

Add these environment variables to your `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://yourapp.com/telegram/webhook
```

### 3. Run Database Migration

Run the database migration to create the necessary tables:

```bash
python migrations/add_telegram_notifications.py
```

### 4. Start Your App

Start your Flask application. You should see:
- ✅ Telegram notifications enabled

If you see a warning, check your bot token configuration.

## 📱 Bot Commands

Once users start a conversation with your bot, they can use these commands:

### User Commands
- `/start` - Welcome message and setup instructions
- `/help` - Show all available commands
- `/link <username>` - Link Telegram account to app user
- `/status` - Check notification settings  
- `/notifications on|off [type]` - Manage notification preferences
- `/unlink` - Unlink Telegram account

### Admin Commands (admin users only)
- `/stats` - View notification statistics

## 🔧 Configuration

### Webhook Setup (Production)

For production deployment, you need to set up a webhook:

1. Set `TELEGRAM_WEBHOOK_URL` to your public app URL + `/telegram/webhook`
2. Your app will automatically set the webhook when it starts

### Notification Types

The bot supports these notification types:

1. **login** - User login activities
2. **bids** - Auction bids and results  
3. **auction_start** - Auction round starts
4. **auction_end** - Auction round ends
5. **team_changes** - Team modifications
6. **admin_actions** - Administrative actions
7. **system_alerts** - System notifications

### User Preferences

Users can control which notifications they receive:

```bash
# Enable all notifications
/notifications on

# Disable all notifications  
/notifications off

# Enable specific type
/notifications on bids

# Disable specific type
/notifications off login
```

## 🎛️ Admin Panel

Access the admin notification panel at `/admin/notifications/` (admin users only).

### Features:
- **Dashboard** - Overview of bot status and statistics
- **Settings** - Configure bot behavior and limits
- **Users** - Manage linked Telegram users
- **Logs** - View notification history with filtering
- **Broadcast** - Send messages to all users
- **Test** - Send test notifications

## 🔗 User Linking Process

1. User starts conversation with bot: `/start`
2. User links account: `/link their_app_username`
3. Bot verifies the username exists in the app
4. User is now linked and will receive notifications
5. User can customize preferences: `/notifications`

## 📊 Monitoring

### View Statistics
- Total linked users
- Active vs inactive users
- Notification delivery status
- Notifications by type and status

### Logs
All notifications are logged with:
- Delivery status (pending, sent, failed, delivered)
- Timestamp
- User information  
- Message content
- Error details (if failed)

## 🚨 Troubleshooting

### Bot Not Working
1. Check `TELEGRAM_BOT_TOKEN` is correct
2. Verify bot token with BotFather
3. Check app logs for error messages
4. Ensure database migration was run

### Notifications Not Sending  
1. Check if users are linked: `/admin/notifications/users`
2. Verify user notification preferences
3. Check notification logs: `/admin/notifications/logs`
4. Test with: `/admin/notifications/` → Test Notification

### Webhook Issues
1. Ensure `TELEGRAM_WEBHOOK_URL` is publicly accessible
2. Check webhook status: `/telegram/webhook_info`  
3. Set webhook manually: `/telegram/set_webhook`

## 🔐 Security

### Bot Token Security
- Never commit bot tokens to version control
- Use environment variables only
- Regenerate tokens if compromised

### Webhook Security  
- Use HTTPS for webhook URLs
- Consider webhook secret validation (optional)
- Monitor webhook logs for suspicious activity

## 📚 API Reference

### Webhook Endpoints
- `POST /telegram/webhook` - Receive Telegram updates
- `POST /telegram/set_webhook` - Set webhook URL
- `GET /telegram/webhook_info` - Get webhook information

### Admin API Endpoints
- `GET /admin/notifications/` - Admin dashboard
- `GET /admin/notifications/settings` - Bot settings
- `GET /admin/notifications/users` - User management  
- `GET /admin/notifications/logs` - Notification logs
- `POST /admin/notifications/broadcast` - Send broadcast
- `POST /admin/notifications/test_notification` - Test notification

## 🎯 Notification Triggers

The bot automatically sends notifications for these events:

### Authentication
- User login/logout
- New user registration  
- Password changes

### Auction Activity
- Round starts
- Bids placed
- Round ends
- Tiebreakers
- Player acquisitions

### Team Management
- Team settings changes
- Logo uploads
- Member additions/removals

### Admin Actions
- User approvals
- Settings changes
- System maintenance

### System Events
- Database errors
- Performance issues
- Security alerts

## 📈 Performance

### Optimization Features
- Asynchronous message queue
- Background processing
- Rate limiting
- Database indexing  
- Connection pooling

### Scalability
- Supports unlimited users
- Handles high message volumes
- Efficient database queries
- Memory-optimized processing

## 🛠️ Customization

### Message Templates
Edit `telegram_service.py` to customize message formats:
- `format_user_action_message()` - User action notifications
- `format_system_alert_message()` - System alerts

### Add New Notification Types
1. Add new type to `TelegramUser` model preferences
2. Update notification type mappings
3. Add triggers in relevant routes
4. Update bot command handlers

### Custom Bot Commands
Add new commands in `telegram_routes.py`:
1. Add command handler function
2. Register in `handle_telegram_message()`
3. Update help text

## 📄 Database Schema

### Tables Created
- `telegram_user` - Links app users to Telegram
- `notification_log` - Tracks all notifications  
- `notification_settings` - Global bot configuration

### Indexes
- Optimized for fast lookups
- Efficient filtering and sorting
- Performance monitoring friendly

## 🔄 Migration and Updates

### Database Changes
Run migrations when updating:
```bash
python migrations/add_telegram_notifications.py
```

### Rollback (if needed)
```bash  
python migrations/add_telegram_notifications.py rollback
```

### Version Updates
1. Update bot service files
2. Run database migrations
3. Restart application
4. Test functionality

## 💬 Support

### Getting Help
1. Check logs first: `/admin/notifications/logs`
2. Test bot functionality: `/admin/notifications/`
3. Verify webhook status
4. Review configuration settings

### Common Issues
- **"Bot not available"** - Check token configuration
- **"Webhook failed"** - Verify URL accessibility  
- **"No notifications"** - Check user linking and preferences
- **"Database errors"** - Run migrations

This comprehensive Telegram bot integration provides real-time notifications for all user activities in your auction app, with full administrative control and user customization options.
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, TelegramUser, NotificationLog, NotificationSettings, User
from telegram_service import get_telegram_bot
from notification_service import get_notification_service
from functools import wraps
from datetime import datetime, timedelta
import json

# Create blueprint for admin notification routes
admin_notifications_bp = Blueprint('admin_notifications', __name__, url_prefix='/admin/notifications')

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_notifications_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin notification dashboard"""
    try:
        notification_service = get_notification_service()
        telegram_bot = get_telegram_bot()
        
        # Get statistics
        stats = notification_service.get_notification_stats() if notification_service else {}
        
        # Get recent notifications (last 50)
        recent_notifications = NotificationLog.query.order_by(NotificationLog.created_at.desc()).limit(50).all()
        
        # Get all Telegram users
        telegram_users = TelegramUser.query.all()
        
        # Get bot settings
        bot_enabled = NotificationSettings.get_setting('bot_enabled', 'false') == 'true'
        max_notifications = NotificationSettings.get_setting('max_notifications_per_hour', '100')
        rate_limit_enabled = NotificationSettings.get_setting('rate_limit_enabled', 'true') == 'true'
        
        # Get webhook info
        webhook_info = telegram_bot.get_webhook_info() if telegram_bot else {}
        
        return render_template('admin/notifications_dashboard.html',
                             stats=stats,
                             recent_notifications=recent_notifications,
                             telegram_users=telegram_users,
                             bot_enabled=bot_enabled,
                             max_notifications=max_notifications,
                             rate_limit_enabled=rate_limit_enabled,
                             webhook_info=webhook_info,
                             telegram_bot_available=telegram_bot is not None)
    
    except Exception as e:
        flash(f'Error loading dashboard: {e}', 'error')
        return redirect(url_for('dashboard'))

@admin_notifications_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Manage notification settings"""
    if request.method == 'POST':
        try:
            # Update bot settings
            bot_enabled = request.form.get('bot_enabled') == 'on'
            max_notifications = request.form.get('max_notifications', '100')
            rate_limit_enabled = request.form.get('rate_limit_enabled') == 'on'
            admin_chat_id = request.form.get('admin_chat_id', '')
            
            # Validate max_notifications
            try:
                max_notifications = int(max_notifications)
                if max_notifications < 1:
                    max_notifications = 100
            except ValueError:
                max_notifications = 100
            
            # Update settings
            NotificationSettings.set_setting('bot_enabled', str(bot_enabled).lower())
            NotificationSettings.set_setting('max_notifications_per_hour', str(max_notifications))
            NotificationSettings.set_setting('rate_limit_enabled', str(rate_limit_enabled).lower())
            NotificationSettings.set_setting('admin_chat_id', admin_chat_id)
            
            db.session.commit()
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('admin_notifications.settings'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating settings: {e}', 'error')
    
    # Get current settings
    bot_enabled = NotificationSettings.get_setting('bot_enabled', 'false') == 'true'
    max_notifications = NotificationSettings.get_setting('max_notifications_per_hour', '100')
    rate_limit_enabled = NotificationSettings.get_setting('rate_limit_enabled', 'true') == 'true'
    admin_chat_id = NotificationSettings.get_setting('admin_chat_id', '')
    
    return render_template('admin/notification_settings.html',
                         bot_enabled=bot_enabled,
                         max_notifications=max_notifications,
                         rate_limit_enabled=rate_limit_enabled,
                         admin_chat_id=admin_chat_id)

@admin_notifications_bp.route('/users')
@login_required
@admin_required
def users():
    """Manage Telegram users"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    telegram_users = TelegramUser.query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/notification_users.html',
                         telegram_users=telegram_users)

@admin_notifications_bp.route('/users/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    try:
        tg_user = TelegramUser.query.get_or_404(user_id)
        tg_user.is_active = not tg_user.is_active
        db.session.commit()
        
        status = "activated" if tg_user.is_active else "deactivated"
        flash(f'User {tg_user.user.username} {status} successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error toggling user status: {e}', 'error')
    
    return redirect(url_for('admin_notifications.users'))

@admin_notifications_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a Telegram user"""
    try:
        tg_user = TelegramUser.query.get_or_404(user_id)
        username = tg_user.user.username
        
        # Delete associated notification logs first
        NotificationLog.query.filter_by(telegram_user_id=user_id).delete()
        
        # Delete the Telegram user
        db.session.delete(tg_user)
        db.session.commit()
        
        flash(f'Telegram user for {username} deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {e}', 'error')
    
    return redirect(url_for('admin_notifications.users'))

@admin_notifications_bp.route('/logs')
@login_required
@admin_required  
def logs():
    """View notification logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    notification_type = request.args.get('type')
    status = request.args.get('status')
    user_id = request.args.get('user_id', type=int)
    
    query = NotificationLog.query
    
    # Apply filters
    if notification_type:
        query = query.filter_by(notification_type=notification_type)
    if status:
        query = query.filter_by(status=status)
    if user_id:
        query = query.filter_by(telegram_user_id=user_id)
    
    logs = query.order_by(NotificationLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get filter options
    notification_types = db.session.query(NotificationLog.notification_type.distinct()).all()
    notification_types = [t[0] for t in notification_types]
    
    statuses = db.session.query(NotificationLog.status.distinct()).all()
    statuses = [s[0] for s in statuses]
    
    telegram_users = TelegramUser.query.all()
    
    return render_template('admin/notification_logs.html',
                         logs=logs,
                         notification_types=notification_types,
                         statuses=statuses,
                         telegram_users=telegram_users,
                         current_type=notification_type,
                         current_status=status,
                         current_user_id=user_id)

@admin_notifications_bp.route('/test_notification', methods=['POST'])
@login_required
@admin_required
def test_notification():
    """Send a test notification"""
    try:
        notification_service = get_notification_service()
        if not notification_service:
            flash('Notification service not available', 'error')
            return redirect(url_for('admin_notifications.dashboard'))
        
        message_type = request.form.get('type', 'system_alert')
        test_message = request.form.get('message', 'This is a test notification from the admin panel.')
        
        if message_type == 'system_alert':
            notification_service.send_system_alert(
                alert_type='Admin Test',
                message=test_message,
                severity='info'
            )
        elif message_type == 'user_action':
            notification_service.send_user_action_notification(
                user_action='Admin test notification',
                actor_user_id=current_user.id,
                details={'test': True, 'message': test_message}
            )
        
        flash('Test notification sent successfully!', 'success')
        
    except Exception as e:
        flash(f'Error sending test notification: {e}', 'error')
    
    return redirect(url_for('admin_notifications.dashboard'))

@admin_notifications_bp.route('/webhook/set', methods=['POST'])
@login_required
@admin_required
def set_webhook():
    """Set Telegram webhook"""
    try:
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            return jsonify({'error': 'Telegram bot not available'}), 503
        
        webhook_url = request.form.get('webhook_url')
        if not webhook_url:
            return jsonify({'error': 'Webhook URL required'}), 400
        
        success = telegram_bot.set_webhook(webhook_url)
        
        if success:
            flash('Webhook set successfully!', 'success')
            return jsonify({'success': True})
        else:
            flash('Failed to set webhook', 'error') 
            return jsonify({'error': 'Failed to set webhook'}), 500
            
    except Exception as e:
        flash(f'Error setting webhook: {e}', 'error')
        return jsonify({'error': str(e)}), 500

@admin_notifications_bp.route('/webhook/info')
@login_required
@admin_required
def webhook_info():
    """Get webhook info"""
    try:
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            return jsonify({'error': 'Telegram bot not available'}), 503
        
        info = telegram_bot.get_webhook_info()
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_notifications_bp.route('/stats/api')
@login_required
@admin_required
def stats_api():
    """Get notification statistics as JSON"""
    try:
        notification_service = get_notification_service()
        stats = notification_service.get_notification_stats() if notification_service else {}
        
        # Add recent activity
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        today_count = NotificationLog.query.filter(
            NotificationLog.created_at >= today
        ).count()
        
        yesterday_count = NotificationLog.query.filter(
            NotificationLog.created_at >= yesterday,
            NotificationLog.created_at < today
        ).count()
        
        stats['today_notifications'] = today_count
        stats['yesterday_notifications'] = yesterday_count
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_notifications_bp.route('/broadcast', methods=['GET', 'POST'])
@login_required
@admin_required
def broadcast():
    """Broadcast message to all users"""
    if request.method == 'POST':
        try:
            telegram_bot = get_telegram_bot()
            if not telegram_bot:
                flash('Telegram bot not available', 'error')
                return redirect(url_for('admin_notifications.broadcast'))
            
            message = request.form.get('message', '').strip()
            message_type = request.form.get('message_type', 'admin')
            target_users = request.form.get('target_users', 'all')
            
            if not message:
                flash('Message is required', 'error')
                return redirect(url_for('admin_notifications.broadcast'))
            
            # Get target users
            if target_users == 'all':
                telegram_users = TelegramUser.get_active_users()
            elif target_users == 'admins':
                telegram_users = [tu for tu in TelegramUser.get_active_users() if tu.user.is_admin]
            elif target_users == 'regular':
                telegram_users = [tu for tu in TelegramUser.get_active_users() if not tu.user.is_admin]
            else:
                telegram_users = TelegramUser.get_active_users()
            
            if not telegram_users:
                flash('No target users found', 'warning')
                return redirect(url_for('admin_notifications.broadcast'))
            
            # Format message
            if message_type == 'admin':
                formatted_message = f"📢 <b>Admin Announcement</b>\\n\\n{message}"
            elif message_type == 'system':
                formatted_message = f"ℹ️ <b>System Notification</b>\\n\\n{message}"
            else:
                formatted_message = message
            
            # Send to all users
            chat_ids = [user.telegram_chat_id for user in telegram_users]
            results = telegram_bot.broadcast_message(
                chat_ids=chat_ids,
                text=formatted_message,
                parse_mode='HTML'
            )
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            # Log the broadcast
            for telegram_user in telegram_users:
                success = results.get(telegram_user.telegram_chat_id, False)
                log = NotificationLog.create_log(
                    telegram_user_id=telegram_user.id,
                    notification_type='admin_broadcast',
                    message=formatted_message,
                    user_action='Admin broadcast message',
                    actor_user_id=current_user.id,
                    message_data={'broadcast': True, 'target': target_users}
                )
                if success:
                    log.mark_sent()
                else:
                    log.mark_failed('Broadcast delivery failed')
            
            db.session.commit()
            
            flash(f'Broadcast sent to {success_count}/{total_count} users successfully!', 'success')
            return redirect(url_for('admin_notifications.broadcast'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error sending broadcast: {e}', 'error')
    
    # Get user counts for targeting options
    total_users = TelegramUser.query.filter_by(is_active=True).count()
    admin_users = len([tu for tu in TelegramUser.get_active_users() if tu.user.is_admin])
    regular_users = total_users - admin_users
    
    return render_template('admin/notification_broadcast.html',
                         total_users=total_users,
                         admin_users=admin_users,
                         regular_users=regular_users)
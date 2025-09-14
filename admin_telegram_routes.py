from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, User, TelegramUser, NotificationLog, NotificationSettings
from telegram_service import get_telegram_bot
from notification_service import get_notification_service
from sqlalchemy import func, desc, and_
from datetime import datetime, timezone, timedelta
import json
import logging

logger = logging.getLogger(__name__)

# Create blueprint for admin telegram management
admin_telegram_bp = Blueprint('admin_telegram', __name__, url_prefix='/admin/telegram')

@admin_telegram_bp.route('/')
@login_required
def telegram_dashboard():
    """Main admin dashboard for Telegram notifications management"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get service instances
        telegram_bot = get_telegram_bot()
        notification_service = get_notification_service()
        
        # Basic statistics
        total_users = User.query.count()
        linked_users = TelegramUser.query.count()
        active_linked = TelegramUser.query.filter_by(is_active=True).count()
        
        # Notification statistics
        total_notifications = NotificationLog.query.count()
        today_notifications = NotificationLog.query.filter(
            NotificationLog.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        failed_notifications = NotificationLog.query.filter_by(status='failed').count()
        
        # Bot status
        bot_status = {
            'available': telegram_bot is not None,
            'token_valid': telegram_bot.verify_bot_token() if telegram_bot else False,
            'username': current_app.config.get('TELEGRAM_BOT_USERNAME', 'Not configured'),
            'webhook_configured': bool(current_app.config.get('TELEGRAM_WEBHOOK_URL'))
        }
        
        # Recent notifications
        recent_notifications = NotificationLog.query.order_by(desc(NotificationLog.created_at)).limit(10).all()
        
        # Notification type breakdown
        notification_types = db.session.query(
            NotificationLog.notification_type,
            func.count(NotificationLog.id).label('count')
        ).group_by(NotificationLog.notification_type).all()
        
        # User preference statistics
        preference_stats = {
            'login': TelegramUser.query.filter_by(notify_login=True, is_active=True).count(),
            'bids': TelegramUser.query.filter_by(notify_bids=True, is_active=True).count(),
            'auction_start': TelegramUser.query.filter_by(notify_auction_start=True, is_active=True).count(),
            'auction_end': TelegramUser.query.filter_by(notify_auction_end=True, is_active=True).count(),
            'team_changes': TelegramUser.query.filter_by(notify_team_changes=True, is_active=True).count(),
            'admin_actions': TelegramUser.query.filter_by(notify_admin_actions=True, is_active=True).count(),
            'system_alerts': TelegramUser.query.filter_by(notify_system_alerts=True, is_active=True).count()
        }
        
        return render_template('admin/telegram_dashboard.html',
                              total_users=total_users,
                              linked_users=linked_users,
                              active_linked=active_linked,
                              total_notifications=total_notifications,
                              today_notifications=today_notifications,
                              failed_notifications=failed_notifications,
                              bot_status=bot_status,
                              recent_notifications=recent_notifications,
                              notification_types=notification_types,
                              preference_stats=preference_stats)
        
    except Exception as e:
        logger.error(f"Error loading telegram dashboard: {e}")
        flash('Error loading Telegram dashboard', 'error')
        return redirect(url_for('dashboard'))

@admin_telegram_bp.route('/users')
@login_required
def telegram_users():
    """View all Telegram-linked users with detailed information"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Filter options
        status_filter = request.args.get('status', 'all')  # all, active, inactive
        notification_filter = request.args.get('notifications', 'all')  # all, enabled, disabled
        search_query = request.args.get('search', '')
        
        # Base query
        query = TelegramUser.query.join(User)
        
        # Apply filters
        if status_filter == 'active':
            query = query.filter(TelegramUser.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(TelegramUser.is_active == False)
        
        if search_query:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search_query}%'),
                    TelegramUser.telegram_username.ilike(f'%{search_query}%'),
                    TelegramUser.first_name.ilike(f'%{search_query}%')
                )
            )
        
        # Notification filter (users with any notifications enabled)
        if notification_filter == 'enabled':
            query = query.filter(
                db.or_(
                    TelegramUser.notify_login == True,
                    TelegramUser.notify_bids == True,
                    TelegramUser.notify_auction_start == True,
                    TelegramUser.notify_auction_end == True,
                    TelegramUser.notify_team_changes == True,
                    TelegramUser.notify_admin_actions == True,
                    TelegramUser.notify_system_alerts == True
                )
            )
        elif notification_filter == 'disabled':
            query = query.filter(
                and_(
                    TelegramUser.notify_login == False,
                    TelegramUser.notify_bids == False,
                    TelegramUser.notify_auction_start == False,
                    TelegramUser.notify_auction_end == False,
                    TelegramUser.notify_team_changes == False,
                    TelegramUser.notify_admin_actions == False,
                    TelegramUser.notify_system_alerts == False
                )
            )
        
        # Paginate results
        telegram_users_pagination = query.order_by(desc(TelegramUser.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get notification counts for each user
        user_notification_counts = {}
        for tg_user in telegram_users_pagination.items:
            count = NotificationLog.query.filter_by(telegram_user_id=tg_user.id).count()
            user_notification_counts[tg_user.id] = count
        
        return render_template('admin/telegram_users.html',
                              telegram_users=telegram_users_pagination.items,
                              pagination=telegram_users_pagination,
                              notification_counts=user_notification_counts,
                              status_filter=status_filter,
                              notification_filter=notification_filter,
                              search_query=search_query)
        
    except Exception as e:
        logger.error(f"Error loading telegram users: {e}")
        flash('Error loading Telegram users', 'error')
        return redirect(url_for('admin_telegram.telegram_dashboard'))

@admin_telegram_bp.route('/test-notification', methods=['POST'])
@login_required
def test_notification():
    """Send test notification to selected users or all users"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        notification_type = data.get('type', 'system_alerts')
        target_users = data.get('users', [])  # List of telegram_user IDs, empty = all users
        test_mode = data.get('test_mode', False)  # If true, only send to current admin
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        telegram_bot = get_telegram_bot()
        if not telegram_bot:
            return jsonify({'error': 'Telegram bot not available'}), 503
        
        results = {
            'sent': 0,
            'failed': 0,
            'details': []
        }
        
        # Determine target users
        if test_mode:
            # Send only to current admin if they have Telegram linked
            admin_tg = TelegramUser.query.filter_by(user_id=current_user.id, is_active=True).first()
            target_telegram_users = [admin_tg] if admin_tg else []
        elif target_users:
            # Send to specific users
            target_telegram_users = TelegramUser.query.filter(
                TelegramUser.id.in_(target_users),
                TelegramUser.is_active == True
            ).all()
        else:
            # Send to all active users who have this notification type enabled
            target_telegram_users = TelegramUser.get_users_for_notification_type(notification_type)
        
        if not target_telegram_users:
            return jsonify({'error': 'No valid target users found'}), 400
        
        # Send test notification to each user
        for tg_user in target_telegram_users:
            try:
                # Format test message
                test_message = f"🧪 <b>Test Notification</b>\n\n{message}\n\n<i>Sent by admin: {current_user.username}</i>\n<i>Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</i>"
                
                # Send message
                success = telegram_bot.send_message(
                    chat_id=tg_user.telegram_chat_id,
                    text=test_message,
                    parse_mode='HTML'
                )
                
                # Log the attempt
                log_entry = NotificationLog.create_log(
                    telegram_user_id=tg_user.id,
                    notification_type=f"test_{notification_type}",
                    message=test_message,
                    user_action="Admin test notification",
                    actor_user_id=current_user.id,
                    message_data={'test_mode': test_mode, 'original_message': message}
                )
                
                if success:
                    log_entry.mark_sent()
                    results['sent'] += 1
                    results['details'].append({
                        'user': tg_user.user.username,
                        'telegram': f"@{tg_user.telegram_username}" if tg_user.telegram_username else tg_user.first_name,
                        'status': 'sent'
                    })
                else:
                    log_entry.mark_failed("Failed to send message")
                    results['failed'] += 1
                    results['details'].append({
                        'user': tg_user.user.username,
                        'telegram': f"@{tg_user.telegram_username}" if tg_user.telegram_username else tg_user.first_name,
                        'status': 'failed'
                    })
                
                db.session.add(log_entry)
                
            except Exception as e:
                logger.error(f"Failed to send test notification to {tg_user.user.username}: {e}")
                results['failed'] += 1
                results['details'].append({
                    'user': tg_user.user.username,
                    'telegram': f"@{tg_user.telegram_username}" if tg_user.telegram_username else tg_user.first_name,
                    'status': 'error',
                    'error': str(e)
                })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Test notification completed. Sent: {results["sent"]}, Failed: {results["failed"]}',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to send test notification: {str(e)}'}), 500

@admin_telegram_bp.route('/user/<int:user_id>/notifications')
@login_required
def user_notifications(user_id):
    """View notification history for a specific user"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        tg_user = TelegramUser.query.filter_by(user_id=user_id).first()
        if not tg_user:
            flash('User not found or not linked to Telegram', 'error')
            return redirect(url_for('admin_telegram.telegram_users'))
        
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # Get notification history
        notifications = NotificationLog.query.filter_by(telegram_user_id=tg_user.id).order_by(
            desc(NotificationLog.created_at)
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        # Get statistics
        stats = {
            'total': NotificationLog.query.filter_by(telegram_user_id=tg_user.id).count(),
            'sent': NotificationLog.query.filter_by(telegram_user_id=tg_user.id, status='sent').count(),
            'failed': NotificationLog.query.filter_by(telegram_user_id=tg_user.id, status='failed').count(),
            'today': NotificationLog.query.filter(
                NotificationLog.telegram_user_id == tg_user.id,
                NotificationLog.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            ).count()
        }
        
        return render_template('admin/user_notifications.html',
                              tg_user=tg_user,
                              notifications=notifications,
                              stats=stats)
        
    except Exception as e:
        logger.error(f"Error loading user notifications: {e}")
        flash('Error loading user notifications', 'error')
        return redirect(url_for('admin_telegram.telegram_users'))

@admin_telegram_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def telegram_settings():
    """Manage global Telegram settings"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Update notification settings
            for setting_name, setting_value in data.items():
                setting = NotificationSettings.query.filter_by(setting_name=setting_name).first()
                if setting:
                    setting.setting_value = json.dumps(setting_value)
                    setting.updated_at = datetime.now(timezone.utc)
                else:
                    setting = NotificationSettings(
                        setting_name=setting_name,
                        setting_value=json.dumps(setting_value),
                        description=f"Setting for {setting_name}"
                    )
                    db.session.add(setting)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Settings updated successfully'})
            
        except Exception as e:
            logger.error(f"Error updating telegram settings: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to update settings'}), 500
    
    else:
        # GET request - show settings page
        try:
            # Get current settings
            settings = {}
            for setting in NotificationSettings.query.all():
                try:
                    settings[setting.setting_name] = json.loads(setting.setting_value)
                except:
                    settings[setting.setting_name] = setting.setting_value
            
            # Get bot info
            telegram_bot = get_telegram_bot()
            bot_info = {}
            if telegram_bot:
                try:
                    webhook_info = telegram_bot.get_webhook_info()
                    bot_info = webhook_info.get('result', {}) if webhook_info else {}
                except:
                    bot_info = {}
            
            return render_template('admin/telegram_settings.html',
                                  settings=settings,
                                  bot_info=bot_info,
                                  config={
                                      'bot_token_configured': bool(current_app.config.get('TELEGRAM_BOT_TOKEN')),
                                      'bot_username': current_app.config.get('TELEGRAM_BOT_USERNAME', 'Not configured'),
                                      'webhook_url': current_app.config.get('TELEGRAM_WEBHOOK_URL', 'Not configured'),
                                      'link_expires_hours': current_app.config.get('TELEGRAM_LINK_EXPIRES_HOURS', 24)
                                  })
            
        except Exception as e:
            logger.error(f"Error loading telegram settings: {e}")
            flash('Error loading Telegram settings', 'error')
            return redirect(url_for('admin_telegram.telegram_dashboard'))

@admin_telegram_bp.route('/user/<int:telegram_user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(telegram_user_id):
    """Toggle a user's active status"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        tg_user = TelegramUser.query.get_or_404(telegram_user_id)
        tg_user.is_active = not tg_user.is_active
        tg_user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        status = "activated" if tg_user.is_active else "deactivated"
        
        return jsonify({
            'success': True,
            'message': f'User {tg_user.user.username} {status} successfully',
            'new_status': tg_user.is_active
        })
        
    except Exception as e:
        logger.error(f"Error toggling user status: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update user status'}), 500

@admin_telegram_bp.route('/user/<int:telegram_user_id>/unlink', methods=['POST'])
@login_required
def admin_unlink_user(telegram_user_id):
    """Admin function to unlink a user's Telegram account"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        tg_user = TelegramUser.query.get_or_404(telegram_user_id)
        username = tg_user.user.username
        
        # Log the admin action
        log_entry = NotificationLog.create_log(
            telegram_user_id=tg_user.id,
            notification_type='admin_actions',
            message=f'Admin {current_user.username} unlinked Telegram account for user {username}',
            user_action='Admin unlink user',
            actor_user_id=current_user.id
        )
        db.session.add(log_entry)
        
        # Delete the telegram user
        db.session.delete(tg_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully unlinked Telegram account for {username}'
        })
        
    except Exception as e:
        logger.error(f"Error unlinking user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to unlink user'}), 500

@admin_telegram_bp.route('/stats/api')
@login_required
def stats_api():
    """API endpoint for dashboard statistics (for AJAX updates)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get real-time statistics
        stats = {
            'total_users': User.query.count(),
            'linked_users': TelegramUser.query.count(),
            'active_linked': TelegramUser.query.filter_by(is_active=True).count(),
            'total_notifications': NotificationLog.query.count(),
            'today_notifications': NotificationLog.query.filter(
                NotificationLog.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            ).count(),
            'failed_notifications': NotificationLog.query.filter_by(status='failed').count(),
            'bot_status': {
                'available': get_telegram_bot() is not None,
                'token_valid': get_telegram_bot().verify_bot_token() if get_telegram_bot() else False
            }
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500
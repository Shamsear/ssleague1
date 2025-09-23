/**
 * Real-time Round Status Manager
 * Handles live updates for active rounds, new round notifications, and timer updates
 * without requiring page refreshes
 */

class RealTimeRoundsManager {
    constructor(options = {}) {
        this.pollInterval = options.pollInterval || 2000; // Poll every 2 seconds
        this.isPolling = false;
        this.pollTimer = null;
        this.lastActiveRoundsCount = 0;
        this.lastBulkRoundId = null;
        this.isAdmin = options.isAdmin || false;
        this.currentPage = options.currentPage || 'dashboard';
        this.showNotifications = options.showNotifications !== false;
        
        // Bind methods to preserve context
        this.startPolling = this.startPolling.bind(this);
        this.stopPolling = this.stopPolling.bind(this);
        this.pollForUpdates = this.pollForUpdates.bind(this);
        this.handleRoundUpdate = this.handleRoundUpdate.bind(this);
        this.showNewRoundNotification = this.showNewRoundNotification.bind(this);
        
        // Initialize
        this.init();
    }
    
    init() {
        // Get initial round count
        const activeRoundsContainer = document.getElementById('active-rounds-container');
        if (activeRoundsContainer) {
            const roundElements = activeRoundsContainer.querySelectorAll('[data-round-id]');
            this.lastActiveRoundsCount = roundElements.length;
        }
        
        // Start polling when page is visible
        this.setupVisibilityHandling();
        this.startPolling();
        
        console.log('RealTimeRoundsManager initialized');
    }
    
    setupVisibilityHandling() {
        // Stop polling when page is hidden, resume when visible
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopPolling();
            } else {
                this.startPolling();
            }
        });
        
        // Handle page unload
        window.addEventListener('beforeunload', () => {
            this.stopPolling();
        });
    }
    
    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.pollTimer = setInterval(this.pollForUpdates, this.pollInterval);
        console.log('Started real-time polling for round updates');
    }
    
    stopPolling() {
        if (!this.isPolling) return;
        
        this.isPolling = false;
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
        console.log('Stopped real-time polling');
    }
    
    async pollForUpdates() {
        try {
            const endpoint = this.isAdmin ? '/admin_dashboard_update' : '/team_dashboard_update';
            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.handleRoundUpdate(data);
            
        } catch (error) {
            console.error('Error polling for round updates:', error);
            // Don't stop polling on error, just log it
        }
    }
    
    handleRoundUpdate(data) {
        // Handle new rounds starting
        if (data.just_started_rounds && data.just_started_rounds.length > 0) {
            this.handleNewRounds(data.just_started_rounds);
        }
        
        // Handle bulk round status changes
        if (data.bulk_round_status_changed) {
            this.handleBulkRoundStatusChange(data);
        }
        
        // Update round counts and UI elements
        this.updateRoundUI(data);
        
        // Handle tiebreakers
        if (data.team_tiebreakers_count > 0 || data.team_bulk_tiebreakers_count > 0) {
            this.handleTiebreakers(data);
        }
        
        // Check if full refresh is needed
        if (data.needs_refresh && this.showNotifications) {
            this.handlePageRefreshNeeded(data);
        }
    }
    
    handleNewRounds(newRounds) {
        newRounds.forEach(round => {
            console.log(`New round started: ${round.position} (ID: ${round.id})`);
            
            // Show notification
            if (this.showNotifications) {
                this.showNewRoundNotification(round);
            }
            
            // Refresh the active rounds section
            this.refreshActiveRoundsSection();
            
            // Start round timer if we have timer elements
            this.initializeRoundTimer(round.id);
        });
        
        this.lastActiveRoundsCount += newRounds.length;
    }
    
    handleBulkRoundStatusChange(data) {
        if (data.bulk_round_just_started && this.showNotifications) {
            this.showBulkRoundNotification('started', data.active_bulk_round);
        } else if (data.bulk_round_just_ended && this.showNotifications) {
            this.showBulkRoundNotification('ended');
        }
        
        // Refresh the bulk round section
        this.refreshBulkRoundSection();
    }
    
    async refreshActiveRoundsSection() {
        const container = document.getElementById('active-rounds-container');
        if (!container) return;
        
        try {
            const endpoint = this.isAdmin ? '/admin/rounds_update' : '/team_dashboard_update';
            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (this.isAdmin && data.activeRoundsHtml) {
                container.innerHTML = data.activeRoundsHtml;
                this.initializeAllRoundTimers();
            } else if (!this.isAdmin) {
                // For team users, reload the entire dashboard to get updated template
                this.softRefreshPage();
            }
            
        } catch (error) {
            console.error('Error refreshing active rounds section:', error);
        }
    }
    
    async refreshBulkRoundSection() {
        // Similar to refreshActiveRoundsSection but for bulk rounds
        const container = document.getElementById('bulk-rounds-container');
        if (container) {
            // You can implement bulk round specific refresh here
            console.log('Refreshing bulk rounds section');
        }
    }
    
    updateRoundUI(data) {
        // Update round counters
        const activeCountElement = document.querySelector('[data-active-rounds-count]');
        if (activeCountElement && data.active_rounds_count !== undefined) {
            activeCountElement.textContent = data.active_rounds_count;
        }
        
        // Update navigation badges
        const roundsBadge = document.querySelector('.nav-rounds-badge');
        if (roundsBadge && data.active_rounds_count !== undefined) {
            if (data.active_rounds_count > 0) {
                roundsBadge.textContent = data.active_rounds_count;
                roundsBadge.style.display = 'inline';
            } else {
                roundsBadge.style.display = 'none';
            }
        }
    }
    
    handleTiebreakers(data) {
        if (data.team_tiebreakers_count > 0) {
            // Redirect to tiebreaker if needed
            console.log('Tiebreakers detected, may need redirect');
        }
    }
    
    handlePageRefreshNeeded(data) {
        // Instead of full page refresh, try to update sections dynamically
        console.log('Page refresh needed, performing soft refresh');
        this.softRefreshPage();
    }
    
    softRefreshPage() {
        // Reload only the dynamic content areas instead of full page refresh
        this.refreshActiveRoundsSection();
        this.refreshBulkRoundSection();
    }
    
    showNewRoundNotification(round) {
        // Create and show a notification for new round
        const notification = this.createNotification({
            title: 'New Round Started!',
            message: `${round.position} round is now active (${round.max_bids} bids allowed)`,
            type: 'success',
            duration: 8000,
            actions: [{
                text: 'Place Bids',
                href: '/team_round'
            }]
        });
        
        this.showNotification(notification);
        
        // Also play a sound if available
        this.playNotificationSound();
    }
    
    showBulkRoundNotification(action, bulkRound = null) {
        let message;
        if (action === 'started') {
            message = `Bulk round started! Base price: £${bulkRound.base_price.toLocaleString()}`;
        } else {
            message = 'Bulk round has ended';
        }
        
        const notification = this.createNotification({
            title: `Bulk Round ${action === 'started' ? 'Started' : 'Ended'}!`,
            message: message,
            type: action === 'started' ? 'info' : 'warning',
            duration: 6000,
            actions: action === 'started' ? [{
                text: 'View Round',
                href: '/team_bulk_round'
            }] : []
        });
        
        this.showNotification(notification);
        this.playNotificationSound();
    }
    
    createNotification({title, message, type = 'info', duration = 5000, actions = []}) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} fade-in`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            background: ${this.getNotificationColor(type)};
            color: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            max-width: 350px;
            word-wrap: break-word;
            animation: slideInFromRight 0.5s ease-out;
        `;
        
        const content = document.createElement('div');
        content.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 4px;">${title}</div>
            <div style="font-size: 14px; margin-bottom: ${actions.length > 0 ? '8px' : '0'};">${message}</div>
            ${actions.map(action => `
                <a href="${action.href}" 
                   style="display: inline-block; background: rgba(255,255,255,0.2); 
                          color: white; text-decoration: none; padding: 4px 8px; 
                          border-radius: 4px; font-size: 12px; margin-right: 4px;">
                    ${action.text}
                </a>
            `).join('')}
        `;
        
        notification.appendChild(content);
        
        // Auto-remove notification
        setTimeout(() => {
            notification.remove();
        }, duration);
        
        // Click to close
        notification.addEventListener('click', (e) => {
            if (e.target.tagName !== 'A') {
                notification.remove();
            }
        });
        
        return notification;
    }
    
    showNotification(notification) {
        document.body.appendChild(notification);
        
        // Add CSS animation if not already present
        if (!document.querySelector('#round-notification-styles')) {
            const style = document.createElement('style');
            style.id = 'round-notification-styles';
            style.textContent = `
                @keyframes slideInFromRight {
                    0% { transform: translateX(100%); opacity: 0; }
                    100% { transform: translateX(0); opacity: 1; }
                }
                .fade-in { animation: slideInFromRight 0.5s ease-out; }
            `;
            document.head.appendChild(style);
        }
    }
    
    getNotificationColor(type) {
        const colors = {
            success: '#10b981',
            info: '#3b82f6',
            warning: '#f59e0b',
            error: '#ef4444'
        };
        return colors[type] || colors.info;
    }
    
    playNotificationSound() {
        // Play a subtle notification sound
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrPn66hVFApGn+LyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMcBjiR2e7MeSsFJHfH8N2QQAoUXrTp66hVFApGn+DyvmM=');
            audio.volume = 0.1;
            audio.play().catch(() => {
                // Ignore audio play errors (user interaction required, etc.)
            });
        } catch (error) {
            // Ignore audio errors
        }
    }
    
    initializeRoundTimer(roundId) {
        // Initialize individual round timer
        const timerElement = document.getElementById(`timer-remaining-${roundId}`);
        if (timerElement) {
            this.startRoundTimer(roundId);
        }
    }
    
    initializeAllRoundTimers() {
        // Initialize all visible round timers
        const timerElements = document.querySelectorAll('[id^="timer-remaining-"]');
        timerElements.forEach(element => {
            const roundId = element.id.replace('timer-remaining-', '');
            this.startRoundTimer(roundId);
        });
    }
    
    startRoundTimer(roundId) {
        // Enhanced timer that auto-updates from server
        const timerElement = document.getElementById(`timer-remaining-${roundId}`);
        if (!timerElement) return;
        
        const updateTimer = async () => {
            try {
                const response = await fetch(`/check_round_status/${roundId}`);
                const data = await response.json();
                
                if (data.active && data.remaining) {
                    const minutes = Math.floor(data.remaining / 60);
                    const seconds = Math.floor(data.remaining % 60);
                    timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                    
                    if (data.remaining > 0) {
                        setTimeout(updateTimer, 1000);
                    } else {
                        timerElement.textContent = "0:00";
                        this.refreshActiveRoundsSection(); // Refresh when timer expires
                    }
                } else {
                    timerElement.textContent = "Ended";
                    this.refreshActiveRoundsSection(); // Refresh when round ends
                }
            } catch (error) {
                console.error(`Error updating timer for round ${roundId}:`, error);
            }
        };
        
        updateTimer();
    }
    
    // Public methods
    refreshNow() {
        this.pollForUpdates();
    }
    
    setPollInterval(interval) {
        this.pollInterval = interval;
        if (this.isPolling) {
            this.stopPolling();
            this.startPolling();
        }
    }
}

// Global instance - will be initialized when DOM is ready
let realTimeRoundsManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on a page that needs real-time updates
    const needsRealTime = (
        document.getElementById('active-rounds-container') ||
        document.querySelector('[data-active-rounds-count]') ||
        document.body.classList.contains('dashboard-page') ||
        document.body.classList.contains('rounds-page')
    );
    
    if (needsRealTime) {
        // Detect if user is admin
        const isAdmin = document.body.classList.contains('admin-page') || 
                       window.location.pathname.includes('/admin');
        
        // Detect current page
        let currentPage = 'dashboard';
        if (window.location.pathname.includes('/admin')) {
            currentPage = 'admin';
        } else if (window.location.pathname.includes('/team_round')) {
            currentPage = 'team_round';
        }
        
        realTimeRoundsManager = new RealTimeRoundsManager({
            isAdmin: isAdmin,
            currentPage: currentPage,
            pollInterval: 2000,
            showNotifications: true
        });
        
        console.log('Real-time rounds manager initialized for', currentPage);
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (realTimeRoundsManager) {
        realTimeRoundsManager.stopPolling();
    }
});

// Expose for manual control
window.RealTimeRoundsManager = RealTimeRoundsManager;
window.realTimeRoundsManager = realTimeRoundsManager;
/**
 * Timer Utility Library
 * Provides consistent timer functionality across the application
 * Fixes client-side drift and improves timer accuracy
 */

class TimerManager {
    constructor() {
        this.timers = new Map();
        this.serverTimeOffset = 0;
        this.isActive = false;
        
        // Start the main timer loop
        this.startTimerLoop();
    }

    /**
     * Add a new timer
     * @param {string} timerId - Unique identifier for the timer
     * @param {Object} config - Timer configuration
     */
    addTimer(timerId, config) {
        const timer = {
            id: timerId,
            endpointUrl: config.endpointUrl,
            displayElements: config.displayElements || [],
            callbacks: config.callbacks || {},
            lastServerSync: null,
            serverTimeRemaining: null,
            lastUpdateTime: null,
            isActive: true,
            syncInterval: config.syncInterval || 5000, // Sync every 5 seconds
            lastSyncTime: 0,
            errorCount: 0,
            maxErrors: 3
        };

        this.timers.set(timerId, timer);
        
        // Initial sync
        this.syncTimerWithServer(timerId);
    }

    /**
     * Remove a timer
     * @param {string} timerId - Timer identifier
     */
    removeTimer(timerId) {
        this.timers.delete(timerId);
    }

    /**
     * Start the main timer loop
     */
    startTimerLoop() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.updateLoop();
    }

    /**
     * Stop the main timer loop
     */
    stopTimerLoop() {
        this.isActive = false;
    }

    /**
     * Main update loop - runs every 100ms for smooth updates
     */
    updateLoop() {
        if (!this.isActive) return;

        const now = performance.now();

        this.timers.forEach((timer, timerId) => {
            // Check if we need to sync with server
            if (now - timer.lastSyncTime >= timer.syncInterval) {
                this.syncTimerWithServer(timerId);
            } else if (timer.serverTimeRemaining !== null && timer.lastUpdateTime !== null) {
                // Update timer locally
                this.updateTimerDisplay(timerId);
            }
        });

        // Schedule next update
        requestAnimationFrame(() => this.updateLoop());
    }

    /**
     * Sync timer with server
     * @param {string} timerId - Timer identifier
     */
    async syncTimerWithServer(timerId) {
        const timer = this.timers.get(timerId);
        if (!timer || !timer.endpointUrl) return;

        try {
            const response = await fetch(timer.endpointUrl + `?_=${Date.now()}`, {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            const syncTime = performance.now();

            // Update timer with server data
            timer.serverTimeRemaining = data.remaining || 0;
            timer.lastUpdateTime = syncTime;
            timer.lastSyncTime = syncTime;
            timer.errorCount = 0;

            // Handle timer expiration or inactivity
            if (!data.active || data.remaining <= 0) {
                this.handleTimerExpired(timerId, data);
                return;
            }

            // Update display immediately
            this.updateTimerDisplay(timerId);

            // Call sync callback if provided
            if (timer.callbacks.onSync) {
                timer.callbacks.onSync(data);
            }

        } catch (error) {
            console.error(`Timer sync error for ${timerId}:`, error);
            
            timer.errorCount++;
            if (timer.errorCount >= timer.maxErrors) {
                console.warn(`Timer ${timerId} exceeded max errors, removing timer`);
                this.removeTimer(timerId);
                
                if (timer.callbacks.onError) {
                    timer.callbacks.onError(error);
                }
            }
        }
    }

    /**
     * Update timer display locally between server syncs
     * @param {string} timerId - Timer identifier
     */
    updateTimerDisplay(timerId) {
        const timer = this.timers.get(timerId);
        if (!timer || timer.serverTimeRemaining === null) return;

        const now = performance.now();
        const elapsedSinceSync = (now - timer.lastUpdateTime) / 1000; // Convert to seconds
        const currentRemaining = Math.max(timer.serverTimeRemaining - elapsedSinceSync, 0);

        // Update display elements
        timer.displayElements.forEach(element => {
            if (element.type === 'countdown') {
                this.updateCountdownDisplay(element, currentRemaining);
            } else if (element.type === 'progress') {
                this.updateProgressDisplay(element, currentRemaining, element.duration);
            }
        });

        // Call update callback if provided
        if (timer.callbacks.onUpdate) {
            timer.callbacks.onUpdate(currentRemaining);
        }

        // Check for expiration
        if (currentRemaining <= 0) {
            this.handleTimerExpired(timerId, { remaining: 0, active: false });
        }
    }

    /**
     * Update countdown display element
     * @param {Object} element - Display element configuration
     * @param {number} seconds - Remaining seconds
     */
    updateCountdownDisplay(element, seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        let display = '';
        if (element.format === 'HH:MM:SS' || hours > 0) {
            display = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            display = `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }

        const displayElement = document.getElementById(element.elementId);
        if (displayElement) {
            displayElement.textContent = display;
            
            // Apply styling based on remaining time
            this.updateTimerStyling(displayElement, seconds);
        }
    }

    /**
     * Update progress bar display element
     * @param {Object} element - Display element configuration
     * @param {number} remaining - Remaining seconds
     * @param {number} duration - Total duration in seconds
     */
    updateProgressDisplay(element, remaining, duration) {
        const percent = duration > 0 ? Math.max((remaining / duration) * 100, 0) : 0;
        
        const progressElement = document.getElementById(element.elementId);
        if (progressElement) {
            progressElement.style.width = `${percent}%`;
            
            // Update progress bar color based on remaining time
            if (remaining < 60) {
                progressElement.classList.add('bg-red-500');
                progressElement.classList.remove('bg-primary', 'bg-orange-500');
            } else if (remaining < 300) {
                progressElement.classList.add('bg-orange-500');
                progressElement.classList.remove('bg-primary', 'bg-red-500');
            } else {
                progressElement.classList.add('bg-primary');
                progressElement.classList.remove('bg-orange-500', 'bg-red-500');
            }
        }
    }

    /**
     * Update timer styling based on remaining time
     * @param {HTMLElement} element - Timer display element
     * @param {number} seconds - Remaining seconds
     */
    updateTimerStyling(element, seconds) {
        // Remove all timing-related classes first
        element.classList.remove(
            'text-red-600', 'text-orange-500', 'text-primary',
            'animate-pulse', 'animate-pulse-fast'
        );

        if (seconds <= 0) {
            element.classList.add('text-red-600', 'animate-pulse-fast');
        } else if (seconds < 60) {
            element.classList.add('text-red-600', 'animate-pulse');
        } else if (seconds < 300) {
            element.classList.add('text-orange-500');
        } else {
            element.classList.add('text-primary');
        }
    }

    /**
     * Handle timer expiration
     * @param {string} timerId - Timer identifier
     * @param {Object} data - Server response data
     */
    handleTimerExpired(timerId, data) {
        const timer = this.timers.get(timerId);
        if (!timer) return;

        console.log(`Timer ${timerId} expired or became inactive`);

        // Call expiration callback if provided
        if (timer.callbacks.onExpired) {
            timer.callbacks.onExpired(data);
        } else {
            // Default behavior: reload page or redirect
            if (data.redirect_to) {
                window.location.href = data.redirect_to;
            } else {
                setTimeout(() => window.location.reload(), 1000);
            }
        }

        // Remove the timer
        this.removeTimer(timerId);
    }

    /**
     * Get current remaining time for a timer
     * @param {string} timerId - Timer identifier
     * @returns {number} Remaining seconds
     */
    getRemainingTime(timerId) {
        const timer = this.timers.get(timerId);
        if (!timer || timer.serverTimeRemaining === null) return 0;

        const now = performance.now();
        const elapsedSinceSync = (now - timer.lastUpdateTime) / 1000;
        return Math.max(timer.serverTimeRemaining - elapsedSinceSync, 0);
    }

    /**
     * Check if a timer is active
     * @param {string} timerId - Timer identifier
     * @returns {boolean} True if timer is active
     */
    isTimerActive(timerId) {
        return this.timers.has(timerId) && this.timers.get(timerId).isActive;
    }

    /**
     * Update server time offset for better synchronization
     * @param {number} serverTime - Server timestamp
     */
    updateServerTimeOffset(serverTime) {
        const clientTime = Date.now();
        this.serverTimeOffset = serverTime - clientTime;
    }
}

// Global timer manager instance
const timerManager = new TimerManager();

/**
 * Utility functions for common timer operations
 */
const TimerUtils = {
    /**
     * Format seconds into HH:MM:SS or MM:SS format
     * @param {number} seconds - Seconds to format
     * @param {boolean} alwaysShowHours - Always show hours even if 0
     * @returns {string} Formatted time string
     */
    formatTime: function(seconds, alwaysShowHours = false) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        if (alwaysShowHours || hours > 0) {
            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
    },

    /**
     * Add a simple countdown timer
     * @param {string} timerId - Unique timer ID
     * @param {string} endpointUrl - Server endpoint URL
     * @param {string} displayElementId - ID of element to display countdown
     * @param {Object} options - Additional options
     */
    addCountdownTimer: function(timerId, endpointUrl, displayElementId, options = {}) {
        timerManager.addTimer(timerId, {
            endpointUrl: endpointUrl,
            displayElements: [{
                type: 'countdown',
                elementId: displayElementId,
                format: options.format || 'MM:SS'
            }],
            callbacks: options.callbacks || {},
            syncInterval: options.syncInterval || 5000
        });
    },

    /**
     * Add a progress bar timer
     * @param {string} timerId - Unique timer ID
     * @param {string} endpointUrl - Server endpoint URL
     * @param {string} progressElementId - ID of progress bar element
     * @param {number} duration - Total duration in seconds
     * @param {Object} options - Additional options
     */
    addProgressTimer: function(timerId, endpointUrl, progressElementId, duration, options = {}) {
        timerManager.addTimer(timerId, {
            endpointUrl: endpointUrl,
            displayElements: [{
                type: 'progress',
                elementId: progressElementId,
                duration: duration
            }],
            callbacks: options.callbacks || {},
            syncInterval: options.syncInterval || 5000
        });
    },

    /**
     * Add a combined countdown and progress timer
     * @param {string} timerId - Unique timer ID
     * @param {string} endpointUrl - Server endpoint URL
     * @param {string} countdownElementId - ID of countdown element
     * @param {string} progressElementId - ID of progress bar element
     * @param {number} duration - Total duration in seconds
     * @param {Object} options - Additional options
     */
    addCombinedTimer: function(timerId, endpointUrl, countdownElementId, progressElementId, duration, options = {}) {
        timerManager.addTimer(timerId, {
            endpointUrl: endpointUrl,
            displayElements: [
                {
                    type: 'countdown',
                    elementId: countdownElementId,
                    format: options.format || 'MM:SS'
                },
                {
                    type: 'progress',
                    elementId: progressElementId,
                    duration: duration
                }
            ],
            callbacks: options.callbacks || {},
            syncInterval: options.syncInterval || 5000
        });
    },

    /**
     * Remove a timer
     * @param {string} timerId - Timer ID to remove
     */
    removeTimer: function(timerId) {
        timerManager.removeTimer(timerId);
    },

    /**
     * Get remaining time for a timer
     * @param {string} timerId - Timer ID
     * @returns {number} Remaining seconds
     */
    getRemainingTime: function(timerId) {
        return timerManager.getRemainingTime(timerId);
    },

    /**
     * Check if timer is active
     * @param {string} timerId - Timer ID
     * @returns {boolean} True if active
     */
    isActive: function(timerId) {
        return timerManager.isTimerActive(timerId);
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TimerManager, TimerUtils, timerManager };
}

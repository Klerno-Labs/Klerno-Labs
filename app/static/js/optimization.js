/**
 * Real-time optimization utilities for Klerno Labs frontend
 * Provides instant feedback, skeleton loading, and optimized WebSocket handling
 */

// WebSocket connection manager with exponential backoff
class OptimizedWebSocket {
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            maxReconnectAttempts: 10,
            baseDelay: 500,
            maxDelay: 30000,
            pingInterval: 30000,
            ...options
        };
        
        this.ws = null;
        this.reconnectAttempts = 0;
        this.isConnecting = false;
        this.listeners = new Map();
        this.pingTimer = null;
        this.connectionStartTime = null;
        
        this.connect();
    }
    
    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.CONNECTING)) {
            return;
        }
        
        this.isConnecting = true;
        this.connectionStartTime = performance.now();
        
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                const latency = performance.now() - this.connectionStartTime;
                console.log(`WebSocket connected in ${latency.toFixed(2)}ms`);
                
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                
                // Send initial ping with timestamp
                this.send({ ping: Date.now() });
                
                // Start ping interval
                this.startPinging();
                
                this.emit('connected', { latency });
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.emit('message', data);
                    
                    // Handle ping/pong for latency measurement
                    if (data.type === 'pong') {
                        const latency = Date.now() - (data.ping || 0);
                        this.emit('latency', { latency });
                    }
                } catch (error) {
                    console.warn('Failed to parse WebSocket message:', error);
                }
            };
            
            this.ws.onclose = () => {
                this.isConnecting = false;
                this.stopPinging();
                this.emit('disconnected');
                this.scheduleReconnect();
            };
            
            this.ws.onerror = () => {
                this.emit('error');
            };
            
        } catch (error) {
            this.isConnecting = false;
            this.scheduleReconnect();
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            this.emit('maxReconnectAttemptsReached');
            return;
        }
        
        const delay = Math.min(
            this.options.baseDelay * Math.pow(2, this.reconnectAttempts),
            this.options.maxDelay
        );
        
        this.reconnectAttempts++;
        
        setTimeout(() => {
            this.connect();
        }, delay);
    }
    
    startPinging() {
        this.stopPinging();
        this.pingTimer = setInterval(() => {
            this.send({ ping: Date.now() });
        }, this.options.pingInterval);
    }
    
    stopPinging() {
        if (this.pingTimer) {
            clearInterval(this.pingTimer);
            this.pingTimer = null;
        }
    }
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }
    
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
    }
    
    off(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    }
    
    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in WebSocket ${event} listener:`, error);
                }
            });
        }
    }
    
    close() {
        this.stopPinging();
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Skeleton loading state manager
class SkeletonLoader {
    static create(element, options = {}) {
        const config = {
            rows: 3,
            animate: true,
            className: 'skeleton-loader',
            ...options
        };
        
        if (!element) return;
        
        // Store original content
        element.dataset.originalContent = element.innerHTML;
        
        // Create skeleton HTML
        const skeletonRows = Array(config.rows).fill(0).map(() => 
            `<div class="skeleton-row ${config.animate ? 'animate' : ''}">
                <div class="skeleton-cell skeleton-short"></div>
                <div class="skeleton-cell skeleton-medium"></div>
                <div class="skeleton-cell skeleton-long"></div>
                <div class="skeleton-cell skeleton-short"></div>
                <div class="skeleton-cell skeleton-medium"></div>
            </div>`
        ).join('');
        
        element.innerHTML = `<div class="${config.className}">${skeletonRows}</div>`;
        element.classList.add('loading');
        
        return {
            remove: () => {
                if (element.dataset.originalContent !== undefined) {
                    element.innerHTML = element.dataset.originalContent;
                    delete element.dataset.originalContent;
                }
                element.classList.remove('loading');
            }
        };
    }
}

// Optimistic update manager for instant feedback
class OptimisticUpdates {
    constructor() {
        this.pendingUpdates = new Map();
        this.updateId = 0;
    }
    
    add(element, updateFn, rollbackFn) {
        const id = ++this.updateId;
        
        // Apply optimistic update
        updateFn();
        
        // Store rollback function
        this.pendingUpdates.set(id, {
            element,
            rollback: rollbackFn,
            timestamp: Date.now()
        });
        
        // Add loading indicator
        element.classList.add('optimistic-update');
        
        return id;
    }
    
    confirm(id) {
        const update = this.pendingUpdates.get(id);
        if (update) {
            update.element.classList.remove('optimistic-update');
            update.element.classList.add('confirmed-update');
            this.pendingUpdates.delete(id);
            
            // Remove confirmed class after animation
            setTimeout(() => {
                update.element.classList.remove('confirmed-update');
            }, 300);
        }
    }
    
    rollback(id) {
        const update = this.pendingUpdates.get(id);
        if (update) {
            update.rollback();
            update.element.classList.remove('optimistic-update');
            update.element.classList.add('rollback-update');
            this.pendingUpdates.delete(id);
            
            // Remove rollback class after animation
            setTimeout(() => {
                update.element.classList.remove('rollback-update');
            }, 300);
        }
    }
    
    cleanup(maxAge = 30000) {
        const now = Date.now();
        for (const [id, update] of this.pendingUpdates) {
            if (now - update.timestamp > maxAge) {
                this.rollback(id);
            }
        }
    }
}

// Performance monitoring for frontend
class FrontendPerformance {
    constructor() {
        this.metrics = {
            apiCalls: [],
            wsLatency: [],
            pageLoadTimes: []
        };
        this.maxMetrics = 100;
    }
    
    recordApiCall(endpoint, duration, success = true) {
        this.metrics.apiCalls.push({
            endpoint,
            duration,
            success,
            timestamp: Date.now()
        });
        
        if (this.metrics.apiCalls.length > this.maxMetrics) {
            this.metrics.apiCalls.shift();
        }
        
        // Log slow API calls
        if (duration > 1000) {
            console.warn(`Slow API call: ${endpoint} took ${duration}ms`);
        }
    }
    
    recordWebSocketLatency(latency) {
        this.metrics.wsLatency.push({
            latency,
            timestamp: Date.now()
        });
        
        if (this.metrics.wsLatency.length > this.maxMetrics) {
            this.metrics.wsLatency.shift();
        }
    }
    
    getAverageApiTime() {
        if (this.metrics.apiCalls.length === 0) return 0;
        
        const total = this.metrics.apiCalls.reduce((sum, call) => sum + call.duration, 0);
        return total / this.metrics.apiCalls.length;
    }
    
    getAverageWsLatency() {
        if (this.metrics.wsLatency.length === 0) return 0;
        
        const total = this.metrics.wsLatency.reduce((sum, metric) => sum + metric.latency, 0);
        return total / this.metrics.wsLatency.length;
    }
    
    getSlowApiCalls(threshold = 1000) {
        return this.metrics.apiCalls.filter(call => call.duration > threshold);
    }
    
    getSummary() {
        return {
            avgApiTime: Math.round(this.getAverageApiTime()),
            avgWsLatency: Math.round(this.getAverageWsLatency()),
            slowApiCalls: this.getSlowApiCalls().length,
            totalApiCalls: this.metrics.apiCalls.length,
            wsMetrics: this.metrics.wsLatency.length
        };
    }
}

// Enhanced fetch with performance monitoring and optimistic updates
async function optimizedFetch(url, options = {}) {
    const startTime = performance.now();
    
    try {
        const response = await fetch(url, options);
        const duration = performance.now() - startTime;
        
        // Record performance metric
        if (window.frontendPerf) {
            window.frontendPerf.recordApiCall(url, duration, response.ok);
        }
        
        return response;
    } catch (error) {
        const duration = performance.now() - startTime;
        
        // Record failed API call
        if (window.frontendPerf) {
            window.frontendPerf.recordApiCall(url, duration, false);
        }
        
        throw error;
    }
}

// Smart polling with backoff based on activity
class SmartPoller {
    constructor(fetchFn, options = {}) {
        this.fetchFn = fetchFn;
        this.options = {
            baseInterval: 5000,
            activeInterval: 2000,
            inactiveInterval: 15000,
            maxInterval: 60000,
            inactivityThreshold: 60000,
            ...options
        };
        
        this.currentInterval = this.options.baseInterval;
        this.timer = null;
        this.lastActivity = Date.now();
        this.isActive = true;
        
        this.setupActivityListeners();
        this.start();
    }
    
    setupActivityListeners() {
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
        
        events.forEach(event => {
            document.addEventListener(event, () => {
                this.lastActivity = Date.now();
                if (!this.isActive) {
                    this.isActive = true;
                    this.adjustInterval();
                }
            }, { passive: true });
        });
        
        // Check for inactivity
        setInterval(() => {
            const timeSinceActivity = Date.now() - this.lastActivity;
            const wasActive = this.isActive;
            this.isActive = timeSinceActivity < this.options.inactivityThreshold;
            
            if (wasActive !== this.isActive) {
                this.adjustInterval();
            }
        }, 10000);
    }
    
    adjustInterval() {
        const newInterval = this.isActive ? 
            this.options.activeInterval : 
            this.options.inactiveInterval;
            
        if (newInterval !== this.currentInterval) {
            this.currentInterval = newInterval;
            this.restart();
        }
    }
    
    start() {
        this.stop();
        this.timer = setInterval(() => {
            if (!document.hidden) {
                this.fetchFn();
            }
        }, this.currentInterval);
    }
    
    stop() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }
    
    restart() {
        this.start();
    }
}

// Initialize global instances
window.frontendPerf = new FrontendPerformance();
window.optimisticUpdates = new OptimisticUpdates();

// Clean up optimistic updates periodically
setInterval(() => {
    window.optimisticUpdates.cleanup();
}, 30000);

// Export for use in other scripts
window.KlernoOptimization = {
    OptimizedWebSocket,
    SkeletonLoader,
    OptimisticUpdates,
    FrontendPerformance,
    optimizedFetch,
    SmartPoller
};
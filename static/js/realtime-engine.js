
// ===================================================================
// KLERNO LABS REAL-TIME CLIENT ENGINE
// Elite WebSocket Client for Top 0.01% Applications
// ===================================================================

class RealTimeEngine {
    constructor(options = {}) {
        this.wsUrl = options.wsUrl || this.getWebSocketUrl();
        this.userId = options.userId || this.generateUserId();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.heartbeatInterval = 30000;
        this.heartbeatTimer = null;
        this.websocket = null;
        this.isConnected = false;
        this.eventHandlers = new Map();
        this.messageQueue = [];
        this.currentRoom = null;
        this.userPresence = new Map();
        
        this.init();
    }

    init() {
        this.connect();
        this.setupEventListeners();
        this.startHeartbeat();
        
        // Auto-reconnect on visibility change
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !this.isConnected) {
                this.connect();
            }
        });
    }

    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/${this.userId}`;
    }

    generateUserId() {
        return 'user_' + Math.random().toString(36).substr(2, 9);
    }

    connect() {
        try {
            this.websocket = new WebSocket(this.wsUrl);
            
            this.websocket.onopen = (event) => {
                console.log('🔗 Connected to real-time server');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.flushMessageQueue();
                this.emit('connected', { userId: this.userId });
                this.updateConnectionStatus('connected');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = (event) => {
                console.log('🔌 Disconnected from real-time server');
                this.isConnected = false;
                this.emit('disconnected', { code: event.code, reason: event.reason });
                this.updateConnectionStatus('disconnected');
                this.attemptReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', error);
                this.updateConnectionStatus('error');
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.attemptReconnect();
        }
    }

    disconnect() {
        if (this.websocket) {
            this.websocket.close();
        }
        this.stopHeartbeat();
    }

    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.updateConnectionStatus('failed');
            return;
        }

        this.reconnectAttempts++;
        this.updateConnectionStatus('reconnecting');
        
        console.log(`🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay * this.reconnectAttempts);
    }

    send(message) {
        if (this.isConnected && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        } else {
            // Queue message for when connection is restored
            this.messageQueue.push(message);
        }
    }

    flushMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }

    handleMessage(message) {
        const { type } = message;
        
        switch (type) {
            case 'pong':
                // Heartbeat response
                break;
                
            case 'user_presence':
                this.handleUserPresence(message);
                break;
                
            case 'chat_message':
                this.handleChatMessage(message);
                break;
                
            case 'data_update':
                this.handleDataUpdate(message);
                break;
                
            case 'user_activity':
                this.handleUserActivity(message);
                break;
                
            case 'room_member_joined':
            case 'room_member_left':
                this.handleRoomEvent(message);
                break;
                
            default:
                this.emit(type, message);
        }
    }

    handleUserPresence(message) {
        const { user_id, action, status } = message;
        
        if (action === 'joined') {
            this.userPresence.set(user_id, { status: 'online', lastSeen: new Date() });
            this.showUserNotification(`${user_id} joined`, 'success');
        } else if (action === 'left') {
            this.userPresence.set(user_id, { status: 'offline', lastSeen: new Date() });
            this.showUserNotification(`${user_id} left`, 'info');
        }
        
        this.updateUserPresenceUI();
        this.emit('user_presence', message);
    }

    handleChatMessage(message) {
        this.displayChatMessage(message);
        this.emit('chat_message', message);
        
        // Show notification if not in focus
        if (document.hidden) {
            this.showNotification(`New message from ${message.user_id}`, message.content);
        }
    }

    handleDataUpdate(message) {
        this.emit('data_update', message);
        this.updateDataVisualization(message.data);
    }

    handleUserActivity(message) {
        this.emit('user_activity', message);
        this.showUserActivity(message);
    }

    handleRoomEvent(message) {
        this.emit('room_event', message);
        this.updateRoomMembersUI(message);
    }

    // Real-time features
    joinRoom(roomId) {
        this.currentRoom = roomId;
        this.send({
            type: 'join_room',
            room_id: roomId
        });
    }

    leaveRoom(roomId) {
        this.send({
            type: 'leave_room',
            room_id: roomId
        });
        if (this.currentRoom === roomId) {
            this.currentRoom = null;
        }
    }

    sendChatMessage(content, roomId = null) {
        this.send({
            type: 'chat_message',
            content: content,
            room_id: roomId || this.currentRoom
        });
    }

    sendDataUpdate(data) {
        this.send({
            type: 'data_update',
            data: data
        });
    }

    sendUserActivity(activity) {
        this.send({
            type: 'user_activity',
            data: activity
        });
    }

    // UI Updates
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `connection-status ${status}`;
        }
        
        // Update connection indicator
        const indicator = document.getElementById('connection-indicator');
        if (indicator) {
            indicator.className = `connection-indicator ${status}`;
        }
    }

    updateUserPresenceUI() {
        const presenceContainer = document.getElementById('user-presence');
        if (!presenceContainer) return;
        
        presenceContainer.innerHTML = '';
        
        this.userPresence.forEach((presence, userId) => {
            const userElement = document.createElement('div');
            userElement.className = `user-presence ${presence.status}`;
            userElement.innerHTML = `
                <div class="user-avatar">
                    <div class="status-indicator ${presence.status}"></div>
                </div>
                <span class="user-name">${userId}</span>
            `;
            presenceContainer.appendChild(userElement);
        });
    }

    displayChatMessage(message) {
        const chatContainer = document.getElementById('chat-messages');
        if (!chatContainer) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = 'chat-message';
        messageElement.innerHTML = `
            <div class="message-header">
                <span class="user-name">${message.user_id}</span>
                <span class="timestamp">${new Date(message.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="message-content">${this.escapeHtml(message.content)}</div>
        `;
        
        chatContainer.appendChild(messageElement);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    updateDataVisualization(data) {
        // Update charts and dashboards with real-time data
        if (window.dataViz && window.dataViz.charts) {
            // Trigger chart updates
            this.emit('visualization_update', data);
        }
    }

    showUserActivity(activity) {
        const activityFeed = document.getElementById('activity-feed');
        if (!activityFeed) return;
        
        const activityElement = document.createElement('div');
        activityElement.className = 'activity-item';
        activityElement.innerHTML = `
            <div class="activity-icon">👤</div>
            <div class="activity-content">
                <span class="user-name">${activity.user_id}</span>
                <span class="activity-text">${activity.activity.type || 'is active'}</span>
                <span class="activity-time">${new Date(activity.timestamp).toLocaleTimeString()}</span>
            </div>
        `;
        
        activityFeed.insertBefore(activityElement, activityFeed.firstChild);
        
        // Keep only recent activities
        while (activityFeed.children.length > 50) {
            activityFeed.removeChild(activityFeed.lastChild);
        }
    }

    // Notifications
    showNotification(title, body, options = {}) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, { body, icon: '/static/icons/logo.png', ...options });
        } else if ('Notification' in window && Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    new Notification(title, { body, icon: '/static/icons/logo.png', ...options });
                }
            });
        }
    }

    showUserNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `user-notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 3000);
    }

    // Event system
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }

    // Utility methods
    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'ping' });
            }
        }, this.heartbeatInterval);
    }

    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    setupEventListeners() {
        // Setup page visibility handling
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.sendUserActivity({ type: 'page_visible' });
            }
        });
        
        // Track user interactions
        ['click', 'scroll', 'keypress'].forEach(eventType => {
            document.addEventListener(eventType, this.throttle(() => {
                this.sendUserActivity({ type: `user_${eventType}` });
            }, 5000));
        });
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }
}

// Initialize real-time engine
document.addEventListener('DOMContentLoaded', () => {
    window.realTime = new RealTimeEngine();
    
    // Setup chat interface if present
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const message = chatInput.value.trim();
                if (message) {
                    window.realTime.sendChatMessage(message);
                    chatInput.value = '';
                }
            }
        });
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealTimeEngine;
}

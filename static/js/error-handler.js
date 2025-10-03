
// ===================================================================
// KLERNO LABS ADVANCED ERROR HANDLER
// Bulletproof Error Handling & Recovery
// ===================================================================

class AdvancedErrorHandler {
    constructor() {
        this.errorQueue = [];
        this.retryAttempts = new Map();
        this.maxRetries = 3;
        this.retryDelay = 1000;
        this.init();
    }

    init() {
        this.setupGlobalErrorHandling();
        this.setupPromiseRejectionHandling();
        this.setupNetworkErrorHandling();
        this.setupResourceErrorHandling();
        this.createErrorBoundary();
    }

    // Global error handling
    setupGlobalErrorHandling() {
        window.addEventListener('error', (event) => {
            this.handleError({
                type: 'javascript',
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                error: event.error,
                timestamp: new Date().toISOString()
            });
        });
    }

    // Promise rejection handling
    setupPromiseRejectionHandling() {
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError({
                type: 'promise',
                message: event.reason?.message || 'Unhandled promise rejection',
                error: event.reason,
                timestamp: new Date().toISOString()
            });
            
            // Prevent console spam
            event.preventDefault();
        });
    }

    // Network error handling
    setupNetworkErrorHandling() {
        // Intercept fetch requests
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return response;
            } catch (error) {
                return this.handleNetworkError(error, args);
            }
        };

        // XMLHttpRequest error handling
        const originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(...args) {
            this.addEventListener('error', (event) => {
                window.errorHandler.handleError({
                    type: 'network',
                    message: 'XMLHttpRequest failed',
                    url: args[1],
                    method: args[0],
                    timestamp: new Date().toISOString()
                });
            });
            
            return originalOpen.apply(this, args);
        };
    }

    // Resource error handling
    setupResourceErrorHandling() {
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                this.handleResourceError(event.target);
            }
        }, true);
    }

    // Handle different types of errors
    handleError(errorInfo) {
        console.error('Error captured:', errorInfo);
        
        // Add to error queue
        this.errorQueue.push(errorInfo);
        
        // Show user-friendly notification
        this.showErrorNotification(errorInfo);
        
        // Report to error tracking service
        this.reportError(errorInfo);
        
        // Attempt recovery if possible
        this.attemptRecovery(errorInfo);
    }

    handleNetworkError(error, fetchArgs) {
        const url = fetchArgs[0];
        const retryKey = `fetch_${url}`;
        const retryCount = this.retryAttempts.get(retryKey) || 0;

        if (retryCount < this.maxRetries) {
            this.retryAttempts.set(retryKey, retryCount + 1);
            
            return new Promise((resolve) => {
                setTimeout(async () => {
                    try {
                        const response = await fetch(...fetchArgs);
                        this.retryAttempts.delete(retryKey);
                        resolve(response);
                    } catch (retryError) {
                        resolve(this.handleNetworkError(retryError, fetchArgs));
                    }
                }, this.retryDelay * Math.pow(2, retryCount));
            });
        }

        // All retries failed, show error state
        this.showNetworkErrorState(error, url);
        return Promise.reject(error);
    }

    handleResourceError(element) {
        const src = element.src || element.href;
        const tagName = element.tagName.toLowerCase();
        
        switch (tagName) {
            case 'img':
                this.handleImageError(element);
                break;
            case 'script':
                this.handleScriptError(element);
                break;
            case 'link':
                this.handleStylesheetError(element);
                break;
            default:
                console.warn(`Failed to load resource: ${src}`);
        }
    }

    handleImageError(img) {
        // Replace with placeholder
        img.src = '/static/images/placeholder.svg';
        img.alt = 'Image failed to load';
        img.classList.add('error-placeholder');
    }

    handleScriptError(script) {
        // Create fallback script or show warning
        const fallback = document.createElement('div');
        fallback.className = 'script-error-notice';
        fallback.innerHTML = `
            <p>⚠️ Some features may not work as expected due to a loading error.</p>
            <button onclick="location.reload()">Reload Page</button>
        `;
        script.parentNode?.insertBefore(fallback, script);
    }

    handleStylesheetError(link) {
        // Load fallback CSS or create minimal styles
        const fallback = document.createElement('style');
        fallback.textContent = `
            body { font-family: Arial, sans-serif; }
            .error-notice { 
                background: #fee; 
                border: 1px solid #fcc; 
                padding: 10px; 
                margin: 10px 0; 
            }
        `;
        document.head.appendChild(fallback);
    }

    // Error recovery mechanisms
    attemptRecovery(errorInfo) {
        switch (errorInfo.type) {
            case 'network':
                this.offerNetworkRecovery();
                break;
            case 'javascript':
                this.offerJavaScriptRecovery(errorInfo);
                break;
            case 'promise':
                this.offerPromiseRecovery();
                break;
        }
    }

    offerNetworkRecovery() {
        if (!navigator.onLine) {
            this.showOfflineNotice();
        } else {
            this.showRetryOption();
        }
    }

    offerJavaScriptRecovery(errorInfo) {
        // Attempt to reload specific components
        if (errorInfo.filename?.includes('components')) {
            this.reloadComponent(errorInfo.filename);
        }
    }

    offerPromiseRecovery() {
        // Show generic recovery options
        this.showRecoveryOptions();
    }

    // User interface methods
    showErrorNotification(errorInfo) {
        const notification = document.createElement('div');
        notification.className = 'error-notification';
        notification.innerHTML = `
            <div class="error-notification-content">
                <span class="error-icon">⚠️</span>
                <div class="error-text">
                    <strong>Something went wrong</strong>
                    <p>${this.getUserFriendlyMessage(errorInfo)}</p>
                </div>
                <button class="error-dismiss" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        this.getNotificationContainer().appendChild(notification);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            notification.remove();
        }, 10000);
    }

    showNetworkErrorState(error, url) {
        const errorBanner = document.createElement('div');
        errorBanner.className = 'network-error-banner';
        errorBanner.innerHTML = `
            <div class="error-banner-content">
                <span class="error-icon">📡</span>
                <div class="error-text">
                    <strong>Connection Problem</strong>
                    <p>We're having trouble connecting to our servers.</p>
                </div>
                <div class="error-actions">
                    <button onclick="location.reload()" class="retry-btn">Retry</button>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" class="dismiss-btn">Dismiss</button>
                </div>
            </div>
        `;
        
        document.body.insertBefore(errorBanner, document.body.firstChild);
    }

    showOfflineNotice() {
        const offlineBanner = document.createElement('div');
        offlineBanner.className = 'offline-banner';
        offlineBanner.innerHTML = `
            <div class="banner-content">
                <span class="offline-icon">📴</span>
                <span>You appear to be offline. Some features may not work.</span>
                <button onclick="location.reload()" class="reconnect-btn">Try to Reconnect</button>
            </div>
        `;
        
        document.body.insertBefore(offlineBanner, document.body.firstChild);
        
        // Remove when back online
        window.addEventListener('online', () => {
            offlineBanner.remove();
        }, { once: true });
    }

    showRetryOption() {
        const retryBanner = document.createElement('div');
        retryBanner.className = 'retry-banner';
        retryBanner.innerHTML = `
            <div class="banner-content">
                <span>Something went wrong. Would you like to try again?</span>
                <button onclick="location.reload()" class="retry-btn">Retry</button>
                <button onclick="this.parentElement.parentElement.remove()" class="dismiss-btn">Dismiss</button>
            </div>
        `;
        
        document.body.insertBefore(retryBanner, document.body.firstChild);
    }

    showRecoveryOptions() {
        const modal = document.createElement('div');
        modal.className = 'error-recovery-modal';
        modal.innerHTML = `
            <div class="modal-backdrop" onclick="this.parentElement.remove()"></div>
            <div class="modal-content">
                <h3>Oops! Something went wrong</h3>
                <p>We've encountered an unexpected issue. Here are some things you can try:</p>
                <div class="recovery-options">
                    <button onclick="location.reload()" class="recovery-option">
                        🔄 Refresh the page
                    </button>
                    <button onclick="window.history.back()" class="recovery-option">
                        ← Go back
                    </button>
                    <button onclick="localStorage.clear(); location.reload()" class="recovery-option">
                        🗑️ Clear cache and reload
                    </button>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" class="recovery-option secondary">
                        Continue anyway
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    // Error boundary simulation for JavaScript
    createErrorBoundary() {
        const originalConsoleError = console.error;
        console.error = (...args) => {
            // Check if this is a React-like component error
            if (args[0]?.includes?.('React') || args[0]?.includes?.('component')) {
                this.handleComponentError(args);
            }
            return originalConsoleError.apply(console, args);
        };
    }

    handleComponentError(errorArgs) {
        // Find and replace failed components with error boundaries
        const errorComponents = document.querySelectorAll('[data-component-error]');
        errorComponents.forEach(component => {
            component.innerHTML = `
                <div class="component-error">
                    <h4>Component Error</h4>
                    <p>This component failed to load properly.</p>
                    <button onclick="location.reload()">Reload Page</button>
                </div>
            `;
        });
    }

    // Utility methods
    getUserFriendlyMessage(errorInfo) {
        const friendlyMessages = {
            'network': 'We're having trouble connecting to our servers. Please check your internet connection.',
            'javascript': 'A technical issue occurred. The page may not work as expected.',
            'promise': 'An operation didn't complete successfully. You may want to try again.',
            'resource': 'Some content failed to load. The page should still be functional.'
        };
        
        return friendlyMessages[errorInfo.type] || 'An unexpected error occurred.';
    }

    getNotificationContainer() {
        let container = document.getElementById('error-notifications');
        if (!container) {
            container = document.createElement('div');
            container.id = 'error-notifications';
            container.className = 'error-notifications-container';
            document.body.appendChild(container);
        }
        return container;
    }

    reportError(errorInfo) {
        // In a real application, send to your error tracking service
        fetch('/api/errors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(errorInfo)
        }).catch(() => {
            // Silently fail if error reporting fails
            console.warn('Failed to report error to server');
        });
    }

    // Public API
    clearErrors() {
        this.errorQueue = [];
        this.retryAttempts.clear();
        document.querySelectorAll('.error-notification, .network-error-banner, .offline-banner').forEach(el => el.remove());
    }

    getErrorCount() {
        return this.errorQueue.length;
    }

    getErrors() {
        return [...this.errorQueue];
    }
}

// Initialize global error handler
window.addEventListener('DOMContentLoaded', () => {
    window.errorHandler = new AdvancedErrorHandler();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdvancedErrorHandler;
}

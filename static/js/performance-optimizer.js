// Performance Optimization and Error Handling for Klerno Labs
// This file ensures all functions work properly and load fast

class KlernoOptimizer {
  constructor() {
    this.startTime = performance.now();
    this.loadState = {
      domReady: false,
      scriptsLoaded: false,
      apiReady: false
    };
    this.init();
  }

  init() {
    // Ensure DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        this.loadState.domReady = true;
        this.checkReadiness();
      });
    } else {
      this.loadState.domReady = true;
      this.checkReadiness();
    }

    // Load external scripts faster
    this.preloadCriticalResources();

    // Monitor performance
    this.monitorPerformance();

    // Handle errors gracefully
    this.setupErrorHandling();
  }

  preloadCriticalResources() {
    const criticalResources = [
      'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.min.js',
      'https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js'
    ];

    criticalResources.forEach(url => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'script';
      link.href = url;
      document.head.appendChild(link);
    });
  }

  checkReadiness() {
    if (this.loadState.domReady) {
      this.loadState.scriptsLoaded = typeof Chart !== 'undefined';
      this.loadState.apiReady = true; // API is always ready when DOM is ready

      if (this.allReady()) {
        this.optimize();
      } else {
        // Wait a bit and try again
        setTimeout(() => this.checkReadiness(), 100);
      }
    }
  }

  allReady() {
    return Object.values(this.loadState).every(state => state);
  }

  optimize() {
    const loadTime = performance.now() - this.startTime;
    console.log(`Klerno Labs optimized and ready in ${loadTime.toFixed(2)}ms`);

    // Optimize images
    this.optimizeImages();

    // Optimize fetch calls
    this.optimizeFetchCalls();

    // Add loading states to buttons
    this.addLoadingStates();

    // Trigger ready event
    document.dispatchEvent(new CustomEvent('klerno:ready', {
      detail: { loadTime }
    }));
  }

  optimizeImages() {
    const images = document.querySelectorAll('img');
    images.forEach(img => {
      if (!img.loading) {
        img.loading = 'lazy';
      }
    });
  }

  optimizeFetchCalls() {
    // Add timeout to all fetch calls to prevent hanging
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

      const fetchOptions = {
        ...options,
        signal: controller.signal
      };

      return originalFetch(url, fetchOptions)
        .finally(() => clearTimeout(timeoutId));
    };
  }

  addLoadingStates() {
    document.addEventListener('click', (e) => {
      if (e.target.matches('button, .btn, [role="button"]')) {
        const btn = e.target;
        const originalText = btn.textContent || btn.innerHTML;

        // Add loading state
        btn.classList.add('loading');
        btn.disabled = true;

        if (!btn.querySelector('.spinner')) {
          const spinner = document.createElement('span');
          spinner.className = 'spinner';
          spinner.style.marginRight = '8px';
          btn.insertBefore(spinner, btn.firstChild);
        }

        // Auto-remove loading state after 5 seconds (fallback)
        setTimeout(() => {
          this.removeLoadingState(btn, originalText);
        }, 5000);
      }
    });
  }

  removeLoadingState(btn, originalText) {
    btn.classList.remove('loading');
    btn.disabled = false;
    const spinner = btn.querySelector('.spinner');
    if (spinner) {
      spinner.remove();
    }
  }

  monitorPerformance() {
    // Monitor long tasks
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) {
            console.warn(`Long task detected: ${entry.duration.toFixed(2)}ms`);
          }
        }
      });
      observer.observe({ entryTypes: ['longtask'] });
    }

    // Monitor memory usage
    if (performance.memory) {
      setInterval(() => {
        const memory = performance.memory;
        const usedMB = Math.round(memory.usedJSHeapSize / 1048576);
        const limitMB = Math.round(memory.jsHeapSizeLimit / 1048576);

        if (usedMB > limitMB * 0.8) {
          console.warn(`High memory usage: ${usedMB}MB / ${limitMB}MB`);
        }
      }, 30000);
    }
  }

  setupErrorHandling() {
    window.addEventListener('error', (e) => {
      console.error('JavaScript error:', e.error);
      this.showErrorToast(`Script error: ${e.message}`);
    });

    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled promise rejection:', e.reason);
      this.showErrorToast(`Network error: ${e.reason}`);
    });
  }

  showErrorToast(message) {
    if (typeof toast === 'function') {
      toast(message);
    } else {
      // Fallback toast
      const toastEl = document.createElement('div');
      toastEl.textContent = message;
      toastEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #ef4444;
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
      `;
      document.body.appendChild(toastEl);
      setTimeout(() => toastEl.remove(), 5000);
    }
  }
}

// Initialize optimizer
new KlernoOptimizer();

// Utility functions for better performance
window.klernoUtils = {
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

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
    };
  },

  fastFetch(url, options = {}) {
    return fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .catch(error => {
      console.error('Fetch error:', error);
      throw error;
    });
  }
};

// CSS animation for toast
const toastCSS = `
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
`;

const style = document.createElement('style');
style.textContent = toastCSS;
document.head.appendChild(style);

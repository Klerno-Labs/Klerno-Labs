// Klerno Labs - Elite Application JavaScript with Performance Optimization

// Performance monitoring
class PerformanceMonitor {
  constructor() {
    this.metrics = {};
    this.startTime = performance.now();
    this.init();
  }

  init() {
    this.trackPageLoad();
    this.trackResourceLoading();
    this.trackUserInteractions();
  }

  trackPageLoad() {
    window.addEventListener('load', () => {
      const loadTime = performance.now() - this.startTime;
      this.metrics.pageLoadTime = loadTime;
      console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);
      
      if (loadTime > 3000) {
        console.warn('Slow page load detected');
      }
    });
  }

  trackResourceLoading() {
    window.addEventListener('error', (e) => {
      if (e.target !== window) {
        console.error('Resource loading failed:', e.target.src || e.target.href);
      }
    }, true);
  }

  trackUserInteractions() {
    document.addEventListener('click', (e) => {
      if (e.target.matches('button, a, [role="button"]')) {
        const startTime = performance.now();
        requestAnimationFrame(() => {
          const responseTime = performance.now() - startTime;
          if (responseTime > 100) {
            console.warn(`Slow interaction response: ${responseTime.toFixed(2)}ms`);
          }
        });
      }
    });
  }
}

// Advanced loading manager
class LoadingManager {
  constructor() {
    this.activeLoaders = new Set();
    this.createLoadingOverlay();
  }

  createLoadingOverlay() {
    if (document.querySelector('.global-loading-overlay')) return;
    
    const overlay = document.createElement('div');
    overlay.className = 'global-loading-overlay';
    overlay.innerHTML = `
      <div class="loading-content">
        <div class="loading-spinner-advanced"></div>
        <div class="loading-text">Loading...</div>
        <div class="loading-progress">
          <div class="loading-progress-bar"></div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  show(message = 'Loading...', showProgress = false) {
    const overlay = document.querySelector('.global-loading-overlay');
    const text = overlay.querySelector('.loading-text');
    const progress = overlay.querySelector('.loading-progress');
    
    text.textContent = message;
    progress.style.display = showProgress ? 'block' : 'none';
    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    this.activeLoaders.add(Symbol());
  }

  hide() {
    if (this.activeLoaders.size > 1) {
      this.activeLoaders.delete(this.activeLoaders.values().next().value);
      return;
    }
    
    const overlay = document.querySelector('.global-loading-overlay');
    overlay.style.display = 'none';
    document.body.style.overflow = '';
    this.activeLoaders.clear();
  }

  updateProgress(percentage) {
    const progressBar = document.querySelector('.loading-progress-bar');
    if (progressBar) {
      progressBar.style.width = `${percentage}%`;
    }
  }
}

// Main application initialization
document.addEventListener('DOMContentLoaded', function() {
  console.log('Klerno Labs Elite Application initializing...');
  
  // Initialize performance monitoring
  window.performanceMonitor = new PerformanceMonitor();
  window.loadingManager = new LoadingManager();
  
  // Add skip to content link for accessibility
  const skipLink = document.createElement('a');
  skipLink.href = '#main';
  skipLink.className = 'skip-to-content';
  skipLink.textContent = 'Skip to content';
  skipLink.style.cssText = `
    position: absolute;
    left: -10000px;
    top: auto;
    width: 1px;
    height: 1px;
    overflow: hidden;
    background: var(--color-primary);
    color: white;
    padding: 8px 16px;
    text-decoration: none;
    border-radius: 4px;
    z-index: 10000;
  `;
  skipLink.addEventListener('focus', function() {
    this.style.left = '10px';
    this.style.top = '10px';
    this.style.width = 'auto';
    this.style.height = 'auto';
  });
  skipLink.addEventListener('blur', function() {
    this.style.left = '-10000px';
    this.style.top = 'auto';
    this.style.width = '1px';
    this.style.height = '1px';
  });
  document.body.insertBefore(skipLink, document.body.firstChild);
  
  // Initialize tooltips and popovers if Bootstrap is available
  if (typeof bootstrap !== 'undefined') {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
      return new bootstrap.Popover(popoverTriggerEl);
    });
  }
  
  // Enhanced form validation
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
      const submitBtn = this.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        submitBtn.disabled = true;
        submitBtn.classList.add('loading');
        
        const originalText = submitBtn.textContent;
        submitBtn.innerHTML = `
          <span class="loading-spinner" style="display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top: 2px solid white; border-radius: 50%; animation: spin 1s linear infinite; margin-right: 8px;"></span>
          ${originalText.includes('Sign') ? 'Signing In...' : 'Processing...'}
        `;
        
        setTimeout(() => {
          submitBtn.disabled = false;
          submitBtn.classList.remove('loading');
          submitBtn.textContent = originalText;
        }, 10000);
      }
    });
    
    form.querySelectorAll('input, textarea, select').forEach(field => {
      field.addEventListener('blur', function() {
        this.classList.toggle('was-validated', this.checkValidity());
      });
    });
  });
  
  // Add smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });
  
  // Add click ripple effects to buttons
  document.querySelectorAll('button, .btn').forEach(button => {
    button.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      ripple.className = 'ripple';
      ripple.style.cssText = `
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        pointer-events: none;
        animation: ripple-animation 0.6s linear;
        z-index: 1;
      `;
      
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;
      
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      
      this.style.position = 'relative';
      this.style.overflow = 'hidden';
      this.appendChild(ripple);
      
      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
  });
  
  // Add intersection observer for animations
  if ('IntersectionObserver' in window) {
    const animationObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-in');
        }
      });
    }, { threshold: 0.1 });
    
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
      animationObserver.observe(el);
    });
  }
  
  // Keyboard shortcuts
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal.show').forEach(modal => {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
          bsModal.hide();
        }
      });
    }
  });
  
  console.log('Elite Application initialized successfully');
});

// Global styles
const globalStyles = document.createElement('style');
globalStyles.textContent = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  
  @keyframes ripple-animation {
    to {
      transform: scale(2);
      opacity: 0;
    }
  }
  
  .global-loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    backdrop-filter: blur(8px);
  }
  
  .loading-content {
    text-align: center;
    color: white;
  }
  
  .loading-spinner-advanced {
    width: 60px;
    height: 60px;
    border: 4px solid rgba(255, 255, 255, 0.2);
    border-top: 4px solid var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 20px;
  }
  
  .loading-text {
    font-size: 18px;
    font-weight: 500;
    margin-bottom: 15px;
  }
  
  .loading-progress {
    width: 200px;
    height: 4px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
    margin: 0 auto;
    overflow: hidden;
    display: none;
  }
  
  .loading-progress-bar {
    height: 100%;
    background: var(--color-primary);
    width: 0%;
    transition: width 0.3s ease;
  }
  
  .skip-to-content:focus {
    transform: translateY(0);
    opacity: 1;
  }
  
  body.keyboard-navigation *:focus {
    outline: 2px solid var(--color-primary) !important;
    outline-offset: 2px !important;
  }
  
  .was-validated .form-control:valid {
    border-color: var(--color-success);
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 8 8'%3e%3cpath fill='%2310B981' d='m2.3 6.73.84-.84L1.1 3.85l-.84.84L2.3 6.73z'/%3e%3cpath fill='%2310B981' d='m5.7 1.27-.84.84 2.04 2.04.84-.84L5.7 1.27z'/%3e%3c/svg%3e");
  }
  
  .was-validated .form-control:invalid {
    border-color: var(--color-danger);
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 8 8'%3e%3cpath fill='%23EF4444' d='M7.4 6.3l-1.1 1.1L4 5.1 1.7 7.4.6 6.3 2.9 4 .6 1.7 1.7.6 4 2.9 6.3.6l1.1 1.1L5.1 4z'/%3e%3c/svg%3e");
  }
  
  .animate-in {
    animation: slideInUp 0.6s ease forwards;
  }
  
  @keyframes slideInUp {
    from {
      opacity: 0;
      transform: translateY(30px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;
document.head.appendChild(globalStyles);

// Global error handling
window.addEventListener('error', (e) => {
  console.error('Global error caught:', e.error);
  if (window.loadingManager) {
    window.loadingManager.hide();
  }
});

window.addEventListener('unhandledrejection', (e) => {
  console.error('Unhandled promise rejection:', e.reason);
  e.preventDefault();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
  if (window.performanceMonitor) {
    console.log('Performance metrics:', window.performanceMonitor.metrics);
  }
});
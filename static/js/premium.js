
// ===================================================================
// KLERNO LABS PREMIUM UI JAVASCRIPT
// Top 0.1% Interactive Features
// ===================================================================

class KlernoPremiumUI {
    constructor() {
        this.init();
    }

    init() {
        this.initAnimations();
        this.initInteractions();
        this.initTooltips();
        this.initProgressBars();
        this.initCounters();
        this.initSmoothScrolling();
        this.initParallax();
        this.initThemeToggle();
        this.initNotifications();
        this.initLazyLoading();
    }

    // ===================================================================
    // PREMIUM ANIMATIONS
    // ===================================================================

    initAnimations() {
        // Intersection Observer for scroll animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('klerno-animate-fade-in');
                }
            });
        }, observerOptions);

        // Observe all animatable elements
        document.querySelectorAll('.klerno-card, .klerno-stat-card').forEach(el => {
            observer.observe(el);
        });
    }

    // ===================================================================
    // INTERACTIVE FEATURES
    // ===================================================================

    initInteractions() {
        // Premium hover effects
        document.querySelectorAll('.klerno-card').forEach(card => {
            card.addEventListener('mouseenter', (e) => {
                e.target.style.transform = 'translateY(-8px) scale(1.02)';
                e.target.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            });

            card.addEventListener('mouseleave', (e) => {
                e.target.style.transform = 'translateY(0) scale(1)';
            });
        });

        // Button ripple effects
        document.querySelectorAll('.klerno-btn').forEach(btn => {
            btn.addEventListener('click', this.createRipple);
        });
    }

    createRipple(e) {
        const button = e.currentTarget;
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;

        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: rgba(255, 255, 255, 0.6);
            border-radius: 50%;
            transform: scale(0);
            animation: ripple 0.6s linear;
            pointer-events: none;
        `;

        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
    }

    // ===================================================================
    // PREMIUM TOOLTIPS
    // ===================================================================

    initTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(el => {
            el.addEventListener('mouseenter', this.showTooltip);
            el.addEventListener('mouseleave', this.hideTooltip);
        });
    }

    showTooltip(e) {
        const tooltip = document.createElement('div');
        tooltip.className = 'klerno-tooltip';
        tooltip.textContent = e.target.dataset.tooltip;

        tooltip.style.cssText = `
            position: absolute;
            background: rgba(17, 24, 39, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            z-index: 10000;
            pointer-events: none;
            opacity: 0;
            transform: translateY(8px);
            transition: all 0.2s ease;
            backdrop-filter: blur(8px);
        `;

        document.body.appendChild(tooltip);

        const rect = e.target.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';

        requestAnimationFrame(() => {
            tooltip.style.opacity = '1';
            tooltip.style.transform = 'translateY(0)';
        });

        e.target._tooltip = tooltip;
    }

    hideTooltip(e) {
        if (e.target._tooltip) {
            e.target._tooltip.remove();
            e.target._tooltip = null;
        }
    }

    // ===================================================================
    // ANIMATED COUNTERS
    // ===================================================================

    initCounters() {
        document.querySelectorAll('.klerno-stat-value[data-count]').forEach(counter => {
            const target = parseInt(counter.dataset.count);
            let current = 0;
            const increment = target / 60; // 60 frames

            const updateCounter = () => {
                current += increment;
                if (current < target) {
                    counter.textContent = Math.floor(current).toLocaleString();
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target.toLocaleString();
                }
            };

            // Start animation when element is in view
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !counter.dataset.animated) {
                        counter.dataset.animated = 'true';
                        updateCounter();
                    }
                });
            });

            observer.observe(counter);
        });
    }

    // ===================================================================
    // PROGRESS BARS
    // ===================================================================

    initProgressBars() {
        document.querySelectorAll('.klerno-progress-bar').forEach(bar => {
            const progress = bar.querySelector('.klerno-progress-fill');
            const percentage = progress.dataset.percentage;

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !progress.dataset.animated) {
                        progress.dataset.animated = 'true';
                        progress.style.width = percentage + '%';
                    }
                });
            });

            observer.observe(bar);
        });
    }

    // ===================================================================
    // SMOOTH SCROLLING
    // ===================================================================

    initSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // ===================================================================
    // PARALLAX EFFECTS
    // ===================================================================

    initParallax() {
        const parallaxElements = document.querySelectorAll('.klerno-parallax');

        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const rate = scrolled * -0.5;

            parallaxElements.forEach(el => {
                el.style.transform = `translate3d(0, ${rate}px, 0)`;
            });
        });
    }

    // ===================================================================
    // THEME TOGGLE
    // ===================================================================

    initThemeToggle() {
        const themeToggle = document.querySelector('.klerno-theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                document.body.classList.toggle('dark-theme');
                localStorage.setItem('theme',
                    document.body.classList.contains('dark-theme') ? 'dark' : 'light'
                );
            });
        }

        // Load saved theme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
        }
    }

    // ===================================================================
    // NOTIFICATIONS
    // ===================================================================

    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `klerno-notification klerno-notification-${type}`;
        notification.innerHTML = `
            <div class="klerno-notification-content">
                <span class="klerno-notification-message">${message}</span>
                <button class="klerno-notification-close">&times;</button>
            </div>
        `;

        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            border-left: 4px solid var(--klerno-${type === 'error' ? 'error' : type === 'success' ? 'success' : 'primary'});
            z-index: 10000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            min-width: 300px;
        `;

        document.body.appendChild(notification);

        // Slide in
        requestAnimationFrame(() => {
            notification.style.transform = 'translateX(0)';
        });

        // Close button
        notification.querySelector('.klerno-notification-close').addEventListener('click', () => {
            this.hideNotification(notification);
        });

        // Auto-hide
        setTimeout(() => {
            this.hideNotification(notification);
        }, duration);
    }

    hideNotification(notification) {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }

    initNotifications() {
        // Create notification container if it doesn't exist
        if (!document.querySelector('.klerno-notifications')) {
            const container = document.createElement('div');
            container.className = 'klerno-notifications';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                pointer-events: none;
            `;
            document.body.appendChild(container);
        }
    }

    // ===================================================================
    // LAZY LOADING
    // ===================================================================

    initLazyLoading() {
        const lazyImages = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        lazyImages.forEach(img => imageObserver.observe(img));
    }
}

// ===================================================================
// CSS ANIMATIONS (injected dynamically)
// ===================================================================

const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }

    .klerno-progress-bar {
        background: #e5e7eb;
        border-radius: 9999px;
        overflow: hidden;
        height: 8px;
    }

    .klerno-progress-fill {
        background: linear-gradient(90deg, var(--klerno-primary), var(--klerno-secondary));
        height: 100%;
        width: 0%;
        transition: width 2s cubic-bezier(0.4, 0, 0.2, 1);
        border-radius: inherit;
    }

    .klerno-notification-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
    }

    .klerno-notification-close {
        background: none;
        border: none;
        font-size: 20px;
        cursor: pointer;
        color: #6b7280;
        padding: 0;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .klerno-notification-close:hover {
        color: #374151;
    }

    img.lazy {
        opacity: 0;
        transition: opacity 0.3s;
    }

    img.lazy.loaded {
        opacity: 1;
    }
`;

document.head.appendChild(style);

// ===================================================================
// INITIALIZE
// ===================================================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.KlernoUI = new KlernoPremiumUI();
    });
} else {
    window.KlernoUI = new KlernoPremiumUI();
}

// Export for global access
window.KlernoPremiumUI = KlernoPremiumUI;

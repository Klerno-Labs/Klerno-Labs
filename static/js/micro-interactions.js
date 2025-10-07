
// ===================================================================
// KLERNO LABS MICRO-INTERACTIONS ENGINE
// Delightful JavaScript Interactions
// ===================================================================

class MicroInteractionsEngine {
    constructor() {
        this.init();
    }

    init() {
        this.setupScrollAnimations();
        this.setupPageTransitions();
        this.setupFormInteractions();
        this.setupButtonEffects();
        this.setupMenuAnimations();
        this.setupTooltips();
        this.setupProgressIndicators();
        this.setupNotifications();
        this.setupGestureInteractions();
    }

    // Scroll-triggered animations
    setupScrollAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        }, observerOptions);

        // Observe all animation elements
        document.querySelectorAll('.fade-in-up, .fade-in-left, .fade-in-right, .scale-in')
            .forEach(el => observer.observe(el));
    }

    // Page transition effects
    setupPageTransitions() {
        // Fade in page content
        window.addEventListener('load', () => {
            document.body.classList.add('loaded');
            document.querySelectorAll('.page-transition')
                .forEach(el => el.classList.add('loaded'));
        });

        // Smooth scroll for internal links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // Enhanced form interactions
    setupFormInteractions() {
        document.querySelectorAll('input, textarea').forEach(input => {
            // Focus animations
            input.addEventListener('focus', () => {
                input.parentElement?.classList.add('focused');
            });

            input.addEventListener('blur', () => {
                input.parentElement?.classList.remove('focused');
                this.validateField(input);
            });

            // Real-time validation
            input.addEventListener('input', () => {
                this.validateField(input);
            });
        });
    }

    validateField(field) {
        const value = field.value.trim();
        const type = field.type;

        field.classList.remove('input-success', 'input-error');

        if (value) {
            let isValid = true;

            // Basic validation based on type
            switch (type) {
                case 'email':
                    isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
                    break;
                case 'tel':
                    isValid = /^[\+]?[1-9][\d\s\-\(\)]{7,15}$/.test(value);
                    break;
                case 'url':
                    isValid = /^https?:\/\/.+/.test(value);
                    break;
                default:
                    isValid = value.length >= 2;
            }

            field.classList.add(isValid ? 'input-success' : 'input-error');
        }
    }

    // Button interaction effects
    setupButtonEffects() {
        document.querySelectorAll('.btn-micro').forEach(button => {
            button.addEventListener('click', (e) => {
                // Create ripple effect
                const ripple = document.createElement('span');
                const rect = button.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;

                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                ripple.classList.add('ripple');

                button.appendChild(ripple);

                setTimeout(() => {
                    ripple.remove();
                }, 600);
            });
        });
    }

    // Menu animations
    setupMenuAnimations() {
        document.querySelectorAll('.menu-item').forEach((item, index) => {
            item.style.animationDelay = `${index * 0.1}s`;
        });
    }

    // Dynamic tooltips
    setupTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            let timeout;

            element.addEventListener('mouseenter', () => {
                clearTimeout(timeout);
                element.classList.add('tooltip-active');
            });

            element.addEventListener('mouseleave', () => {
                timeout = setTimeout(() => {
                    element.classList.remove('tooltip-active');
                }, 300);
            });
        });
    }

    // Progress indicators
    setupProgressIndicators() {
        // Page load progress
        const progress = document.createElement('div');
        progress.className = 'page-progress';
        progress.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 3px;
            background: linear-gradient(45deg, var(--klerno-primary), var(--klerno-accent));
            z-index: 9999;
            transition: width 0.3s ease;
        `;
        document.body.appendChild(progress);

        // Update progress on scroll
        window.addEventListener('scroll', () => {
            const scrollTop = window.pageYOffset;
            const docHeight = document.body.scrollHeight - window.innerHeight;
            const scrollPercent = (scrollTop / docHeight) * 100;
            progress.style.width = scrollPercent + '%';
        });
    }

    // Notification system
    setupNotifications() {
        this.notificationContainer = document.createElement('div');
        this.notificationContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        document.body.appendChild(this.notificationContainer);
    }

    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} notification-slide-in`;
        notification.style.cssText = `
            background: white;
            border-left: 4px solid var(--klerno-${type === 'info' ? 'primary' : type});
            border-radius: var(--klerno-radius-lg);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            padding: 16px 20px;
            margin-bottom: 12px;
            color: var(--klerno-gray-800);
            font-weight: 500;
        `;
        notification.textContent = message;

        this.notificationContainer.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('notification-slide-out');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, duration);
    }

    // Gesture interactions
    setupGestureInteractions() {
        let startX, startY, currentX, currentY;

        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });

        document.addEventListener('touchmove', (e) => {
            if (!startX || !startY) return;

            currentX = e.touches[0].clientX;
            currentY = e.touches[0].clientY;

            const diffX = startX - currentX;
            const diffY = startY - currentY;

            // Swipe detection
            if (Math.abs(diffX) > Math.abs(diffY)) {
                if (Math.abs(diffX) > 50) {
                    if (diffX > 0) {
                        this.handleSwipeLeft();
                    } else {
                        this.handleSwipeRight();
                    }
                }
            }
        });

        document.addEventListener('touchend', () => {
            startX = null;
            startY = null;
        });
    }

    handleSwipeLeft() {
        // Handle left swipe
        console.log('Swiped left');
    }

    handleSwipeRight() {
        // Handle right swipe
        console.log('Swiped right');
    }

    // Public API methods
    animateElement(element, animation) {
        element.classList.add(animation);

        return new Promise(resolve => {
            element.addEventListener('animationend', () => {
                element.classList.remove(animation);
                resolve();
            }, { once: true });
        });
    }

    showLoading(element) {
        const loader = document.createElement('div');
        loader.className = 'loading-dots';
        loader.innerHTML = '<div></div><div></div><div></div><div></div>';

        element.style.position = 'relative';
        element.appendChild(loader);

        return () => loader.remove();
    }

    createSkeleton(element) {
        const skeleton = element.cloneNode(true);
        skeleton.classList.add('skeleton');
        skeleton.textContent = '';

        element.parentNode.insertBefore(skeleton, element);
        element.style.display = 'none';

        return () => {
            skeleton.remove();
            element.style.display = '';
        };
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.microInteractions = new MicroInteractionsEngine();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MicroInteractionsEngine;
}

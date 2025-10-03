/**
 * KLERNO LABS - ELITE JAVASCRIPT ENHANCEMENTS
 * Top 0.01% quality interactions and animations
 */

class EliteEnhancements {
    constructor() {
        this.init();
    }

    init() {
        this.setupPageTransitions();
        this.setupStaggerAnimations();
        this.setupFormEnhancements();
        this.setupLoadingStates();
        this.setupIntersectionObserver();
        this.setupAdvancedInteractions();
    }

    // Page Transition System
    setupPageTransitions() {
        // Add page transition class to main content
        const main = document.querySelector('main');
        if (main) {
            main.classList.add('page-transition');
        }

        // Smooth navigation transitions
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href^="/"]');
            if (link && !link.target && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                this.transitionToPage(link.href);
            }
        });
    }

    async transitionToPage(url) {
        const main = document.querySelector('main');
        if (main) {
            main.style.opacity = '0';
            main.style.transform = 'translateY(20px)';

            setTimeout(() => {
                window.location.href = url;
            }, 200);
        }
    }

    // Stagger Animations for Lists
    setupStaggerAnimations() {
        const observeStagger = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const children = entry.target.children;
                    Array.from(children).forEach((child, index) => {
                        child.classList.add('stagger-item');
                        child.style.animationDelay = `${index * 0.1}s`;
                    });
                    observeStagger.unobserve(entry.target);
                }
            });
        });

        document.querySelectorAll('.nav, .card-group, .list-group').forEach(el => {
            observeStagger.observe(el);
        });
    }

    // Enhanced Form Interactions
    setupFormEnhancements() {
        // Auto-resize textareas
        document.querySelectorAll('textarea').forEach(textarea => {
            this.autoResize(textarea);
            textarea.addEventListener('input', () => this.autoResize(textarea));
        });

        // Form validation enhancements
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                this.showFormSubmitting(form);
            });
        });

        // Enhanced input focus effects
        document.querySelectorAll('.form-control').forEach(input => {
            input.addEventListener('focus', () => {
                this.addFocusGlow(input);
            });

            input.addEventListener('blur', () => {
                this.removeFocusGlow(input);
            });
        });
    }

    autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    }

    addFocusGlow(input) {
        const parent = input.closest('.form-floating, .mb-3, .form-group');
        if (parent) {
            parent.classList.add('glow-effect');
        }
    }

    removeFocusGlow(input) {
        const parent = input.closest('.form-floating, .mb-3, .form-group');
        if (parent) {
            parent.classList.remove('glow-effect');
        }
    }

    showFormSubmitting(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            const originalText = submitBtn.textContent;
            submitBtn.innerHTML = '<span class="spinner me-2"></span>Processing...';
            submitBtn.disabled = true;

            // Reset after 5 seconds if form hasn't redirected
            setTimeout(() => {
                if (submitBtn) {
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                }
            }, 5000);
        }
    }

    // Loading States and Skeletons
    setupLoadingStates() {
        // Add loading skeletons for dynamic content
        this.createSkeletonLoaders();

        // Progressive image loading
        document.querySelectorAll('img[data-src]').forEach(img => {
            this.lazyLoadImage(img);
        });
    }

    createSkeletonLoaders() {
        document.querySelectorAll('[data-loading]').forEach(el => {
            const skeleton = document.createElement('div');
            skeleton.className = 'skeleton';
            skeleton.style.height = el.dataset.height || '20px';
            skeleton.style.width = el.dataset.width || '100%';
            skeleton.style.marginBottom = '10px';

            el.appendChild(skeleton);

            // Remove skeleton when content loads
            const observer = new MutationObserver(() => {
                if (el.children.length > 1) {
                    skeleton.remove();
                    observer.disconnect();
                }
            });

            observer.observe(el, { childList: true });
        });
    }

    lazyLoadImage(img) {
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('fade-in');
                    imageObserver.unobserve(img);
                }
            });
        });

        imageObserver.observe(img);
    }

    // Intersection Observer for Animations
    setupIntersectionObserver() {
        const animateOnScroll = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    animateOnScroll.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        document.querySelectorAll('.card, .alert, .badge').forEach(el => {
            animateOnScroll.observe(el);
        });
    }

    // Advanced Interactive Elements
    setupAdvancedInteractions() {
        // Enhanced tooltips
        this.setupAdvancedTooltips();

        // Ripple effect for buttons
        this.setupRippleEffect();

        // Enhanced notifications
        this.setupNotifications();

        // Parallax effects (performance-conscious)
        this.setupParallax();
    }

    setupAdvancedTooltips() {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            el.addEventListener('mouseenter', () => {
                el.classList.add('scale-in');
            });
        });
    }

    setupRippleEffect() {
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const ripple = document.createElement('span');
                const rect = btn.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;

                ripple.style.cssText = `
          position: absolute;
          width: ${size}px;
          height: ${size}px;
          left: ${x}px;
          top: ${y}px;
          background: rgba(255, 255, 255, 0.3);
          border-radius: 50%;
          transform: scale(0);
          animation: ripple 0.6s ease-out;
          pointer-events: none;
        `;

                btn.style.position = 'relative';
                btn.style.overflow = 'hidden';
                btn.appendChild(ripple);

                setTimeout(() => ripple.remove(), 600);
            });
        });
    }

    setupNotifications() {
        // Enhanced alert system
        window.showEliteNotification = (message, type = 'info', duration = 5000) => {
            const notification = document.createElement('div');
            notification.className = `alert alert-${type} alert-dismissible fade show slide-up`;
            notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: var(--glass-shadow);
        backdrop-filter: var(--glass-backdrop);
      `;

            notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      `;

            document.body.appendChild(notification);

            setTimeout(() => {
                notification.classList.add('fade-out');
                setTimeout(() => notification.remove(), 300);
            }, duration);
        };
    }

    setupParallax() {
        const parallaxElements = document.querySelectorAll('[data-parallax]');

        if (parallaxElements.length > 0 && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            let ticking = false;

            const updateParallax = () => {
                const scrollY = window.pageYOffset;

                parallaxElements.forEach(el => {
                    const speed = parseFloat(el.dataset.parallax) || 0.5;
                    const yPos = -(scrollY * speed);
                    el.style.transform = `translate3d(0, ${yPos}px, 0)`;
                });

                ticking = false;
            };

            const requestParallaxUpdate = () => {
                if (!ticking) {
                    requestAnimationFrame(updateParallax);
                    ticking = true;
                }
            };

            window.addEventListener('scroll', requestParallaxUpdate, { passive: true });
        }
    }
}

// CSS for ripple animation
const rippleCSS = `
  @keyframes ripple {
    from {
      transform: scale(0);
      opacity: 1;
    }
    to {
      transform: scale(4);
      opacity: 0;
    }
  }

  .fade-out {
    opacity: 0 !important;
    transform: translateX(100%) !important;
    transition: all 0.3s ease-out !important;
  }
`;

// Inject CSS
const style = document.createElement('style');
style.textContent = rippleCSS;
document.head.appendChild(style);

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new EliteEnhancements());
} else {
    new EliteEnhancements();
}

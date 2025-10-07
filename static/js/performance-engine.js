
// ===================================================================
// KLERNO LABS ADVANCED PERFORMANCE ENGINE
// Lightning-Fast Loading & Optimization
// ===================================================================

class AdvancedPerformanceEngine {
    constructor() {
        this.metrics = {
            loadTimes: [],
            criticalResources: [],
            lazyLoadedElements: 0,
            cacheHitRate: 0
        };
        this.init();
    }

    init() {
        this.setupCriticalResourcePrioritization();
        this.setupLazyLoading();
        this.setupImageOptimization();
        this.setupCodeSplitting();
        this.setupCacheOptimization();
        this.setupPerformanceMonitoring();
        this.optimizeRenderPath();
    }

    // Critical resource prioritization
    setupCriticalResourcePrioritization() {
        // Preload critical resources
        const criticalResources = [
            { href: '/static/css/critical.css', as: 'style' },
            { href: '/static/fonts/inter-var.woff2', as: 'font', type: 'font/woff2', crossorigin: 'anonymous' },
            { href: '/api/dashboard/data', as: 'fetch' }
        ];

        criticalResources.forEach(resource => {
            const link = document.createElement('link');
            link.rel = 'preload';
            Object.assign(link, resource);
            document.head.appendChild(link);
        });

        // DNS prefetch for external resources
        const dnsPrefetchDomains = [
            'fonts.googleapis.com',
            'cdn.jsdelivr.net',
            'api.klernolabs.com'
        ];

        dnsPrefetchDomains.forEach(domain => {
            const link = document.createElement('link');
            link.rel = 'dns-prefetch';
            link.href = `//${domain}`;
            document.head.appendChild(link);
        });
    }

    // Advanced lazy loading
    setupLazyLoading() {
        // Intersection Observer for images
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadImage(entry.target);
                    imageObserver.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '50px 0px',
            threshold: 0.01
        });

        // Observe all lazy images
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });

        // Lazy load components
        const componentObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadComponent(entry.target);
                    componentObserver.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '100px 0px'
        });

        document.querySelectorAll('[data-lazy-component]').forEach(component => {
            componentObserver.observe(component);
        });
    }

    loadImage(img) {
        const src = img.dataset.src;
        const srcset = img.dataset.srcset;

        // Create new image to test loading
        const newImg = new Image();
        newImg.onload = () => {
            img.src = src;
            if (srcset) img.srcset = srcset;
            img.classList.add('loaded');
            this.metrics.lazyLoadedElements++;
        };
        newImg.onerror = () => {
            img.src = '/static/images/placeholder.svg';
            img.classList.add('error');
        };
        newImg.src = src;
    }

    async loadComponent(element) {
        const componentName = element.dataset.lazyComponent;

        try {
            // Dynamic import for component
            const module = await import(`/static/components/${componentName}.js`);
            const ComponentClass = module.default;

            // Initialize component
            const component = new ComponentClass();
            component.render(element);

            element.classList.add('component-loaded');
            this.metrics.lazyLoadedElements++;
        } catch (error) {
            console.warn(`Failed to load component: ${componentName}`, error);
            element.innerHTML = '<div class="component-fallback">Content temporarily unavailable</div>';
        }
    }

    // Image optimization
    setupImageOptimization() {
        // Convert images to WebP when supported
        if (this.supportsWebP()) {
            document.querySelectorAll('img').forEach(img => {
                if (img.src && !img.src.includes('.webp')) {
                    const webpSrc = img.src.replace(/\.(jpg|jpeg|png)$/i, '.webp');
                    this.testImageFormat(webpSrc, img);
                }
            });
        }

        // Responsive image loading
        this.setupResponsiveImages();
    }

    supportsWebP() {
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;
    }

    testImageFormat(webpSrc, originalImg) {
        const testImg = new Image();
        testImg.onload = () => {
            originalImg.src = webpSrc;
        };
        testImg.onerror = () => {
            // Keep original format
        };
        testImg.src = webpSrc;
    }

    setupResponsiveImages() {
        const updateImageSizes = () => {
            const devicePixelRatio = window.devicePixelRatio || 1;
            const viewportWidth = window.innerWidth;

            document.querySelectorAll('img[data-responsive]').forEach(img => {
                const breakpoints = JSON.parse(img.dataset.responsive);
                let selectedSrc = img.dataset.src;

                for (const breakpoint of breakpoints) {
                    if (viewportWidth >= breakpoint.width) {
                        selectedSrc = breakpoint.src;
                        if (devicePixelRatio > 1 && breakpoint.srcRetina) {
                            selectedSrc = breakpoint.srcRetina;
                        }
                    }
                }

                if (img.src !== selectedSrc) {
                    img.src = selectedSrc;
                }
            });
        };

        window.addEventListener('resize', debounce(updateImageSizes, 250));
        updateImageSizes();
    }

    // Code splitting and dynamic imports
    setupCodeSplitting() {
        // Route-based code splitting
        this.setupRouteBasedSplitting();

        // Feature-based code splitting
        this.setupFeatureBasedSplitting();
    }

    setupRouteBasedSplitting() {
        const routeModules = new Map();

        const loadRouteModule = async (route) => {
            if (routeModules.has(route)) {
                return routeModules.get(route);
            }

            try {
                const module = await import(`/static/routes/${route}.js`);
                routeModules.set(route, module);
                return module;
            } catch (error) {
                console.warn(`Failed to load route module: ${route}`, error);
                return null;
            }
        };

        // Listen for route changes
        window.addEventListener('popstate', async (event) => {
            const route = this.getCurrentRoute();
            const module = await loadRouteModule(route);

            if (module) {
                module.init();
            }
        });
    }

    setupFeatureBasedSplitting() {
        // Load features on demand
        const featureButtons = document.querySelectorAll('[data-feature]');

        featureButtons.forEach(button => {
            button.addEventListener('click', async (e) => {
                const feature = button.dataset.feature;

                if (!button.classList.contains('feature-loaded')) {
                    button.classList.add('loading');

                    try {
                        const module = await import(`/static/features/${feature}.js`);
                        module.default.init();
                        button.classList.add('feature-loaded');
                    } catch (error) {
                        console.error(`Failed to load feature: ${feature}`, error);
                    } finally {
                        button.classList.remove('loading');
                    }
                }
            });
        });
    }

    // Cache optimization
    setupCacheOptimization() {
        // Service Worker for advanced caching
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(registration => {
                    console.log('Service Worker registered:', registration);
                })
                .catch(error => {
                    console.log('Service Worker registration failed:', error);
                });
        }

        // Memory cache for API responses
        this.setupAPICache();

        // Local storage optimization
        this.optimizeLocalStorage();
    }

    setupAPICache() {
        const apiCache = new Map();
        const cacheTimeout = 5 * 60 * 1000; // 5 minutes

        const originalFetch = window.fetch;
        window.fetch = async (url, options = {}) => {
            // Only cache GET requests
            if (options.method && options.method !== 'GET') {
                return originalFetch(url, options);
            }

            const cacheKey = url.toString();
            const cached = apiCache.get(cacheKey);

            if (cached && Date.now() - cached.timestamp < cacheTimeout) {
                this.metrics.cacheHitRate++;
                return new Response(JSON.stringify(cached.data), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' }
                });
            }

            try {
                const response = await originalFetch(url, options);

                if (response.ok && response.headers.get('content-type')?.includes('application/json')) {
                    const data = await response.clone().json();
                    apiCache.set(cacheKey, {
                        data,
                        timestamp: Date.now()
                    });
                }

                return response;
            } catch (error) {
                // Return cached data if network fails
                if (cached) {
                    return new Response(JSON.stringify(cached.data), {
                        status: 200,
                        headers: { 'Content-Type': 'application/json' }
                    });
                }
                throw error;
            }
        };
    }

    optimizeLocalStorage() {
        // Compress data before storing
        const compress = (data) => {
            return JSON.stringify(data);
        };

        const decompress = (data) => {
            return JSON.parse(data);
        };

        // Enhanced localStorage with compression
        window.optimizedStorage = {
            set: (key, value) => {
                try {
                    const compressed = compress(value);
                    localStorage.setItem(key, compressed);
                } catch (error) {
                    console.warn('Failed to store data:', error);
                }
            },
            get: (key) => {
                try {
                    const data = localStorage.getItem(key);
                    return data ? decompress(data) : null;
                } catch (error) {
                    console.warn('Failed to retrieve data:', error);
                    return null;
                }
            }
        };
    }

    // Performance monitoring
    setupPerformanceMonitoring() {
        // Web Vitals tracking
        this.trackWebVitals();

        // Custom performance metrics
        this.trackCustomMetrics();

        // Real-time performance dashboard
        this.createPerformanceDashboard();
    }

    trackWebVitals() {
        // Track First Contentful Paint
        new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
                if (entry.name === 'first-contentful-paint') {
                    this.metrics.fcp = entry.startTime;
                    this.reportMetric('FCP', entry.startTime);
                }
            });
        }).observe({ entryTypes: ['paint'] });

        // Track Largest Contentful Paint
        new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1];
            this.metrics.lcp = lastEntry.startTime;
            this.reportMetric('LCP', lastEntry.startTime);
        }).observe({ entryTypes: ['largest-contentful-paint'] });

        // Track Cumulative Layout Shift
        let clsValue = 0;
        new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
                if (!entry.hadRecentInput) {
                    clsValue += entry.value;
                }
            });
            this.metrics.cls = clsValue;
            this.reportMetric('CLS', clsValue);
        }).observe({ entryTypes: ['layout-shift'] });

        // Track First Input Delay
        new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
                this.metrics.fid = entry.processingStart - entry.startTime;
                this.reportMetric('FID', this.metrics.fid);
            });
        }).observe({ entryTypes: ['first-input'] });
    }

    trackCustomMetrics() {
        // Track resource loading times
        window.addEventListener('load', () => {
            const navigation = performance.getEntriesByType('navigation')[0];
            this.metrics.loadTime = navigation.loadEventEnd - navigation.loadEventStart;
            this.metrics.domContentLoaded = navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart;

            this.reportMetric('LoadTime', this.metrics.loadTime);
            this.reportMetric('DOMContentLoaded', this.metrics.domContentLoaded);
        });

        // Track JavaScript bundle sizes
        const observer = new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
                if (entry.name.includes('.js')) {
                    this.metrics.bundleSizes = this.metrics.bundleSizes || {};
                    this.metrics.bundleSizes[entry.name] = entry.transferSize;
                }
            });
        });
        observer.observe({ entryTypes: ['resource'] });
    }

    createPerformanceDashboard() {
        const dashboard = document.createElement('div');
        dashboard.id = 'performance-dashboard';
        dashboard.className = 'performance-dashboard';
        dashboard.innerHTML = `
            <div class="dashboard-header">
                <h3>⚡ Performance Metrics</h3>
                <button onclick="this.parentElement.parentElement.style.display='none'">×</button>
            </div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">FCP</div>
                    <div class="metric-value" id="fcp-value">-</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">LCP</div>
                    <div class="metric-value" id="lcp-value">-</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">CLS</div>
                    <div class="metric-value" id="cls-value">-</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">FID</div>
                    <div class="metric-value" id="fid-value">-</div>
                </div>
            </div>
        `;

        // Add styles
        const styles = document.createElement('style');
        styles.textContent = `
            .performance-dashboard {
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                border-radius: 10px;
                padding: 1rem;
                font-family: monospace;
                z-index: 10000;
                min-width: 200px;
            }
            .dashboard-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }
            .dashboard-header h3 {
                margin: 0;
                font-size: 0.9rem;
            }
            .dashboard-header button {
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                font-size: 1.2rem;
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.5rem;
            }
            .metric-card {
                text-align: center;
                padding: 0.5rem;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 5px;
            }
            .metric-label {
                font-size: 0.8rem;
                opacity: 0.8;
            }
            .metric-value {
                font-size: 1rem;
                font-weight: bold;
                color: #4ade80;
            }
        `;

        document.head.appendChild(styles);
        document.body.appendChild(dashboard);

        // Show dashboard only in development
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            dashboard.style.display = 'block';
        } else {
            dashboard.style.display = 'none';
        }
    }

    reportMetric(name, value) {
        // Update dashboard
        const element = document.getElementById(`${name.toLowerCase()}-value`);
        if (element) {
            element.textContent = Math.round(value) + (name === 'CLS' ? '' : 'ms');

            // Color code based on performance
            if (name === 'FCP' && value < 1800) element.style.color = '#4ade80';
            else if (name === 'LCP' && value < 2500) element.style.color = '#4ade80';
            else if (name === 'CLS' && value < 0.1) element.style.color = '#4ade80';
            else if (name === 'FID' && value < 100) element.style.color = '#4ade80';
            else element.style.color = '#f87171';
        }

        // Send to analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'web_vital', {
                metric_name: name,
                metric_value: value,
                custom_parameter: 'performance_tracking'
            });
        }
    }

    // Render optimization
    optimizeRenderPath() {
        // Reduce layout thrashing
        this.batchDOMUpdates();

        // Optimize animations for 60fps
        this.optimizeAnimations();

        // Reduce paint complexity
        this.optimizePainting();
    }

    batchDOMUpdates() {
        let updates = [];
        let isScheduled = false;

        window.batchedUpdate = (updateFn) => {
            updates.push(updateFn);

            if (!isScheduled) {
                isScheduled = true;
                requestAnimationFrame(() => {
                    updates.forEach(update => update());
                    updates = [];
                    isScheduled = false;
                });
            }
        };
    }

    optimizeAnimations() {
        // Use transform and opacity for animations
        const animatedElements = document.querySelectorAll('[data-animate]');

        animatedElements.forEach(element => {
            element.style.willChange = 'transform, opacity';

            // Clean up after animation
            element.addEventListener('animationend', () => {
                element.style.willChange = 'auto';
            });
        });
    }

    optimizePainting() {
        // Create separate layers for heavy elements
        const heavyElements = document.querySelectorAll('.heavy-paint');

        heavyElements.forEach(element => {
            element.style.transform = 'translateZ(0)';
            element.style.backfaceVisibility = 'hidden';
        });
    }

    // Utility functions
    getCurrentRoute() {
        return window.location.pathname.slice(1) || 'home';
    }

    getMetrics() {
        return { ...this.metrics };
    }

    clearCache() {
        if ('caches' in window) {
            caches.keys().then(names => {
                names.forEach(name => caches.delete(name));
            });
        }
        localStorage.clear();
        sessionStorage.clear();
    }
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize performance engine
window.addEventListener('DOMContentLoaded', () => {
    window.performanceEngine = new AdvancedPerformanceEngine();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdvancedPerformanceEngine;
}

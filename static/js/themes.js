
// ===================================================================
// KLERNO LABS PREMIUM THEMES SYSTEM
// Dynamic Theme Management
// ===================================================================

class PremiumThemeSystem {
    constructor() {
        this.currentTheme = this.getSavedTheme() || 'light';
        this.themes = ['light', 'dark', 'enterprise', 'cyberpunk'];
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.createThemeSelector();
        this.setupSystemThemeDetection();
        this.setupThemeEvents();
    }

    applyTheme(themeName) {
        document.documentElement.setAttribute('data-theme', themeName);
        this.currentTheme = themeName;
        this.saveTheme(themeName);
        this.updateThemeSelector();
        this.notifyThemeChange(themeName);
    }

    createThemeSelector() {
        const selector = document.createElement('div');
        selector.className = 'theme-selector';
        selector.innerHTML = `
            <button class="theme-option" data-theme="light">☀️ Light</button>
            <button class="theme-option" data-theme="dark">🌙 Dark</button>
            <button class="theme-option" data-theme="enterprise">🏢 Enterprise</button>
            <button class="theme-option" data-theme="cyberpunk">🚀 Cyberpunk</button>
        `;

        // Add event listeners
        selector.querySelectorAll('.theme-option').forEach(button => {
            button.addEventListener('click', () => {
                const theme = button.dataset.theme;
                this.applyTheme(theme);
            });
        });

        // Insert into page
        const nav = document.querySelector('.nav') || document.querySelector('header') || document.body;
        nav.appendChild(selector);

        this.themeSelector = selector;
    }

    updateThemeSelector() {
        if (this.themeSelector) {
            this.themeSelector.querySelectorAll('.theme-option').forEach(button => {
                button.classList.toggle('active', button.dataset.theme === this.currentTheme);
            });
        }
    }

    setupSystemThemeDetection() {
        // Detect system theme preference
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            
            const handleSystemThemeChange = (e) => {
                if (!this.getSavedTheme()) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            };

            mediaQuery.addListener(handleSystemThemeChange);
            
            // Apply system theme if no saved preference
            if (!this.getSavedTheme()) {
                this.applyTheme(mediaQuery.matches ? 'dark' : 'light');
            }
        }
    }

    setupThemeEvents() {
        // Keyboard shortcuts for theme switching
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.key >= '1' && e.key <= '4') {
                e.preventDefault();
                const themeIndex = parseInt(e.key) - 1;
                if (this.themes[themeIndex]) {
                    this.applyTheme(this.themes[themeIndex]);
                }
            }
        });

        // Custom theme event
        document.addEventListener('theme-change-request', (e) => {
            if (e.detail && e.detail.theme) {
                this.applyTheme(e.detail.theme);
            }
        });
    }

    saveTheme(themeName) {
        try {
            localStorage.setItem('klerno-theme', themeName);
        } catch (error) {
            console.warn('Failed to save theme preference:', error);
        }
    }

    getSavedTheme() {
        try {
            return localStorage.getItem('klerno-theme');
        } catch (error) {
            console.warn('Failed to get saved theme:', error);
            return null;
        }
    }

    notifyThemeChange(themeName) {
        // Dispatch custom event
        const event = new CustomEvent('theme-changed', {
            detail: { theme: themeName }
        });
        document.dispatchEvent(event);

        // Update meta theme-color
        this.updateMetaThemeColor(themeName);
    }

    updateMetaThemeColor(themeName) {
        const themeColors = {
            light: '#6366f1',
            dark: '#0f172a',
            enterprise: '#1e40af',
            cyberpunk: '#00d4ff'
        };

        let metaTheme = document.querySelector('meta[name="theme-color"]');
        if (!metaTheme) {
            metaTheme = document.createElement('meta');
            metaTheme.name = 'theme-color';
            document.head.appendChild(metaTheme);
        }

        metaTheme.content = themeColors[themeName] || themeColors.light;
    }

    // Public API
    getCurrentTheme() {
        return this.currentTheme;
    }

    getAvailableThemes() {
        return [...this.themes];
    }

    switchToNextTheme() {
        const currentIndex = this.themes.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % this.themes.length;
        this.applyTheme(this.themes[nextIndex]);
    }

    switchToPreviousTheme() {
        const currentIndex = this.themes.indexOf(this.currentTheme);
        const prevIndex = currentIndex === 0 ? this.themes.length - 1 : currentIndex - 1;
        this.applyTheme(this.themes[prevIndex]);
    }
}

// Initialize theme system
document.addEventListener('DOMContentLoaded', () => {
    window.themeSystem = new PremiumThemeSystem();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PremiumThemeSystem;
}

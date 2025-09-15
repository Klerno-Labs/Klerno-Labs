/**
 * THEME CONTROLLER
 * JavaScript for handling light/dark theme switching
 */

class ThemeController {
  constructor() {
    this.themeKey = 'klerno-theme';
    this.currentTheme = this.getStoredTheme() || this.getSystemTheme();
    this.init();
  }

  init() {
    this.applyTheme(this.currentTheme);
    this.createThemeToggle();
    this.bindEvents();
  }

  getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  getStoredTheme() {
    return localStorage.getItem(this.themeKey);
  }

  storeTheme(theme) {
    localStorage.setItem(this.themeKey, theme);
  }

  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    this.currentTheme = theme;
    this.storeTheme(theme);
    this.updateToggleIcon();
  }

  toggleTheme() {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    this.applyTheme(newTheme);
    
    // Add a subtle animation to indicate the change
    document.body.style.transition = 'background-color 0.3s ease';
    setTimeout(() => {
      document.body.style.transition = '';
    }, 300);
  }

  createThemeToggle() {
    const toggle = document.createElement('button');
    toggle.className = 'theme-toggle';
    toggle.setAttribute('aria-label', 'Toggle theme');
    toggle.setAttribute('title', 'Toggle light/dark theme');
    toggle.innerHTML = this.getToggleIcon();
    
    document.body.appendChild(toggle);
    this.toggleElement = toggle;
  }

  getToggleIcon() {
    if (this.currentTheme === 'light') {
      return `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      `;
    } else {
      return `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"/>
          <path d="m12 1 1.5 1.5-1.5 1.5-1.5-1.5L12 1zm0 18 1.5 1.5-1.5 1.5-1.5-1.5L12 19zm11-7h-3m-16 0h-3m15.5-6.5-2.12 2.12m-11.31 11.31-2.12 2.12m15.5 6.5-2.12-2.12M5.64 5.64 3.52 3.52"/>
        </svg>
      `;
    }
  }

  updateToggleIcon() {
    if (this.toggleElement) {
      this.toggleElement.innerHTML = this.getToggleIcon();
    }
  }

  bindEvents() {
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
      if (!this.getStoredTheme()) {
        this.applyTheme(e.matches ? 'light' : 'dark');
      }
    });

    // Theme toggle click
    document.addEventListener('click', (e) => {
      if (e.target.closest('.theme-toggle')) {
        this.toggleTheme();
      }
    });

    // Keyboard accessibility
    document.addEventListener('keydown', (e) => {
      if (e.target.closest('.theme-toggle') && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        this.toggleTheme();
      }
    });
  }
}

// Animation utilities
class AnimationController {
  static observeElements() {
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('animate-fade-in');
            observer.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
      });

      // Observe all elements with animate-on-scroll class
      document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
      });
    }
  }

  static initScrollAnimations() {
    // Parallax effect for hero sections
    window.addEventListener('scroll', () => {
      const scrolled = window.pageYOffset;
      const parallaxElements = document.querySelectorAll('.parallax');
      
      parallaxElements.forEach(element => {
        const speed = element.dataset.speed || 0.5;
        const yPos = -(scrolled * speed);
        element.style.transform = `translateY(${yPos}px)`;
      });
    });
  }

  static initHoverEffects() {
    // Add magnetic effect to buttons
    document.querySelectorAll('.btn-elite').forEach(button => {
      button.addEventListener('mousemove', (e) => {
        const rect = button.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        
        button.style.transform = `translate(${x * 0.1}px, ${y * 0.1}px)`;
      });

      button.addEventListener('mouseleave', () => {
        button.style.transform = '';
      });
    });
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Initialize theme controller
  new ThemeController();
  
  // Initialize animations
  AnimationController.observeElements();
  AnimationController.initScrollAnimations();
  AnimationController.initHoverEffects();
});

// Export for use in other modules
window.KlernoTheme = {
  ThemeController,
  AnimationController
};
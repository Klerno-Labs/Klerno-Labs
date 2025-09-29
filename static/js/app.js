// Klerno Labs - Main Application JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Klerno application initialized');

    // Add skip to content link for accessibility
    const skipLink = document.createElement('a');
    skipLink.href = '#main';
    skipLink.className = 'skip-to-content';
    skipLink.textContent = 'Skip to content';
    document.body.insertBefore(skipLink, document.body.firstChild);

    // Initialize tooltips and popovers if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });

        // Activate the first tab in each tab container
        document.querySelectorAll('[role="tablist"]').forEach(tablist => {
            const firstTab = tablist.querySelector('[role="tab"]');
            if (firstTab && !tablist.querySelector('[aria-selected="true"]')) {
                firstTab.setAttribute('aria-selected', 'true');
                firstTab.classList.add('active');
                const panelId = firstTab.getAttribute('aria-controls');
                if (panelId) {
                    const panel = document.getElementById(panelId);
                    if (panel) {
                        panel.removeAttribute('hidden');
                    }
                }
            }
        });

        // Set up tab click handlers
        document.querySelectorAll('[role="tab"]').forEach(tab => {
            tab.addEventListener('click', function() {
                const tablist = this.closest('[role="tablist"]');
                if (!tablist) return;

                // Hide all panels and deactivate all tabs
                const tabs = tablist.querySelectorAll('[role="tab"]');
                tabs.forEach(t => {
                    t.setAttribute('aria-selected', 'false');
                    t.classList.remove('active');
                    const panelId = t.getAttribute('aria-controls');
                    if (panelId) {
                        const panel = document.getElementById(panelId);
                        if (panel) {
                            panel.setAttribute('hidden', '');
                        }
                    }
                });

                // Activate clicked tab and show its panel
                this.setAttribute('aria-selected', 'true');
                this.classList.add('active');
                const panelId = this.getAttribute('aria-controls');
                if (panelId) {
                    const panel = document.getElementById(panelId);
                    if (panel) {
                        panel.removeAttribute('hidden');
                    }
                }
            });
        });
    }

    // Handle form submissions with AJAX if needed
    const ajaxForms = document.querySelectorAll('form[data-ajax="true"]');
    ajaxForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            // Show loading state
            const submitBtn = this.querySelector('[type="submit"]');
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="loading-spinner me-2"></span>Processing...';
            }

            // Reset previous errors
            this.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            this.querySelectorAll('.invalid-feedback').forEach(el => el.remove());

            const formData = new FormData(this);
            const url = this.getAttribute('action') || window.location.href;
            const method = this.getAttribute('method') || 'POST';

            fetch(url, {
                method: method,
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Network response error: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Handle the response
                if (data.redirect) {
                    window.location.href = data.redirect;
                } else if (data.message) {
                    showMessage(data.message, data.success ? 'success' : 'danger');

                    // Reset form on success if requested
                    if (data.success && this.getAttribute('data-reset-on-success') === 'true') {
                        this.reset();
                    }
                }

                // Handle field errors
                if (data.errors) {
                    Object.keys(data.errors).forEach(field => {
                        const input = this.querySelector(`[name="${field}"]`);
                        if (input) {
                            input.classList.add('is-invalid');
                            const feedback = document.createElement('div');
                            feedback.className = 'invalid-feedback';
                            feedback.textContent = data.errors[field];
                            input.parentNode.appendChild(feedback);
                        }
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('An error occurred. Please try again.', 'danger');
            })
            .finally(() => {
                // Restore submit button
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            });
        });
    });

    // Helper function to show messages
    function showMessage(message, type = 'info') {
        // Create alerts container if it doesn't exist
        let alertsContainer = document.getElementById('alerts-container');
        if (!alertsContainer) {
            alertsContainer = document.createElement('div');
            alertsContainer.id = 'alerts-container';
            alertsContainer.className = 'position-fixed top-0 end-0 p-3';
            alertsContainer.style.zIndex = '1050';
            document.body.appendChild(alertsContainer);
        }

        // Create alert element
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.role = 'alert';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Add animation class
        alert.classList.add('fade-in');

        // Add to container
        alertsContainer.appendChild(alert);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }, 5000);
    }

    // Format currency values (USD or XRP)
    window.formatCurrency = function(value, currency = 'XRP') {
        if (isNaN(value)) return '-';

        if (currency === 'XRP') {
            return parseFloat(value).toFixed(2) + ' XRP';
        } else if (currency === 'USD') {
            return '$' + parseFloat(value).toFixed(2);
        }

        return value;
    };

    // Format date/time values
    window.formatDateTime = function(date) {
        if (!date) return '-';

        const d = new Date(date);
        if (isNaN(d.getTime())) return date;

        return d.toLocaleString();
    };

    // Format risk score with color coding
    window.formatRiskScore = function(score) {
        if (isNaN(score)) return '-';

        const numScore = parseFloat(score);
        let cls = 'risk-low';

        if (numScore >= 0.75) {
            cls = 'risk-high';
        } else if (numScore >= 0.5) {
            cls = 'risk-medium';
        }

        return `<span class="risk-score ${cls}">${(numScore * 100).toFixed(0)}</span>`;
    };

    // Expose globals
    window.showMessage = showMessage;

    // Handle darkmode toggle if present
    const darkModeToggle = document.getElementById('darkmode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.documentElement.classList.toggle('dark-mode');
            const isDarkMode = document.documentElement.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDarkMode ? 'true' : 'false');
        });

        // Check for saved preference
        if (localStorage.getItem('darkMode') === 'true') {
            document.documentElement.classList.add('dark-mode');
        }
    }
});


// ===================================================================
// KLERNO LABS STUNNING DATA VISUALIZATION ENGINE
// Enterprise-Grade Charts & Analytics
// ===================================================================

class StunningDataVisualizationEngine {
    constructor() {
        this.charts = new Map();
        this.themes = {
            light: {
                background: '#ffffff',
                text: '#1f2937',
                grid: '#e5e7eb',
                primary: '#6366f1',
                secondary: '#8b5cf6',
                accent: '#06b6d4',
                success: '#10b981',
                warning: '#f59e0b',
                error: '#ef4444'
            },
            dark: {
                background: '#0f172a',
                text: '#f8fafc',
                grid: '#334155',
                primary: '#818cf8',
                secondary: '#a78bfa',
                accent: '#22d3ee',
                success: '#34d399',
                warning: '#fbbf24',
                error: '#f87171'
            }
        };
        this.currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        this.init();
    }

    init() {
        this.loadChartLibraries();
        this.setupThemeListener();
        this.createChartRegistry();
    }

    async loadChartLibraries() {
        // Load Chart.js
        if (!window.Chart) {
            await this.loadScript('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js');
        }

        // Load D3.js
        if (!window.d3) {
            await this.loadScript('https://d3js.org/d3.v7.min.js');
        }

        console.log('📊 Chart libraries loaded successfully');
    }

    loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    setupThemeListener() {
        document.addEventListener('theme-changed', (e) => {
            this.currentTheme = e.detail.theme;
            this.updateAllChartsTheme();
        });
    }

    createChartRegistry() {
        this.chartTypes = {
            'line': this.createLineChart.bind(this),
            'bar': this.createBarChart.bind(this),
            'pie': this.createPieChart.bind(this),
            'doughnut': this.createDoughnutChart.bind(this),
            'radar': this.createRadarChart.bind(this),
            'scatter': this.createScatterChart.bind(this),
            'area': this.createAreaChart.bind(this),
            'heatmap': this.createHeatmapChart.bind(this),
            'gauge': this.createGaugeChart.bind(this),
            'treemap': this.createTreemapChart.bind(this)
        };
    }

    // Chart Creation Methods
    createLineChart(containerId, data, options = {}) {
        const ctx = document.getElementById(containerId).getContext('2d');
        const theme = this.themes[this.currentTheme];

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((dataset, index) => ({
                    ...dataset,
                    borderColor: dataset.borderColor || this.getColorByIndex(index),
                    backgroundColor: dataset.backgroundColor || this.getColorByIndex(index, 0.1),
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: theme.background,
                    pointBorderWidth: 2
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        labels: {
                            color: theme.text,
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: theme.background,
                        titleColor: theme.text,
                        bodyColor: theme.text,
                        borderColor: theme.grid,
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: theme.grid,
                            lineWidth: 1
                        },
                        ticks: {
                            color: theme.text
                        }
                    },
                    y: {
                        grid: {
                            color: theme.grid,
                            lineWidth: 1
                        },
                        ticks: {
                            color: theme.text
                        }
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeInOutQuart'
                },
                ...options
            }
        });

        this.charts.set(containerId, chart);
        return chart;
    }

    createBarChart(containerId, data, options = {}) {
        const ctx = document.getElementById(containerId).getContext('2d');
        const theme = this.themes[this.currentTheme];

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((dataset, index) => ({
                    ...dataset,
                    backgroundColor: dataset.backgroundColor || this.getGradient(ctx, index),
                    borderColor: dataset.borderColor || this.getColorByIndex(index),
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: theme.text,
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: theme.background,
                        titleColor: theme.text,
                        bodyColor: theme.text,
                        borderColor: theme.grid,
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: theme.text
                        }
                    },
                    y: {
                        grid: {
                            color: theme.grid,
                            lineWidth: 1
                        },
                        ticks: {
                            color: theme.text
                        }
                    }
                },
                animation: {
                    duration: 1500,
                    easing: 'easeOutBounce'
                },
                ...options
            }
        });

        this.charts.set(containerId, chart);
        return chart;
    }

    createPieChart(containerId, data, options = {}) {
        const ctx = document.getElementById(containerId).getContext('2d');
        const theme = this.themes[this.currentTheme];

        const chart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: data.colors || this.generateColorPalette(data.values.length),
                    borderColor: theme.background,
                    borderWidth: 4,
                    hoverOffset: 15
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: theme.text,
                            usePointStyle: true,
                            padding: 20,
                            generateLabels: (chart) => {
                                const data = chart.data;
                                return data.labels.map((label, index) => ({
                                    text: `${label} (${data.datasets[0].data[index]})`,
                                    fillStyle: data.datasets[0].backgroundColor[index],
                                    strokeStyle: data.datasets[0].backgroundColor[index],
                                    pointStyle: 'circle'
                                }));
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: theme.background,
                        titleColor: theme.text,
                        bodyColor: theme.text,
                        borderColor: theme.grid,
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12,
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${context.label}: ${context.parsed} (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 2000
                },
                ...options
            }
        });

        this.charts.set(containerId, chart);
        return chart;
    }

    createAreaChart(containerId, data, options = {}) {
        const ctx = document.getElementById(containerId).getContext('2d');
        const theme = this.themes[this.currentTheme];

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((dataset, index) => ({
                    ...dataset,
                    fill: true,
                    backgroundColor: this.getGradient(ctx, index, true),
                    borderColor: this.getColorByIndex(index),
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        labels: {
                            color: theme.text,
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    filler: {
                        propagate: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: theme.grid,
                            lineWidth: 1
                        },
                        ticks: {
                            color: theme.text
                        }
                    },
                    y: {
                        grid: {
                            color: theme.grid,
                            lineWidth: 1
                        },
                        ticks: {
                            color: theme.text
                        },
                        stacked: options.stacked || false
                    }
                },
                elements: {
                    line: {
                        tension: 0.4
                    }
                },
                ...options
            }
        });

        this.charts.set(containerId, chart);
        return chart;
    }

    createGaugeChart(containerId, value, options = {}) {
        const container = document.getElementById(containerId);
        const theme = this.themes[this.currentTheme];

        // Clear container
        container.innerHTML = '';

        // Create SVG
        const svg = d3.select(container)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', '0 0 400 300');

        const width = 400;
        const height = 300;
        const margin = 40;
        const radius = Math.min(width, height) / 2 - margin;

        const g = svg.append('g')
            .attr('transform', `translate(${width/2}, ${height/2})`);

        // Arc generator
        const arc = d3.arc()
            .innerRadius(radius * 0.65)
            .outerRadius(radius * 0.85);

        // Background arc
        g.append('path')
            .datum({startAngle: -Math.PI/2, endAngle: Math.PI/2})
            .style('fill', theme.grid)
            .attr('d', arc);

        // Value arc
        const valueAngle = -Math.PI/2 + (value / 100) * Math.PI;
        g.append('path')
            .datum({startAngle: -Math.PI/2, endAngle: valueAngle})
            .style('fill', theme.primary)
            .attr('d', arc);

        // Center text
        g.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .style('font-size', '48px')
            .style('font-weight', 'bold')
            .style('fill', theme.text)
            .text(`${value}%`);

        // Label
        g.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '2.5em')
            .style('font-size', '16px')
            .style('fill', theme.text)
            .text(options.label || 'Performance');

        return { update: (newValue) => this.createGaugeChart(containerId, newValue, options) };
    }

    // Utility Methods
    getColorByIndex(index) {
        const colors = [
            '#6366f1', '#8b5cf6', '#06b6d4', '#10b981',
            '#f59e0b', '#ef4444', '#ec4899', '#14b8a6'
        ];
        return colors[index % colors.length];
    }

    getGradient(ctx, index, isArea = false) {
        const color = this.getColorByIndex(index);
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);

        if (isArea) {
            gradient.addColorStop(0, color + '40');
            gradient.addColorStop(1, color + '00');
        } else {
            gradient.addColorStop(0, color);
            gradient.addColorStop(1, color + '80');
        }

        return gradient;
    }

    generateColorPalette(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(this.getColorByIndex(i));
        }
        return colors;
    }

    updateAllChartsTheme() {
        this.charts.forEach((chart, id) => {
            // Recreate chart with new theme
            const canvas = document.getElementById(id);
            if (canvas) {
                const rect = canvas.getBoundingClientRect();
                chart.destroy();
                // Note: In a real implementation, you'd store chart config and recreate
            }
        });
    }

    // Dashboard Creation
    createDashboard(containerId, config) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';
        container.className = 'analytics-dashboard';

        // Create dashboard grid
        const dashboard = document.createElement('div');
        dashboard.className = 'dashboard-grid';

        config.widgets.forEach((widget, index) => {
            const widgetElement = this.createWidget(widget, `widget-${index}`);
            dashboard.appendChild(widgetElement);
        });

        container.appendChild(dashboard);

        // Initialize charts in widgets
        config.widgets.forEach((widget, index) => {
            if (widget.type === 'chart') {
                setTimeout(() => {
                    this.chartTypes[widget.chartType](`chart-${index}`, widget.data, widget.options);
                }, 100);
            }
        });
    }

    createWidget(config, id) {
        const widget = document.createElement('div');
        widget.className = `dashboard-widget ${config.size || 'medium'}`;
        widget.innerHTML = `
            <div class="widget-header">
                <h3 class="widget-title">${config.title}</h3>
                <div class="widget-actions">
                    <button class="widget-action" onclick="dataViz.exportWidget('${id}')">📊</button>
                    <button class="widget-action" onclick="dataViz.refreshWidget('${id}')">🔄</button>
                </div>
            </div>
            <div class="widget-content">
                ${config.type === 'chart' ? `<canvas id="chart-${id.split('-')[1]}"></canvas>` : config.content || ''}
            </div>
        `;
        return widget;
    }

    // Data Generation for Demo
    generateDemoData() {
        return {
            revenue: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Revenue',
                    data: [65000, 78000, 82000, 91000, 85000, 94000],
                    borderColor: '#6366f1',
                    backgroundColor: '#6366f1'
                }]
            },
            userGrowth: {
                labels: ['Q1', 'Q2', 'Q3', 'Q4'],
                datasets: [{
                    label: 'New Users',
                    data: [1200, 1900, 3000, 2800],
                    backgroundColor: ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b']
                }]
            },
            performance: {
                labels: ['Performance', 'Security', 'Reliability', 'Scalability', 'User Experience'],
                datasets: [{
                    label: 'Metrics',
                    data: [98, 95, 97, 92, 96],
                    backgroundColor: 'rgba(99, 102, 241, 0.2)',
                    borderColor: '#6366f1',
                    pointBackgroundColor: '#6366f1'
                }]
            }
        };
    }

    // Export functionality
    exportWidget(widgetId) {
        const widget = document.getElementById(widgetId);
        // Implementation would use html2canvas or similar
        console.log(`Exporting widget: ${widgetId}`);
    }

    refreshWidget(widgetId) {
        // Implementation would fetch new data and update
        console.log(`Refreshing widget: ${widgetId}`);
    }
}

// Initialize visualization engine
document.addEventListener('DOMContentLoaded', () => {
    window.dataViz = new StunningDataVisualizationEngine();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StunningDataVisualizationEngine;
}

// Workly Main JavaScript
// Global utilities and interactive functionality

(function() {
    'use strict';

    // Initialize application when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initializeApp();
    });

    function initializeApp() {
        initializeTooltips();
        initializePopovers();
        initializeForms();
        initializeTimers();
        initializeNotifications();
        initializeTheme();
    }

    // Initialize Bootstrap tooltips
    function initializeTooltips() {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Initialize Bootstrap popovers
    function initializePopovers() {
        var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }

    // Form enhancements
    function initializeForms() {
        // Add loading states to form submissions
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner"></span> Caricamento...';
                }
            });
        });

        // Real-time form validation
        const inputs = document.querySelectorAll('.form-control, .form-select');
        inputs.forEach(input => {
            input.addEventListener('blur', validateInput);
            input.addEventListener('input', debounce(validateInput, 500));
        });
    }

    // Input validation
    function validateInput(e) {
        const input = e.target;
        const isValid = input.checkValidity();
        
        input.classList.remove('is-valid', 'is-invalid');
        
        if (input.value.trim() !== '') {
            input.classList.add(isValid ? 'is-valid' : 'is-invalid');
        }
    }

    // Debounce utility
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

    // Real-time clock updates
    function initializeTimers() {
        updateClocks();
        setInterval(updateClocks, 1000);
    }

    function updateClocks() {
        const clockElements = document.querySelectorAll('[data-clock]');
        clockElements.forEach(element => {
            const now = new Date();
            const format = element.dataset.clock || 'time';
            
            let timeString;
            switch(format) {
                case 'datetime':
                    timeString = now.toLocaleString('it-IT');
                    break;
                case 'date':
                    timeString = now.toLocaleDateString('it-IT');
                    break;
                default:
                    timeString = now.toLocaleTimeString('it-IT');
            }
            
            element.textContent = timeString;
        });
    }

    // Notification system
    function initializeNotifications() {
        // Auto-hide alerts after 5 seconds
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.classList.add('fade');
                    setTimeout(() => alert.remove(), 150);
                }
            }, 5000);
        });
    }

    // Theme management
    function initializeTheme() {
        // Maintain dark theme consistency
        const theme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-bs-theme', theme);
    }

    // Global utility functions
    window.Workly = {
        // Show loading state
        showLoading: function(element) {
            if (element) {
                element.classList.add('loading');
            }
        },

        // Hide loading state
        hideLoading: function(element) {
            if (element) {
                element.classList.remove('loading');
            }
        },

        // Show notification
        showNotification: function(message, type = 'info') {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            const container = document.querySelector('.container');
            if (container) {
                container.insertBefore(alertDiv, container.firstChild);
                
                // Auto-hide after 5 seconds
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.classList.remove('show');
                        setTimeout(() => alertDiv.remove(), 150);
                    }
                }, 5000);
            }
        },

        // Confirm dialog
        confirm: function(message, callback) {
            if (confirm(message)) {
                callback();
            }
        },

        // Format time duration
        formatDuration: function(hours) {
            if (!hours) return '00:00';
            const totalMinutes = Math.round(hours * 60);
            const h = Math.floor(totalMinutes / 60);
            const m = totalMinutes % 60;
            return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
        },

        // Format date
        formatDate: function(date) {
            if (typeof date === 'string') {
                date = new Date(date);
            }
            return date.toLocaleDateString('it-IT');
        },

        // Format datetime
        formatDateTime: function(date) {
            if (typeof date === 'string') {
                date = new Date(date);
            }
            return date.toLocaleString('it-IT');
        },

        // AJAX helper
        ajax: function(url, options = {}) {
            const defaults = {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            };
            
            const config = { ...defaults, ...options };
            
            return fetch(url, config)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .catch(error => {
                    console.error('AJAX error:', error);
                    this.showNotification('Errore di connessione', 'danger');
                    throw error;
                });
        }
    };

    // Chart utilities
    window.ChartUtils = {
        // Default chart colors
        colors: [
            'rgba(54, 162, 235, 0.8)',
            'rgba(255, 99, 132, 0.8)',
            'rgba(255, 206, 86, 0.8)',
            'rgba(75, 192, 192, 0.8)',
            'rgba(153, 102, 255, 0.8)',
            'rgba(255, 159, 64, 0.8)'
        ],

        // Default chart options
        defaultOptions: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            }
        },

        // Create gradient
        createGradient: function(ctx, color1, color2) {
            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, color1);
            gradient.addColorStop(1, color2);
            return gradient;
        }
    };

    // QR Code utilities
    window.QRUtils = {
        // Generate QR code for URL
        generateQR: function(element, url, options = {}) {
            const defaults = {
                width: 200,
                height: 200,
                colorDark: '#000000',
                colorLight: '#ffffff',
                margin: 2
            };
            
            const config = { ...defaults, ...options };
            
            if (typeof QRCode !== 'undefined') {
                QRCode.toCanvas(element, url, config, function (error) {
                    if (error) {
                        console.error('QR Code generation error:', error);
                    }
                });
            } else {
                console.warn('QRCode library not loaded');
            }
        }
    };

    // Attendance specific utilities
    window.AttendanceUtils = {
        // Check if user can check in/out
        canCheckIn: function(lastAttendance) {
            if (!lastAttendance) return true;
            const today = new Date().toDateString();
            const lastDate = new Date(lastAttendance.date).toDateString();
            return today !== lastDate || !lastAttendance.entry_time;
        },

        canCheckOut: function(todayAttendance) {
            return todayAttendance && todayAttendance.entry_time && !todayAttendance.exit_time;
        },

        // Calculate work hours
        calculateHours: function(entry, exit) {
            if (!entry || !exit) return 0;
            const entryTime = new Date(entry);
            const exitTime = new Date(exit);
            return (exitTime - entryTime) / (1000 * 60 * 60); // Convert to hours
        }
    };

    // Initialize page-specific functionality
    const page = document.body.dataset.page;
    if (page) {
        switch(page) {
            case 'dashboard':
                initializeDashboard();
                break;
            case 'attendance':
                initializeAttendance();
                break;
            case 'statistics':
                initializeStatistics();
                break;
        }
    }

    function initializeDashboard() {
        // Dashboard-specific initialization
        console.log('Dashboard initialized');
    }

    function initializeAttendance() {
        // Attendance-specific initialization
        console.log('Attendance page initialized');
    }

    function initializeStatistics() {
        // Statistics-specific initialization
        console.log('Statistics page initialized');
    }

})();

// Service Worker registration for offline capability (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Only register if service worker file exists
        fetch('/sw.js', { method: 'HEAD' })
            .then(response => {
                if (response.ok) {
                    navigator.serviceWorker.register('/sw.js')
                        .then(registration => {
                            console.log('SW registered: ', registration);
                        })
                        .catch(registrationError => {
                            console.log('SW registration failed: ', registrationError);
                        });
                }
            })
            .catch(() => {
                // Service worker file doesn't exist, skip registration
            });
    });
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    // Could send errors to logging service in production
});

// Global unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    // Could send errors to logging service in production
});

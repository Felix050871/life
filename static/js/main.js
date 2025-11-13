/**
 * Main JavaScript file for Workforce Management Platform
 * Provides enhanced interactivity and user experience
 */

// Global application object
window.WorkforceApp = {
    // Configuration
    config: {
        dateFormat: 'DD/MM/YYYY',
        timeFormat: 'HH:mm',
        refreshInterval: 30000, // 30 seconds
        animationDuration: 300
    },

    // Initialize the application
    init: function() {
        this.setupEventListeners();
        this.initializeComponents();
        this.startPeriodicUpdates();
    },

    // Set up global event listeners
    setupEventListeners: function() {
        // Handle form submissions with loading states
        document.addEventListener('submit', this.handleFormSubmit.bind(this));
        
        // Handle confirm dialogs
        document.addEventListener('click', this.handleConfirmActions.bind(this));
        
        // Handle responsive table scrolling
        this.setupResponsiveTables();
        
        // Handle date input validations
        this.setupDateValidations();
        
        // Setup auto-save for forms
        this.setupAutoSave();
    },

    // Initialize components
    initializeComponents: function() {
        this.initializeTooltips();
        this.initializePopovers();
        this.initializeDatePickers();
        this.initializeTimeDisplays();
        this.animateCards();
    },

    // Handle form submissions with loading states
    handleFormSubmit: function(event) {
        const form = event.target;
        if (!form.matches('form')) return;

        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn) {
            // Add loading state
            submitBtn.disabled = true;
            submitBtn.classList.add('loading');
            
            // Add spinner if it doesn't exist
            if (!submitBtn.querySelector('.spinner-border')) {
                const spinner = document.createElement('span');
                spinner.className = 'spinner-border spinner-border-sm me-2';
                spinner.setAttribute('role', 'status');
                spinner.setAttribute('aria-hidden', 'true');
                submitBtn.insertBefore(spinner, submitBtn.firstChild);
            }

            // Re-enable after 5 seconds as fallback
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.classList.remove('loading');
                const spinner = submitBtn.querySelector('.spinner-border');
                if (spinner) spinner.remove();
            }, 5000);
        }
    },

    // Handle confirm actions
    handleConfirmActions: function(event) {
        const element = event.target.closest('[onclick*="confirm"]');
        if (!element) return;

        const onclickValue = element.getAttribute('onclick');
        if (onclickValue && onclickValue.includes('confirm(')) {
            event.preventDefault();
            
            // Extract confirm message
            const match = onclickValue.match(/confirm\(['"]([^'"]+)['"]\)/);
            const message = match ? match[1] : 'Are you sure?';
            
            // Show custom confirm dialog
            this.showConfirmDialog(message, () => {
                // If confirmed, execute the original action
                if (element.href) {
                    window.location.href = element.href;
                } else {
                    // Handle form submission or other actions
                    const form = element.closest('form');
                    if (form) form.submit();
                }
            });
        }
    },

    // Setup responsive tables
    setupResponsiveTables: function() {
        const tables = document.querySelectorAll('.table-responsive');
        tables.forEach(table => {
            // Add scroll indicators
            this.addScrollIndicators(table);
        });
    },

    // Add scroll indicators to tables
    addScrollIndicators: function(tableContainer) {
        const table = tableContainer.querySelector('table');
        if (!table) return;

        const checkScroll = () => {
            const isScrollable = table.scrollWidth > tableContainer.clientWidth;
            const isScrolledToEnd = tableContainer.scrollLeft >= (table.scrollWidth - tableContainer.clientWidth - 1);
            
            tableContainer.classList.toggle('has-scroll', isScrollable);
            tableContainer.classList.toggle('scrolled-to-end', isScrolledToEnd);
        };

        tableContainer.addEventListener('scroll', checkScroll);
        window.addEventListener('resize', checkScroll);
        checkScroll();
    },

    // Setup date validations
    setupDateValidations: function() {
        const dateInputs = document.querySelectorAll('input[type="date"]');
        dateInputs.forEach(input => {
            input.addEventListener('change', this.validateDateInput.bind(this));
        });
    },

    // Validate date input
    validateDateInput: function(event) {
        const input = event.target;
        const value = input.value;
        
        if (value) {
            const selectedDate = new Date(value);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            
            // Add validation feedback
            const feedback = input.parentNode.querySelector('.date-feedback');
            if (feedback) feedback.remove();
            
            const feedbackEl = document.createElement('div');
            feedbackEl.className = 'date-feedback mt-1';
            
            if (selectedDate < today && input.name.includes('start_date')) {
                feedbackEl.className += ' text-warning';
                feedbackEl.innerHTML = '<small><i class="fas fa-exclamation-triangle me-1"></i>Data nel passato</small>';
            } else if (selectedDate > new Date(today.getTime() + 365 * 24 * 60 * 60 * 1000)) {
                feedbackEl.className += ' text-info';
                feedbackEl.innerHTML = '<small><i class="fas fa-info-circle me-1"></i>Data molto futura</small>';
            }
            
            if (feedbackEl.innerHTML) {
                input.parentNode.appendChild(feedbackEl);
            }
        }
    },

    // Setup auto-save for forms
    setupAutoSave: function() {
        const forms = document.querySelectorAll('form[data-autosave]');
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                input.addEventListener('input', this.debounce(() => {
                    this.autoSaveForm(form);
                }, 2000));
            });
        });
    },

    // Auto-save form data to localStorage
    autoSaveForm: function(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        const formId = form.id || form.action;
        localStorage.setItem(`autosave_${formId}`, JSON.stringify(data));
        
        // Show auto-save indicator
        this.showAutoSaveIndicator();
    },

    // Show auto-save indicator
    showAutoSaveIndicator: function() {
        let indicator = document.querySelector('.autosave-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'autosave-indicator position-fixed bottom-0 end-0 m-3';
            indicator.innerHTML = '<div class="toast show" role="alert"><div class="toast-body"><i class="fas fa-save me-2"></i>Bozza salvata automaticamente</div></div>';
            document.body.appendChild(indicator);
        }
        
        indicator.style.display = 'block';
        setTimeout(() => {
            indicator.style.display = 'none';
        }, 2000);
    },

    // Initialize tooltips
    initializeTooltips: function() {
        if (typeof bootstrap !== 'undefined') {
            // Escludi elementi dentro le modal per evitare conflitti
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]:not(.modal [data-bs-toggle="tooltip"])'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
            
            // Gestisci l'apertura/chiusura delle modal
            document.addEventListener('shown.bs.modal', function (event) {
                // Distruggi tutti i tooltip quando una modal viene aperta
                const modalTooltips = event.target.querySelectorAll('[data-bs-toggle="tooltip"]');
                modalTooltips.forEach(function(el) {
                    const tooltip = bootstrap.Tooltip.getInstance(el);
                    if (tooltip) {
                        tooltip.dispose();
                    }
                });
            });
        }
    },

    // Initialize popovers
    initializePopovers: function() {
        if (typeof bootstrap !== 'undefined') {
            const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
            popoverTriggerList.map(function (popoverTriggerEl) {
                return new bootstrap.Popover(popoverTriggerEl);
            });
        }
    },

    // Initialize date pickers with defaults
    initializeDatePickers: function() {
        const dateInputs = document.querySelectorAll('input[type="date"]');
        const today = new Date().toISOString().split('T')[0];
        
        dateInputs.forEach(input => {
            if (!input.value && input.dataset.defaultToday) {
                input.value = today;
            }
        });
    },

    // Initialize time displays
    initializeTimeDisplays: function() {
        this.updateTimeDisplays();
        setInterval(() => {
            this.updateTimeDisplays();
        }, 1000);
    },

    // Update all time displays
    updateTimeDisplays: function() {
        const timeDisplays = document.querySelectorAll('.time-display, #time-display');
        const now = new Date();
        const timeString = now.toLocaleTimeString('it-IT', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        timeDisplays.forEach(display => {
            if (display) {
                display.textContent = timeString;
            }
        });

        // Update clock displays
        const clockDisplays = document.querySelectorAll('.clock-display');
        clockDisplays.forEach(clock => {
            if (clock) {
                clock.textContent = timeString;
            }
        });
    },

    // Animate cards on page load
    animateCards: function() {
        const cards = document.querySelectorAll('.card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.5s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    },

    // Show custom confirm dialog
    showConfirmDialog: function(message, onConfirm, onCancel) {
        // Create modal if it doesn't exist
        let modal = document.querySelector('#confirmModal');
        if (!modal) {
            modal = this.createConfirmModal();
        }

        // Update message
        modal.querySelector('.modal-body').textContent = message;

        // Set up event listeners
        const confirmBtn = modal.querySelector('.btn-danger');
        const cancelBtn = modal.querySelector('.btn-secondary');

        confirmBtn.onclick = () => {
            if (onConfirm) onConfirm();
            bootstrap.Modal.getInstance(modal).hide();
        };

        cancelBtn.onclick = () => {
            if (onCancel) onCancel();
            bootstrap.Modal.getInstance(modal).hide();
        };

        // Show modal
        new bootstrap.Modal(modal).show();
    },

    // Create confirm modal
    createConfirmModal: function() {
        const modalHTML = `
            <div class="modal fade" id="confirmModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Conferma Azione</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            Sei sicuro di voler procedere?
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annulla</button>
                            <button type="button" class="btn btn-danger">Conferma</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        return document.querySelector('#confirmModal');
    },

    // Start periodic updates
    startPeriodicUpdates: function() {
        // Update time displays
        setInterval(() => {
            this.updateTimeDisplays();
        }, 1000);

        // Update page data periodically (if needed)
        if (document.querySelector('[data-auto-refresh]')) {
            setInterval(() => {
                this.refreshPageData();
            }, this.config.refreshInterval);
        }
    },

    // Refresh page data
    refreshPageData: function() {
        // Only refresh if user is active (not idle)
        if (this.isUserActive()) {
            // Refresh specific components that need real-time updates
            this.refreshAttendanceStatus();
            this.refreshNotifications();
        }
    },

    // Check if user is active
    isUserActive: function() {
        // Simple activity detection
        const lastActivity = this.lastActivity || Date.now();
        return (Date.now() - lastActivity) < 300000; // 5 minutes
    },

    // Refresh attendance status
    refreshAttendanceStatus: function() {
        const statusElements = document.querySelectorAll('[data-attendance-status]');
        statusElements.forEach(element => {
            // Update attendance status indicators
            this.updateAttendanceIndicator(element);
        });
    },

    // Update attendance indicator
    updateAttendanceIndicator: function(element) {
        const status = element.dataset.attendanceStatus;
        const indicator = element.querySelector('.status-dot');
        
        if (indicator) {
            indicator.className = 'status-dot';
            
            switch (status) {
                case 'clocked-in':
                    indicator.classList.add('clocked-in');
                    break;
                case 'on-break':
                    indicator.classList.add('on-break');
                    break;
                case 'clocked-out':
                    indicator.classList.add('clocked-out');
                    break;
            }
        }
    },

    // Refresh notifications
    refreshNotifications: function() {
        // Placeholder for future notification updates
        const badges = document.querySelectorAll('.notification-badge');
        if (badges.length > 0) {
            // Could update badge counts here when implemented
        }
    },

    // Utility functions
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Format date
    formatDate: function(date, format) {
        if (!date) return '';
        
        const d = new Date(date);
        const day = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const year = d.getFullYear();
        
        switch (format) {
            case 'DD/MM/YYYY':
                return `${day}/${month}/${year}`;
            case 'YYYY-MM-DD':
                return `${year}-${month}-${day}`;
            default:
                return d.toLocaleDateString('it-IT');
        }
    },

    // Format time
    formatTime: function(time, format) {
        if (!time) return '';
        
        const t = new Date(`1970-01-01T${time}`);
        
        switch (format) {
            case 'HH:mm':
                return t.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
            default:
                return t.toLocaleTimeString('it-IT');
        }
    },

    // Show toast notification
    showToast: function(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        
        // Create structure safely without innerHTML
        const flexDiv = document.createElement('div');
        flexDiv.className = 'd-flex';
        
        const toastBody = document.createElement('div');
        toastBody.className = 'toast-body';
        toastBody.textContent = message; // Safe: prevents XSS
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close btn-close-white me-2 m-auto';
        closeButton.setAttribute('data-bs-dismiss', 'toast');
        
        flexDiv.appendChild(toastBody);
        flexDiv.appendChild(closeButton);
        toast.appendChild(flexDiv);

        // Add to toast container
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(container);
        }

        container.appendChild(toast);

        // Show toast
        const bsToast = new bootstrap.Toast(toast, { delay: duration });
        bsToast.show();

        // Remove from DOM after hide
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
};

// Track user activity
document.addEventListener('mousemove', () => {
    WorkforceApp.lastActivity = Date.now();
});

document.addEventListener('keypress', () => {
    WorkforceApp.lastActivity = Date.now();
});

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    WorkforceApp.init();
});

// Export for use in other scripts
window.WA = WorkforceApp;
// JavaScript per il sistema Presidio - Gestione Coperture

document.addEventListener('DOMContentLoaded', function() {
    // Inizializza tutti i componenti quando la pagina è caricata
    initializePresidioComponents();
});

function initializePresidioComponents() {
    // Inizializza DataTables se presenti
    initializeDataTables();
    
    // Inizializza form di ricerca
    initializeSearchForm();
    
    // Inizializza validazione form
    initializeFormValidation();
    
    // Inizializza multi-select personalizzati
    initializeMultiSelect();
    
    // Inizializza tooltip e popover
    initializeTooltips();
    
    // Inizializza eventi di collasso
    initializeCollapseEvents();
}

// Inizializzazione DataTables
function initializeDataTables() {
    if (typeof $.fn.DataTable !== 'undefined') {
        $('.table-presidio').DataTable({
            language: {
                url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/it-IT.json'
            },
            responsive: true,
            pageLength: 25,
            order: [[0, 'desc']], // Ordina per data creazione
            columnDefs: [
                {
                    targets: -1, // Ultima colonna (azioni)
                    orderable: false,
                    searchable: false
                }
            ]
        });
    }
}

// Form di ricerca con filtri
function initializeSearchForm() {
    const searchForm = document.getElementById('presidio-search-form');
    if (searchForm) {
        // Auto-submit su cambio filtri
        const filterInputs = searchForm.querySelectorAll('select, input[type="date"]');
        filterInputs.forEach(input => {
            input.addEventListener('change', function() {
                searchForm.submit();
            });
        });
        
        // Reset filtri
        const resetBtn = document.getElementById('reset-filters');
        if (resetBtn) {
            resetBtn.addEventListener('click', function() {
                filterInputs.forEach(input => {
                    input.value = '';
                });
                searchForm.submit();
            });
        }
    }
}

// Validazione form avanzata
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
        
        // Validazione real-time per alcuni campi
        const timeInputs = form.querySelectorAll('input[type="time"]');
        timeInputs.forEach(input => {
            input.addEventListener('blur', validateTimeInput);
        });
        
        const dateInputs = form.querySelectorAll('input[type="date"]');
        dateInputs.forEach(input => {
            input.addEventListener('blur', validateDateInput);
        });
    });
}

// Validazione input tempo
function validateTimeInput(event) {
    const input = event.target;
    const form = input.closest('form');
    
    if (input.name === 'end_time') {
        const startTimeInput = form.querySelector('input[name="start_time"]');
        if (startTimeInput && startTimeInput.value && input.value) {
            if (input.value <= startTimeInput.value) {
                input.setCustomValidity('L\'ora di fine deve essere successiva all\'ora di inizio');
            } else {
                input.setCustomValidity('');
            }
        }
    }
    
    if (input.name === 'break_end') {
        const breakStartInput = form.querySelector('input[name="break_start"]');
        if (breakStartInput && breakStartInput.value && input.value) {
            if (input.value <= breakStartInput.value) {
                input.setCustomValidity('L\'ora di fine pausa deve essere successiva all\'ora di inizio pausa');
            } else {
                input.setCustomValidity('');
            }
        }
    }
}

// Validazione input data
function validateDateInput(event) {
    const input = event.target;
    const form = input.closest('form');
    
    if (input.name === 'end_date') {
        const startDateInput = form.querySelector('input[name="start_date"]');
        if (startDateInput && startDateInput.value && input.value) {
            if (new Date(input.value) < new Date(startDateInput.value)) {
                input.setCustomValidity('La data di fine deve essere successiva alla data di inizio');
            } else {
                input.setCustomValidity('');
            }
        }
    }
}

// Multi-select personalizzato per ruoli
function initializeMultiSelect() {
    const multiSelects = document.querySelectorAll('.multi-select-container');
    multiSelects.forEach(container => {
        const select = container.querySelector('select[multiple]');
        const display = container.querySelector('.multi-select-display');
        
        if (select && display) {
            setupMultiSelect(select, display, container);
        }
    });
}

function setupMultiSelect(select, display, container) {
    // Nascondi il select originale
    select.style.display = 'none';
    
    // Aggiorna il display quando cambiano le selezioni
    select.addEventListener('change', function() {
        updateMultiSelectDisplay(select, display);
    });
    
    // Click per aprire/chiudere
    display.addEventListener('click', function() {
        toggleMultiSelectDropdown(container);
    });
    
    // Inizializza il display
    updateMultiSelectDisplay(select, display);
}

function updateMultiSelectDisplay(select, display) {
    display.innerHTML = '';
    
    const selectedOptions = Array.from(select.selectedOptions);
    if (selectedOptions.length === 0) {
        display.innerHTML = '<span class="text-muted">Seleziona ruoli...</span>';
        return;
    }
    
    selectedOptions.forEach(option => {
        const item = document.createElement('span');
        item.className = 'selected-item';
        item.innerHTML = `
            ${option.text}
            <button type="button" class="remove-item" data-value="${option.value}">×</button>
        `;
        
        const removeBtn = item.querySelector('.remove-item');
        removeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            option.selected = false;
            select.dispatchEvent(new Event('change'));
        });
        
        display.appendChild(item);
    });
}

// Tooltip e popover
function initializeTooltips() {
    // Bootstrap tooltips
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
}

// Eventi di collasso per visualizzazione dettagli
function initializeCollapseEvents() {
    const collapseButtons = document.querySelectorAll('[data-toggle="collapse"]');
    collapseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const target = document.querySelector(button.getAttribute('data-target'));
            if (target) {
                target.classList.toggle('show');
                
                // Cambia icona
                const icon = button.querySelector('i');
                if (icon) {
                    icon.classList.toggle('fa-chevron-down');
                    icon.classList.toggle('fa-chevron-up');
                }
            }
        });
    });
}

// Gestione preset giorni settimana
function handleDaysPreset(presetValue) {
    const checkboxes = document.querySelectorAll('input[name="days_of_week"]');
    
    // Deseleziona tutti
    checkboxes.forEach(cb => cb.checked = false);
    
    // Seleziona in base al preset
    switch(presetValue) {
        case 'workdays':
            // Lunedì-Venerdì (0-4)
            [0, 1, 2, 3, 4].forEach(day => {
                const cb = document.querySelector(`input[name="days_of_week"][value="${day}"]`);
                if (cb) cb.checked = true;
            });
            break;
        case 'weekend':
            // Sabato-Domenica (5-6)
            [5, 6].forEach(day => {
                const cb = document.querySelector(`input[name="days_of_week"][value="${day}"]`);
                if (cb) cb.checked = true;
            });
            break;
        case 'all_week':
            // Tutti i giorni (0-6)
            [0, 1, 2, 3, 4, 5, 6].forEach(day => {
                const cb = document.querySelector(`input[name="days_of_week"][value="${day}"]`);
                if (cb) cb.checked = true;
            });
            break;
        case 'custom':
            // Non fare nulla, lascia selezione manuale
            break;
    }
}

// Conferma eliminazione
function confirmDelete(message) {
    return confirm(message || 'Sei sicuro di voler eliminare questo elemento?');
}

// Toast notifications
function showToast(message, type = 'info') {
    // Crea container se non esiste
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    // Crea toast
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Mostra toast
    if (typeof bootstrap !== 'undefined') {
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Rimuovi dopo che si nasconde
        toast.addEventListener('hidden.bs.toast', function() {
            container.removeChild(toast);
        });
    } else {
        // Fallback senza Bootstrap
        toast.style.display = 'block';
        setTimeout(() => {
            if (container.contains(toast)) {
                container.removeChild(toast);
            }
        }, window.CONFIG?.TOAST_DURATION_ERROR || 5000);
    }
}

// Utilità per chiamate AJAX
function makeAjaxRequest(url, method = 'GET', data = null) {
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: data ? JSON.stringify(data) : null
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    });
}

// Gestione errori globale
window.addEventListener('error', function(e) {
    console.error('Errore JavaScript:', e.error);
    showToast('Si è verificato un errore. Ricarica la pagina se il problema persiste.', 'danger');
});

// Export per uso esterno
window.PresidioScripts = {
    showToast,
    confirmDelete,
    handleDaysPreset,
    makeAjaxRequest
};
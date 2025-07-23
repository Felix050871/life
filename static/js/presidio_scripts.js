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
        }, 5000);
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
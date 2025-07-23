// JavaScript per Gestione Presidio - Sistema Gestione Presenze
// Estratto dal sistema completo per implementazione standalone

// Gestione dinamica slot temporali
let slotCounter = 0;

function addTimeSlot(dayNum) {
    const container = document.getElementById(`day-${dayNum}-slots`);
    const template = document.getElementById('time-slot-template');
    
    if (!container || !template) {
        console.error('Elementi container o template non trovati');
        return;
    }
    
    // Clona il template
    const newSlot = template.cloneNode(true);
    newSlot.style.display = 'block';
    newSlot.id = `slot-${dayNum}-${slotCounter}`;
    
    // Aggiorna i nomi dei campi per essere unici
    const inputs = newSlot.querySelectorAll('input, select');
    inputs.forEach(input => {
        if (input.name) {
            input.name = input.name.replace('[]', `[${slotCounter}]`);
        }
        input.id = `${input.className}_${dayNum}_${slotCounter}`;
    });
    
    // Imposta il giorno della settimana
    const dayInput = newSlot.querySelector('.day-of-week');
    if (dayInput) {
        dayInput.value = dayNum;
    }
    
    // Aggiungi al container
    container.appendChild(newSlot);
    
    // Aggiorna il contatore nel tab
    updateDayCounter(dayNum);
    
    slotCounter++;
}

function removeTimeSlot(button) {
    const slotCard = button.closest('.time-slot');
    if (slotCard) {
        const dayInput = slotCard.querySelector('.day-of-week');
        const dayNum = dayInput ? dayInput.value : null;
        
        slotCard.remove();
        
        if (dayNum !== null) {
            updateDayCounter(parseInt(dayNum));
        }
    }
}

function updateDayCounter(dayNum) {
    const container = document.getElementById(`day-${dayNum}-slots`);
    const counter = document.getElementById(`day-${dayNum}-count`);
    
    if (container && counter) {
        const slots = container.querySelectorAll('.time-slot');
        counter.textContent = slots.length;
        
        // Aggiorna classe del tab in base al numero di slot
        const tab = document.getElementById(`day-${dayNum}-tab`);
        if (tab) {
            if (slots.length > 0) {
                tab.classList.add('text-success');
                tab.classList.remove('text-muted');
            } else {
                tab.classList.remove('text-success');
                tab.classList.add('text-muted');
            }
        }
    }
}

// Gestione copertura presidio
function selectCoverage() {
    const select = document.getElementById('coverage-select');
    if (!select) return;
    
    const selectedOption = select.options[select.selectedIndex];
    const coverageId = select.value;
    
    if (coverageId) {
        // Mostra sezione gestione turni
        const managementSection = document.getElementById('shift-management');
        if (managementSection) {
            managementSection.style.display = 'block';
        }
        
        // Aggiorna campi nascosti per generazione automatica
        const coverageIdAuto = document.getElementById('coverage-id-auto');
        if (coverageIdAuto) {
            coverageIdAuto.value = coverageId;
        }
        
        // Carica e mostra dettagli copertura
        loadCoverageDetails(coverageId);
    } else {
        // Nascondi sezione gestione turni
        const managementSection = document.getElementById('shift-management');
        if (managementSection) {
            managementSection.style.display = 'none';
        }
    }
}

function updateCoverageDetails() {
    const select = document.getElementById('coverage-select');
    const infoDiv = document.getElementById('coverage-info');
    const periodSpan = document.getElementById('info-period');
    
    if (!select || !infoDiv || !periodSpan) return;
    
    const selectedOption = select.options[select.selectedIndex];
    
    if (select.value && selectedOption) {
        const period = selectedOption.getAttribute('data-period');
        periodSpan.textContent = period;
        infoDiv.style.display = 'block';
        
        // Aggiorna display periodo per generazione automatica
        const autoPeriodDisplay = document.getElementById('auto-period-display');
        if (autoPeriodDisplay) {
            autoPeriodDisplay.textContent = period;
        }
        
        // Estrai date dal periodo per i campi nascosti
        if (period) {
            const dates = period.split(' - ');
            if (dates.length === 2) {
                const startDate = convertDateFormat(dates[0]);
                const endDate = convertDateFormat(dates[1]);
                
                const autoStartDate = document.getElementById('auto-start-date');
                const autoEndDate = document.getElementById('auto-end-date');
                
                if (autoStartDate) autoStartDate.value = startDate;
                if (autoEndDate) autoEndDate.value = endDate;
            }
        }
    } else {
        infoDiv.style.display = 'none';
    }
}

function convertDateFormat(dateStr) {
    // Converte da "dd/mm/yyyy" a "yyyy-mm-dd"
    const parts = dateStr.split('/');
    if (parts.length === 3) {
        return `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
    }
    return dateStr;
}

function loadCoverageDetails(coverageId) {
    if (!coverageId) return;
    
    fetch(`/api/presidio_coverage/${coverageId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCoverageDetails(data);
            } else {
                console.error('Errore nel caricamento dettagli copertura:', data.message);
            }
        })
        .catch(error => {
            console.error('Errore nella richiesta:', error);
        });
}

function displayCoverageDetails(data) {
    const detailsDiv = document.getElementById('coverage-details');
    if (!detailsDiv) return;
    
    let html = '<div class="mt-2"><strong>Coperture:</strong><br>';
    
    if (data.coverages && data.coverages.length > 0) {
        const coveragesByDay = {};
        
        // Raggruppa per giorno
        data.coverages.forEach(coverage => {
            if (!coveragesByDay[coverage.day_of_week]) {
                coveragesByDay[coverage.day_of_week] = [];
            }
            coveragesByDay[coverage.day_of_week].push(coverage);
        });
        
        // Nomi giorni
        const dayNames = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'];
        
        Object.keys(coveragesByDay).sort().forEach(day => {
            const dayNum = parseInt(day);
            const dayName = dayNames[dayNum] || `Giorno ${dayNum}`;
            html += `<small><strong>${dayName}:</strong> `;
            
            const dayCoverages = coveragesByDay[day]
                .map(c => `${c.start_time}-${c.end_time}`)
                .join(', ');
            
            html += `${dayCoverages}</small><br>`;
        });
    } else {
        html += '<small class="text-muted">Nessuna copertura definita</small>';
    }
    
    html += '</div>';
    detailsDiv.innerHTML = html;
}

// Gestione status template
function toggleTemplateStatus(templateId, newStatus) {
    if (!confirm(`Sei sicuro di voler ${newStatus ? 'attivare' : 'disattivare'} questo template?`)) {
        return;
    }
    
    fetch(`/presidio_coverage/toggle_status/${templateId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_active: newStatus })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(data.message || 'Errore durante l\'operazione', 'error');
        }
    })
    .catch(error => {
        console.error('Errore:', error);
        showToast('Errore di connessione', 'error');
    });
}

function confirmDelete(templateId, templateName) {
    if (!confirm(`Sei sicuro di voler eliminare il template "${templateName}"?\n\nQuesta azione disattiverà il template e tutte le sue coperture.`)) {
        return;
    }
    
    fetch(`/presidio_coverage/delete/${templateId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(data.message || 'Errore durante l\'eliminazione', 'error');
        }
    })
    .catch(error => {
        console.error('Errore:', error);
        showToast('Errore di connessione', 'error');
    });
}

// Funzione toast per notifiche
function showToast(message, type = 'info') {
    // Crea il container toast se non esiste
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Crea il toast
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto text-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'}">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'} me-1"></i>
                    ${type === 'success' ? 'Successo' : type === 'error' ? 'Errore' : 'Informazione'}
                </strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Mostra il toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: type === 'error' ? 5000 : 3000
    });
    
    toast.show();
    
    // Rimuovi dall'DOM dopo che si nasconde
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Inizializzazione alla pagina caricata
document.addEventListener('DOMContentLoaded', function() {
    // Aggiorna contatori per giorni esistenti
    for (let day = 0; day < 7; day++) {
        updateDayCounter(day);
    }
    
    // Inizializza select copertura se presente
    const coverageSelect = document.getElementById('coverage-select');
    if (coverageSelect) {
        updateCoverageDetails();
    }
    
    // Gestione form submit per evitare doppi submit
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            submitButtons.forEach(btn => {
                btn.disabled = true;
                setTimeout(() => btn.disabled = false, 3000);
            });
        });
    });
});
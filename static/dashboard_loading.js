// Sistema di indicatori di caricamento per Dashboard Team
function showLoading() {
    // Funzione legacy disabilitata per prevenire overlay persistente
    console.log('showLoading called but disabled to prevent overlay issues');
    
    // Solo feedback sul pulsante, NO overlay globale
    const submitButton = document.getElementById('customSearchBtn');
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Caricamento...';
        console.log('Form button feedback only - no global overlay');
    }
}

function showLoadingForm(form) {
    // Cambia solo il pulsante di submit del form, NON l'overlay globale
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Caricamento...';
        console.log('Form submission started with button feedback only');
    }
}

// Funzione showLoadingExport rimossa completamente per eliminare overlay persistenti

// Sistema ottimizzato per gestione loading overlay
document.addEventListener('DOMContentLoaded', function() {
    // Forza la rimozione dell'overlay quando la pagina è caricata
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('d-none');
        overlay.style.display = 'none'; // Forza anche lo stile CSS
        console.log('Loading overlay forced hidden on page load');
    }
    
    // Auto-nasconde overlay dopo massimo 8 secondi (ridotto per migliore UX)
    setTimeout(() => {
        if (overlay && !overlay.classList.contains('d-none')) {
            overlay.classList.add('d-none');
            overlay.style.display = 'none';
            console.log('Loading overlay auto-hidden dopo timeout');
            
            // Ripristina controlli se ancora disabilitati
            const submitButton = document.getElementById('customSearchBtn');
            if (submitButton && submitButton.disabled) {
                submitButton.disabled = false;
                submitButton.innerHTML = '<i class="fas fa-search me-1"></i>Visualizza';
            }
        }
    }, 8000);
});

// Gestisce il browser back/forward
window.addEventListener('pageshow', function(event) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('d-none');
    }
});
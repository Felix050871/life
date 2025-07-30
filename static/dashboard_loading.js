// Sistema di indicatori di caricamento per Dashboard Team
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('d-none');
        
        // Disabilita tutti i controlli per prevenire azioni multiple DOPO il submit
        const exportButtons = document.querySelectorAll('.export-btn');
        exportButtons.forEach(btn => btn.style.pointerEvents = 'none');
        
        // Disabilita il pulsante submit solo DOPO aver permesso l'invio del form
        setTimeout(() => {
            const submitButton = document.getElementById('customSearchBtn');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Caricamento...';
            }
        }, 100);
    }
}

function showLoadingExport(element) {
    // Cambia temporaneamente il testo del pulsante per l'export
    const originalContent = element.innerHTML;
    element.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generazione...';
    element.style.pointerEvents = 'none';
    
    // NON mostrare l'overlay globale per l'export - solo il pulsante cambia
    // L'export è veloce e non necessita di overlay full-screen
    
    // Ripristina il pulsante rapidamente dopo l'avvio del download
    setTimeout(() => {
        element.innerHTML = originalContent;
        element.style.pointerEvents = 'auto';
        console.log('Export button restored after download started');
    }, 800); // Ridotto a 800ms per export veloce
}

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
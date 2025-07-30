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
    
    // Ripristina dopo 3 secondi (tempo stimato per download)
    setTimeout(() => {
        element.innerHTML = originalContent;
        element.style.pointerEvents = 'auto';
    }, 3000);
}

// Mostra loading automaticamente se la pagina è lenta da caricare
document.addEventListener('DOMContentLoaded', function() {
    // Nasconde overlay se presente (pagina caricata correttamente)
    const overlay = document.getElementById('loadingOverlay');
    if (overlay && !overlay.classList.contains('d-none')) {
        overlay.classList.add('d-none');
    }
    
    // Auto-nasconde overlay dopo massimo 15 secondi per prevenire loop infiniti
    setTimeout(() => {
        if (overlay && !overlay.classList.contains('d-none')) {
            overlay.classList.add('d-none');
            console.log('Loading overlay auto-hidden dopo timeout');
            // Mostra un messaggio di errore se il caricamento è troppo lento
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-warning alert-dismissible fade show';
            alertDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                Il caricamento sta impiegando più del previsto. La pagina dovrebbe aggiornarsi a breve.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('.container-fluid').prepend(alertDiv);
        }
    }, 15000);
});

// Gestisce il browser back/forward
window.addEventListener('pageshow', function(event) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('d-none');
    }
});
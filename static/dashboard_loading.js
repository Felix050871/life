// Sistema di indicatori di caricamento per Dashboard Team
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('d-none');
        
        // Disabilita tutti i controlli per prevenire azioni multiple DOPO il submit
        const exportButtons = document.querySelectorAll('.export-btn');
        exportButtons.forEach(btn => btn.style.pointerEvents = 'none');
        
        // Non disabilitare gli input del form altrimenti i dati non vengono inviati
        const submitButton = document.getElementById('customSearchBtn');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Caricamento...';
        }
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
});

// Gestisce il browser back/forward
window.addEventListener('pageshow', function(event) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('d-none');
    }
});
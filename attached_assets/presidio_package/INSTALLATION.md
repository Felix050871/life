# Guida Installazione - Pacchetto Presidio

Questa guida spiega come integrare il pacchetto funzioni Presidio in un progetto Flask esistente.

## Prerequisiti

- Flask applicazione esistente
- SQLAlchemy configurato
- Flask-Login per autenticazione
- Bootstrap 5 per UI
- DataTables per tabelle interattive

## Struttura File

```
presidio_package/
├── README.md                    # Documentazione generale
├── INSTALLATION.md             # Questa guida
├── templates/
│   ├── presidio_coverage.html  # Gestione copertura presidio
│   ├── view_presidi.html       # Visualizzazione presidi
│   └── presidio_detail.html    # Dettaglio presidio
├── routes/
│   └── presidio_routes.py      # Route Flask
├── models/
│   └── presidio_models.py      # Modelli database
├── forms/
│   └── presidio_forms.py       # Form WTForms
└── static/
    ├── js/
    │   └── presidio_scripts.js  # JavaScript
    └── css/
        └── presidio_styles.css  # CSS personalizzati
```

## Passo 1: Database

### Integra i modelli nel tuo models.py

```python
# Aggiungi al tuo models.py esistente
from presidio_package.models.presidio_models import (
    PresidioCoverageTemplate, 
    PresidioCoverage,
    get_active_presidio_templates,
    get_presidio_coverage_for_day,
    get_required_roles_for_time_slot
)
```

### Crea le tabelle

```python
# Nel tuo script di inizializzazione database
with app.app_context():
    db.create_all()
```

## Passo 2: Route

### Integra le route nel tuo routes.py

```python
# Aggiungi al tuo routes.py esistente
from presidio_package.routes.presidio_routes import *
```

Oppure importa singolarmente:

```python
from presidio_package.routes.presidio_routes import (
    presidio_coverage,
    presidio_coverage_edit,
    presidio_detail,
    view_presidi,
    api_presidio_coverage,
    toggle_presidio_template_status,
    delete_presidio_template
)
```

## Passo 3: Form

### Integra i form nel tuo forms.py

```python
# Aggiungi al tuo forms.py esistente
from presidio_package.forms.presidio_forms import (
    PresidioCoverageTemplateForm,
    PresidioCoverageForm,
    PresidioCoverageSearchForm
)
```

## Passo 4: Template

### Copia i template nella directory templates/

```bash
cp presidio_package/templates/* templates/
```

### Verifica che base.html includa:

```html
<!-- Nel <head> -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<link rel="stylesheet" href="{{ url_for('static', filename='css/presidio_styles.css') }}">

<!-- Prima di </body> -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<script src="{{ url_for('static', filename='js/presidio_scripts.js') }}"></script>
```

## Passo 5: Asset Statici

### Copia i file CSS e JavaScript

```bash
cp presidio_package/static/css/* static/css/
cp presidio_package/static/js/* static/js/
```

## Passo 6: Modello User

### Verifica che il modello User abbia il metodo can_manage_shifts()

```python
class User(UserMixin, db.Model):
    # ... altri campi ...
    
    def can_manage_shifts(self):
        """Verifica se l'utente può gestire i turni"""
        return self.role in ['Admin', 'Project Manager']
    
    def get_full_name(self):
        """Restituisce nome completo"""
        return f"{self.first_name} {self.last_name}".strip()
```

## Passo 7: Menu Navigazione

### Aggiungi voci menu nel template base

```html
<!-- Nel menu principale -->
<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="presidioDropdown" role="button" data-bs-toggle="dropdown">
        <i class="fas fa-shield-alt me-1"></i>Presidio
    </a>
    <ul class="dropdown-menu">
        {% if current_user.can_manage_shifts() %}
        <li><a class="dropdown-item" href="{{ url_for('presidio_coverage') }}">
            <i class="fas fa-cog me-1"></i>Gestione Copertura
        </a></li>
        {% endif %}
        <li><a class="dropdown-item" href="{{ url_for('view_presidi') }}">
            <i class="fas fa-eye me-1"></i>Visualizza Presidi
        </a></li>
    </ul>
</li>
```

## Passo 8: Permessi e Sicurezza

### Verifica che il decoratore @login_required funzioni

```python
from flask_login import login_required, current_user
```

### Sistema di permessi

Il sistema usa `current_user.can_manage_shifts()` per:
- Gestione copertura presidio (solo Admin/PM)
- Modifica template (solo Admin/PM)
- Eliminazione template (solo Admin/PM)

La visualizzazione è accessibile a tutti gli utenti autenticati.

## Passo 9: Test

### Test base di funzionamento

1. Avvia l'applicazione
2. Accedi con utente Admin/PM
3. Vai a "Presidio > Gestione Copertura"
4. Crea un nuovo template
5. Aggiungi coperture per diversi giorni
6. Verifica visualizzazione in "Visualizza Presidi"

### Test API

```bash
# Test API dettagli copertura
curl -H "Content-Type: application/json" \
     -X GET http://localhost:5000/api/presidio_coverage/1
```

## Risoluzione Problemi

### Errore tabelle non esistenti
```python
# Esegui migrazione database
with app.app_context():
    db.create_all()
```

### Errore import moduli
```python
# Verifica paths nel PYTHONPATH
import sys
sys.path.append('presidio_package')
```

### Errore CSS/JS non caricati
```python
# Verifica configurazione Flask per file statici
app = Flask(__name__, static_folder='static')
```

### Errore permessi utente
```python
# Verifica che User.can_manage_shifts() ritorni True per admin
user = User.query.filter_by(role='Admin').first()
print(user.can_manage_shifts())  # Deve essere True
```

## Configurazione Avanzata

### Personalizzazione Ruoli

Modifica i ruoli disponibili in `presidio_forms.py`:

```python
required_roles = SelectMultipleField('Ruoli Richiesti', choices=[
    ('TuoRuolo1', 'Tuo Ruolo 1'),
    ('TuoRuolo2', 'Tuo Ruolo 2'),
    # ... altri ruoli
])
```

### Personalizzazione Orari

I template supportano:
- Orari 24/7 con supporto turni notturni
- Pause personalizzabili
- Sovrapposizioni orarie multiple
- Validità temporale dei template

### Integrazione Calendario

Per integrare con FullCalendar esistente:

```javascript
// Aggiungi eventi presidio al calendario
const presidioEvents = await fetch('/api/presidio_coverage/1')
    .then(response => response.json());
```

## Support

Per problemi o domande:
1. Verifica la console browser per errori JavaScript
2. Controlla i log Flask per errori server
3. Verifica che tutte le dipendenze siano installate
4. Controlla che i permessi utente siano configurati correttamente
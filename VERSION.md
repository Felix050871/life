# Workly Platform - Version Information

## Versione Corrente: 2.0.3
**Data Release**: 31 Luglio 2025  
**Build**: 20250731-103000  
**Compatibilità Database**: v2.0+

## Novità Versione 2.0.3

### Ottimizzazioni Performance
- **Caricamento Lazy ACI Tables**: Record caricati solo con filtri applicati
- **Upload Excel Ottimizzato**: Processamento a batch (100 record) per file grandi
- **Validazione File Size**: Limite 50MB con controllo JavaScript
- **Progress Bar Upload**: Feedback real-time durante elaborazione

### Miglioramenti Sistema ACI
- Elaborazione solo colonne A, B, C (MARCA, MODELLO, COSTO KM)
- Gestione timeout prevenuta con batch processing
- Interfaccia utente ottimizzata con 3 stati visualizzazione
- Statistiche separate: Record DB vs Record Filtrati

### Bug Fix
- Risolto crash upload file Excel voluminosi (1400+ record)
- Corretta gestione memoria durante elaborazione batch
- Eliminati timeout su upload lunghi

## Architettura Sistema

### Backend
- **Framework**: Flask 2.3+
- **Database**: PostgreSQL 12+ con SQLAlchemy ORM
- **Autenticazione**: Flask-Login con hash sicuri
- **File Processing**: pandas + openpyxl per Excel

### Frontend  
- **UI Framework**: Bootstrap 5 (tema dark Replit)
- **JavaScript**: Vanilla ES6+ per interattività
- **Icons**: Font Awesome 6
- **Export**: Client-side Excel con SheetJS

### Database Schema
- **35+ Tabelle** per gestione completa workforce
- **30+ Permessi granulari** per controllo accesso
- **Multi-sede** con gestione dinamica utenti
- **Audit Trail** per tracciabilità modifiche

## Requisiti Sistema

### Minimi
- Python 3.9+
- PostgreSQL 12+
- 4GB RAM
- 10GB spazio disco

### Consigliati
- Python 3.11
- PostgreSQL 14+
- 8GB RAM
- 20GB spazio disco
- SSD per database

## Funzionalità Principali

### Gestione Workforce (100% completo)
- ✅ Sistema presenze con QR code
- ✅ Gestione turni automatica
- ✅ Ferie/permessi con workflow approvazione
- ✅ Note spese multi-categoria
- ✅ Straordinari con moltiplicatori
- ✅ Messaggistica interna
- ✅ Dashboard analitiche

### Sistema ACI (100% completo)
- ✅ Upload Excel massivo ottimizzato  
- ✅ Filtri avanzati con caricamento lazy
- ✅ Gestione costi chilometrici
- ✅ Export Excel professionale
- ✅ Back office amministratore

### Sicurezza (100% completo)
- ✅ Autenticazione robusta
- ✅ CSRF protection
- ✅ SQL injection prevention
- ✅ XSS protection
- ✅ Session management sicuro

## Compatibilità

### Sistemi Operativi
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Ubuntu 18.04+ LTS
- ✅ Debian 10+
- ✅ CentOS 7+/RHEL 7+

### Browser
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### Database
- ✅ PostgreSQL 12, 13, 14, 15
- ✅ Connection pooling
- ✅ Backup/restore tools

## Installazione

### Automatica (Consigliata)
```bash
# Linux/macOS
./install.sh

# Windows  
install.bat
```

### Manuale
Consultare `INSTALLATION_GUIDE_LOCAL.md` per setup dettagliato.

## Storia Versioni

### v2.0.3 (31 Luglio 2025)
- Ottimizzazioni performance ACI tables
- Upload Excel batch processing
- Bug fix timeout file grandi

### v2.0.2 (30 Luglio 2025)  
- Sistema export Excel unificato
- Dashboard team ottimizzata
- Correzioni overlay caricamento

### v2.0.1 (29 Luglio 2025)
- Sistema messaggistica completo
- Widget dashboard personalizzabili
- UI sidebar modernizzata

### v2.0.0 (25 Luglio 2025)
- Rilascio maggiore sistema completo
- 30+ permessi granulari
- Sistema multi-sede dinamico
- ACI back office integrato

### v1.x (Luglio 2025)
- Versioni sviluppo NS12
- Migrazione a Workly Platform
- Implementazione funzionalità base

## Piani Futuri

### v2.1.0 (Roadmap Q3 2025)
- [ ] API REST completa
- [ ] App mobile companion
- [ ] Notifiche push
- [ ] Integrazione LDAP/AD

### v2.2.0 (Roadmap Q4 2025)
- [ ] Machine learning presenze
- [ ] Analytics predittive
- [ ] Dashboard executive
- [ ] Multi-tenant architecture

## Supporto

### Documentazione
- `README_INSTALLATION.md` - Guida installazione rapida
- `INSTALLATION_GUIDE_LOCAL.md` - Setup completo
- `FUNCTIONALITY_DESCRIPTION.md` - Descrizione funzionalità

### File Log
- `logs/workly.log` - Log applicazione
- `logs/error.log` - Log errori
- `logs/access.log` - Log accessi

### Community
- Issues GitHub per bug report
- Documentazione wiki online
- Forum supporto tecnico

---

**© 2025 Workly Platform Team**  
**Licenza**: Uso Locale e Sviluppo  
**Supporto**: Documentazione inclusa nel pacchetto
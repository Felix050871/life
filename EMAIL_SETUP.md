# 📧 Configurazione Sistema Email - Life

## Overview
Il sistema email è ora completamente implementato e invia notifiche automatiche per:
- ✅ Approvazione richieste ferie/permessi
- ❌ Rifiuto richieste ferie/permessi  
- 🔒 Reset password
- 📊 Approvazione/Rifiuto straordinari

## Configurazione SMTP

### 1. Variabili di Ambiente Necessarie

Aggiungi queste variabili nei **Secrets** di Replit:

```bash
MAIL_SERVER=smtp.gmail.com              # Server SMTP (esempio Gmail)
MAIL_PORT=587                           # Porta SMTP (587 per TLS)
MAIL_USE_TLS=True                       # Usa TLS per sicurezza
MAIL_USERNAME=tuo-email@gmail.com       # Email mittente
MAIL_PASSWORD=tua-app-password          # Password applicazione (NON la password email)
MAIL_DEFAULT_SENDER=noreply@life.com  # OPZIONALE: Email mittente visualizzata
```

**Nota importante:** `MAIL_DEFAULT_SENDER` è opzionale. Se non configurato, il sistema userà automaticamente `MAIL_USERNAME` come mittente.

### 2. Provider SMTP Consigliati

#### **Gmail** (Gratis, max 500 email/giorno)
```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tuo-email@gmail.com
MAIL_PASSWORD=[App Password generata da Google]
```

**Come ottenere App Password Google:**
1. Vai su https://myaccount.google.com/security
2. Abilita "Verifica in 2 passaggi"
3. Cerca "Password per le app"
4. Genera una nuova password per "Mail" e "Windows Computer"
5. Usa quella password in `MAIL_PASSWORD`

#### **SendGrid** (Professionale, 100 email/giorno gratis)
```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=[Email verificata su SendGrid]
MAIL_PASSWORD=[SendGrid API Key]
```

**⚠️ IMPORTANTE per SendGrid:**
1. Vai su https://app.sendgrid.com/settings/sender_auth/senders
2. Verifica un'email mittente (Sender Identity)
3. Usa l'email verificata in `MAIL_USERNAME`
4. Se non verifichi un'email, riceverai errore 550

**Per usare "apikey" come username:**
- Se usi `MAIL_USERNAME=apikey`, devi impostare `MAIL_DEFAULT_SENDER` con un'email verificata su SendGrid

#### **Mailgun** (Professionale, flessibile)
```bash
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=[Mailgun Username]
MAIL_PASSWORD=[Mailgun Password]
```

#### **Office 365/Outlook**
```bash
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tuo-email@outlook.com
MAIL_PASSWORD=[Password Outlook]
```

### 3. Configurazione su Replit

1. **Apri il pannello Secrets:**
   - Clicca sull'icona 🔒 "Secrets" nella sidebar di Replit
   - Oppure cerca "Secrets" nella barra di ricerca

2. **Aggiungi ogni variabile:**
   - Key: `MAIL_SERVER`
   - Value: `smtp.gmail.com` (esempio)
   - Clicca "Add new secret"
   
3. **Ripeti per tutte le variabili** sopra elencate

4. **Riavvia l'applicazione** dopo aver aggiunto tutti i secrets

### 4. Test del Sistema Email

Per testare se le email funzionano:

1. **Reset Password:**
   - Vai su `/forgot_password`
   - Inserisci un'email utente esistente
   - Controlla la casella email

2. **Approvazione Richiesta:**
   - Crea una richiesta ferie/permesso
   - Approvala come manager
   - L'utente riceverà email di notifica

### 5. Troubleshooting

#### Email non arrivano
```bash
# Verifica secrets configurati
echo $MAIL_SERVER
echo $MAIL_PORT
echo $MAIL_USERNAME

# Controlla logs applicazione per errori
# I logs mostreranno "Errore invio email: ..." se qualcosa va male
```

#### Errore "Authentication failed"
- Gmail: assicurati di usare App Password, non la password normale
- Verifica username/password corretti
- Controlla che l'account mittente non abbia 2FA senza App Password

#### Email in spam
- Configura SPF/DKIM sul tuo dominio (avanzato)
- Usa un servizio professionale come SendGrid
- Aggiungi mittente alla whitelist del destinatario

### 6. Modalità Sviluppo (Senza SMTP)

Se non configuri le credenziali SMTP:
- ❌ Le email NON vengono inviate
- ✅ L'applicazione continua a funzionare normalmente
- 📋 I link reset password vengono mostrati direttamente nel flash message
- 🖨️ Gli errori email vengono loggati in console

### 7. Personalizzazione Email

Per modificare i template email, edita `email_utils.py`:
- `send_leave_approval_email()` - Template approvazione
- `send_leave_rejection_email()` - Template rifiuto
- `send_password_reset_email()` - Template reset password

Ogni funzione supporta:
- `body_text` - Versione testo semplice
- `body_html` - Versione HTML con stili

## File Implementati

- ✅ `email_utils.py` - Funzioni invio email
- ✅ `app.py` - Inizializzazione Flask-Mail
- ✅ `config.py` - Configurazioni SMTP
- ✅ `blueprints/leave.py` - Notifiche richieste
- ✅ `blueprints/auth.py` - Reset password
- ✅ `requirements.txt` - Flask-Mail aggiunto

## Stato Implementazione

✅ Sistema completo e funzionante
✅ Fallback graceful se SMTP non configurato
✅ Email HTML responsive con template professionale
✅ Logging errori per debug

**Prossimi passi:** Configura i secrets SMTP e testa!

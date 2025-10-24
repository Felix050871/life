#!/usr/bin/env python3
"""
Script per popolare il database con le mansioni standard estratte dal file Excel.
Popola le mansioni per tutte le aziende nel sistema.

Uso: python populate_mansioni.py
"""

from app import app, db
from models import Mansione, Company
from datetime import datetime

# Lista delle 37 mansioni estratte dal file Excel DEFINITIVO (colonna 9)
MANSIONI_STANDARD = [
    "Addetto Manutenzione",
    "Addetto Stampa",
    "Addetto Ufficio Tecnico",
    "Amministratore Delegato",
    "Amministratore Unico",
    "Analista Programmatore",
    "Assistente Tecnico",
    "Capo Area",
    "Capo Cantiere",
    "Capo Reparto",
    "Capo Squadra",
    "Carpentiere",
    "Centralinista",
    "Chief Technical Officer",
    "Consulente",
    "Direttore",
    "Direttore Generale",
    "Direttore Tecnico",
    "Elettricista",
    "Impiegato Amministrativo",
    "Impiegato Commerciale",
    "Impiegato Tecnico",
    "Installatore",
    "Operaio",
    "Operaio Generico",
    "Operaio Qualificato",
    "Operaio Specializzato",
    "Operatore",
    "Presidente",
    "Project Manager",
    "Responsabile Amministrativo",
    "Responsabile Commerciale",
    "Responsabile Marketing",
    "Responsabile Qualità",
    "Responsabile Tecnico",
    "Stagista",
    "Tecnico"
]

def populate_mansioni():
    """Popola le mansioni per tutte le aziende"""
    
    with app.app_context():
        # Ottieni tutte le aziende
        companies = Company.query.all()
        
        if not companies:
            print("⚠️  Nessuna azienda trovata nel database")
            return
        
        print(f"📊 Trovate {len(companies)} aziende")
        print(f"📋 Mansioni da creare: {len(MANSIONI_STANDARD)}")
        print()
        
        total_created = 0
        total_skipped = 0
        
        for company in companies:
            print(f"🏢 Azienda: {company.name} (ID: {company.id})")
            
            created_count = 0
            skipped_count = 0
            
            for mansione_nome in sorted(MANSIONI_STANDARD):
                # Verifica se la mansione esiste già per questa azienda
                existing = Mansione.query.filter_by(
                    company_id=company.id,
                    nome=mansione_nome
                ).first()
                
                if existing:
                    skipped_count += 1
                    total_skipped += 1
                else:
                    # Crea nuova mansione
                    mansione = Mansione(
                        company_id=company.id,
                        nome=mansione_nome,
                        active=True,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.session.add(mansione)
                    created_count += 1
                    total_created += 1
            
            # Commit per questa azienda
            db.session.commit()
            
            print(f"   ✅ Create: {created_count}")
            print(f"   ⏭️  Saltate (già esistenti): {skipped_count}")
            print()
        
        print("=" * 60)
        print(f"✅ COMPLETATO!")
        print(f"   Totale mansioni create: {total_created}")
        print(f"   Totale mansioni saltate: {total_skipped}")
        print(f"   Aziende processate: {len(companies)}")
        print("=" * 60)

if __name__ == '__main__':
    print("=" * 60)
    print("POPOLAMENTO MANSIONI STANDARD")
    print("=" * 60)
    print()
    
    try:
        populate_mansioni()
    except Exception as e:
        print(f"❌ ERRORE: {str(e)}")
        import traceback
        traceback.print_exc()

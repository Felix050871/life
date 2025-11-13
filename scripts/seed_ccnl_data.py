#!/usr/bin/env python3
"""
Seed script per popolare le tabelle CCNL con dati standard italiani.
Questo script è idempotente e può essere eseguito più volte senza duplicare dati.

Usage:
    python scripts/seed_ccnl_data.py --company-id 1
    python scripts/seed_ccnl_data.py --all-companies
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Company, CCNLContract, CCNLQualification, CCNLLevel

# Dati CCNL italiani standard
CCNL_DATA = {
    "Commercio": {
        "descrizione": "Contratto Collettivo Nazionale del Terziario, della Distribuzione e dei Servizi",
        "qualifiche": {
            "Quadro": {
                "descrizione": "Personale con funzioni di coordinamento e supervisione",
                "livelli": [
                    {"codice": "1°", "descrizione": "Quadro primo livello"},
                    {"codice": "2°", "descrizione": "Quadro secondo livello"},
                ]
            },
            "Impiegato": {
                "descrizione": "Personale amministrativo e di concetto",
                "livelli": [
                    {"codice": "1°", "descrizione": "Impiegato primo livello"},
                    {"codice": "2°", "descrizione": "Impiegato secondo livello"},
                    {"codice": "3°", "descrizione": "Impiegato terzo livello"},
                    {"codice": "4°", "descrizione": "Impiegato quarto livello"},
                    {"codice": "5°", "descrizione": "Impiegato quinto livello"},
                    {"codice": "6°", "descrizione": "Impiegato sesto livello"},
                    {"codice": "7°", "descrizione": "Impiegato settimo livello"},
                ]
            },
            "Operaio": {
                "descrizione": "Personale operativo",
                "livelli": [
                    {"codice": "1°", "descrizione": "Operaio primo livello - specializzato"},
                    {"codice": "2°", "descrizione": "Operaio secondo livello - qualificato"},
                    {"codice": "3°", "descrizione": "Operaio terzo livello"},
                    {"codice": "4°", "descrizione": "Operaio quarto livello"},
                    {"codice": "5°", "descrizione": "Operaio quinto livello"},
                    {"codice": "6°", "descrizione": "Operaio sesto livello"},
                    {"codice": "7°", "descrizione": "Operaio settimo livello"},
                ]
            }
        }
    },
    "Metalmeccanici": {
        "descrizione": "Contratto Collettivo Nazionale Metalmeccanici Industria",
        "qualifiche": {
            "Quadro": {
                "descrizione": "Quadri con funzioni direttive",
                "livelli": [
                    {"codice": "1", "descrizione": "Quadro livello 1"},
                    {"codice": "2", "descrizione": "Quadro livello 2"},
                    {"codice": "3", "descrizione": "Quadro livello 3"},
                    {"codice": "4", "descrizione": "Quadro livello 4"},
                    {"codice": "5", "descrizione": "Quadro livello 5"},
                    {"codice": "6", "descrizione": "Quadro livello 6"},
                    {"codice": "7", "descrizione": "Quadro livello 7"},
                    {"codice": "8", "descrizione": "Quadro livello 8"},
                ]
            },
            "Impiegato": {
                "descrizione": "Impiegati tecnici e amministrativi",
                "livelli": [
                    {"codice": "1", "descrizione": "Impiegato livello 1 - concetto elevato"},
                    {"codice": "2", "descrizione": "Impiegato livello 2 - concetto"},
                    {"codice": "3", "descrizione": "Impiegato livello 3 - d'ordine"},
                    {"codice": "4", "descrizione": "Impiegato livello 4"},
                    {"codice": "5", "descrizione": "Impiegato livello 5"},
                    {"codice": "6", "descrizione": "Impiegato livello 6"},
                    {"codice": "7", "descrizione": "Impiegato livello 7"},
                    {"codice": "8", "descrizione": "Impiegato livello 8"},
                    {"codice": "9", "descrizione": "Impiegato livello 9"},
                ]
            },
            "Operaio": {
                "descrizione": "Operai produzione",
                "livelli": [
                    {"codice": "1", "descrizione": "Operaio livello 1 - specializzato"},
                    {"codice": "2", "descrizione": "Operaio livello 2 - specializzato"},
                    {"codice": "3", "descrizione": "Operaio livello 3 - qualificato"},
                    {"codice": "4", "descrizione": "Operaio livello 4 - qualificato"},
                    {"codice": "5", "descrizione": "Operaio livello 5 - comune"},
                    {"codice": "6", "descrizione": "Operaio livello 6 - comune"},
                    {"codice": "7", "descrizione": "Operaio livello 7"},
                    {"codice": "8", "descrizione": "Operaio livello 8"},
                    {"codice": "9", "descrizione": "Operaio livello 9"},
                ]
            }
        }
    },
    "Terziario Distribuzione e Servizi": {
        "descrizione": "CCNL per i dipendenti da aziende del terziario, della distribuzione e dei servizi",
        "qualifiche": {
            "Quadro": {
                "descrizione": "Quadri",
                "livelli": [
                    {"codice": "Q1", "descrizione": "Quadro livello 1"},
                    {"codice": "Q2", "descrizione": "Quadro livello 2"},
                    {"codice": "Q3", "descrizione": "Quadro livello 3"},
                    {"codice": "Q4", "descrizione": "Quadro livello 4"},
                ]
            },
            "Impiegato": {
                "descrizione": "Impiegati",
                "livelli": [
                    {"codice": "1", "descrizione": "Impiegato 1° livello super"},
                    {"codice": "2", "descrizione": "Impiegato 2° livello"},
                    {"codice": "3", "descrizione": "Impiegato 3° livello"},
                    {"codice": "4", "descrizione": "Impiegato 4° livello"},
                    {"codice": "5", "descrizione": "Impiegato 5° livello"},
                    {"codice": "6", "descrizione": "Impiegato 6° livello"},
                    {"codice": "7", "descrizione": "Impiegato 7° livello"},
                ]
            },
            "Operaio": {
                "descrizione": "Operai",
                "livelli": [
                    {"codice": "1", "descrizione": "Operaio 1° livello"},
                    {"codice": "2", "descrizione": "Operaio 2° livello"},
                    {"codice": "3", "descrizione": "Operaio 3° livello"},
                ]
            }
        }
    }
}


def seed_ccnl_for_company(company_id: int, dry_run: bool = False):
    """Popola i dati CCNL per una specifica azienda"""
    
    company = db.session.get(Company, company_id)
    if not company:
        print(f"❌ Company ID {company_id} non trovata!")
        return False
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Seeding CCNL data for company: {company.name} (ID: {company_id})")
    print("=" * 80)
    
    stats = {"ccnl": 0, "qualifiche": 0, "livelli": 0, "skipped": 0}
    
    for ccnl_nome, ccnl_info in CCNL_DATA.items():
        # Check se CCNL esiste già
        existing_ccnl = CCNLContract.query.filter_by(
            company_id=company_id,
            nome=ccnl_nome
        ).first()
        
        if existing_ccnl:
            print(f"  ⏭  CCNL '{ccnl_nome}' già esistente (ID: {existing_ccnl.id})")
            ccnl = existing_ccnl
            stats["skipped"] += 1
        else:
            if not dry_run:
                ccnl = CCNLContract(
                    company_id=company_id,
                    nome=ccnl_nome,
                    descrizione=ccnl_info["descrizione"],
                    active=True
                )
                db.session.add(ccnl)
                db.session.flush()  # Get ID for relationships
                print(f"  ✓ Created CCNL: {ccnl_nome} (ID: {ccnl.id})")
                stats["ccnl"] += 1
            else:
                print(f"  [DRY] Would create CCNL: {ccnl_nome}")
                continue  # Skip qualifiche in dry run if CCNL doesn't exist
        
        # Process qualifiche
        for qual_nome, qual_info in ccnl_info["qualifiche"].items():
            existing_qual = CCNLQualification.query.filter_by(
                ccnl_id=ccnl.id,
                nome=qual_nome
            ).first()
            
            if existing_qual:
                print(f"    ⏭  Qualifica '{qual_nome}' già esistente")
                qualification = existing_qual
                stats["skipped"] += 1
            else:
                if not dry_run:
                    qualification = CCNLQualification(
                        ccnl_id=ccnl.id,
                        company_id=company_id,
                        nome=qual_nome,
                        descrizione=qual_info["descrizione"],
                        active=True
                    )
                    db.session.add(qualification)
                    db.session.flush()
                    print(f"    ✓ Created Qualifica: {qual_nome} (ID: {qualification.id})")
                    stats["qualifiche"] += 1
                else:
                    print(f"    [DRY] Would create Qualifica: {qual_nome}")
                    continue
            
            # Process livelli
            for livello_data in qual_info["livelli"]:
                existing_level = CCNLLevel.query.filter_by(
                    qualification_id=qualification.id,
                    codice=livello_data["codice"]
                ).first()
                
                if existing_level:
                    stats["skipped"] += 1
                else:
                    if not dry_run:
                        level = CCNLLevel(
                            qualification_id=qualification.id,
                            company_id=company_id,
                            codice=livello_data["codice"],
                            descrizione=livello_data["descrizione"],
                            active=True
                        )
                        db.session.add(level)
                        stats["livelli"] += 1
                    else:
                        print(f"      [DRY] Would create Level: {livello_data['codice']}")
    
    if not dry_run:
        db.session.commit()
        print("\n✅ Seeding completato con successo!")
    else:
        print("\n[DRY RUN] Nessuna modifica al database")
    
    print(f"\nStatistiche:")
    print(f"  - CCNL creati: {stats['ccnl']}")
    print(f"  - Qualifiche create: {stats['qualifiche']}")
    print(f"  - Livelli creati: {stats['livelli']}")
    print(f"  - Record già esistenti (skipped): {stats['skipped']}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Seed CCNL data for companies')
    parser.add_argument('--company-id', type=int, help='Specific company ID to seed')
    parser.add_argument('--all-companies', action='store_true', help='Seed all companies')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without making changes')
    
    args = parser.parse_args()
    
    if not args.company_id and not args.all_companies:
        parser.print_help()
        print("\n❌ Error: You must specify either --company-id or --all-companies")
        sys.exit(1)
    
    with app.app_context():
        if args.all_companies:
            companies = Company.query.all()
            print(f"Found {len(companies)} companies to seed")
            for company in companies:
                seed_ccnl_for_company(company.id, dry_run=args.dry_run)
        else:
            seed_ccnl_for_company(args.company_id, dry_run=args.dry_run)


if __name__ == '__main__':
    main()

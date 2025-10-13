#!/usr/bin/env python3
"""
Script di migrazione per il sistema multi-tenant.
Crea l'azienda default NS12 e associa tutti gli utenti e le sedi esistenti.
"""

from app import app, db
from models import Company, User, Sede
from datetime import datetime

def migrate_to_multitenant():
    """Migra il database al sistema multi-tenant"""
    
    with app.app_context():
        print("=== MIGRAZIONE AL SISTEMA MULTI-TENANT ===\n")
        
        # 1. Crea le tabelle se non esistono
        print("1. Creazione tabelle database...")
        db.create_all()
        print("   ✓ Tabelle create con successo\n")
        
        # 2. Verifica se esiste già l'azienda NS12
        ns12 = Company.query.filter_by(code='NS12').first()
        
        if ns12:
            print("2. Azienda NS12 già esistente")
            print(f"   - ID: {ns12.id}")
            print(f"   - Nome: {ns12.name}\n")
        else:
            # 3. Crea l'azienda default NS12
            print("2. Creazione azienda default NS12...")
            ns12 = Company(
                name='NS12 S.r.l.',
                code='NS12',
                description='Azienda principale - Creata automaticamente durante la migrazione al sistema multi-tenant',
                active=True
            )
            db.session.add(ns12)
            db.session.commit()
            print(f"   ✓ Azienda NS12 creata con ID: {ns12.id}\n")
        
        # 4. Associa tutti gli utenti esistenti a NS12
        print("3. Associazione utenti esistenti a NS12...")
        users_without_company = User.query.filter(
            (User.company_id == None) & (User.is_system_admin == False)
        ).all()
        
        if users_without_company:
            for user in users_without_company:
                user.company_id = ns12.id
                print(f"   - {user.username} ({user.get_full_name()}) → NS12")
            
            db.session.commit()
            print(f"   ✓ {len(users_without_company)} utenti associati a NS12\n")
        else:
            print("   - Tutti gli utenti sono già associati a un'azienda\n")
        
        # 5. Associa tutte le sedi esistenti a NS12
        print("4. Associazione sedi esistenti a NS12...")
        sedi_without_company = Sede.query.filter_by(company_id=None).all()
        
        if sedi_without_company:
            for sede in sedi_without_company:
                sede.company_id = ns12.id
                print(f"   - {sede.name} → NS12")
            
            db.session.commit()
            print(f"   ✓ {len(sedi_without_company)} sedi associate a NS12\n")
        else:
            print("   - Tutte le sedi sono già associate a un'azienda\n")
        
        # 6. Statistiche finali
        print("5. Statistiche finali:")
        total_companies = Company.query.count()
        total_users = User.query.filter_by(company_id=ns12.id).count()
        total_sedi = Sede.query.filter_by(company_id=ns12.id).count()
        system_admins = User.query.filter_by(is_system_admin=True).count()
        
        print(f"   - Aziende totali: {total_companies}")
        print(f"   - Utenti NS12: {total_users}")
        print(f"   - Sedi NS12: {total_sedi}")
        print(f"   - Amministratori di sistema: {system_admins}")
        
        print("\n=== MIGRAZIONE COMPLETATA CON SUCCESSO ===")
        print("\nIMPORTANTE:")
        print("1. L'azienda NS12 è stata creata come azienda principale")
        print("2. Tutti gli utenti e le sedi esistenti sono stati associati a NS12")
        print("3. Per creare un amministratore di sistema, esegui il comando:")
        print("   python create_system_admin.py")

if __name__ == '__main__':
    migrate_to_multitenant()

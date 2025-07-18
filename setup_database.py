#!/usr/bin/env python3
"""
Script per inizializzare il database di Workly con dati di base
"""
import os
import sys
from datetime import datetime, time
from werkzeug.security import generate_password_hash

# Aggiungi la directory workly al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Sede, WorkSchedule

def setup_database():
    """Inizializza il database con dati di base"""
    with app.app_context():
        print("Creazione tabelle database...")
        db.create_all()
        
        # Verifica se esistono già dati
        if User.query.first():
            print("Database già popolato, skip inizializzazione.")
            return
        
        print("Popolamento database con dati iniziali...")
        
        # Crea sedi di esempio
        sede_milano = Sede(
            name="Milano Centro",
            address="Via Roma 123, Milano",
            description="Sede principale Milano",
            active=True
        )
        
        sede_roma = Sede(
            name="Roma EUR",
            address="Via del Commercio 456, Roma",
            description="Sede Roma Eur",
            active=True
        )
        
        db.session.add_all([sede_milano, sede_roma])
        db.session.commit()
        
        # Crea orari di lavoro per le sedi
        orario_standard_mi = WorkSchedule(
            sede_id=sede_milano.id,
            name="Orario Standard",
            start_time=time(9, 0),
            end_time=time(18, 0),
            description="Orario lavorativo standard 9-18",
            active=True
        )
        
        orario_flessibile_mi = WorkSchedule(
            sede_id=sede_milano.id,
            name="Orario Flessibile",
            start_time=time(8, 30),
            end_time=time(17, 30),
            description="Orario flessibile 8:30-17:30",
            active=True
        )
        
        orario_standard_rm = WorkSchedule(
            sede_id=sede_roma.id,
            name="Orario Standard",
            start_time=time(9, 0),
            end_time=time(18, 0),
            description="Orario lavorativo standard 9-18",
            active=True
        )
        
        db.session.add_all([orario_standard_mi, orario_flessibile_mi, orario_standard_rm])
        db.session.commit()
        
        # Crea utenti di esempio
        admin_user = User(
            username="admin",
            email="admin@workly.com",
            password_hash=generate_password_hash("admin123"),
            role="Admin",
            first_name="Mario",
            last_name="Rossi",
            sede_id=sede_milano.id,
            active=True,
            part_time_percentage=100.0
        )
        
        responsabile_user = User(
            username="responsabile",
            email="responsabile@workly.com", 
            password_hash=generate_password_hash("resp123"),
            role="Responsabili",
            first_name="Giuseppe",
            last_name="Verdi",
            sede_id=sede_milano.id,
            active=True,
            part_time_percentage=100.0
        )
        
        sviluppatore_user = User(
            username="sviluppatore",
            email="dev@workly.com",
            password_hash=generate_password_hash("dev123"), 
            role="Sviluppatore",
            first_name="Luca",
            last_name="Bianchi",
            sede_id=sede_roma.id,
            active=True,
            part_time_percentage=100.0
        )
        
        operatore_user = User(
            username="operatore",
            email="op@workly.com",
            password_hash=generate_password_hash("op123"),
            role="Operatore", 
            first_name="Anna",
            last_name="Neri",
            sede_id=sede_milano.id,
            active=True,
            part_time_percentage=80.0  # Part-time
        )
        
        management_user = User(
            username="management",
            email="mgmt@workly.com",
            password_hash=generate_password_hash("mgmt123"),
            role="Management",
            first_name="Roberto",
            last_name="Ferrari",
            sede_id=None,  # Management non ha sede specifica
            active=True,
            part_time_percentage=100.0
        )
        
        db.session.add_all([admin_user, responsabile_user, sviluppatore_user, operatore_user, management_user])
        db.session.commit()
        
        print("Database inizializzato con successo!")
        print("\nUtenti creati:")
        print("- admin / admin123 (Admin)")
        print("- responsabile / resp123 (Responsabili)")
        print("- sviluppatore / dev123 (Sviluppatore)")
        print("- operatore / op123 (Operatore)")
        print("- management / mgmt123 (Management)")
        print("\nSedi create:")
        print("- Milano Centro")
        print("- Roma EUR")
        print("\nOrari di lavoro configurati per ogni sede")

if __name__ == '__main__':
    setup_database()
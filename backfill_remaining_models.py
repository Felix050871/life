#!/usr/bin/env python
"""
Backfill company_id for Intervention and ReperibilitaTemplate
"""

import sys
from app import db, app
from models import Intervention, ReperibilitaTemplate, User

def backfill_intervention():
    """Backfill Intervention.company_id from user"""
    print("\n=== Backfilling Intervention ===")
    records = Intervention.query.filter(Intervention.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            user = User.query.get(record.user_id)
            if user and user.company_id:
                record.company_id = user.company_id
                updated += 1
            else:
                print(f"  ⚠️  Intervention {record.id}: User {record.user_id} has no company_id")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating Intervention {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def backfill_reperibilita_template():
    """Backfill ReperibilitaTemplate.company_id from creator"""
    print("\n=== Backfilling ReperibilitaTemplate ===")
    records = ReperibilitaTemplate.query.filter(ReperibilitaTemplate.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            creator = User.query.get(record.created_by)
            if creator and creator.company_id:
                record.company_id = creator.company_id
                updated += 1
            else:
                print(f"  ⚠️  ReperibilitaTemplate {record.id}: Creator {record.created_by} has no company_id")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating ReperibilitaTemplate {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def main():
    force = '--force' in sys.argv
    
    print("=" * 70)
    print("  BACKFILL REMAINING MODELS: Intervention, ReperibilitaTemplate")
    print("=" * 70)
    
    if not force:
        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return
    else:
        print("🚀 FORCE MODE - Skipping confirmation")
    
    with app.app_context():
        total_updated = 0
        total_errors = 0
        
        try:
            # Run backfill functions
            funcs = [backfill_intervention, backfill_reperibilita_template]
            
            for func in funcs:
                updated, errors = func()
                total_updated += updated
                total_errors += errors
            
            print("\n" + "=" * 70)
            print(f"  SUMMARY: {total_updated} records updated, {total_errors} errors")
            print("=" * 70)
            
            db.session.commit()
            print("\n💾 Committing changes to database...")
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()

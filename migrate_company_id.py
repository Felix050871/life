#!/usr/bin/env python3
"""
Database Migration Script - Backfill company_id for Multi-Tenant Isolation
===========================================================================

This script backfills the company_id field for all existing records in tables
that were recently updated to support multi-tenant architecture.

Tables affected:
- WorkSchedule
- ACITable
- LeaveType
- OvertimeType
- OvertimeRequest
- MileageRequest
- ShiftTemplate
- PresidioCoverageTemplate
- ExpenseCategory
- ExpenseReport

Strategy:
1. For records with user relationships (created_by, employee_id, user_id):
   - Use user.company_id
2. For records with sede relationships:
   - Use sede.company_id  
3. For orphaned records:
   - Log warning and skip (to be handled manually)

Usage:
    python migrate_company_id.py [--dry-run]
"""

import sys
import os
from app import db, app
from models import (
    WorkSchedule, ACITable, LeaveType, OvertimeType, OvertimeRequest,
    MileageRequest, ShiftTemplate, PresidioCoverageTemplate, PresidioCoverage,
    ExpenseCategory, ExpenseReport, Holiday, User, Sede
)

def backfill_work_schedule():
    """Backfill WorkSchedule.company_id from Sede.company_id"""
    print("\n=== Backfilling WorkSchedule ===")
    records = WorkSchedule.query.filter(WorkSchedule.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            if record.sede_id:
                sede = Sede.query.get(record.sede_id)
                if sede and sede.company_id:
                    record.company_id = sede.company_id
                    updated += 1
                else:
                    print(f"  ⚠️  WorkSchedule {record.id}: Sede {record.sede_id} has no company_id")
                    errors += 1
            else:
                print(f"  ⚠️  WorkSchedule {record.id}: No sede_id")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating WorkSchedule {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def backfill_aci_table():
    """Backfill ACITable.company_id - assign to first company (shared resource)"""
    print("\n=== Backfilling ACITable ===")
    from models import Company
    records = ACITable.query.filter(ACITable.company_id == None).all()
    
    # Get first company as default (ACITable is often a shared resource)
    first_company = Company.query.first()
    if not first_company:
        print("  ⚠️  No companies found, skipping ACITable")
        return 0, len(records)
    
    updated = 0
    for record in records:
        record.company_id = first_company.id
        updated += 1
    
    print(f"  ℹ️  Assigned all {updated} ACITable records to company: {first_company.name}")
    return updated, 0

def backfill_leave_type():
    """Backfill LeaveType.company_id - assign to first company (shared resource)"""
    print("\n=== Backfilling LeaveType ===")
    from models import Company
    records = LeaveType.query.filter(LeaveType.company_id == None).all()
    
    first_company = Company.query.first()
    if not first_company:
        print("  ⚠️  No companies found, skipping LeaveType")
        return 0, len(records)
    
    updated = 0
    for record in records:
        record.company_id = first_company.id
        updated += 1
    
    print(f"  ℹ️  Assigned all {updated} LeaveType records to company: {first_company.name}")
    return updated, 0

def backfill_overtime_type():
    """Backfill OvertimeType.company_id - assign to first company"""
    print("\n=== Backfilling OvertimeType ===")
    from models import Company
    records = OvertimeType.query.filter(OvertimeType.company_id == None).all()
    
    first_company = Company.query.first()
    if not first_company:
        print("  ⚠️  No companies found, skipping OvertimeType")
        return 0, len(records)
    
    updated = 0
    for record in records:
        record.company_id = first_company.id
        updated += 1
    
    print(f"  ℹ️  Assigned all {updated} OvertimeType records to company: {first_company.name}")
    return updated, 0

def backfill_overtime_request():
    """Backfill OvertimeRequest.company_id from employee.company_id"""
    print("\n=== Backfilling OvertimeRequest ===")
    records = OvertimeRequest.query.filter(OvertimeRequest.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            employee = User.query.get(record.employee_id)
            if employee and employee.company_id:
                record.company_id = employee.company_id
                updated += 1
            else:
                print(f"  ⚠️  OvertimeRequest {record.id}: Employee {record.employee_id} has no company_id")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating OvertimeRequest {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def backfill_mileage_request():
    """Backfill MileageRequest.company_id from user.company_id"""
    print("\n=== Backfilling MileageRequest ===")
    records = MileageRequest.query.filter(MileageRequest.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            user = User.query.get(record.user_id)
            if user and user.company_id:
                record.company_id = user.company_id
                updated += 1
            else:
                print(f"  ⚠️  MileageRequest {record.id}: User {record.user_id} has no company_id")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating MileageRequest {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def backfill_shift_template():
    """Backfill ShiftTemplate.company_id from creator.company_id"""
    print("\n=== Backfilling ShiftTemplate ===")
    records = ShiftTemplate.query.filter(ShiftTemplate.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            creator = User.query.get(record.created_by)
            if creator and creator.company_id:
                record.company_id = creator.company_id
                updated += 1
            else:
                print(f"  ⚠️  ShiftTemplate {record.id}: Creator {record.created_by} has no company_id")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating ShiftTemplate {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def backfill_presidio_coverage_template():
    """Backfill PresidioCoverageTemplate.company_id from sede or creator"""
    print("\n=== Backfilling PresidioCoverageTemplate ===")
    records = PresidioCoverageTemplate.query.filter(PresidioCoverageTemplate.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            # Try sede first
            if record.sede_id:
                sede = Sede.query.get(record.sede_id)
                if sede and sede.company_id:
                    record.company_id = sede.company_id
                    updated += 1
                    continue
            
            # Fallback to creator
            creator = User.query.get(record.created_by)
            if creator and creator.company_id:
                record.company_id = creator.company_id
                updated += 1
            else:
                print(f"  ⚠️  PresidioCoverageTemplate {record.id}: No valid company_id source")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating PresidioCoverageTemplate {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def backfill_expense_category():
    """Backfill ExpenseCategory.company_id from creator.company_id"""
    print("\n=== Backfilling ExpenseCategory ===")
    records = ExpenseCategory.query.filter(ExpenseCategory.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            creator = User.query.get(record.created_by)
            if creator and creator.company_id:
                record.company_id = creator.company_id
                updated += 1
            else:
                print(f"  ⚠️  ExpenseCategory {record.id}: Creator {record.created_by} has no company_id")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating ExpenseCategory {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def backfill_expense_report():
    """Backfill ExpenseReport.company_id from employee.company_id"""
    print("\n=== Backfilling ExpenseReport ===")
    records = ExpenseReport.query.filter(ExpenseReport.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            employee = User.query.get(record.employee_id)
            if employee and employee.company_id:
                record.company_id = employee.company_id
                updated += 1
            else:
                print(f"  ⚠️  ExpenseReport {record.id}: Employee {record.employee_id} has no company_id")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating ExpenseReport {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def backfill_presidio_coverage():
    """Backfill PresidioCoverage.company_id from template or creator"""
    print("\n=== Backfilling PresidioCoverage ===")
    records = PresidioCoverage.query.filter(PresidioCoverage.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            # Try template first
            if record.template_id:
                template = PresidioCoverageTemplate.query.get(record.template_id)
                if template and template.company_id:
                    record.company_id = template.company_id
                    updated += 1
                    continue
            
            # Fallback to creator
            creator = User.query.get(record.created_by)
            if creator and creator.company_id:
                record.company_id = creator.company_id
                updated += 1
            else:
                print(f"  ⚠️  PresidioCoverage {record.id}: No valid company_id source")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating PresidioCoverage {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def backfill_holiday():
    """Backfill Holiday.company_id from sede or creator"""
    print("\n=== Backfilling Holiday ===")
    records = Holiday.query.filter(Holiday.company_id == None).all()
    updated = 0
    errors = 0
    
    for record in records:
        try:
            # Try sede first (if specified)
            if record.sede_id:
                sede = Sede.query.get(record.sede_id)
                if sede and sede.company_id:
                    record.company_id = sede.company_id
                    updated += 1
                    continue
            
            # Fallback to creator for national holidays
            creator = User.query.get(record.created_by)
            if creator and creator.company_id:
                record.company_id = creator.company_id
                updated += 1
            else:
                print(f"  ⚠️  Holiday {record.id}: No valid company_id source")
                errors += 1
        except Exception as e:
            print(f"  ❌ Error updating Holiday {record.id}: {e}")
            errors += 1
    
    print(f"  ✅ Updated: {updated}, Errors: {errors}")
    return updated, errors

def main():
    """Main migration execution"""
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv
    
    print("=" * 70)
    print("  MULTI-TENANT MIGRATION: Backfill company_id")
    print("=" * 70)
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be committed")
    else:
        print("\n⚠️  PRODUCTION MODE - Changes will be committed to database")
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
            # Run all backfill functions
            funcs = [
                backfill_work_schedule,
                backfill_aci_table,
                backfill_leave_type,
                backfill_overtime_type,
                backfill_overtime_request,
                backfill_mileage_request,
                backfill_shift_template,
                backfill_presidio_coverage_template,
                backfill_presidio_coverage,
                backfill_holiday,
                backfill_expense_category,
                backfill_expense_report
            ]
            
            for func in funcs:
                updated, errors = func()
                total_updated += updated
                total_errors += errors
            
            print("\n" + "=" * 70)
            print(f"  SUMMARY: {total_updated} records updated, {total_errors} errors")
            print("=" * 70)
            
            if dry_run:
                print("\n🔍 DRY RUN - Rolling back all changes")
                db.session.rollback()
            else:
                print("\n💾 Committing changes to database...")
                db.session.commit()
                print("✅ Migration completed successfully!")
                
        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    main()

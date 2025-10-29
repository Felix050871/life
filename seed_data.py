"""
Data seeding functions for automatic database initialization
"""
import logging
from app import db

logger = logging.getLogger(__name__)


def seed_leave_type_defaults():
    """
    Seeds default minimum_duration_hours values for common leave types.
    
    This function is called automatically at application startup to ensure
    that common leave types have appropriate minimum duration defaults.
    Safe to run multiple times - only updates rows where minimum_duration_hours is NULL.
    
    Defaults:
    - Ferie (FE): 8 hours (1 full day)
    - Malattia (MAL): 4 hours (half day)
    - Others: NULL (admin configurable)
    """
    try:
        from models import LeaveType
        
        # Find Ferie (vacation) types and set 8 hours if not already set
        ferie_types = LeaveType.query.filter(
            db.or_(
                LeaveType.code == 'FE',
                LeaveType.name.ilike('%ferie%')
            ),
            LeaveType.minimum_duration_hours.is_(None)
        ).all()
        
        for leave_type in ferie_types:
            leave_type.minimum_duration_hours = 8.0
            logger.info(f"Setting default minimum duration for Ferie: {leave_type.name} ({leave_type.code})")
        
        # Find Malattia (sick leave) types and set 4 hours if not already set
        malattia_types = LeaveType.query.filter(
            db.or_(
                LeaveType.code == 'MAL',
                LeaveType.name.ilike('%malattia%')
            ),
            LeaveType.minimum_duration_hours.is_(None)
        ).all()
        
        for leave_type in malattia_types:
            leave_type.minimum_duration_hours = 4.0
            logger.info(f"Setting default minimum duration for Malattia: {leave_type.name} ({leave_type.code})")
        
        # Commit changes if any were made
        if ferie_types or malattia_types:
            db.session.commit()
            logger.info(f"Seeded default minimum durations: {len(ferie_types)} Ferie, {len(malattia_types)} Malattia")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding leave type defaults: {e}")


def seed_all():
    """
    Master seeding function that calls all individual seed functions.
    Safe to run multiple times - designed to be idempotent.
    """
    logger.info("Starting data seeding...")
    seed_leave_type_defaults()
    logger.info("Data seeding complete")

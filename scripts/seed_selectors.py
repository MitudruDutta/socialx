#!/usr/bin/env python3
"""
Seed default Twitter selectors into the database.
Run this after initial setup to enable DB-based selector management.
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timezone
from app.storage import SessionLocal, init_db
from app.storage.models import TwitterSelector
from app.automation.selectors import TwitterSelectors

def seed_selectors():
    """Seed default selectors into database"""
    try:
        init_db()
        
        if not hasattr(TwitterSelectors, 'DEFAULT_SELECTORS'):
            print("❌ TwitterSelectors missing DEFAULT_SELECTORS")
            return

        defaults = TwitterSelectors.DEFAULT_SELECTORS
        
        with SessionLocal() as db:
            added = 0
            updated = 0
            
            for name, selector in defaults.items():
                existing = db.query(TwitterSelector).filter(
                    TwitterSelector.element_name == name
                ).first()
                
                if existing:
                    # Only update if marked invalid
                    if existing.validation_status == "invalid":
                        existing.selector = selector
                        existing.validation_status = "unknown"
                        existing.failure_count = 0
                        updated += 1
                else:
                    db.add(TwitterSelector(
                        element_name=name,
                        selector=selector,
                        selector_type="css",
                        validation_status="unknown",
                        last_validated=datetime.now(timezone.utc)
                    ))
                    added += 1
            
            db.commit()
            print(f"✓ Seeded selectors: {added} added, {updated} updated")
            
    except Exception as e:
        print(f"❌ Failed to seed selectors: {e}")
        sys.exit(1)


if __name__ == "__main__":
    seed_selectors()

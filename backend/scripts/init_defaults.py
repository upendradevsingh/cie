#!/usr/bin/env python3
"""Initialize default data for SalesLens tenants.

This script creates default prompt templates and other necessary data
for tenants that don't have them. Should be run after tenant creation
or as part of application initialization.

Usage:
    python scripts/init_defaults.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.tenant import Tenant
from app.models.prompt_template import PromptTemplate
from app.config import settings


def init_prompt_templates(db, tenant: Tenant) -> bool:
    """Create default prompt template for a tenant if none exists.

    Args:
        db: Database session
        tenant: Tenant to create template for

    Returns:
        True if template was created, False if already exists
    """
    # Check if tenant already has an active prompt template
    existing = db.query(PromptTemplate).filter_by(
        tenant_id=tenant.id,
        is_active=True
    ).first()

    if existing:
        return False

    # Read the default prompt template
    prompt_file = Path(__file__).parent.parent / "app" / "prompts" / "call_analysis.jinja2"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Default prompt template not found at {prompt_file}")

    with open(prompt_file, 'r') as f:
        template_content = f.read()

    # Create default prompt template
    prompt_template = PromptTemplate(
        tenant_id=tenant.id,
        name="Default Call Analysis",
        description="Default template for analyzing sales calls with quality scoring, lead intelligence, and keyword extraction",
        template_content=template_content,
        version=1,
        is_active=True
    )

    db.add(prompt_template)
    return True


def main():
    """Initialize default data for all tenants."""
    print("SalesLens - Initializing default data")
    print("=" * 60)

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Get all active tenants
        tenants = db.query(Tenant).filter_by(is_active=True).all()

        if not tenants:
            print("⚠️  No active tenants found")
            return

        print(f"Found {len(tenants)} active tenant(s)\n")

        created_count = 0

        for tenant in tenants:
            print(f"Processing tenant: {tenant.name}")

            # Initialize prompt templates
            if init_prompt_templates(db, tenant):
                print(f"  ✓ Created default prompt template")
                created_count += 1
            else:
                print(f"  ✓ Prompt template already exists")

        db.commit()

        print("\n" + "=" * 60)
        print(f"✅ Initialization complete!")
        print(f"   Created {created_count} prompt template(s)")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Migration script to fix existing databases where first admin user is not a publisher.
This script should be run once to ensure any existing first admin user also has publisher status.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app
from neo_bloggy.database import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def migrate_admin_publisher_status():
    """Migrate existing admin users to also have publisher status."""
    logger.info(
        "Starting migration to ensure admin users also have publisher status..."
    )

    try:
        with app.app_context():
            db = get_db()

            # Find all users who are admin but not publisher
            admin_not_publisher = list(
                db.users.find(
                    {
                        "is_admin": True,
                        "is_publisher": {
                            "$ne": True
                        },  # Either False or doesn't exist
                    }
                )
            )

            if not admin_not_publisher:
                logger.info(
                    "No users found that need migration (all admins are already publishers)."
                )
                return

            logger.info(
                "Found %d admin users who are not publishers. Updating...",
                len(admin_not_publisher),
            )

            for user in admin_not_publisher:
                logger.info("  - Updating user: %s", user["name"])
                db.users.update_one(
                    {"_id": user["_id"]}, {"$set": {"is_publisher": True}}
                )

            logger.info(
                "Successfully updated %d users to have publisher status.",
                len(admin_not_publisher),
            )

            # Verify the changes
            still_not_publisher = list(
                db.users.find({"is_admin": True, "is_publisher": {"$ne": True}})
            )

            if still_not_publisher:
                logger.warning(
                    "%d admin users still don't have publisher status.",
                    len(still_not_publisher),
                )
            else:
                logger.info("All admin users now have publisher status.")

    except Exception as e:
        logger.error("Migration failed with error: %s", e, exc_info=True)


if __name__ == "__main__":
    migrate_admin_publisher_status()

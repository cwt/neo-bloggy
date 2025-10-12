#!/usr/bin/env python3
"""
Migration script to fix existing databases where first admin user is not a publisher.
This script should be run once to ensure any existing first admin user also has publisher status.
"""
import sys
import os

sys.path.insert(0, "/home/cwt/Projects/neo-bloggy")

from app import app, get_db


def migrate_admin_publisher_status():
    """Migrate existing admin users to also have publisher status."""
    print(
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
                print(
                    "✅ No users found that need migration (all admins are already publishers)."
                )
                return

            print(
                f"Found {len(admin_not_publisher)} admin users who are not publishers. Updating..."
            )

            for user in admin_not_publisher:
                print(f"  - Updating user: {user['name']}")
                db.users.update_one(
                    {"_id": user["_id"]}, {"$set": {"is_publisher": True}}
                )

            print(
                f"✅ Successfully updated {len(admin_not_publisher)} users to have publisher status."
            )

            # Verify the changes
            still_not_publisher = list(
                db.users.find({"is_admin": True, "is_publisher": {"$ne": True}})
            )

            if still_not_publisher:
                print(
                    f"⚠️  Warning: {len(still_not_publisher)} admin users still don't have publisher status."
                )
            else:
                print("✅ All admin users now have publisher status.")

    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    migrate_admin_publisher_status()

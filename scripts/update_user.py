#!/usr/bin/env python3
"""
User Management Script for Neo Bloggy

This script allows administrators to manage users from the command line:
- Enable/disable users
- Promote/demote admin status
- List all users
- Show user details

Usage:
    python update_user.py --list
    python update_user.py --email user@example.com --enable
    python update_user.py --email user@example.com --disable
    python update_user.py --email user@example.com --make-admin
    python update_user.py --email user@example.com --remove-admin
    python update_user.py --email user@example.com --enable --make-admin
"""

import argparse
import logging
import neosqlite
import os
import sys
import tomllib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_id_for_query(id_value):
    """Convert an ID value for database query, handling both integer and ObjectId formats.

    For maximum compatibility:
    - New documents have ObjectId in _id field
    - Old documents may still have integer _id until updated
    - Returns appropriate format based on NeoSQLite requirements
    """
    try:
        # Try to parse as integer for backward compatibility
        int_id = int(id_value)
        # Return integer for integer IDs
        return int_id
    except (ValueError, TypeError):
        # If it's not an integer, it might already be an ObjectId hex string
        # Return string representation for parameter binding compatibility
        try:
            import neosqlite

            # Try to create an ObjectId from the value to validate it
            object_id = neosqlite.objectid.ObjectId(id_value)
            # Return string representation for broader compatibility
            return str(object_id)
        except Exception:
            # If all attempts fail, return the original value
            return id_value


def load_config():
    """Load configuration from file, with support for custom path via environment variable."""
    # Check for custom config path in environment variable
    config_path = os.environ.get("NEO_BLOGGY_CONFIG_PATH")
    if not config_path:
        # Default to config.toml in the parent directory
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config.toml"
        )

    config = {}
    if os.path.exists(config_path):
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    return config


# Load configuration
config = load_config()

# Database configuration - use the same path as the main app
DB_PATH = config.get("database", {}).get("db_path", "neo-bloggy.db")


def get_all_users():
    """Get all users from the database."""
    try:
        db = neosqlite.Connection(DB_PATH)
        users = list(db.users.find())
        return users
    except Exception as e:
        logger.error("Error retrieving users: %s", e)
        return []


def get_user_by_email(email):
    """Get a user by email address."""
    try:
        db = neosqlite.Connection(DB_PATH)
        user = db.users.find_one({"email": email})
        return user
    except Exception as e:
        logger.error("Error retrieving user: %s", e)
        return None


def update_user_status(email, is_active=None, is_admin=None):
    """Update user status (active/inactive) and/or admin status."""
    try:
        db = neosqlite.Connection(DB_PATH)

        # Find the user by email
        user = db.users.find_one({"email": email})

        if not user:
            logger.error("User with email %s not found.", email)
            return False

        # Prepare update data
        update_data = {}
        if is_active is not None:
            update_data["is_active"] = is_active
        if is_admin is not None:
            update_data["is_admin"] = is_admin

        # Update the user
        db.users.update_one({"_id": user["_id"]}, {"$set": update_data})

        # Create status messages
        status_msgs = []
        if is_active is not None:
            status_msgs.append("enabled" if is_active else "disabled")
        if is_admin is not None:
            status_msgs.append(
                "promoted to admin" if is_admin else "demoted from admin"
            )

        action = " and ".join(status_msgs) if status_msgs else "updated"
        logger.info("User %s (%s) has been %s.", user["name"], email, action)

        # Show current status
        updated_user = db.users.find_one({"_id": user["_id"]})
        logger.info(
            "Current status: is_active=%s, is_admin=%s",
            updated_user.get("is_active", True),
            updated_user.get("is_admin", False),
        )
        return True

    except Exception as e:
        logger.error("Error updating user: %s", e)
        return False


def list_users():
    """List all users with their status."""
    try:
        users = get_all_users()
        if not users:
            logger.warning("No users found in the database.")
            return

        logger.info("Users in the database:")
        logger.info("-" * 80)
        logger.info(
            "%-25s %-30s %-10s %-10s", "Name", "Email", "Status", "Admin"
        )
        logger.info("-" * 80)

        for user in users:
            status = "Active" if user.get("is_active", True) else "Disabled"
            admin = "Yes" if user.get("is_admin", False) else "No"
            logger.info(
                "%-25s %-30s %-10s %-10s",
                user.get("name", "N/A"),
                user.get("email", "N/A"),
                status,
                admin,
            )

    except Exception as e:
        logger.error("Error listing users: %s", e)


def show_user_details(email):
    """Show detailed information about a specific user."""
    try:
        user = get_user_by_email(email)
        if not user:
            logger.error("User with email %s not found.", email)
            return

        logger.info("User Details for %s:", email)
        logger.info("-" * 40)
        logger.info("Name: %s", user.get("name", "N/A"))
        logger.info("Email: %s", user.get("email", "N/A"))
        logger.info("Active: %s", user.get("is_active", True))
        logger.info("Admin: %s", user.get("is_admin", False))
        logger.info(
            "Security Question: %s", user.get("security_question", "N/A")
        )
        logger.info("User ID: %s", user.get("_id", "N/A"))

    except Exception as e:
        logger.error("Error showing user details: %s", e)


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Manage Neo Bloggy users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--email", "-e", help="Email address of the user to manage"
    )

    parser.add_argument(
        "--list", "-l", action="store_true", help="List all users"
    )

    parser.add_argument(
        "--details",
        "-d",
        action="store_true",
        help="Show detailed information about a user (requires --email)",
    )

    parser.add_argument(
        "--enable", action="store_true", help="Enable the user account"
    )

    parser.add_argument(
        "--disable", action="store_true", help="Disable the user account"
    )

    parser.add_argument(
        "--make-admin",
        "-a",
        action="store_true",
        help="Promote user to administrator",
    )

    parser.add_argument(
        "--remove-admin",
        "-r",
        action="store_true",
        help="Demote user from administrator",
    )

    # Check if database exists
    if not os.path.exists(DB_PATH):
        logger.error("Database file '%s' not found.", DB_PATH)
        logger.error("Please run this script from the project directory.")
        sys.exit(1)

    args = parser.parse_args()

    # Handle list option
    if args.list:
        list_users()
        return

    # Handle details option
    if args.details:
        if not args.email:
            logger.error("--email is required with --details")
            sys.exit(1)
        show_user_details(args.email)
        return

    # Handle user management
    if args.email:
        # Determine what actions to take
        is_active = None
        is_admin = None

        if args.enable and args.disable:
            logger.error("Cannot use both --enable and --disable")
            sys.exit(1)

        if args.make_admin and args.remove_admin:
            logger.error("Cannot use both --make-admin and --remove-admin")
            sys.exit(1)

        if args.enable:
            is_active = True
        elif args.disable:
            is_active = False

        if args.make_admin:
            is_admin = True
        elif args.remove_admin:
            is_admin = False

        # If no actions specified, show help
        if is_active is None and is_admin is None:
            logger.error(
                "No action specified. Use --enable, --disable, --make-admin, or --remove-admin"
            )
            parser.print_help()
            sys.exit(1)

        update_user_status(args.email, is_active, is_admin)
    else:
        # No arguments provided, show help
        parser.print_help()


if __name__ == "__main__":
    main()

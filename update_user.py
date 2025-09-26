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

import neosqlite
import os
import argparse
import sys
import tomllib


def get_id_for_query(id_value):
    """Convert an ID value for database query, handling both integer and ObjectId formats.
    
    For NeoSQLite v1.1.0 compatibility:
    - New documents have ObjectId in _id field
    - Old documents may still have integer _id until updated
    - Also check the 'id' field which always contains the integer ID for all documents
    """
    try:
        # Try to parse as integer for backward compatibility
        int_id = int(id_value)
        # For NeoSQLite v1.1.0, we can query either the integer ID in 'id' field
        # or attempt to use ObjectId format in '_id' field
        # Return a query that checks both
        return int_id
    except (ValueError, TypeError):
        # If it's not an integer, it might already be an ObjectId hex string
        # For NeoSQLite v1.1.0, we might need to use the ObjectId type
        try:
            import neosqlite
            # Try to create an ObjectId from the value
            object_id = neosqlite.ObjectId(id_value)
            return object_id
        except:
            # If all attempts fail, return the original value
            return id_value


def load_config():
    """Load configuration from file, with support for custom path via environment variable."""
    # Check for custom config path in environment variable
    config_path = os.environ.get("NEO_BLOGGY_CONFIG_PATH", "config.toml")

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
        print(f"Error retrieving users: {e}")
        return []


def get_user_by_email(email):
    """Get a user by email address."""
    try:
        db = neosqlite.Connection(DB_PATH)
        user = db.users.find_one({"email": email})
        return user
    except Exception as e:
        print(f"Error retrieving user: {e}")
        return None


def update_user_status(email, is_active=None, is_admin=None):
    """Update user status (active/inactive) and/or admin status."""
    try:
        db = neosqlite.Connection(DB_PATH)

        # Find the user by email
        user = db.users.find_one({"email": email})

        if not user:
            print(f"User with email {email} not found.")
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
        print(f"User {user['name']} ({email}) has been {action}.")

        # Show current status
        updated_user = db.users.find_one({"_id": user["_id"]})
        print(
            f"Current status: is_active={updated_user.get('is_active', True)}, is_admin={updated_user.get('is_admin', False)}"
        )
        return True

    except Exception as e:
        print(f"Error updating user: {e}")
        return False


def list_users():
    """List all users with their status."""
    try:
        users = get_all_users()
        if not users:
            print("No users found in the database.")
            return

        print("Users in the database:")
        print("-" * 80)
        print(f"{'Name':<25} {'Email':<30} {'Status':<10} {'Admin':<10}")
        print("-" * 80)

        for user in users:
            status = "Active" if user.get("is_active", True) else "Disabled"
            admin = "Yes" if user.get("is_admin", False) else "No"
            print(
                f"{user.get('name', 'N/A'):<25} {user.get('email', 'N/A'):<30} {status:<10} {admin:<10}"
            )

    except Exception as e:
        print(f"Error listing users: {e}")


def show_user_details(email):
    """Show detailed information about a specific user."""
    try:
        user = get_user_by_email(email)
        if not user:
            print(f"User with email {email} not found.")
            return

        print(f"User Details for {email}:")
        print("-" * 40)
        print(f"Name: {user.get('name', 'N/A')}")
        print(f"Email: {user.get('email', 'N/A')}")
        print(f"Active: {user.get('is_active', True)}")
        print(f"Admin: {user.get('is_admin', False)}")
        print(f"Security Question: {user.get('security_question', 'N/A')}")
        print(f"User ID: {user.get('_id', 'N/A')}")

    except Exception as e:
        print(f"Error showing user details: {e}")


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
        print(f"Database file '{DB_PATH}' not found.")
        print("Please run this script from the project directory.")
        sys.exit(1)

    args = parser.parse_args()

    # Handle list option
    if args.list:
        list_users()
        return

    # Handle details option
    if args.details:
        if not args.email:
            print("Error: --email is required with --details")
            sys.exit(1)
        show_user_details(args.email)
        return

    # Handle user management
    if args.email:
        # Determine what actions to take
        is_active = None
        is_admin = None

        if args.enable and args.disable:
            print("Error: Cannot use both --enable and --disable")
            sys.exit(1)

        if args.make_admin and args.remove_admin:
            print("Error: Cannot use both --make-admin and --remove-admin")
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
            print(
                "Error: No action specified. Use --enable, --disable, --make-admin, or --remove-admin"
            )
            parser.print_help()
            sys.exit(1)

        update_user_status(args.email, is_active, is_admin)
    else:
        # No arguments provided, show help
        parser.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Migration script to clean up legacy GridFS tables.

This script removes old dot-notation GridFS tables (fs.files, fs.chunks)
and any stray 'fs' table that can cause "unknown database fs" errors
when using NeoSQLite >= 1.6.0.

Background:
-----------
NeoSQLite 1.6.0+ changed GridFS table naming from dot-notation (fs.files)
to underscore-notation (fs_files). During migration, if both old and new
tables exist, GridFSBucket initialization can fail with "unknown database fs"
because SQLite interprets 'fs.files' as 'database fs, table files'.

This script safely removes the legacy tables after confirming the new
underscore-notation tables exist and contain data.

Usage:
------
    python scripts/cleanup_gridfs_legacy_tables.py

"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3

from neo_bloggy import create_app
from neo_bloggy.config import config

DB_PATH = config.get("database", {}).get("db_path", "neo-bloggy.db")


def check_table_exists(conn, table_name):
    """Check if a table exists in the database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def get_table_count(conn, table_name):
    """Get the number of rows in a table."""
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def cleanup_legacy_tables():
    """Remove legacy GridFS tables that cause initialization errors."""
    print("=" * 60)
    print("GridFS Legacy Table Cleanup")
    print("=" * 60)
    print()

    # Connect to the database
    print(f"Connecting to database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file not found: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)

    try:
        # Check current state
        print("\nCurrent GridFS tables:")
        print("-" * 40)

        legacy_tables = {
            "fs.files": check_table_exists(conn, "fs.files"),
            "fs.chunks": check_table_exists(conn, "fs.chunks"),
            "fs": check_table_exists(conn, "fs"),
        }

        new_tables = {
            "fs_files": check_table_exists(conn, "fs_files"),
            "fs_chunks": check_table_exists(conn, "fs_chunks"),
        }

        for table, exists in legacy_tables.items():
            status = "EXISTS" if exists else "not found"
            print(f"  {table:15} : {status}")

        print()
        for table, exists in new_tables.items():
            if exists:
                count = get_table_count(conn, table)
                print(f"  {table:15} : EXISTS ({count} rows)")
            else:
                print(f"  {table:15} : not found")

        # Validation: new tables must exist before removing old ones
        print()
        print("-" * 40)
        print("Validation:")

        if not new_tables["fs_files"]:
            print("  ERROR: New table 'fs_files' does not exist!")
            print("  Cannot proceed with cleanup.")
            return False

        if not new_tables["fs_chunks"]:
            print("  ERROR: New table 'fs_chunks' does not exist!")
            print("  Cannot proceed with cleanup.")
            return False

        print("  ✓ New underscore-notation tables exist")

        # Check if there's anything to clean up
        tables_to_remove = [t for t, exists in legacy_tables.items() if exists]

        if not tables_to_remove:
            print()
            print("No legacy tables found. Nothing to clean up.")
            print("Your database is already up-to-date.")
            return True

        print()
        print(f"Tables to remove: {', '.join(tables_to_remove)}")
        print()

        # Confirm before proceeding
        response = input("Continue with cleanup? (y/N): ")
        if response.lower() != "y":
            print("Cleanup cancelled.")
            return True

        # Perform cleanup
        print()
        print("Removing legacy tables...")
        print("-" * 40)

        removed_count = 0
        for table in tables_to_remove:
            try:
                # Quote table names that may contain dots
                conn.execute(f'DROP TABLE IF EXISTS "{table}"')
                print(f"  ✓ Dropped: {table}")
                removed_count += 1
            except Exception as e:
                print(f"  ✗ Failed to drop {table}: {e}")

        conn.commit()

        print()
        print("=" * 60)
        print("Cleanup completed!")
        print(f"  Tables removed: {removed_count}")
        print("=" * 60)

        # Verify the cleanup
        print()
        print("Verification:")
        print("-" * 40)
        remaining_legacy = [
            t for t in legacy_tables.keys() if check_table_exists(conn, t)
        ]
        if remaining_legacy:
            print(f"  WARNING: Some legacy tables still exist: {remaining_legacy}")
        else:
            print("  ✓ All legacy tables removed successfully")

        # Verify new tables are still intact
        if check_table_exists(conn, "fs_files") and check_table_exists(
            conn, "fs_chunks"
        ):
            print("  ✓ New tables intact and operational")
        else:
            print("  ERROR: New tables were affected!")
            return False

        return True

    except Exception as e:
        print(f"\nERROR: Cleanup failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = cleanup_legacy_tables()
    sys.exit(0 if success else 1)

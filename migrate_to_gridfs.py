#!/usr/bin/env python3
"""
Migration script to move all existing files from filesystem to GridFS.
"""

import os
import sys
import time
import tomllib

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the app and its configuration
from app import app, get_db, get_gridfs

# Load configuration from config.toml
CONFIG_FILE = "config.toml"
config = {}

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "rb") as f:
        config = tomllib.load(f)

# Database configuration - use the same path as the main app
DB_PATH = config.get("database", {}).get("db_path", "neo-bloggy.db")


def extract_username_from_filename(filename):
    """Extract username from filename if possible, otherwise return 'unknown'."""
    # Try the standard format: username_originalname_uuid.extension
    parts = filename.split("_")
    if len(parts) >= 3:
        return parts[0]

    # Try other common patterns
    # If it's a UUID pattern, we might not be able to extract a username
    if "-" in filename and "." in filename:
        name_part = filename.split(".")[0]
        if "-" in name_part:
            # This looks like a UUID-based filename
            return "unknown"

    # Default fallback
    return "unknown"


def migrate_files_to_gridfs():
    """Migrate all existing files from filesystem to GridFS."""

    print("Starting migration of files from filesystem to GridFS...")

    # Get upload folder path
    upload_folder = app.config["UPLOAD_FOLDER"]

    # Check if upload folder exists
    if not os.path.exists(upload_folder):
        print("Upload folder does not exist. Nothing to migrate.")
        return

    # Get list of files in upload folder
    try:
        files = os.listdir(upload_folder)
        print(f"Found {len(files)} files to migrate.")
    except Exception as e:
        print(f"Error reading upload folder: {e}")
        return

    if not files:
        print("No files to migrate.")
        return

    # Initialize database connection
    with app.app_context():
        get_db()
        gfs = get_gridfs()

        if gfs is None:
            print("Error: Could not initialize GridFS")
            return

        migrated_count = 0
        error_count = 0

        # Process each file
        for filename in files:
            try:
                print(f"Processing {filename}...")

                # Skip non-files
                file_path = os.path.join(upload_folder, filename)
                if not os.path.isfile(file_path):
                    continue

                # Extract user from filename (best effort)
                username = extract_username_from_filename(filename)

                # Open and process the image
                with open(file_path, "rb") as f:
                    # Read the file content
                    file_content = f.read()

                    # Store file in GridFS with metadata
                    file_id = gfs.upload_from_stream(
                        filename,
                        file_content,
                        metadata={
                            "user": username,
                            "original_filename": filename,
                            "uploaded_at": os.path.getmtime(file_path),
                            "migrated": True,
                            "migration_date": time.time(),
                        },
                    )

                print(f"  Successfully migrated {filename} with ID {file_id}")
                migrated_count += 1

            except Exception as e:
                print(f"  Error migrating {filename}: {e}")
                error_count += 1
                continue

        print("\nMigration completed!")
        print(f"  Successfully migrated: {migrated_count}")
        print(f"  Errors: {error_count}")

        # Optionally remove the original files after successful migration
        if migrated_count > 0 and error_count == 0:
            print("\nAll files migrated successfully.")
            response = input(
                "Do you want to remove the original files from the filesystem? (y/N): "
            )
            if response.lower() == "y":
                for filename in files:
                    file_path = os.path.join(upload_folder, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            print(f"  Removed {filename}")
                        except Exception as e:
                            print(f"  Error removing {filename}: {e}")
                print("Original files removed from filesystem.")
                # Also remove the upload directory if it's empty
                try:
                    os.rmdir(upload_folder)
                    print("Upload directory removed.")
                except Exception as e:
                    print(
                        f"Could not remove upload directory (might not be empty): {e}"
                    )
            else:
                print("Original files kept in filesystem.")
        elif error_count > 0:
            print(
                f"\nMigration completed with {error_count} errors. Please check the files manually."
            )


if __name__ == "__main__":
    migrate_files_to_gridfs()

#!/usr/bin/env python3
"""
Migration script to move all existing files from filesystem to GridFS.
"""

import logging
import os
import sys
import time
import tomllib

# Add the project directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Import the app and its configuration
from app import app
from neo_bloggy.database import get_db, get_gridfs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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

    logger.info("Starting migration of files from filesystem to GridFS...")

    # Get upload folder path
    upload_folder = app.config["UPLOAD_FOLDER"]

    # Check if upload folder exists
    if not os.path.exists(upload_folder):
        logger.info("Upload folder does not exist. Nothing to migrate.")
        return

    # Get list of files in upload folder
    try:
        files = os.listdir(upload_folder)
        logger.info("Found %d files to migrate.", len(files))
    except Exception as e:
        logger.error("Error reading upload folder: %s", e)
        return

    if not files:
        logger.info("No files to migrate.")
        return

    # Initialize database connection
    with app.app_context():
        get_db()
        gfs = get_gridfs()

        if gfs is None:
            logger.error("Error: Could not initialize GridFS")
            return

        migrated_count = 0
        error_count = 0

        # Process each file
        for filename in files:
            try:
                logger.info("Processing %s...", filename)

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

                logger.info(
                    "  Successfully migrated %s with ID %s", filename, file_id
                )
                migrated_count += 1

            except Exception as e:
                logger.error("  Error migrating %s: %s", filename, e)
                error_count += 1
                continue

        logger.info("\nMigration completed!")
        logger.info("  Successfully migrated: %d", migrated_count)
        logger.info("  Errors: %d", error_count)

        # Optionally remove the original files after successful migration
        if migrated_count > 0 and error_count == 0:
            logger.info("\nAll files migrated successfully.")
            response = input(
                "Do you want to remove the original files from the filesystem? (y/N): "
            )
            if response.lower() == "y":
                for filename in files:
                    file_path = os.path.join(upload_folder, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            logger.info("  Removed %s", filename)
                        except Exception as e:
                            logger.error("  Error removing %s: %s", filename, e)
                logger.info("Original files removed from filesystem.")
                # Also remove the upload directory if it's empty
                try:
                    os.rmdir(upload_folder)
                    logger.info("Upload directory removed.")
                except Exception as e:
                    logger.info(
                        "Could not remove upload directory (might not be empty): %s",
                        e,
                    )
            else:
                logger.info("Original files kept in filesystem.")
        elif error_count > 0:
            logger.info(
                "\nMigration completed with %d errors. Please check the files manually.",
                error_count,
            )


if __name__ == "__main__":
    migrate_files_to_gridfs()

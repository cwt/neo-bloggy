#!/usr/bin/env python3
"""
Migration script to update existing database for NeoSQLite v1.1.0 ObjectId compatibility

According to NeoSQLite v1.1.0 changes:
- New documents automatically get ObjectId in _id field when no _id is provided
- Existing documents keep their integer _id until updated/replaced
- The schema now has (id INTEGER PRIMARY KEY, _id JSONB, data JSONB) structure
- For a clean migration, we need to update all existing documents to trigger
  ObjectId generation in the _id field
"""

import logging
import neosqlite
import os
import sys
import tomllib
from datetime import datetime

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


def migrate_collection_documents(db, collection_name):
    """
    Update all documents in a collection to trigger ObjectId generation in NeoSQLite v1.1.0
    By updating each document (even with empty update), NeoSQLite will generate ObjectIds
    for the _id field automatically if they don't exist
    """
    logger.info("Processing collection: %s", collection_name)

    collection = getattr(db, collection_name)
    documents = list(collection.find())

    logger.info("Found %d documents in %s", len(documents), collection_name)

    for i, doc in enumerate(documents):
        original_id = doc.get("_id")

        # Update the document with an empty update to trigger ObjectId generation
        # In NeoSQLite v1.1.0, when documents are updated, they will have ObjectId in _id field
        # For documents with integer _id, this will convert to ObjectId
        collection.update_one({"_id": original_id}, {"$set": {}})

        logger.info(
            "  Updated document %d/%d with original _id: %s",
            i + 1,
            len(documents),
            original_id,
        )

    logger.info("Finished processing collection: %s", collection_name)


def migrate_database_to_objectid():
    """
    Migrate all collections in the database by updating documents to trigger ObjectId generation
    """
    logger.info("Starting migration to NeoSQLite v1.1.0 ObjectId format...")
    logger.info("Database path: %s", DB_PATH)

    if not os.path.exists(DB_PATH):
        logger.error("Database file '%s' not found.", DB_PATH)
        return False

    try:
        # Connect to the database
        db = neosqlite.Connection(DB_PATH)

        # Collections to migrate (based on the blog application)
        collections_to_migrate = ["users", "blog_posts", "blog_comments"]

        for collection_name in collections_to_migrate:
            try:
                # Check if collection exists by trying to access it
                collection = getattr(db, collection_name)
                # Try to find any documents to see if collection exists
                sample_doc = collection.find_one()

                if sample_doc is not None:
                    migrate_collection_documents(db, collection_name)
                else:
                    logger.info(
                        "Collection %s does not exist or is empty, skipping...",
                        collection_name,
                    )
            except Exception as e:
                logger.error(
                    "Error accessing collection %s: %s", collection_name, e
                )
                continue

        logger.info("Migration to NeoSQLite v1.1.0 ObjectId format completed!")
        logger.info(
            "All existing documents have been updated to trigger ObjectId generation for the _id field."
        )
        logger.info(
            "Please test your application to ensure all functionality works correctly."
        )
        return True

    except Exception as e:
        logger.error("Error during migration: %s", e, exc_info=True)
        return False


def backup_database():
    """
    Create a backup of the current database before migration
    """
    import shutil

    backup_name = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.info("Creating backup: %s", backup_name)

    try:
        shutil.copy2(DB_PATH, backup_name)
        logger.info("Backup created successfully: %s", backup_name)
        return backup_name
    except Exception as e:
        logger.error("Error creating backup: %s", e)
        return None


if __name__ == "__main__":
    logger.info("NeoSQLite v1.1.0 ObjectId Migration Script")
    logger.info("=" * 60)
    logger.info("This script will update all existing documents to work with")
    logger.info("NeoSQLite v1.1.0's ObjectId format while maintaining")
    logger.info("the integer ID in the 'id' field for compatibility.")
    logger.info("=" * 60)

    # Confirm with user before proceeding
    response = input(
        "\nThis script will update your database to work with NeoSQLite v1.1.0.\n"
        "A backup will be created first.\n"
        "Do you want to proceed? (y/N): "
    )

    if response.lower() != "y":
        logger.info("Migration cancelled.")
        sys.exit(0)

    # Create backup
    backup_path = backup_database()
    if backup_path is None:
        logger.error("Could not create backup. Aborting migration.")
        sys.exit(1)

    # Perform migration
    success = migrate_database_to_objectid()

    if not success:
        logger.error(
            "\nMigration failed. Your data is preserved in the backup file."
        )
        logger.error("Backup location: %s", backup_path)
        sys.exit(1)
    else:
        logger.info("\nMigration completed successfully!")
        logger.info("Backup available at: %s", backup_path)
        logger.info(
            "\nYour database is now compatible with NeoSQLite v1.1.0 ObjectId format."
        )

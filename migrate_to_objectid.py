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
import neosqlite
import os
import sys
import tomllib
from datetime import datetime


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


def migrate_collection_documents(db, collection_name):
    """
    Update all documents in a collection to trigger ObjectId generation in NeoSQLite v1.1.0
    By updating each document (even with empty update), NeoSQLite will generate ObjectIds 
    for the _id field automatically if they don't exist
    """
    print(f"Processing collection: {collection_name}")
    
    collection = getattr(db, collection_name)
    documents = list(collection.find())
    
    print(f"Found {len(documents)} documents in {collection_name}")
    
    for i, doc in enumerate(documents):
        original_id = doc.get("_id")
        
        # Update the document with an empty update to trigger ObjectId generation
        # In NeoSQLite v1.1.0, when documents are updated, they will have ObjectId in _id field
        # For documents with integer _id, this will convert to ObjectId
        collection.update_one({"_id": original_id}, {"$set": {}})
        
        print(f"  Updated document {i+1}/{len(documents)} with original _id: {original_id}")
    
    print(f"Finished processing collection: {collection_name}")


def migrate_database_to_objectid():
    """
    Migrate all collections in the database by updating documents to trigger ObjectId generation
    """
    print("Starting migration to NeoSQLite v1.1.0 ObjectId format...")
    print(f"Database path: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print(f"Database file '{DB_PATH}' not found.")
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
                    print(f"Collection {collection_name} does not exist or is empty, skipping...")
            except Exception as e:
                print(f"Error accessing collection {collection_name}: {e}")
                continue
        
        print("Migration to NeoSQLite v1.1.0 ObjectId format completed!")
        print("All existing documents have been updated to trigger ObjectId generation for the _id field.")
        print("Please test your application to ensure all functionality works correctly.")
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


def backup_database():
    """
    Create a backup of the current database before migration
    """
    import shutil
    from datetime import datetime
    
    backup_name = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup: {backup_name}")
    
    try:
        shutil.copy2(DB_PATH, backup_name)
        print(f"Backup created successfully: {backup_name}")
        return backup_name
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None


if __name__ == "__main__":
    print("NeoSQLite v1.1.0 ObjectId Migration Script")
    print("=" * 60)
    print("This script will update all existing documents to work with")
    print("NeoSQLite v1.1.0's ObjectId format while maintaining")
    print("the integer ID in the 'id' field for compatibility.")
    print("=" * 60)
    
    # Confirm with user before proceeding
    response = input("\nThis script will update your database to work with NeoSQLite v1.1.0.\n"
                     "A backup will be created first.\n"
                     "Do you want to proceed? (y/N): ")
    
    if response.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    # Create backup
    backup_path = backup_database()
    if backup_path is None:
        print("Could not create backup. Aborting migration.")
        sys.exit(1)
    
    # Perform migration
    success = migrate_database_to_objectid()
    
    if not success:
        print("\nMigration failed. Your data is preserved in the backup file.")
        print(f"Backup location: {backup_path}")
        sys.exit(1)
    else:
        print(f"\nMigration completed successfully!")
        print(f"Backup available at: {backup_path}")
        print("\nYour database is now compatible with NeoSQLite v1.1.0 ObjectId format.")
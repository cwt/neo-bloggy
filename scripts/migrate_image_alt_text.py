#!/usr/bin/env python3
"""Migration script to populate alt_text for existing images in GridFS.

This script updates all existing GridFS images that don't have alt_text set,
using their original_filename as the default alt_text.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo_bloggy import create_app
from neo_bloggy.database import get_db


def migrate_alt_text():
    """Migrate existing images to have alt_text in metadata."""
    print("Starting alt_text migration for GridFS images...")

    # Create app context
    app = create_app()

    with app.app_context():
        db = get_db()

        try:
            # Use PyMongo-like API (NeoSQLite >= 1.3.1)
            cursor = db.fs.files.find({})
            files = list(cursor)

            if not files:
                print("No images found in GridFS.")
                return True

            print(f"Found {len(files)} files in GridFS.")

            updated_count = 0
            skipped_count = 0
            error_count = 0

            for file_doc in files:
                file_id = file_doc._id
                filename = file_doc.filename
                metadata = file_doc.metadata or {}

                try:
                    # Check if alt_text already exists
                    if "alt_text" in metadata and metadata["alt_text"]:
                        print(
                            f"  SKIP: {filename} (already has alt_text: '{metadata['alt_text']}')"
                        )
                        skipped_count += 1
                        continue

                    # Get original_filename or use filename as fallback
                    original_filename = metadata.get(
                        "original_filename", filename
                    )

                    # Update metadata using PyMongo-like API (NeoSQLite >= 1.3.1)
                    db.fs.files.update_one(
                        {"_id": file_id},
                        {"$set": {"metadata.alt_text": original_filename}},
                    )

                    print(
                        f"  UPDATE: {filename} -> alt_text = '{original_filename}'"
                    )
                    updated_count += 1

                except Exception as e:
                    print(f"  ERROR: Failed to update {filename}: {e}")
                    error_count += 1

            print("\n" + "=" * 60)
            print("Migration completed!")
            print(f"  Updated: {updated_count} files")
            print(f"  Skipped: {skipped_count} files")
            print(f"  Errors:  {error_count} files")
            print("=" * 60)

            return error_count == 0

        except Exception as e:
            print(f"ERROR: Migration failed: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = migrate_alt_text()
    sys.exit(0 if success else 1)

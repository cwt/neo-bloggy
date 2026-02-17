"""Database module for Neo Bloggy application."""

import logging

from flask import g
import neosqlite
from neosqlite import gridfs
from neo_bloggy.config import DB_PATH, TOKENIZER_NAME, TOKENIZER_PATH

logger = logging.getLogger(__name__)


def close_db(error):
    """Close database connection at the end of the request."""
    if "db" in g:
        g.db.close()
        g.pop("db", None)
    # GridFS doesn't need explicit closing as it uses the same database connection


def get_db():
    """Get database connection for the current request."""
    if "db" not in g:
        # Try to initialize with tokenizers, fallback to no tokenizers if fails
        try:
            g.db = neosqlite.Connection(
                DB_PATH,
                tokenizers=(
                    [(TOKENIZER_NAME, TOKENIZER_PATH)]
                    if TOKENIZER_NAME and TOKENIZER_PATH
                    else None
                ),  # Tokenizers can be more than one.
            )
            # Create FTS indexes for blog posts if they don't exist
            g.db.blog_posts.create_index(
                "title", fts=True, tokenizer=TOKENIZER_NAME
            )
            g.db.blog_posts.create_index(
                "subtitle", fts=True, tokenizer=TOKENIZER_NAME
            )
            # Add FTS index for body content to enable comprehensive search
            g.db.blog_posts.create_index(
                "body", fts=True, tokenizer=TOKENIZER_NAME
            )
        except Exception as e:
            # Fallback to connection without tokenizers
            logger.warning("Failed to initialize with tokenizers: %s", e)
            g.db = neosqlite.Connection(DB_PATH, tokenizers=None)
            # Create FTS indexes without specific tokenizer
            g.db.blog_posts.create_index("title", fts=True)
            g.db.blog_posts.create_index("subtitle", fts=True)
            # Add FTS index for body content to enable comprehensive search
            g.db.blog_posts.create_index("body", fts=True)
        finally:
            # Create datetime index on datetime
            g.db.blog_posts.create_index("datetime", datetime_field=True)
            # Create index for author field (heavily used in queries)
            g.db.blog_posts.create_index("author")
            # Create index for tags field to support $elemMatch queries
            g.db.blog_posts.create_index("tags")
            # Create datetime index on comments datetime
            g.db.blog_comments.create_index("datetime", datetime_field=True)
            # Create index for parent_post field (heavily used for finding comments for a post)
            g.db.blog_comments.create_index("parent_post")
            # Create index for comment_author field (used for comment management)
            g.db.blog_comments.create_index("comment_author")
            # Create unique index for user names
            g.db.users.create_index("name", unique=True)
            # Create index for user email (used for authentication)
            g.db.users.create_index("email")
            # Create index for user status fields (used frequently in queries)
            g.db.users.create_index("is_active")
            g.db.users.create_index("is_admin")
            g.db.users.create_index("is_publisher")

        # Initialize GridFS for file storage
        try:
            g.gfs = gridfs.GridFSBucket(g.db.db)
        except Exception as e:
            logger.warning("Failed to initialize GridFS: %s", e)
            g.gfs = None

    return g.db


def get_gridfs():
    """Get GridFS instance for the current request."""
    if "gfs" not in g:
        get_db()  # This will initialize both db and gfs
        if "gfs" not in g:
            # If gfs wasn't initialized in get_db, try to initialize it now
            try:
                g.gfs = gridfs.GridFSBucket(g.db.db)
            except Exception as e:
                logger.warning("Failed to initialize GridFS: %s", e)
                g.gfs = None
    return g.get("gfs", None)


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
        try:
            # Try to create an ObjectId from the value to validate it
            object_id = neosqlite.objectid.ObjectId(id_value)
            # Return the string representation for broad compatibility in queries
            return str(object_id)
        except Exception:
            # If all attempts fail, return the original value
            return id_value


def get_objectid_for_gridfs(id_value):
    """Convert an ID value to ObjectId for GridFS operations.

    GridFS requires actual ObjectId objects for file operations.
    This function ensures proper conversion for GridFS compatibility.

    Args:
        id_value: The ID value to convert (can be string, int, or ObjectId)

    Returns:
        ObjectId object or integer ID for GridFS operations

    Raises:
        ValueError: If the ID cannot be converted to a valid format
    """
    # If it's already an ObjectId, return as-is
    if isinstance(id_value, neosqlite.objectid.ObjectId):
        return id_value

    # If it's an integer, return as-is (for backward compatibility)
    if isinstance(id_value, int):
        return id_value

    # Try to parse as integer first
    try:
        return int(id_value)
    except (ValueError, TypeError):
        pass

    # Try to create an ObjectId from string
    try:
        return neosqlite.objectid.ObjectId(id_value)
    except Exception:
        raise ValueError(f"Invalid ID format for GridFS: {id_value}")


def get_active_users(db):
    """Get list of active users from the database."""
    return [user["name"] for user in db.users.find({"is_active": True})]


def filter_active_user_content(
    content_list, active_users, author_field="comment_author"
):
    """Filter content to only include items from active users."""
    return [item for item in content_list if item[author_field] in active_users]


def get_publisher_users(db):
    """Get list of publisher users from the database."""
    return [user["name"] for user in db.users.find({"is_publisher": True})]

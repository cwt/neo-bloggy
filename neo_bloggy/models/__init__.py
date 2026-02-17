"""Data models and database interaction patterns for Neo Bloggy application."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from neo_bloggy.database import get_db, get_id_for_query

logger = logging.getLogger(__name__)


class BaseModel:
    """Base model class with common database operations."""

    collection_name: Optional[str] = None

    @classmethod
    def find_one(cls, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document matching the query."""
        db = get_db()
        # Automatically handle _id conversion if present in query
        if "_id" in query:
            query["_id"] = get_id_for_query(query["_id"])
        return getattr(db, cls.collection_name).find_one(query)  # type: ignore

    @classmethod
    def find_many(
        cls,
        query: Dict[str, Any],
        sort: Optional[Tuple[str, int]] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Find multiple documents matching the query."""
        db = get_db()
        # Automatically handle _id conversion if present in query
        if "_id" in query:
            query["_id"] = get_id_for_query(query["_id"])
        cursor = getattr(db, cls.collection_name).find(query)  # type: ignore

        if sort:
            cursor = cursor.sort(*sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        return list(cursor)

    @classmethod
    def count_documents(cls, query: Dict[str, Any]) -> int:
        """Count documents matching the query."""
        db = get_db()
        # Automatically handle _id conversion if present in query
        if "_id" in query:
            query["_id"] = get_id_for_query(query["_id"])
        return getattr(db, cls.collection_name).count_documents(query)  # type: ignore

    @classmethod
    def insert_one(cls, data: Dict[str, Any]) -> Any:
        """Insert a single document."""
        db = get_db()
        return getattr(db, cls.collection_name).insert_one(data)  # type: ignore

    @classmethod
    def update_one(
        cls, query: Dict[str, Any], update_data: Dict[str, Any]
    ) -> Any:
        """Update a single document."""
        db = get_db()
        # Automatically handle _id conversion if present in query
        if "_id" in query:
            query["_id"] = get_id_for_query(query["_id"])
        return getattr(db, cls.collection_name).update_one(  # type: ignore
            query, {"$set": update_data}
        )

    @classmethod
    def get_db(cls) -> Any:
        """Get database connection."""
        return get_db()

    @classmethod
    def delete_one(cls, query: Dict[str, Any]) -> Any:
        """Delete a single document."""
        db = get_db()
        # Automatically handle _id conversion if present in query
        if "_id" in query:
            query["_id"] = get_id_for_query(query["_id"])
        return getattr(db, cls.collection_name).delete_one(query)  # type: ignore


class User(BaseModel):
    """User model."""

    collection_name = "users"

    @classmethod
    def find_by_name(cls, name):
        """Find user by name."""
        return cls.find_one({"name": name})

    @classmethod
    def find_by_email(cls, email):
        """Find user by email."""
        return cls.find_one({"email": email})

    @classmethod
    def find_active_users(cls):
        """Find all active users."""
        return cls.find_many({"is_active": True})

    @classmethod
    def find_publisher_users(cls):
        """Find all publisher users."""
        return cls.find_many({"is_publisher": True})

    @classmethod
    def find_admin_users(cls):
        """Find all admin users."""
        return cls.find_many({"is_admin": True})

    @classmethod
    def create_user(cls, user_data):
        """Create a new user."""
        return cls.insert_one(user_data)

    @classmethod
    def update_user_status(cls, user_id, is_active):
        """Update user's active status."""
        return cls.update_one({"_id": user_id}, {"is_active": is_active})

    @classmethod
    def update_user_admin_status(cls, user_id, is_admin):
        """Update user's admin status."""
        return cls.update_one({"_id": user_id}, {"is_admin": is_admin})

    @classmethod
    def update_user_publisher_status(cls, user_id, is_publisher):
        """Update user's publisher status."""
        return cls.update_one({"_id": user_id}, {"is_publisher": is_publisher})


class Post(BaseModel):
    """Blog post model."""

    collection_name = "blog_posts"

    @classmethod
    def find_by_author(cls, author):
        """Find posts by author."""
        return cls.find_many({"author": author}, sort=("datetime", -1))

    @classmethod
    def find_by_tag(cls, tag):
        """Find posts by tag."""
        return cls.find_many(
            {"tags": {"$elemMatch": tag}}, sort=("datetime", -1)
        )

    @classmethod
    def find_published_posts(cls, authors):
        """Find posts by published authors."""
        return cls.find_many(
            {"author": {"$in": authors}}, sort=("datetime", -1)
        )

    @classmethod
    def find_all_posts(cls, skip=None, limit=None):
        """Find all posts with optional pagination."""
        return cls.find_many({}, sort=("datetime", -1), skip=skip, limit=limit)

    @classmethod
    def find_by_img_url(cls, img_url_pattern):
        """Find posts that contain the given image URL pattern."""
        # Use regex to find posts where img_url contains the pattern
        # This works for both full URL matches and partial matches (with file_id)
        return cls.find_many({"img_url": {"$regex": img_url_pattern}})

    @classmethod
    def create_post(cls, post_data):
        """Create a new post."""
        return cls.insert_one(post_data)

    @classmethod
    def update_post(cls, post_id, update_data):
        """Update a post."""
        return cls.update_one({"_id": post_id}, update_data)

    @classmethod
    def delete_post(cls, post_id):
        """Delete a post."""
        return cls.delete_one({"_id": post_id})

    @classmethod
    def ensure_tags_field(cls):
        """Ensure all posts have a tags field."""
        posts_without_tags = cls.find_many({"tags": {"$exists": False}})

        updated_count = 0
        for post in posts_without_tags:
            try:
                cls.update_one({"_id": post["_id"]}, {"tags": []})
                updated_count += 1
            except Exception as e:
                logger.error("Error updating post %s: %s", post["_id"], e)

        return updated_count


class Comment(BaseModel):
    """Comment model."""

    collection_name = "blog_comments"

    @classmethod
    def find_by_post_id(cls, post_id):
        """Find comments by post ID."""
        return cls.find_many(
            {"parent_post": get_id_for_query(post_id)}, sort=("datetime", -1)
        )

    @classmethod
    def find_by_author(cls, author):
        """Find comments by author."""
        return cls.find_many({"comment_author": author}, sort=("datetime", -1))

    @classmethod
    def create_comment(cls, comment_data):
        """Create a new comment."""
        return cls.insert_one(comment_data)

    @classmethod
    def delete_comment(cls, comment_id):
        """Delete a comment."""
        return cls.delete_one({"_id": comment_id})

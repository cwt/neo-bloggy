"""Data models for Neo Bloggy application.

This module provides model classes with domain-specific query methods.
All database operations leverage NeoSQLite's built-in methods directly.

NeoSQLite (>=1.2.3) automatically handles ID type conversion for all fields,
including _id and reference fields like parent_post.
"""

from neo_bloggy.database import get_db


def _get_collection(name):
    """Get a collection by name."""
    return getattr(get_db(), name)


class User:
    """User model with domain-specific query methods."""

    collection = "users"

    @classmethod
    def find_one(cls, query):
        return _get_collection(cls.collection).find_one(query)

    @classmethod
    def find_many(cls, query, sort=None, skip=None, limit=None):
        cursor = _get_collection(cls.collection).find(query)
        if sort:
            cursor = cursor.sort(*sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

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
        return _get_collection(cls.collection).insert_one(user_data)

    @classmethod
    def update_user_status(cls, user_id, is_active):
        """Update user's active status."""
        return _get_collection(cls.collection).update_one(
            {"_id": user_id}, {"$set": {"is_active": is_active}}
        )

    @classmethod
    def update_user_admin_status(cls, user_id, is_admin):
        """Update user's admin status."""
        return _get_collection(cls.collection).update_one(
            {"_id": user_id}, {"$set": {"is_admin": is_admin}}
        )

    @classmethod
    def update_user_publisher_status(cls, user_id, is_publisher):
        """Update user's publisher status."""
        return _get_collection(cls.collection).update_one(
            {"_id": user_id}, {"$set": {"is_publisher": is_publisher}}
        )

    @classmethod
    def count_documents(cls, query):
        """Count documents matching the query."""
        return _get_collection(cls.collection).count_documents(query)

    @classmethod
    def update_profile(cls, user_id, update_data):
        """Update user profile data."""
        return _get_collection(cls.collection).update_one(
            {"_id": user_id}, {"$set": update_data}
        )


class Post:
    """Blog post model with domain-specific query methods."""

    collection = "blog_posts"

    # Post status constants
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"

    @classmethod
    def find_one(cls, query):
        return _get_collection(cls.collection).find_one(query)

    @classmethod
    def find_many(cls, query, sort=None, skip=None, limit=None):
        cursor = _get_collection(cls.collection).find(query)
        if sort:
            cursor = cursor.sort(*sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    @classmethod
    def count_documents(cls, query):
        return _get_collection(cls.collection).count_documents(query)

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
    def find_by_img_url(cls, img_url):
        """Find posts that have the exact given image URL."""
        return cls.find_many({"img_url": img_url})

    @classmethod
    def find_drafts_by_author(cls, author):
        """Find draft posts by author."""
        return cls.find_many(
            {"author": author, "status": cls.STATUS_DRAFT},
            sort=("datetime", -1),
        )

    @classmethod
    def create_post(cls, post_data):
        """Create a new post."""
        return _get_collection(cls.collection).insert_one(post_data)

    @classmethod
    def update_post(cls, post_id, update_data):
        """Update a post."""
        return _get_collection(cls.collection).update_one(
            {"_id": post_id}, {"$set": update_data}
        )

    @classmethod
    def delete_post(cls, post_id):
        """Delete a post."""
        return _get_collection(cls.collection).delete_one({"_id": post_id})

    @classmethod
    def ensure_status_field(cls):
        """Ensure all posts have a status field (default to published for backward compatibility)."""
        import logging

        logger = logging.getLogger(__name__)

        posts_without_status = cls.find_many({"status": {"$exists": False}})
        collection = _get_collection(cls.collection)

        updated_count = 0
        for post in posts_without_status:
            try:
                collection.update_one(
                    {"_id": post["_id"]},
                    {"$set": {"status": cls.STATUS_PUBLISHED}},
                )
                updated_count += 1
            except Exception as e:
                logger.error("Error updating post %s: %s", post["_id"], e)

        return updated_count

    @classmethod
    def ensure_tags_field(cls):
        """Ensure all posts have a tags field."""
        import logging

        logger = logging.getLogger(__name__)

        posts_without_tags = cls.find_many({"tags": {"$exists": False}})
        collection = _get_collection(cls.collection)

        updated_count = 0
        for post in posts_without_tags:
            try:
                collection.update_one(
                    {"_id": post["_id"]}, {"$set": {"tags": []}}
                )
                updated_count += 1
            except Exception as e:
                logger.error("Error updating post %s: %s", post["_id"], e)

        return updated_count


class Comment:
    """Comment model with domain-specific query methods."""

    collection = "blog_comments"

    @classmethod
    def find_one(cls, query):
        return _get_collection(cls.collection).find_one(query)

    @classmethod
    def find_many(cls, query, sort=None, skip=None, limit=None):
        cursor = _get_collection(cls.collection).find(query)
        if sort:
            cursor = cursor.sort(*sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    @classmethod
    def find_by_post_id(cls, post_id):
        """Find comments by post ID."""
        return cls.find_many({"parent_post": post_id}, sort=("datetime", -1))

    @classmethod
    def find_by_author(cls, author):
        """Find comments by author."""
        return cls.find_many({"comment_author": author}, sort=("datetime", -1))

    @classmethod
    def create_comment(cls, comment_data):
        """Create a new comment."""
        return _get_collection(cls.collection).insert_one(comment_data)

    @classmethod
    def delete_comment(cls, comment_id):
        """Delete a comment."""
        return _get_collection(cls.collection).delete_one({"_id": comment_id})

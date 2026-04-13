"""Caching module for Neo Bloggy application."""

import logging
import time

from neo_bloggy.caching.cache_impl import (
    FileCache,
    clear_cache as clear_cache_internal,
    clear_expired_cache as clear_expired_cache_internal,
    get_cache_instance,
    get_cache_key,
)
from neo_bloggy.config import config, CACHE_ENABLED, CACHE_TIMEOUT

logger = logging.getLogger(__name__)

# Cache version key constant for invalidating post-related caches
POSTS_CACHE_VERSION_KEY = "posts_cache_version"

# Initialize cache based on configuration
cache_storage = get_cache_instance(config, cache_timeout=CACHE_TIMEOUT)


def clear_expired_cache():
    """Remove expired cache entries."""

    if not CACHE_ENABLED:
        return
    clear_expired_cache_internal(cache_storage, cache_timeout=CACHE_TIMEOUT)


def clear_cache():
    """Clear all cache entries."""

    clear_cache_internal(cache_storage)


def preload_cache():
    """
    Preload the cache with frequently accessed data when the app starts.
    This function is called after the app is loaded when gunicorn uses preload_app=True.
    """
    if CACHE_ENABLED:
        logger.info("Preloading cache with frequently accessed data...")

        # Preload main posts page for anonymous users (first page only to avoid loading all posts)
        try:
            from flask import current_app

            with current_app.app_context():
                from neo_bloggy.database import get_publisher_users

                # For anonymous users, get posts from publisher users (as in get_all_posts)
                publisher_users = get_publisher_users()

                # Calculate total posts and fetch first page for pagination info
                from neo_bloggy.config import POSTS_PER_PAGE
                from neo_bloggy.database import get_paginated_posts

                # Only cache the first page to avoid loading all posts at startup
                per_page = POSTS_PER_PAGE  # Use the configured default
                query = {"author": {"$in": publisher_users}}
                posts, total_posts = get_paginated_posts(query, 0, per_page)

                # Pre-render the template with posts to populate cache (first page only)
                cache_version = get_posts_cache_version()
                cache_key = get_cache_key(
                    f"get_all_posts_v{cache_version}_page_1_per_page_{per_page}"
                )

                total_pages = (
                    total_posts + per_page - 1
                ) // per_page  # Ceiling division
                has_next = 1 < total_pages
                has_prev = False  # Page 1 never has previous

                # Create a request context to allow render_template to work properly
                with current_app.test_request_context("/"):
                    from flask import render_template

                    result = render_template(
                        "index.html",
                        all_posts=posts,
                        pagination={
                            "page": 1,
                            "per_page": per_page,
                            "total": total_posts,
                            "pages": total_pages,
                            "has_next": has_next,
                            "has_prev": has_prev,
                        },
                        page_title=f"Home - {config.get('app', {}).get('site_title', 'Neo Bloggy')}: Where Good Ideas Find You",
                    )

                if isinstance(cache_storage, FileCache):
                    cache_storage.set(cache_key, result)
                    cache_storage.set(POSTS_CACHE_VERSION_KEY, cache_version)

                    # For FileCache, we can't easily get the count, so just report success
                    logger.info("Main posts page (page 1) cached successfully.")
                    logger.info(
                        "Cached %d posts out of %d total posts.",
                        len(posts),
                        total_posts,
                    )
                    logger.info("Cache stored to file system.")
                else:
                    # In-memory cache (fallback)
                    cache_storage[cache_key] = (result, time.time())

                    logger.info("Main posts page (page 1) cached successfully.")
                    logger.info(
                        "Cached %d posts out of %d total posts.",
                        len(posts),
                        total_posts,
                    )
                    logger.info(
                        "Cache storage now contains %d items.",
                        len(cache_storage),
                    )

                # Cache could also include other frequently accessed data
                # For example, we could pre-cache common tag pages or other frequently accessed content
        except Exception as e:
            logger.error("Error preloading cache: %s", e, exc_info=True)

        logger.info("Cache preloading completed.")


def get_posts_cache_version():
    """Get the current posts cache version from storage."""
    if not CACHE_ENABLED:
        return 0

    if isinstance(cache_storage, FileCache):
        version = cache_storage.get(POSTS_CACHE_VERSION_KEY)
        return version if version is not None else 0
    else:
        # In-memory cache fallback
        if POSTS_CACHE_VERSION_KEY in cache_storage:
            version, timestamp = cache_storage[POSTS_CACHE_VERSION_KEY]
            if time.time() - timestamp < CACHE_TIMEOUT:
                return version
        return 0


def on_app_ready():
    """
    Function to run when the app is ready - this can be used to populate cache
    or run other initializations after the app is loaded.
    """
    # Ensure first admin has publisher status
    from neo_bloggy.services import UserService

    UserService.ensure_first_admin_is_publisher()

    # Ensure all posts have tags and status fields
    from neo_bloggy.models import Post

    Post.ensure_tags_field()
    Post.ensure_status_field()

    # Clear all existing cache to start fresh
    if CACHE_ENABLED:
        if isinstance(cache_storage, FileCache):
            cache_storage.clear()
            logger.info("Cleared all existing cache files.")
        else:
            # In-memory cache
            cache_storage.clear()
            logger.info("Cleared all in-memory cache.")

    # Preload cache with frequently accessed data
    preload_cache()

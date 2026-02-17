#!/usr/bin/env python3
"""
More detailed debug script to test the post route issue.
"""

import logging

from neo_bloggy import create_app
from neo_bloggy.models import User
from neo_bloggy.posts.helpers import get_post_with_comments

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create the app
app = create_app()


def debug_post_access_detailed():
    logger.info("Testing post access in detail...")

    with app.app_context():
        # Get a post ID dynamically from the database
        from neo_bloggy.models import Post
        posts = Post.find_all_posts()
        if not posts:
            logger.warning("No posts found in database")
            return

        post_id = str(posts[0]["_id"])
        logger.info("Using post ID from database: %s", post_id)

        # Simulate the exact logic from CommentService.show_post
        requested_post, requested_post_comments = get_post_with_comments(post_id)

        logger.info("Post found: %s", requested_post is not None)
        if requested_post:
            logger.info("Post title: %s", requested_post.get('title'))
            logger.info("Post author: %s", requested_post.get('author'))

        # Get current user (should be None since we're not in a request context)
        # Use try/except to handle the case where we're outside request context
        try:
            from neo_bloggy.auth import get_current_user
            current_user = get_current_user()
        except RuntimeError:
            # Outside request context, current_user is effectively None
            current_user = None
        logger.info("Current user: %s", current_user)

        # Check if the post author exists
        post_author = User.find_by_name(requested_post["author"]) if requested_post else None
        logger.info("Post author found: %s", post_author is not None)
        if post_author:
            logger.info("Author is_active: %s", post_author.get('is_active', True))
            logger.info("Author is_publisher: %s", post_author.get('is_publisher', False))
            logger.info("Author is_admin: %s", post_author.get('is_admin', False))

            # Test the exact conditions that cause redirects
            is_admin = current_user and current_user.get("is_admin", False)
            logger.info("Is current user admin: %s", is_admin)

            # Condition 1: Non-admin users cannot view posts from inactive users
            if not is_admin and not post_author.get("is_active", True):
                logger.info("REDIRECT CONDITION 1: Would redirect because post author is not active and current user is not admin")
            else:
                logger.info("PASS CONDITION 1: Post author is active OR current user is admin")

            # Condition 2: For anonymous users or non-admin users, check if the post author is a publisher
            if not is_admin and not post_author.get("is_publisher"):
                logger.info("REDIRECT CONDITION 2: Would redirect because post author is not publisher and current user is not admin")
                # Check if current user is the author
                if not current_user or current_user.get("name") != requested_post["author"]:
                    logger.info("SUB-CONDITION: Current user is not the author")
                else:
                    logger.info("SUB-CONDITION: Current user IS the author")
            else:
                logger.info("PASS CONDITION 2: Post author is publisher OR current user is admin")


if __name__ == "__main__":
    debug_post_access_detailed()
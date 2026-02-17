#!/usr/bin/env python3
"""
Test script to simulate the exact request flow for the post route.
"""

import logging
import traceback

from neo_bloggy import create_app
from neo_bloggy.models import User
from neo_bloggy.database import get_active_users
from neo_bloggy.auth import get_current_user
from neo_bloggy.posts.helpers import get_post_with_comments

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create the app
app = create_app()


def simulate_show_post(post_id):
    """Simulate the exact logic from CommentService.show_post"""
    logger.info("Simulating show_post for post_id: %s", post_id)

    with app.test_request_context('/post/' + post_id, method='GET'):
        try:
            current_user = get_current_user()
            logger.info("Current user: %s", current_user)

            # For GET requests, we can use caching
            requested_post, requested_post_comments = get_post_with_comments(post_id)
            logger.info("Requested post found: %s", requested_post is not None)

            if requested_post:
                logger.info("Post title: %s", requested_post.get('title'))
                logger.info("Post author: %s", requested_post.get('author'))

            # Handle case where post is not found
            if not requested_post:
                logger.error("Post not found - would redirect to home")
                return "redirect_home"

            # Check if the post author is active (except for admins)
            post_author = User.find_by_name(requested_post["author"])
            logger.info("Post author found: %s", post_author is not None)

            if not post_author:
                logger.error("Author not found - would redirect to home")
                return "redirect_home"

            # Non-admin users cannot view posts from inactive users
            is_admin = current_user and current_user.get("is_admin", False)
            logger.info("Is admin: %s", is_admin)
            logger.info("Author is_active: %s", post_author.get('is_active', True))

            if not is_admin and not post_author.get("is_active", True):
                logger.error("Author not active and current user not admin - would redirect to home")
                return "redirect_home"

            # For anonymous users or non-admin users, check if the post author is a publisher
            # Non-publisher posts should only be visible to the author and admins
            logger.info("Author is_publisher: %s", post_author.get('is_publisher', False))

            if not is_admin and not post_author.get("is_publisher", False):
                # Only the author of the post or admins can view non-publisher posts
                if (
                    not current_user
                    or current_user.get("name") != requested_post["author"]
                ):
                    logger.error("Author not publisher, current user not admin, and current user not author - would redirect to home")
                    return "redirect_home"

            # Filter comments to only show those from active users
            from neo_bloggy.database import get_db
            db = get_db()
            active_users = get_active_users(db)
            logger.info("Active users: %s", active_users)

            if hasattr(requested_post_comments, "__iter__"):
                from neo_bloggy.services import CommentService
                requested_post_comments = CommentService.filter_active_user_content(
                    requested_post_comments, active_users, "comment_author"
                )
            else:
                # If it's a cursor, convert to list and filter
                from neo_bloggy.services import CommentService
                requested_post_comments = CommentService.filter_active_user_content(
                    list(requested_post_comments),
                    active_users,
                    "comment_author",
                )

            logger.info("Filtered comments count: %d", len(requested_post_comments))

            # Get author information to check if author is a publisher
            post_author_info = User.find_by_name(requested_post["author"])
            logger.info("Post author info found: %s", post_author_info is not None)

            logger.info("SUCCESS: All checks passed, would render post")
            return "success"

        except Exception as e:
            logger.error("EXCEPTION in show_post logic: %s", e)
            logger.error("Exception type: %s", type(e))
            logger.error(traceback.format_exc())
            return "exception_redirect"


if __name__ == "__main__":
    with app.app_context():
        from neo_bloggy.models import Post
        posts = Post.find_all_posts()
        if posts:
            post_id = str(posts[0]["_id"])
            result = simulate_show_post(post_id)
        else:
            logger.warning("No posts found in database")
            result = "no_posts"
    logger.info("\nFinal result: %s", result)
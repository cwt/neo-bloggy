#!/usr/bin/env python3
"""
Debug script to trigger the exact error scenario with full traceback.
"""

import logging
import traceback

from neo_bloggy import create_app
from neo_bloggy.models import Post

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create the app
app = create_app()


def debug_show_post():
    """Debug the show_post functionality with detailed tracing."""
    logger.info("Setting up app context...")

    with app.app_context():
        logger.info("App context established")

        # Get a post ID to test with
        posts = Post.find_all_posts()
        if not posts:
            logger.warning("No posts found in database")
            return

        test_post_id = str(posts[0]["_id"])
        logger.info("Using post ID: %s", test_post_id)

        # Now simulate the exact request context that might cause the error
        with app.test_request_context('/post/' + test_post_id, method='GET'):
            logger.info("Request context established")

            try:
                # Import the exact same things that the service uses
                from neo_bloggy.auth import get_current_user
                from neo_bloggy.posts.helpers import get_post_with_comments
                from neo_bloggy.models import User

                logger.info("Imports successful")

                # Try the exact same logic as in CommentService.show_post
                current_user = get_current_user()
                logger.info("Current user: %s", current_user)

                # For GET requests, we can use caching
                requested_post, requested_post_comments = get_post_with_comments(test_post_id)
                logger.info("Post retrieved successfully: %s", requested_post is not None)

                if requested_post:
                    logger.info("Post title: %s", requested_post.get('title', 'NO TITLE'))

                    # Try the next steps that might cause the error
                    post_author = User.find_by_name(requested_post["author"])
                    logger.info("Post author found: %s", post_author is not None)

                    # Try to access Post.get_db directly to confirm the error exists
                    try:
                        Post.get_db
                        logger.error("ERROR: Post.get_db should not exist!")
                    except AttributeError as e:
                        logger.info("Expected error confirmed: %s", e)

            except Exception as e:
                logger.error("ERROR in debug process: %s", e)
                logger.error("Full traceback:")
                logger.error(traceback.format_exc())
                return False

        logger.info("Debug completed successfully without triggering the error")
        return True


if __name__ == "__main__":
    debug_show_post()
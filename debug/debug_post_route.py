#!/usr/bin/env python3
"""
Debug script to test the post route issue.
"""

import logging

from neo_bloggy import create_app
from neo_bloggy.database import get_id_for_query
from neo_bloggy.models import Post
from neo_bloggy.posts.helpers import get_post_with_comments

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create the app
app = create_app()


def debug_post_access():
    logger.info("Testing post access...")

    # Get a post ID dynamically from the database
    with app.app_context():
        posts = Post.find_all_posts()
        if not posts:
            logger.warning("No posts found in database")
            return

        post_id = str(posts[0]["_id"])
        logger.info("Using post ID from database: %s", post_id)

        # Test the get_id_for_query function
        converted_id = get_id_for_query(post_id)
        logger.info("Original ID: %s", post_id)
        logger.info("Converted ID: %s", converted_id)
        logger.info("Type: %s", type(converted_id))

        # Test finding the post directly
        post = Post.find_one({"_id": post_id})
        logger.info("Post found: %s", post is not None)
        if post:
            logger.info("Post title: %s", post.get('title'))

        # Test the helper function
        post_with_comments, comments = get_post_with_comments(post_id)
        logger.info("Post with comments found: %s", post_with_comments is not None)
        if post_with_comments:
            logger.info("Post title from helper: %s", post_with_comments.get('title'))


if __name__ == "__main__":
    debug_post_access()
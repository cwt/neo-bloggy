from neo_bloggy.models import Post, Comment
from neo_bloggy.database import (
    get_active_users,
    filter_active_user_content,
)
from neo_bloggy.caching.cache_impl import (
    cached_result as cached_result_internal,
    get_cache_instance,
)
from neo_bloggy.config import config, CACHE_TIMEOUT

# Initialize cache based on configuration
cache_storage = get_cache_instance(config, cache_timeout=CACHE_TIMEOUT)


def cached_result(func):
    """Decorator to cache function results with timeout."""
    return cached_result_internal(cache_storage, cache_timeout=CACHE_TIMEOUT)(
        func
    )


@cached_result
def get_post_with_comments(post_id):
    """Get a post with its comments, cached for performance.
    Only show comments from active users.
    """
    post = Post.find_one({"_id": post_id})
    if post:
        comments = Comment.find_by_post_id(post_id)
        # Filter comments to only show those from active users
        active_users = get_active_users()
        comments = filter_active_user_content(
            comments, active_users, "comment_author"
        )
        return post, comments
    return None, []

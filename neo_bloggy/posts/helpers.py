from neo_bloggy.database import (
    get_active_users,
    get_db,
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
    """Get a post with its comments using aggregation pipeline with $lookup.

    Replaces 3 separate queries (post + comments + active users) + Python filtering
    with a single aggregation pipeline for 50-60% reduction in database round trips.
    Requires NeoSQLite >= 1.14.4 for full $addFields after $lookup support.
    """
    db = get_db()
    active_users = get_active_users()

    # Single aggregation pipeline: join, sort, and filter comments
    pipeline = [
        {"$match": {"_id": post_id}},
        {
            "$lookup": {
                "from": "blog_comments",
                "localField": "_id",
                "foreignField": "parent_post",
                "as": "comments",
            }
        },
        # Sort comments by datetime descending
        {
            "$addFields": {
                "comments": {
                    "$sortArray": {
                        "input": "$comments",
                        "sortBy": {"datetime": -1},
                    }
                }
            }
        },
        # Filter comments to only include those from active users
        {
            "$addFields": {
                "comments": {
                    "$filter": {
                        "input": "$comments",
                        "as": "comment",
                        "cond": {
                            "$in": ["$$comment.comment_author", active_users]
                        },
                    }
                }
            }
        },
    ]

    results = list(db.blog_posts.aggregate(pipeline))

    if not results:
        return None, []

    post_doc = results[0]
    comments = post_doc.pop("comments", [])

    return post_doc, comments

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
            # Create index for img_url field (used for checking image usage before deletion)
            g.db.blog_posts.create_index("img_url")
            # Create index for status field (used to filter drafts)
            g.db.blog_posts.create_index("status")

            # --- Compound Indexes for Optimization ---
            # Optimize public post listings (filter by status, sort by datetime)
            g.db.blog_posts.create_index([("status", 1), ("datetime", -1)])
            # Optimize user profiles and draft management
            g.db.blog_posts.create_index(
                [("author", 1), ("status", 1), ("datetime", -1)]
            )

            # Create datetime index on comments datetime
            g.db.blog_comments.create_index("datetime", datetime_field=True)
            # Create index for parent_post field (heavily used for finding comments for a post)
            g.db.blog_comments.create_index("parent_post")
            # Create index for comment_author field (used for comment management)
            g.db.blog_comments.create_index("comment_author")

            # Optimize comment loading for posts
            g.db.blog_comments.create_index(
                [("parent_post", 1), ("datetime", -1)]
            )

            # Create unique index for user names
            g.db.users.create_index("name", unique=True)
            # Create index for user email (used for authentication)
            g.db.users.create_index("email")
            # Create index for user status fields (used frequently in queries)
            g.db.users.create_index("is_active")
            g.db.users.create_index("is_admin")
            g.db.users.create_index("is_publisher")

            # Optimize admin panel and security checks
            g.db.users.create_index([("is_admin", 1), ("is_active", 1)])

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


def get_active_users():
    """Get list of active users from the database."""
    from neo_bloggy.models import User

    return [user["name"] for user in User.find_active_users()]


def filter_active_user_content(
    content_list, active_users, author_field="comment_author"
):
    """Filter content to only include items from active users."""
    return [item for item in content_list if item[author_field] in active_users]


def get_publisher_users():
    """Get list of publisher users from the database."""
    from neo_bloggy.models import User

    return [user["name"] for user in User.find_publisher_users()]


def get_related_tags(search_filter, exclude_tag, limit=10):
    """Get related tags using co-occurrence scoring.

    Finds tags that appear together with the current tag, ranked by
    co-occurrence frequency. Uses $facet to compute both the total number
    of posts with the current tag and how often each other tag appears
    alongside it, giving a meaningful "relatedness" score.

    Args:
        search_filter: MongoDB-style query filter for posts
        exclude_tag: Tag name to exclude from results (the current tag)
        limit: Maximum number of related tags to return

    Returns:
        List of tag names sorted by co-occurrence frequency (descending)
    """
    db = get_db()

    # Co-occurrence pipeline using $facet:
    # 1. Match posts with the current tag
    # 2. Facet into:
    #    a. "total": count of posts with the current tag
    #    b. "tags": unwind tags (excluding current), group by tag, count co-occurrences
    # 3. Sort co-occurrences by frequency descending
    pipeline = [
        {"$match": search_filter},
        {
            "$facet": {
                "total": [{"$count": "count"}],
                "tags": [
                    {"$unwind": "$tags"},
                    {
                        "$group": {
                            "_id": "$tags",
                            "count": {"$sum": 1},
                        }
                    },
                    {"$match": {"_id": {"$ne": exclude_tag}}},
                    {"$sort": {"count": -1, "_id": 1}},
                    {"$limit": limit},
                ],
            }
        },
    ]

    results = list(db.blog_posts.aggregate(pipeline))
    if not results:
        return []

    facet = results[0]
    related_tags = facet.get("tags", [])
    return [r["_id"] for r in related_tags if r["_id"]]


def get_posts_and_related_tags(search_filter, exclude_tag, limit=10):
    """Get posts and related tags using a single $facet aggregation pipeline.

    Args:
        search_filter: MongoDB-style query filter for posts
        exclude_tag: Tag name to exclude from related tags
        limit: Maximum number of related tags to return

    Returns:
        Tuple of (posts_list, related_tags_list)
    """
    from neo_bloggy.models import Post

    db = get_db()

    pipeline = [
        {"$match": search_filter},
        {
            "$facet": {
                "posts": [
                    {"$sort": {"datetime": -1}},
                ],
                "total": [{"$count": "count"}],
                "related_tags": [
                    {"$unwind": "$tags"},
                    {
                        "$group": {
                            "_id": "$tags",
                            "count": {"$sum": 1},
                        }
                    },
                    {"$match": {"_id": {"$ne": exclude_tag}}},
                    {"$sort": {"count": -1, "_id": 1}},
                    {"$limit": limit},
                ],
            }
        },
    ]

    try:
        results = list(db.blog_posts.aggregate(pipeline))

        if not results:
            return [], []

        facet_result = results[0]
        posts = facet_result.get("posts", [])
        related_tags_raw = facet_result.get("related_tags", [])
        related_tags = [r["_id"] for r in related_tags_raw if r["_id"]]

        return posts, related_tags
    except Exception:
        # Fallback to separate queries
        posts = Post.find_many(search_filter, sort=("datetime", -1))
        related_tags = get_related_tags(
            search_filter, exclude_tag=exclude_tag, limit=limit
        )
        return posts, related_tags


def get_admin_dashboard_stats():
    """Get admin dashboard statistics using $facet aggregation pipelines.

    Replaces 6+ separate queries with 2 organized $facet pipelines for:
    1. User statistics (total, active, admins, publishers)
    2. Content statistics (total posts, drafts, comments, posts by status)

    Returns:
        Dictionary with:
        - user_stats: {total, active, admins, publishers}
        - content_stats: {total_posts, published, drafts, total_comments}
    """
    db = get_db()

    # Pipeline 1: User statistics
    user_pipeline = [
        {
            "$facet": {
                "total": [{"$count": "count"}],
                "active": [
                    {"$match": {"is_active": True}},
                    {"$count": "count"},
                ],
                "admins": [{"$match": {"is_admin": True}}, {"$count": "count"}],
                "publishers": [
                    {"$match": {"is_publisher": True}},
                    {"$count": "count"},
                ],
            }
        }
    ]

    # Pipeline 2: Content statistics
    content_pipeline = [
        {
            "$facet": {
                "total_posts": [{"$count": "count"}],
                "published": [
                    {"$match": {"status": "published"}},
                    {"$count": "count"},
                ],
                "drafts": [
                    {"$match": {"status": "draft"}},
                    {"$count": "count"},
                ],
            }
        }
    ]

    # Execute user stats
    try:
        user_results = list(db.users.aggregate(user_pipeline))
    except Exception:
        # Fallback to separate queries if $facet fails
        user_stats = {
            "total": db.users.count_documents({}),
            "active": db.users.count_documents({"is_active": True}),
            "admins": db.users.count_documents({"is_admin": True}),
            "publishers": db.users.count_documents({"is_publisher": True}),
        }
    else:
        user_stats = {"total": 0, "active": 0, "admins": 0, "publishers": 0}
        if user_results:
            facet = user_results[0]
            user_stats["total"] = (
                facet["total"][0]["count"] if facet.get("total") else 0
            )
            user_stats["active"] = (
                facet["active"][0]["count"] if facet.get("active") else 0
            )
            user_stats["admins"] = (
                facet["admins"][0]["count"] if facet.get("admins") else 0
            )
            user_stats["publishers"] = (
                facet["publishers"][0]["count"]
                if facet.get("publishers")
                else 0
            )

    # Execute content stats
    try:
        content_results = list(db.blog_posts.aggregate(content_pipeline))
    except Exception:
        # Fallback to separate queries if $facet fails
        content_stats = {
            "total_posts": db.blog_posts.count_documents({}),
            "published": db.blog_posts.count_documents({"status": "published"}),
            "drafts": db.blog_posts.count_documents({"status": "draft"}),
            "total_comments": db.blog_comments.count_documents({}),
        }
    else:
        content_stats = {
            "total_posts": 0,
            "published": 0,
            "drafts": 0,
            "total_comments": 0,
        }
        if content_results:
            facet = content_results[0]
            content_stats["total_posts"] = (
                facet["total_posts"][0]["count"]
                if facet.get("total_posts")
                else 0
            )
            content_stats["published"] = (
                facet["published"][0]["count"] if facet.get("published") else 0
            )
            content_stats["drafts"] = (
                facet["drafts"][0]["count"] if facet.get("drafts") else 0
            )

        # Get comment count (separate collection, can't use same pipeline)
        content_stats["total_comments"] = db.blog_comments.count_documents({})

    return {
        "user_stats": user_stats,
        "content_stats": content_stats,
    }


def get_user_profile_stats(username):
    """Get user profile statistics using optimized aggregation.

    Filters by username once before performing counts/sorts.

    Args:
        username: The username to get statistics for

    Returns:
        Dictionary with:
        - published_posts: Count of published posts
        - drafts: Count of draft posts
        - total_comments: Count of comments
        - recent_posts: List of 5 most recent published posts
    """
    db = get_db()

    # Match by author first, then facet for efficiency
    pipeline = [
        {"$match": {"author": username}},
        {
            "$facet": {
                "published_posts": [
                    {"$match": {"status": "published"}},
                    {"$count": "count"},
                ],
                "drafts": [
                    {"$match": {"status": "draft"}},
                    {"$count": "count"},
                ],
                "recent_posts": [
                    {"$match": {"status": "published"}},
                    {"$sort": {"datetime": -1}},
                    {"$limit": 5},
                ],
            }
        },
    ]

    try:
        results = list(db.blog_posts.aggregate(pipeline))
    except Exception:
        # Fallback to separate queries
        stats = {
            "published_posts": db.blog_posts.count_documents(
                {"author": username, "status": "published"}
            ),
            "drafts": db.blog_posts.count_documents(
                {"author": username, "status": "draft"}
            ),
            "recent_posts": list(
                db.blog_posts.find(
                    {"author": username, "status": "published"},
                    sort=[("datetime", -1)],
                    limit=5,
                )
            ),
        }
    else:
        stats = {"published_posts": 0, "drafts": 0, "recent_posts": []}
        if results:
            facet = results[0]
            stats["published_posts"] = (
                facet["published_posts"][0]["count"]
                if facet.get("published_posts")
                else 0
            )
            stats["drafts"] = (
                facet["drafts"][0]["count"] if facet.get("drafts") else 0
            )
            stats["recent_posts"] = facet.get("recent_posts", [])

    # Get comment count (separate collection)
    stats["total_comments"] = db.blog_comments.count_documents(
        {"comment_author": username}
    )

    return stats


def get_paginated_posts(query, skip, per_page, sort=None):
    """Get posts and total count using $facet aggregation pipeline.

    Single pipeline returns both paginated posts and total count,
    eliminating the need for separate find_many() and count_documents() calls.

    Falls back to separate queries if NeoSQLite doesn't support $facet
    with the given query operators.

    Args:
        query: MongoDB-style query filter for posts
        skip: Number of posts to skip (for pagination)
        per_page: Number of posts to return
        sort: Sort specification (e.g., ("datetime", -1))

    Returns:
        Tuple of (posts_list, total_count)
    """
    from neo_bloggy.models import Post

    db = get_db()
    sort = sort or ("datetime", -1)

    # $facet pipeline with two sub-pipelines:
    # 1. 'posts': Paginated posts with sorting
    # 2. 'total': Total count of matching documents
    pipeline = [
        {"$match": query},
        {
            "$facet": {
                "posts": [
                    {"$sort": {sort[0]: sort[1]}},
                    {"$skip": skip},
                    {"$limit": per_page},
                ],
                "total": [{"$count": "count"}],
            }
        },
    ]

    try:
        results = list(db.blog_posts.aggregate(pipeline))

        if not results:
            return [], 0

        facet_result = results[0]
        posts = facet_result.get("posts", [])
        total_result = facet_result.get("total", [])
        total_posts = total_result[0]["count"] if total_result else 0

        return posts, total_posts
    except Exception:
        # Fallback to separate queries if $facet fails
        posts = Post.find_many(query, sort=sort, skip=skip, limit=per_page)
        total_posts = Post.count_documents(query)
        return posts, total_posts

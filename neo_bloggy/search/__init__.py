"""Search module for Neo Bloggy application."""

import re
from typing import Any, Dict, Optional

from flask import make_response, redirect, render_template, request, url_for

from neo_bloggy.auth import get_current_user
from neo_bloggy.config import MAX_POSTS_PER_PAGE, POSTS_PER_PAGE, config
from neo_bloggy.database import get_active_users, get_db, get_publisher_users
from neo_bloggy.utils import InputValidator


# Search result constants
CACHE_CONTROL_NO_CACHE = "no-cache, no-store, must-revalidate"
CACHE_CONTROL_PRAGMA = "no-cache"
CACHE_CONTROL_EXPIRES = "0"


def search():
    """
    Search for posts by title, subtitle, and body content.

    Access rules:
    - Logged-in users: See posts from active users
    - Anonymous users: See only publisher posts
    - Admins: Can search all posts including from inactive users
    """
    current_user = get_current_user()
    page, per_page = _get_pagination_params()
    db = get_db()

    # Handle POST request - redirect to GET for pagination support
    if request.method == "POST":
        query = request.form.get("query")
        if query:
            return redirect(
                url_for(
                    "search.search", query=query, page=page, per_page=per_page
                )
            )

    # GET request - get query from args
    query = request.args.get("query", "")

    # Security validation
    if (
        query
        and query.strip()
        and not InputValidator.validate_search_query(query)
    ):
        return redirect(url_for("posts.get_all_posts"))

    # Determine search scope based on user role
    search_context = _get_search_context(current_user, db)

    # Execute search
    posts, total_posts = _execute_search(
        db, query, search_context, page, per_page
    )

    # Build response
    pagination = _build_pagination(page, per_page, total_posts)
    response = make_response(
        render_template(
            "index.html",
            all_posts=posts,
            search_query=query,
            user=current_user,
            pagination=pagination,
            page_title=f"Search: {query} - {config.get('app', {}).get('site_title', 'Neo Bloggy')}",
        )
    )

    # Prevent caching of search results
    response.headers["Cache-Control"] = CACHE_CONTROL_NO_CACHE
    response.headers["Pragma"] = CACHE_CONTROL_PRAGMA
    response.headers["Expires"] = CACHE_CONTROL_EXPIRES
    return response


def _get_pagination_params() -> tuple:
    """Get and validate pagination parameters."""
    page = max(1, int(request.args.get("page", 1)))
    per_page = int(request.args.get("per_page", POSTS_PER_PAGE))
    per_page = max(1, min(per_page, MAX_POSTS_PER_PAGE))
    return page, per_page


def _get_search_context(
    current_user: Optional[Dict[str, Any]], db
) -> Dict[str, Any]:
    """
    Determine search context based on user role.

    Returns dict with:
    - relevant_users: List of usernames to filter by (empty for admins)
    - search_filter_base: Base filter for author restriction
    """
    if current_user:
        if current_user.get("is_admin", False):
            # Admins can search all posts
            return {"relevant_users": [], "search_filter_base": {}}
        else:
            # Regular users see posts from active users
            active_users = get_active_users(db)
            return {
                "relevant_users": active_users,
                "search_filter_base": {"author": {"$in": active_users}},
            }
    else:
        # Anonymous users see only publisher posts
        publisher_users = get_publisher_users(db)
        return {
            "relevant_users": publisher_users,
            "search_filter_base": {"author": {"$in": publisher_users}},
        }


def _execute_search(
    db, query: str, search_context: Dict[str, Any], page: int, per_page: int
) -> tuple:
    """Execute search query and return posts with total count."""
    skip = (page - 1) * per_page
    relevant_users = search_context["relevant_users"]
    search_filter_base = search_context["search_filter_base"]

    if query and query.strip():
        return _execute_text_search(
            db, query, search_filter_base, relevant_users, skip, per_page
        )
    else:
        return _get_all_posts(db, search_filter_base, skip, per_page)


def _execute_text_search(
    db, query, search_filter_base, relevant_users, skip, per_page
) -> tuple:
    """Execute full-text search with fallback to regex search."""
    try:
        # Try FTS search first
        search_filter = _build_fts_filter(
            query, search_filter_base, relevant_users
        )
        total_posts = db.blog_posts.count_documents(search_filter)
        posts = list(
            db.blog_posts.find(search_filter)
            .sort("datetime", -1)
            .skip(skip)
            .limit(per_page)
        )

        # Add relevance scoring
        for post in posts:
            if hasattr(post, "_meta") and "textScore" in post._meta:
                post["search_score"] = post._meta["textScore"]
            else:
                post["search_score"] = 0

        # Sort by relevance
        posts.sort(
            key=lambda x: (
                x.get("search_score", 0),
                x.get("datetime", ""),
            ),
            reverse=True,
        )
        return posts, total_posts

    except Exception:
        # Fallback to regex search
        return _execute_regex_search(
            db, query, search_filter_base, relevant_users, skip, per_page
        )


def _build_fts_filter(query, search_filter_base, relevant_users):
    """Build full-text search filter."""
    text_filter = {"$text": {"$search": query}}
    if relevant_users:
        return {"$and": [text_filter, search_filter_base]}
    return text_filter


def _execute_regex_search(
    db, query, search_filter_base, relevant_users, skip, per_page
) -> tuple:
    """Execute regex-based search as fallback."""
    escaped_query = re.escape(query)
    text_pattern: Dict[str, Any] = {"$regex": escaped_query, "$options": "i"}
    text_patterns = [
        {"title": text_pattern},
        {"subtitle": text_pattern},
        {"body": text_pattern},
    ]

    search_filter: Dict[str, Any]
    if relevant_users:
        search_filter = {
            "$and": [
                {"$or": text_patterns},
                {"author": {"$in": relevant_users}},
            ]
        }
    else:
        search_filter = {"$or": text_patterns}

    total_posts = db.blog_posts.count_documents(search_filter)
    posts = list(
        db.blog_posts.find(search_filter)
        .sort("datetime", -1)
        .skip(skip)
        .limit(per_page)
    )
    return posts, total_posts


def _get_all_posts(db, search_filter_base, skip, per_page) -> tuple:
    """Get all posts without text search."""
    if search_filter_base:
        total_posts = db.blog_posts.count_documents(search_filter_base)
        posts = list(
            db.blog_posts.find(search_filter_base)
            .sort("datetime", -1)
            .skip(skip)
            .limit(per_page)
        )
    else:
        # Admin viewing all posts
        total_posts = db.blog_posts.count_documents({})
        posts = list(
            db.blog_posts.find().sort("datetime", -1).skip(skip).limit(per_page)
        )
    return posts, total_posts


def _build_pagination(page: int, per_page: int, total: int) -> Dict[str, Any]:
    """Build pagination dictionary."""
    total_pages = (total + per_page - 1) // per_page
    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }

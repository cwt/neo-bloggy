"""Authentication module for Neo Bloggy application."""

from flask import g, session
from functools import wraps
from neo_bloggy.models import User


def get_current_user():
    """
    Get the current logged-in user from session.
    Uses flask.g to cache the user for the current request context.
    Returns None if no user is logged in or if there's an issue.
    """

    if "user" not in session:
        return None

    # Check if user is already cached in flask.g
    if hasattr(g, "current_user"):
        return g.current_user

    try:
        user = User.find_by_name(session["user"])
        # Check if user exists and is active
        if user and user.get("is_active", True):
            g.current_user = user
            return user
        else:
            # If user is disabled or doesn't exist, clear the session
            session.clear()
            return None
    except Exception:
        # If there's any database error, clear the session
        session.clear()
        return None


def login_required(f):
    """
    Decorator to require login for routes.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            from flask import flash, redirect, url_for

            flash("You need to login to access this page.")
            return redirect(url_for("auth.login"))
        return f(current_user=current_user, *args, **kwargs)

    return decorated_function


def admin_required(f):
    """
    Decorator to require admin privileges for routes.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            from flask import flash, redirect, url_for

            flash("You need to login to access this page.")
            return redirect(url_for("auth.login"))
        if not current_user.get("is_admin", False):
            from flask import flash, redirect, url_for

            flash("You don't have permission to access this page.")
            return redirect(url_for("posts.get_all_posts"))
        return f(current_user=current_user, *args, **kwargs)

    return decorated_function


def get_absolute_url(endpoint, **values):
    """
    Generate an absolute URL using the configured base URL if available,
    otherwise fall back to Flask's url_for with _external=True.
    """
    from neo_bloggy.config import BASE_URL
    from flask import url_for

    # If base_url is configured, construct the URL using it
    if BASE_URL:
        # Generate the relative URL first
        relative_url = url_for(endpoint, **values)
        # Combine with base URL
        return BASE_URL.rstrip("/") + relative_url
    else:
        # Fall back to Flask's external URL generation
        return url_for(endpoint, _external=True, **values)


def get_canonical_url():
    """
    Get the canonical URL for the current request.
    Uses the configured base URL if available, otherwise falls back to request.url.
    """
    from neo_bloggy.config import BASE_URL
    from flask import request

    if BASE_URL:
        # Construct canonical URL using base URL and current path
        return BASE_URL.rstrip("/") + request.path
    else:
        # Fall back to the original request URL
        return request.url

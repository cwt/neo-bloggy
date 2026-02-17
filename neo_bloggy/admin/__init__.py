"""Admin module for Neo Bloggy application."""

from flask import render_template, redirect, url_for, flash
from neo_bloggy.forms import PasswordRecoveryForm
from neo_bloggy.database import get_db, get_id_for_query
from neo_bloggy.auth import admin_required
from werkzeug.security import generate_password_hash
from neo_bloggy.models import User, Post


@admin_required
def admin_panel(current_user):
    """
    Admin panel to manage users and content.
    """
    # Get all users (except the current admin)
    users = User.find_many({"name": {"$ne": current_user["name"]}})

    return render_template("admin.html", users=users)


@admin_required
def toggle_user_status(current_user, user_id):
    """
    Toggle a user's active status (enable/disable).
    """
    # Find the user to toggle
    user_to_toggle = User.find_one({"_id": get_id_for_query(user_id)})

    if not user_to_toggle:
        flash("User not found.")
        return redirect(url_for("admin.admin_panel"))

    # Prevent admins from disabling other admins
    if user_to_toggle.get("is_admin", False):
        flash("You cannot disable another admin user.")
        return redirect(url_for("admin.admin_panel"))

    # Toggle the user's active status
    new_status = not user_to_toggle.get("is_active", True)
    User.update_user_status(user_id, new_status)

    status_text = "enabled" if new_status else "disabled"
    flash(f"User '{user_to_toggle['name']}' has been {status_text}.")

    # Clear cache since we've modified user status
    from neo_bloggy.config import CACHE_ENABLED

    if CACHE_ENABLED:
        from neo_bloggy.caching import clear_cache

        clear_cache()

    return redirect(url_for("admin.admin_panel"))


@admin_required
def make_admin(current_user, user_id):
    """
    Make a user an admin.
    """
    # Find the user to make admin
    user_to_make_admin = User.find_one({"_id": get_id_for_query(user_id)})

    if not user_to_make_admin:
        flash("User not found.")
        return redirect(url_for("admin.admin_panel"))

    # Make the user an admin
    User.update_user_admin_status(user_id, True)

    flash(f"User '{user_to_make_admin['name']}' is now an admin.")

    # Clear cache since we've modified user permissions
    from neo_bloggy.config import CACHE_ENABLED

    if CACHE_ENABLED:
        from neo_bloggy.caching import clear_cache

        clear_cache()

    return redirect(url_for("admin.admin_panel"))


@admin_required
def toggle_publisher(current_user, user_id):
    """
    Toggle a user's publisher status.
    """
    # Find the user to toggle
    user_to_toggle = User.find_one({"_id": get_id_for_query(user_id)})

    if not user_to_toggle:
        flash("User not found.")
        return redirect(url_for("admin.admin_panel"))

    # Toggle the user's publisher status
    new_publisher_status = not user_to_toggle.get("is_publisher", False)
    User.update_user_publisher_status(user_id, new_publisher_status)

    status_text = "published" if new_publisher_status else "unpublished"
    flash(f"User '{user_to_toggle['name']}' has been marked as {status_text}.")

    # Clear cache since we've modified user status
    from neo_bloggy.config import CACHE_ENABLED

    if CACHE_ENABLED:
        from neo_bloggy.caching import clear_cache

        clear_cache()

    return redirect(url_for("admin.admin_panel"))


def rebuild_search_indexes(current_user):
    """
    Rebuild all FTS indexes for blog posts.
    """
    try:
        db = get_db()
        # Rebuild FTS indexes
        db.blog_posts.reindex("title")
        db.blog_posts.reindex("subtitle")
        db.blog_posts.reindex("body")
        flash("Search indexes rebuilt successfully!")
    except Exception as e:
        flash(f"Failed to rebuild search indexes: {str(e)}")

    return redirect(url_for("admin.admin_panel"))


def unpublished_posts(current_user):
    """
    Admin view to see all unpublished posts.
    Includes posts from non-publisher users, regardless of active status.
    """
    # Get all users who are not publishers
    non_publisher_users = [
        user["name"] for user in User.find_many({"is_publisher": False})
    ]

    # Get all posts by non-publisher users
    posts = Post.find_many(
        {"author": {"$in": non_publisher_users}}, sort=("datetime", -1)
    )

    # Get user information for each post author
    post_authors = {}
    for post in posts:
        if post["author"] not in post_authors:
            author = User.find_by_name(post["author"])
            post_authors[post["author"]] = author

    return render_template(
        "unpublished_posts.html", posts=posts, post_authors=post_authors
    )


def recover_password():
    """
    Recover password using security question.
    Prevent disabled users from recovering password.
    """
    from neo_bloggy.utils import UserValidator

    form = PasswordRecoveryForm()
    if form.validate_on_submit():
        # Validate password recovery data
        user = UserValidator.validate_password_recovery(form)

        if user is None:
            return render_template("recover_password.html", form=form)

        # Update password
        new_password_hash = generate_password_hash(
            form.password.data, method="pbkdf2:sha256", salt_length=8
        )
        db = get_db()
        users = db.users
        users.update_one(
            {"_id": user["_id"]}, {"$set": {"password": new_password_hash}}
        )

        flash(
            "Password successfully reset. You can now log in with your new password."
        )
        return redirect(url_for("auth.login"))

    return render_template("recover_password.html", form=form)

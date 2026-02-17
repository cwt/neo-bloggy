"""Controller module for Neo Bloggy application."""

from flask import render_template, redirect, url_for, flash, request, session
from neo_bloggy.forms import (
    RegisterForm,
    LoginForm,
    EditProfileForm,
    PasswordRecoveryForm,
)
from neo_bloggy.models import User
from neo_bloggy.services import PostService, CommentService
from neo_bloggy.utils import UserValidator
from neo_bloggy.database import get_db, get_id_for_query
from werkzeug.security import generate_password_hash


class UserController:
    """Controller class for user-related operations."""

    @staticmethod
    def register():
        """Handle user registration."""
        form = RegisterForm()
        if form.validate_on_submit():
            try:
                # Validate registration data
                if not UserValidator.validate_registration(form):
                    return redirect(url_for("posts.get_all_posts"))

                db = get_db()
                users = db.users

                # hash and salt the password
                hash_and_salted_password = generate_password_hash(
                    form.password.data, method="pbkdf2:sha256", salt_length=8
                )
                new_user = {
                    "email": form.email.data,
                    "password": hash_and_salted_password,
                    "name": form.name.data,
                    "security_question": form.security_question.data,
                    "security_answer": generate_password_hash(
                        form.security_answer.data.lower(),
                        method="pbkdf2:sha256",
                        salt_length=8,
                    ),
                    "is_admin": False,  # Default to non-admin
                    "is_active": True,  # Default to active
                    "is_publisher": False,  # Default to non-publisher
                }
                # insert new_user into the database
                insert_result = users.insert_one(new_user)
                new_user_id = insert_result.inserted_id

                # Check if there are any admins, if not, make this user an admin
                admin_count = users.count_documents({"is_admin": True})
                if admin_count == 0:
                    users.update_one(
                        {"_id": new_user_id},
                        {"$set": {"is_admin": True, "is_publisher": True}},
                    )
                    flash(
                        "You are the first user. You have been made an administrator."
                    )

                # put the new user into 'session' cookie
                session.permanent = True  # Make the session permanent
                session["user"] = form.name.data
                flash("Registration Successful")
                return redirect(
                    url_for("auth.profile", username=session["user"])
                )
            except Exception as e:
                # Check if the error is due to unique constraint violation on name
                error_msg = str(e).lower()
                if "unique" in error_msg and "name" in error_msg:
                    flash(
                        "A user with that name already exists. Please choose a different name."
                    )
                else:
                    flash(f"Registration failed: {str(e)}")
                return render_template("register.html", form=form)
        return render_template("register.html", form=form)

    @staticmethod
    def login():
        """Handle user login."""
        form = LoginForm()
        if form.validate_on_submit():
            try:
                # Validate login credentials
                existing_user = UserValidator.validate_login(form)

                if existing_user is None:
                    return redirect(url_for("auth.login"))
                else:
                    session.permanent = True  # Make the session permanent
                    session["user"] = existing_user["name"]
                    flash(f"Welcome Back, {existing_user['name'].title()}")
                    return redirect(
                        url_for("auth.profile", username=session["user"])
                    )
            except Exception as e:
                flash(f"Login failed: {str(e)}")
                return render_template("login.html", form=form)
        return render_template("login.html", form=form)

    @staticmethod
    def profile(current_user, username):
        """Handle user profile page."""
        # Security check: Only allow users to view their own profile
        if current_user["name"] != username:
            flash("You can only view your own profile.")
            return redirect(url_for("posts.get_all_posts"))

        db = get_db()
        user = db.users.find_one({"name": username})
        if not user:
            flash("User not found.")
            return redirect(url_for("posts.get_all_posts"))

        posts = db.blog_posts.find({"author": username}).sort("datetime", -1)
        return render_template(
            "profile.html", username=username, posts=posts, user=user
        )

    @staticmethod
    def edit_profile(current_user):
        """Handle user profile editing."""
        # Check if user is active (this is already checked in get_current_user, but being thorough)
        if not current_user.get("is_active", True):
            flash(
                "Your account has been disabled. You cannot edit your profile."
            )
            return redirect(url_for("posts.get_all_posts"))

        form = EditProfileForm()
        # Populate form fields manually, except for name field (which was removed)
        if request.method == "GET":
            form.email.data = current_user["email"]
            form.security_question.data = current_user.get(
                "security_question", ""
            )
            # Note: We don't populate security_answer for security reasons

        if form.validate_on_submit():
            # Validate profile update data
            if not UserValidator.validate_profile_update(form, current_user):
                return render_template("edit_profile.html", form=form)

            db = get_db()
            update_data = {
                "email": form.email.data,
                "security_question": form.security_question.data,
                "security_answer": generate_password_hash(
                    form.security_answer.data.lower(),
                    method="pbkdf2:sha256",
                    salt_length=8,
                ),
            }
            if form.password.data:
                update_data["password"] = generate_password_hash(
                    form.password.data, method="pbkdf2:sha256", salt_length=8
                )

            # Update the user's profile in the database
            db.users.update_one(
                {"_id": current_user["_id"]},
                {"$set": update_data},
            )

            session.permanent = True  # Make sure session remains permanent
            flash("Profile updated successfully!")
            return redirect(
                url_for("auth.profile", username=current_user["name"])
            )
        elif request.method == "GET":
            form.email.data = current_user["email"]
            form.security_question.data = current_user.get(
                "security_question", ""
            )

        return render_template("edit_profile.html", form=form)

    @staticmethod
    def logout():
        """Handle user logout."""
        # Clear all session data
        session.clear()

        # Clear cache to ensure no cached content shows logged-in state
        from neo_bloggy.config import CACHE_ENABLED

        if CACHE_ENABLED:
            from neo_bloggy.caching import clear_cache

            clear_cache()

        response = redirect(url_for("posts.get_all_posts"))
        # Add cache control headers to prevent caching of redirect response
        response.headers["Cache-Control"] = (
            "no-cache, no-store, must-revalidate"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


class PostController:
    """Controller class for post-related operations."""

    @staticmethod
    def get_all_posts(page, per_page):
        """Handle getting all posts."""
        return PostService.get_all_posts(page, per_page)

    @staticmethod
    def create_post(current_user):
        """Handle post creation."""
        return PostService.create_post(current_user)

    @staticmethod
    def edit_post(current_user, post_id):
        """Handle post editing."""
        return PostService.edit_post(current_user, post_id)

    @staticmethod
    def delete_post(current_user, post_id):
        """Handle post deletion."""
        return PostService.delete_post(current_user, post_id)

    @staticmethod
    def show_post(post_id):
        """Handle showing a post."""
        return CommentService.show_post(post_id)

    @staticmethod
    def delete_comment(current_user, comment_id):
        """Handle comment deletion."""
        return CommentService.delete_comment(current_user, comment_id)

    @staticmethod
    def posts_by_tag(tag):
        """Handle showing posts by tag."""
        return PostService.posts_by_tag(tag)


class AdminController:
    """Controller class for admin operations."""

    @staticmethod
    def admin_panel(current_user):
        """Handle admin panel."""
        return render_template(
            "admin.html",
            users=User.find_many({"name": {"$ne": current_user["name"]}}),
        )

    @staticmethod
    def toggle_user_status(current_user, user_id):
        """Handle toggling user status."""
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
            from neo_bloggy.caching.cache_impl import (
                clear_cache as clear_cache_internal,
                get_cache_instance,
            )
            from neo_bloggy.config import config

            cache_storage = get_cache_instance(config)
            clear_cache_internal(cache_storage)
        return redirect(url_for("admin.admin_panel"))

    @staticmethod
    def make_admin(current_user, user_id):
        """Handle making a user an admin."""
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
            from neo_bloggy.caching.cache_impl import (
                clear_cache as clear_cache_internal,
                get_cache_instance,
            )
            from neo_bloggy.config import config

            cache_storage = get_cache_instance(config)
            clear_cache_internal(cache_storage)

        return redirect(url_for("admin.admin_panel"))

    @staticmethod
    def toggle_publisher(current_user, user_id):
        """Handle toggling publisher status."""
        # Find the user to toggle
        user_to_toggle = User.find_one({"_id": get_id_for_query(user_id)})

        if not user_to_toggle:
            flash("User not found.")
            return redirect(url_for("admin.admin_panel"))

        # Toggle the user's publisher status
        new_publisher_status = not user_to_toggle.get("is_publisher", False)
        User.update_user_publisher_status(user_id, new_publisher_status)

        status_text = "published" if new_publisher_status else "unpublished"
        flash(
            f"User '{user_to_toggle['name']}' has been marked as {status_text}."
        )

        # Clear cache since we've modified user status
        from neo_bloggy.config import CACHE_ENABLED

        if CACHE_ENABLED:
            from neo_bloggy.caching.cache_impl import (
                clear_cache as clear_cache_internal,
                get_cache_instance,
            )
            from neo_bloggy.config import config

            cache_storage = get_cache_instance(config)
            clear_cache_internal(cache_storage)

        return redirect(url_for("admin.admin_panel"))

    @staticmethod
    def recover_password():
        """Handle password recovery."""
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

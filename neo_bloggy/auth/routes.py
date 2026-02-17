from flask import Blueprint
from neo_bloggy.controllers import UserController

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    return UserController.register()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    return UserController.login()


@auth_bp.route("/logout")
def logout():
    return UserController.logout()


@auth_bp.route("/profile/<username>")
def profile(username):
    from neo_bloggy.auth import get_current_user

    current_user = get_current_user()
    if not current_user:
        from flask import flash, redirect, url_for

        flash("You need to login to access this page.")
        return redirect(url_for("auth.login"))
    return UserController.profile(current_user, username)


@auth_bp.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    from neo_bloggy.auth import get_current_user

    current_user = get_current_user()
    if not current_user:
        from flask import flash, redirect, url_for

        flash("You need to login to access this page.")
        return redirect(url_for("auth.login"))
    return UserController.edit_profile(current_user)

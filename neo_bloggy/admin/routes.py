from flask import Blueprint
from neo_bloggy.controllers import AdminController
from neo_bloggy.auth import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def admin_panel(current_user):
    return AdminController.admin_panel(current_user)


@admin_bp.route("/admin/toggle_user_status/<user_id>", methods=["POST"])
@admin_required
def toggle_user_status(current_user, user_id):
    return AdminController.toggle_user_status(current_user, user_id)


@admin_bp.route("/admin/make_admin/<user_id>", methods=["POST"])
@admin_required
def make_admin(current_user, user_id):
    return AdminController.make_admin(current_user, user_id)


@admin_bp.route("/admin/toggle_publisher/<user_id>", methods=["POST"])
@admin_required
def toggle_publisher(current_user, user_id):
    return AdminController.toggle_publisher(current_user, user_id)


@admin_bp.route("/admin/rebuild-search-indexes", methods=["POST"])
@admin_required
def rebuild_search_indexes(current_user):
    from neo_bloggy.admin import rebuild_search_indexes as rebuild_internal

    return rebuild_internal(current_user)


@admin_bp.route("/admin/unpublished-posts")
@admin_required
def unpublished_posts(current_user):
    from neo_bloggy.admin import unpublished_posts as unpublished_internal

    return unpublished_internal(current_user)


@admin_bp.route("/recover-password", methods=["GET", "POST"])
def recover_password():
    return AdminController.recover_password()

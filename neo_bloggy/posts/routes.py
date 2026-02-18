from flask import Blueprint
from neo_bloggy.controllers import PostController
from neo_bloggy.auth import login_required

posts_bp = Blueprint("posts", __name__)


@posts_bp.route("/")
def get_all_posts():
    from flask import request
    from neo_bloggy.config import POSTS_PER_PAGE

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", POSTS_PER_PAGE))
    return PostController.get_all_posts(page, per_page)


@posts_bp.route("/post/<post_id>", methods=["GET", "POST"])
def show_post(post_id):
    return PostController.show_post(post_id)


@posts_bp.route("/create-post", methods=["GET", "POST"])
@login_required
def create_post(current_user):
    return PostController.create_post(current_user)


@posts_bp.route("/edit-post/<post_id>", methods=["GET", "POST"])
@login_required
def edit_post(current_user, post_id):
    return PostController.edit_post(current_user, post_id)


@posts_bp.route("/delete/<post_id>")
@login_required
def delete_post(current_user, post_id):
    return PostController.delete_post(current_user, post_id)


@posts_bp.route("/delete-draft/<post_id>")
@login_required
def delete_draft(current_user, post_id):
    return PostController.delete_draft(current_user, post_id)


@posts_bp.route("/delete_comment/<comment_id>")
@login_required
def delete_comment(current_user, comment_id):
    return PostController.delete_comment(current_user, comment_id)


@posts_bp.route("/tag/<tag>")
def posts_by_tag(tag):
    return PostController.posts_by_tag(tag)

from flask import Blueprint
from neo_bloggy.file_upload import (
    gridfs_file,
    upload,
    list_images,
    upload_image,
    delete_image,
    update_image_metadata,
)
from neo_bloggy.auth import login_required

file_upload_bp = Blueprint("file_upload", __name__)


@file_upload_bp.route("/gridfs/<file_id>")
def serve_gridfs_file(file_id):
    return gridfs_file(file_id)


@file_upload_bp.route("/upload", methods=["POST"])
def upload_file():
    return upload()


@file_upload_bp.route("/api/images")
def api_list_images():
    return list_images()


@file_upload_bp.route("/upload-image", methods=["GET", "POST"])
@login_required
def web_upload_image(current_user):
    return upload_image(current_user)


@file_upload_bp.route("/api/images/<file_id>", methods=["DELETE"])
@login_required
def api_delete_image(current_user, file_id):
    return delete_image(current_user, file_id)


@file_upload_bp.route("/api/images/<file_id>", methods=["PUT"])
@login_required
def api_update_image_metadata(current_user, file_id):
    return update_image_metadata(current_user, file_id)

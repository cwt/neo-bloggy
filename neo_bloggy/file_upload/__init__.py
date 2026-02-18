"""File upload module for Neo Bloggy application."""

import hashlib
import io
import logging
import os
import time
import uuid

from flask import (
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)
from PIL import Image
from werkzeug.utils import secure_filename
from neosqlite import gridfs as gridfs_errors

from neo_bloggy.auth import get_current_user
from neo_bloggy.database import (
    get_gridfs,
    get_objectid_for_gridfs,
)
from neo_bloggy.utils import (
    allowed_file,
    validate_image_content,
    get_file_extension_from_content_type,
)
from neo_bloggy.models import Post

logger = logging.getLogger(__name__)


def gridfs_file(file_id):
    """Serve files from GridFS with proper caching headers."""
    # Check if the request is for a JPG conversion (e.g., file_id includes .jpg extension)
    request_for_jpg = False

    if file_id.endswith(".jpg"):
        file_id = file_id[:-4]  # Remove '.jpg' from the end
        request_for_jpg = True

    # Remove any remaining extension (like .webp) from file_id if present
    if "." in file_id:
        file_id = file_id.rsplit(".", 1)[0]

    try:
        gfs = get_gridfs()
        if gfs is None:
            return "File storage system unavailable", 500

        # Convert file_id to ObjectId for GridFS operations
        try:
            gridfs_id = get_objectid_for_gridfs(file_id)
        except ValueError:
            return "Invalid file ID format", 400

        # Open download stream from GridFS
        grid_out = gfs.open_download_stream(gridfs_id)

        # Get file metadata
        filename = grid_out.filename
        # Determine content type based on the original file extension or default to WebP for images
        original_content_type = (
            grid_out.metadata.get("content_type", "image/webp")
            if grid_out.metadata
            else "image/webp"
        )
        file_length = grid_out.length
        upload_date = grid_out.upload_date

        # Generate ETag based on file ID and upload date
        etag_base = f"{gridfs_id}_{upload_date if upload_date else gridfs_id}"
        if request_for_jpg:
            etag_base += "_jpg"  # Add suffix to differentiate between WebP and JPG versions
        etag = hashlib.md5(etag_base.encode()).hexdigest()

        # Check if client has cached version
        if request.headers.get("If-None-Match") == etag:
            return "", 304  # Not modified

        if request_for_jpg:
            # Check file size to prevent memory issues with large files
            # Limit to 20MB (adjust as needed)
            max_file_size = 20 * 1024 * 1024  # 20MB
            if file_length > max_file_size:
                return "File too large for conversion", 413  # Payload too large

            # Convert WebP to JPG
            webp_data = grid_out.read()

            # Validate that the original file is actually a WebP image
            try:
                # Check if the file appears to be WebP by checking magic bytes or trying to open as WebP
                img = Image.open(io.BytesIO(webp_data))
                if img.format != "WEBP":
                    return "JPG conversion only available for WebP images", 400
            except Exception:
                return "JPG conversion only available for WebP images", 400

            try:
                image = Image.open(io.BytesIO(webp_data))

                # Convert RGBA to RGB if necessary (JPG doesn't support transparency)
                if image.mode in ("RGBA", "LA", "P"):
                    # Create a white background for transparent images
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    if image.mode == "P":
                        # Convert palette mode to RGBA first, then composite
                        image = image.convert("RGBA")
                    if image.mode in ("RGBA", "LA"):
                        # Composite the image onto the white background
                        if image.mode == "RGBA":
                            background.paste(image, mask=image.split()[-1])
                        else:
                            background.paste(image, mask=image.split()[-1])
                    image = background
                elif image.mode != "RGB":
                    # Convert other modes (like L, CMYK, etc.) to RGB
                    image = image.convert("RGB")

                # Save as JPG to a BytesIO buffer
                jpg_buffer = io.BytesIO()
                image.save(jpg_buffer, "JPEG", quality=85)
                jpg_buffer.seek(0)
                jpg_data = jpg_buffer.getvalue()

                # Generate response for JPG
                response = make_response(jpg_data)
                response.headers["Content-Type"] = "image/jpeg"
                response.headers["Content-Disposition"] = (
                    f"inline; filename={filename.rsplit('.', 1)[0] if '.' in filename else filename}.jpg"
                )

                # Add caching headers for all images (JPG and WebP both get 1 year cache)
                response.headers["Cache-Control"] = (
                    "public, max-age=31536000"  # Cache for 1 year
                )
                response.headers["ETag"] = etag
                response.headers["Content-Length"] = str(len(jpg_data))

                # Add Last-Modified header if upload_date is available
                if upload_date:
                    # Ensure upload_date is a datetime object
                    if hasattr(upload_date, "strftime"):
                        response.headers["Last-Modified"] = (
                            upload_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                        )
                    else:
                        response.headers["Last-Modified"] = str(upload_date)

                return response
            except Exception as e:
                logger.error(
                    "Error converting WebP to JPG: %s", e, exc_info=True
                )
                return "Error converting image", 500
        else:
            # Serve the original file (WebP)
            # Create response with file data
            response = make_response(grid_out.read())
            response.headers["Content-Type"] = original_content_type
            response.headers["Content-Disposition"] = (
                f"inline; filename={filename}"
            )

            # Add caching headers for all images (JPG and WebP both get 1 year cache)
            response.headers["Cache-Control"] = (
                "public, max-age=31536000"  # Cache for 1 year
            )
            response.headers["ETag"] = etag
            response.headers["Content-Length"] = str(file_length)

            # Add Last-Modified header if upload_date is available
            if upload_date:
                # Ensure upload_date is a datetime object
                if hasattr(upload_date, "strftime"):
                    response.headers["Last-Modified"] = upload_date.strftime(
                        "%a, %d %b %Y %H:%M:%S GMT"
                    )
                else:
                    response.headers["Last-Modified"] = str(upload_date)

            return response
    except gridfs_errors.NoFile:
        return "File not found", 404
    except Exception as e:
        logger.error("Error serving GridFS file: %s", e, exc_info=True)
        return "Error retrieving file", 500


def upload():
    """Handle file uploads from markdown editor."""
    # Check if user is logged in
    if "user" not in session:
        return jsonify({"error": "You must be logged in to upload files"}), 403

    # Check if file is in request
    if "file" not in request.files:
        return jsonify({"error": "No file selected"}), 400

    file = request.files["file"]

    # Check if file is selected
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Check if file has allowed extension
    if file and allowed_file(file.filename):
        # Validate that the file is actually an image
        if not validate_image_content(file):
            return (
                jsonify(
                    {
                        "error": (
                            "File is not a valid image. Please upload PNG, JPG, JPEG, GIF, or WebP images."
                        )
                    }
                ),
                400,
            )

        # Generate a unique filename with user prefix and WebP extension
        filename = secure_filename(file.filename)
        name, _ = os.path.splitext(filename)
        unique_filename = f"{session['user']}_{name}_{uuid.uuid4().hex}.webp"
        original_filename_webp = f"{name}.webp"

        # Save file to GridFS as WebP
        try:
            # Reset file pointer to beginning
            file.seek(0)
            # Open image and convert to WebP
            img = Image.open(file)
            # Convert RGBA to RGB if necessary (WebP supports transparency but it's better to be explicit)
            if img.mode in ("RGBA", "LA"):
                # Create a white background for transparent images
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(
                    img, mask=img.split()[-1] if img.mode == "RGBA" else None
                )
                img = background

            # Save as WebP to a BytesIO buffer
            img_buffer = io.BytesIO()
            img.save(
                img_buffer,
                "WEBP",
                quality=85,
                method=6,
            )
            img_buffer.seek(0)

            # Upload to GridFS
            gfs = get_gridfs()
            if gfs is None:
                return (
                    jsonify({"error": "File storage system unavailable"}),
                    500,
                )

            # Store file in GridFS with metadata
            file_id = gfs.upload_from_stream(
                unique_filename,
                img_buffer,
                metadata={
                    "user": session["user"],
                    "original_filename": original_filename_webp,
                    "uploaded_at": time.time(),
                    "content_type": (
                        "image/webp"
                    ),  # All uploads are converted to WebP
                },
            )

            # Generate URL for the uploaded file (with appropriate extension for social media compatibility)
            content_type = "image/webp"  # All uploads are converted to WebP
            url = url_for(
                "gridfs_file", file_id=file_id
            ) + get_file_extension_from_content_type(content_type)

            # Return success response in format expected by markdown editor
            return jsonify({"data": {"filePath": url}})
        except Exception as e:
            return jsonify({"error": f"Upload failed: {str(e)}"}), 500
    else:
        return (
            jsonify(
                {
                    "error": (
                        "File type not allowed. Please upload PNG, JPG, JPEG, GIF, or WebP images."
                    )
                }
            ),
            400,
        )


def list_images():
    """API endpoint to list uploaded images for the current user or all images for admin with pagination."""
    # Check if user is logged in
    if "user" not in session:
        return jsonify({"error": "You must be logged in to view images"}), 403

    try:
        # Get current user to check admin status
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Authentication error"}), 403

        gfs = get_gridfs()
        if gfs is None:
            return jsonify({"error": "File storage system unavailable"}), 500

        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 12, type=int)
        # Limit per_page to prevent abuse
        per_page = min(per_page, 50)

        # Admins can see all images, regular users can only see their own
        if current_user.get("is_admin", False):
            # Find all files in GridFS (no user filter for admins)
            cursor = gfs.find({})
        else:
            # Use GridFS to find files for the current user by querying metadata
            # Use current_user["name"] for consistency with the user object
            cursor = gfs.find({"metadata.user": current_user["name"]})

        files = list(cursor)
        # Sort by upload date in Python (newest first)
        files.sort(key=lambda x: x.upload_date, reverse=True)

        # Additional security check: ensure non-admin users can only access their own files
        # This is a defensive measure to prevent any potential bypass of the previous check
        if not current_user.get("is_admin", False):
            files = [
                f
                for f in files
                if getattr(f, "metadata", {}).get("user")
                == current_user["name"]
            ]

        # Calculate pagination
        total = len(files)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_files = files[start:end]

        # Create list of image data
        images = []
        for file_doc in paginated_files:
            file_id = file_doc._id
            filename = file_doc.filename
            file_length = file_doc.length
            upload_date = file_doc.upload_date

            file_url = url_for(
                "file_upload.serve_gridfs_file", file_id=file_id
            ) + get_file_extension_from_content_type("image/webp")

            # Extract original filename from metadata if available
            metadata = getattr(file_doc, "metadata", {})
            display_name = metadata.get("original_filename", filename)
            file_user = metadata.get("user", "Unknown")

            images.append(
                {
                    "name": display_name,
                    "url": file_url,
                    "size": file_length,
                    "modified": str(upload_date) if upload_date else None,
                    "user": file_user,  # Include user info for admins
                }
            )

        # Return pagination info along with images
        return jsonify(
            {
                "images": images,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (
                        (total + per_page - 1) // per_page
                    ),  # Ceiling division
                },
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def upload_image(current_user):
    """Handle image uploads from the web interface.
    Prevent disabled users from uploading images.
    """
    if request.method == "POST":
        # Check if file is in request
        if "file" not in request.files:
            flash("No file selected")
            return redirect(request.url)

        file = request.files["file"]

        # Check if file is selected
        if file.filename == "":
            flash("No file selected")
            return redirect(request.url)

        # Check if file has allowed extension
        if file and allowed_file(file.filename):
            # Validate that the file is actually an image
            if not validate_image_content(file):
                flash(
                    "File is not a valid image. Please upload PNG, JPG, JPEG, GIF, or WebP images."
                )
                return redirect(request.url)

            # Generate a unique filename with user prefix and WebP extension
            filename = secure_filename(file.filename)
            name, _ = os.path.splitext(filename)
            unique_filename = (
                f"{current_user['name']}_{name}_{uuid.uuid4().hex}.webp"
            )
            original_filename_webp = f"{name}.webp"

            # Save file to GridFS as WebP
            try:
                # Reset file pointer to beginning
                file.seek(0)
                # Open image and convert to WebP
                img = Image.open(file)
                # Convert RGBA to RGB if necessary
                if img.mode in ("RGBA", "LA"):
                    # Create a white background for transparent images
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(
                        img,
                        mask=img.split()[-1] if img.mode == "RGBA" else None,
                    )
                    img = background

                # Save as WebP to a BytesIO buffer
                img_buffer = io.BytesIO()
                img.save(
                    img_buffer,
                    "WEBP",
                    quality=85,
                    method=6,
                )
                img_buffer.seek(0)

                # Upload to GridFS
                gfs = get_gridfs()
                if gfs is None:
                    flash("File storage system unavailable")
                    return redirect(request.url)

                # Store file in GridFS with metadata
                file_id = gfs.upload_from_stream(
                    unique_filename,
                    img_buffer,
                    metadata={
                        "user": current_user["name"],
                        "original_filename": original_filename_webp,
                        "uploaded_at": time.time(),
                        "content_type": (
                            "image/webp"
                        ),  # All uploads are converted to WebP
                    },
                )

                flash("File uploaded successfully!")
                # Use a special marker for the URL line so the template can handle it differently
                content_type = "image/webp"  # All uploads are converted to WebP
                flash(
                    f"URL_LINE:{url_for('file_upload.serve_gridfs_file', file_id=file_id)}{get_file_extension_from_content_type(content_type)}"
                )
            except Exception as e:
                flash(f"Upload failed: {str(e)}")
        else:
            flash(
                "File type not allowed. Please upload PNG, JPG, JPEG, GIF, or WebP images."
            )

        return redirect(url_for("file_upload.web_upload_image"))

    # GET request - show upload form and list of uploaded files for current user or all files for admin
    try:
        gfs = get_gridfs()
        if gfs is None:
            formatted_files = []
            total_files = 0
        else:
            # Admins can see all images, regular users can only see their own
            if current_user.get("is_admin", False):
                # Find all files in GridFS (no user filter for admins)
                cursor = gfs.find({})
            else:
                # Use GridFS to find files for the current user by querying metadata
                cursor = gfs.find({"metadata.user": current_user["name"]})

            files = list(cursor)
            # Sort by upload date in Python (newest first)
            files.sort(key=lambda x: x.upload_date, reverse=True)

            # Additional security check: ensure non-admin users can only access their own files
            # This is a defensive measure to prevent any potential bypass of the previous check
            if not current_user.get("is_admin", False):
                files = [
                    f
                    for f in files
                    if getattr(f, "metadata", {}).get("user")
                    == current_user["name"]
                ]

            total_files = len(files)

            # Pagination: Get page number from request args, default to 1
            page = request.args.get("page", 1, type=int)
            per_page = 12  # Number of files per page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_files = files[start_idx:end_idx]

            # Create display structure
            formatted_files = []
            for file_doc in paginated_files:
                file_id = file_doc._id
                filename = file_doc.filename

                # Extract original filename from metadata if available
                metadata = getattr(file_doc, "metadata", {})
                display_name = metadata.get("original_filename", filename)
                file_user = metadata.get("user", "Unknown")

                formatted_files.append(
                    {
                        "file_id": file_id,
                        "full_name": filename,
                        "display_name": display_name,
                        "user": file_user,  # Include user info for admins
                    }
                )
    except Exception:
        formatted_files = []
        total_files = 0

    # Calculate pagination info
    page = request.args.get("page", 1, type=int)
    per_page = 12
    total_pages = (total_files + per_page - 1) // per_page  # Ceiling division

    return render_template(
        "upload.html",
        uploaded_files=formatted_files,
        total_files=total_files,
        current_page=page,
        total_pages=total_pages,
        per_page=per_page,
    )


def delete_image(current_user, file_id):
    """Delete an uploaded image.

    Authorization rules:
    - Admin can delete any image
    - Regular users can only delete their own images

    Checks:
    - Verify the image is not being used as a jumbotron in any post
    """
    try:
        # Check if user is logged in
        if not current_user:
            return (
                jsonify({"error": "You must be logged in to delete images"}),
                403,
            )

        # Check if user is active (non-admin users must be active)
        if not current_user.get("is_admin", False) and not current_user.get(
            "is_active", True
        ):
            return (
                jsonify(
                    {
                        "error": "Your account has been disabled. You cannot delete images."
                    }
                ),
                403,
            )

        gfs = get_gridfs()
        if gfs is None:
            return jsonify({"error": "File storage system unavailable"}), 500

        # Convert file_id to ObjectId for GridFS operations
        try:
            gridfs_id = get_objectid_for_gridfs(file_id)
        except ValueError:
            return jsonify({"error": "Invalid file ID format"}), 400

        # Find the file in GridFS using find() with _id filter
        cursor = gfs.find({"_id": gridfs_id})
        files = list(cursor)

        if not files:
            return jsonify({"error": "Image not found"}), 404

        # Get the first (and should be only) file from the cursor
        file_doc = files[0]

        # Get file metadata
        metadata = getattr(file_doc, "metadata", {})
        file_user = metadata.get("user", "Unknown")

        # Check authorization
        is_admin = current_user.get("is_admin", False)
        is_owner = file_user == current_user["name"]

        if not is_admin and not is_owner:
            return (
                jsonify({"error": "You can only delete your own images"}),
                403,
            )

        # Check if the image is being used as a jumbotron in any post
        # Use database query with index for better performance
        posts_using_image = []

        # Search for posts using the exact img_url (all uploads are converted to .webp)
        img_url = (
            url_for("file_upload.serve_gridfs_file", file_id=file_id) + ".webp"
        )
        matching_posts = Post.find_by_img_url(img_url)

        for post in matching_posts:
            posts_using_image.append(
                {
                    "post_id": str(post["_id"]),
                    "title": post.get("title", "Untitled"),
                    "img_url": post.get("img_url", ""),
                }
            )

        # If image is being used, return error with details
        if posts_using_image:
            return (
                jsonify(
                    {
                        "error": "Cannot delete image because it is being used as a jumbotron in the following post(s):",
                        "posts": posts_using_image,
                    }
                ),
                409,
            )  # 409 Conflict

        # Delete the file from GridFS
        gfs.delete(gridfs_id)

        return (
            jsonify({"success": True, "message": "Image deleted successfully"}),
            200,
        )

    except Exception as e:
        logger.error("Error deleting image: %s", e, exc_info=True)
        return jsonify({"error": f"Failed to delete image: {str(e)}"}), 500

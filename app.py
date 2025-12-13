from PIL import Image
from bleach.css_sanitizer import CSSSanitizer
from datetime import datetime
from flask import (
    Flask,
    flash,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
import secrets
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_bootstrap import Bootstrap5
from forms import (
    CommentForm,
    CreatePostForm,
    EditProfileForm,
    LoginForm,
    PasswordRecoveryForm,
    RegisterForm,
)
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import bleach
import io
import markdown
import neosqlite
import os
import re
import time
import tomllib
import uuid

# Configuration flags
HTML_FORMATTING = False  # Set to True for formatting, False for minification


def load_config():
    """Load configuration from file, with support for custom path via environment variable."""
    # Check for custom config path in environment variable
    config_path = os.environ.get("NEO_BLOGGY_CONFIG_PATH", "config.toml")

    config = {}
    if os.path.exists(config_path):
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    return config


# Load configuration
config = load_config()

# Get configuration values with defaults
SECRET_KEY = config.get("app", {}).get("secret_key", "fallback-secret-key")
CACHE_ENABLED = config.get("caching", {}).get("cache_enabled", False)
CACHE_TIMEOUT = config.get("caching", {}).get(
    "cache_timeout", 300
)  # Default 5 minutes

app = Flask(__name__)

# Configure the app to trust proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.secret_key = SECRET_KEY
# Configure session handling for better persistence
# Set SESSION_COOKIE_SECURE to True when running behind HTTPS proxy
app.config["SESSION_COOKIE_SECURE"] = (
    True  # Should be True when behind HTTPS proxy
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24 hours
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

bootstrap = Bootstrap5(app)

# Configure file upload settings
# Note: We're now using GridFS for file storage, so UPLOAD_FOLDER is only used for temporary operations
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = config.get("file_uploads", {}).get(
    "max_content_length", 16 * 1024 * 1024
)  # 16MB max file size

# Create upload directory if it doesn't exist (might be needed for temporary operations)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Allowed file extensions (for upload validation only, all files are converted to WebP)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Database configuration
DB_PATH = config.get("database", {}).get("db_path", "neo-bloggy.db")
TOKENIZER_NAME = config.get("database", {}).get("tokenizer_name", None)
TOKENIZER_PATH = config.get("database", {}).get("tokenizer_path", None)


def allowed_file(filename):
    """Check if the file extension is allowed."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def validate_image_content(file):
    """Validate that the uploaded file is actually an image."""
    try:
        # Reset file pointer to beginning
        file.seek(0)
        # Try to open and verify it's a valid image
        img = Image.open(file)
        img.verify()
        # Reset file pointer again
        file.seek(0)
        return True
    except Exception:
        return False


def markdown_to_html(markdown_text):
    """Convert markdown text to HTML with sanitization."""
    # Convert markdown to HTML
    html = markdown.markdown(
        markdown_text,
        extensions=[
            "extra",
            "codehilite",
            "fenced_code",
        ],
        extension_configs={
            "codehilite": {
                "css_class": "highlight",
            },
        },
    )

    # Create CSS sanitizer to allow safe CSS properties
    css_sanitizer = CSSSanitizer(
        allowed_css_properties=[
            "width",
            "height",
            "max-width",
            "max-height",
            "margin",
            "display",
        ]
    )

    # Sanitize HTML to prevent XSS
    allowed_tags = [
        "a",
        "blockquote",
        "br",
        "code",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "img",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "u",
        "ul",
    ]
    allowed_attributes = {
        "a": ["href", "title"],
        "img": ["src", "alt", "title", "width", "height", "style"],
        "div": ["class"],
        "span": ["class"],
        "pre": ["class"],
    }

    return bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        css_sanitizer=css_sanitizer,
    )


# Cache management
cache_storage = {}


def generate_nonce():
    """Generate a unique nonce for CSP."""
    return secrets.token_urlsafe(16)


def get_csp_nonce():
    """Get or create a CSP nonce for the current request."""
    if not hasattr(g, "csp_nonce"):
        g.csp_nonce = generate_nonce()
    return g.csp_nonce


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
        # Return string representation for parameter binding compatibility
        try:
            import neosqlite

            # Try to create an ObjectId from the value to validate it
            object_id = neosqlite.objectid.ObjectId(id_value)
            # Return string representation for broader compatibility
            return str(object_id)
        except Exception:
            # If all attempts fail, return the original value
            return id_value


def get_cache_key(*args, **kwargs):
    """Generate a cache key from arguments."""
    return str(args) + str(sorted(kwargs.items()))


def get_active_users(db):
    """Get list of active users from the database."""
    return [user["name"] for user in db.users.find({"is_active": True})]


def filter_active_user_content(
    content_list, active_users, author_field="comment_author"
):
    """Filter content to only include items from active users."""
    return [item for item in content_list if item[author_field] in active_users]


def cached_result(func):
    """Decorator to cache function results with timeout."""

    def wrapper(*args, **kwargs):
        if not CACHE_ENABLED:
            return func(*args, **kwargs)

        cache_key = get_cache_key(func.__name__, *args, **kwargs)
        current_time = time.time()

        # Check if we have a cached result that hasn't expired
        if cache_key in cache_storage:
            result, timestamp = cache_storage[cache_key]
            if current_time - timestamp < CACHE_TIMEOUT:
                return result

        # Generate new result and cache it
        result = func(*args, **kwargs)
        cache_storage[cache_key] = (result, current_time)
        return result

    return wrapper


def clear_expired_cache():
    """Remove expired cache entries."""
    if not CACHE_ENABLED:
        return

    current_time = time.time()
    expired_keys = [
        key
        for key, (_, timestamp) in cache_storage.items()
        if current_time - timestamp >= CACHE_TIMEOUT
    ]
    for key in expired_keys:
        del cache_storage[key]


def clear_cache():
    """Clear all cache entries."""
    cache_storage.clear()


# Add a filter to get datetime field from an object (fallback to date if needed)
@app.template_filter("get_datetime")
def get_datetime_filter(obj):
    """Jinja2 filter to get datetime field from an object, falling back to date if needed."""
    if isinstance(obj, dict):
        # Try 'datetime' first, then fall back to 'date'
        return obj.get("datetime") or obj.get("date") or ""
    # If it's already a string/datetime, return as is
    return obj


# Example of how to use caching for expensive operations
@cached_result
def get_post_with_comments(post_id):
    """Get a post with its comments, cached for performance.
    Only show comments from active users.
    """
    db = get_db()

    # Try to query with integer first (for backward compatibility) then ObjectId
    post = db.blog_posts.find_one({"_id": get_id_for_query(post_id)})
    if post:
        comments = list(
            db.blog_comments.find(
                {"parent_post": get_id_for_query(post_id)}
            ).sort("datetime", -1)
        )
        # Filter comments to only show those from active users
        active_users = get_active_users(db)
        comments = filter_active_user_content(
            comments, active_users, "comment_author"
        )
        return post, comments
    return None, []


# Add custom filter for markdown
@app.template_filter("markdown")
def markdown_filter(markdown_text):
    """Jinja2 filter to convert markdown to HTML."""
    return markdown_to_html(markdown_text)


# Add custom filter for datetime formatting
@app.template_filter("format_datetime")
def format_datetime_filter(datetime_str):
    """Jinja2 filter to format ISO datetime string to readable format."""
    try:
        # Parse the ISO format datetime string
        if isinstance(datetime_str, str):
            dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        else:
            # If it's already a datetime object
            dt = datetime_str

        # Format to a readable format - if time is 00:00:00, show just date
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            # Only show date part
            return dt.strftime("%B %d, %Y")
        else:
            # Show both date and time
            return dt.strftime("%B %d, %Y at %H:%M")
    except (ValueError, AttributeError):
        # If parsing fails, return the original string
        return datetime_str


def minify_html(html):
    """Simple HTML minification: right-trim all lines and remove consecutive empty lines.

    Preserves single empty lines that are important for markdown structure,
    while removing excessive whitespace.
    """
    # Split into lines and right-trim whitespace
    lines = [line.rstrip() for line in html.split("\n")]

    # Remove consecutive empty lines, keeping only single empty lines
    cleaned_lines = []
    prev_was_empty = False

    for line in lines:
        is_empty = line == ""

        # If current line is empty and previous line was also empty, skip it
        if is_empty and prev_was_empty:
            continue

        cleaned_lines.append(line)
        prev_was_empty = is_empty

    # Join back with newlines
    minified_html = "\n".join(cleaned_lines)

    return minified_html


def get_file_extension_from_content_type(content_type):
    """Get the appropriate file extension based on content type."""
    extension_map = {
        "image/webp": ".webp",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/ogg": ".ogv",
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
        "application/zip": ".zip",
    }
    return extension_map.get(content_type, "")


def get_content_type_from_file_extension(filename):
    """Get the content type based on file extension."""
    import os

    _, ext = os.path.splitext(filename.lower())
    content_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".ogv": "video/ogg",
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".zip": "application/zip",
    }
    return content_type_map.get(
        ext, "application/octet-stream"
    )  # Default to binary


@app.after_request
def after_request(response):
    """Process HTML responses for minification and clean up expired cache."""
    # Clean up expired cache entries periodically
    if CACHE_ENABLED and int(time.time()) % 60 == 0:  # Roughly every minute
        clear_expired_cache()

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"  # or "SAMEORIGIN" if needed
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Remove any previously set CSP headers to avoid conflicts
    response.headers.pop("Content-Security-Policy", None)
    response.headers.pop("Content-Security-Policy-Report-Only", None)

    # Add Content Security Policy (most permissive for universal compatibility)
    csp_policy = (
        "default-src *; script-src * 'unsafe-inline' 'unsafe-eval'; style-src * 'unsafe-inline'; "
        "img-src * data: blob:; font-src * data:; connect-src *; frame-ancestors *; "
        "object-src 'none'; base-uri 'self';"
    )
    response.headers["Content-Security-Policy"] = csp_policy

    # Add HSTS header
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )

    # Add Cross-Origin-Opener-Policy header
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

    # Minify HTML responses, but be careful not to break markdown-rendered content
    if response.content_type.startswith("text/html"):
        response.set_data(minify_html(response.get_data(as_text=True)))
    return response


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
            print(f"Warning: Failed to initialize with tokenizers: {e}")
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
            # Create datetime index on comments datetime
            g.db.blog_comments.create_index("datetime", datetime_field=True)
            # Create index for parent_post field (heavily used for finding comments for a post)
            g.db.blog_comments.create_index("parent_post")
            # Create index for comment_author field (used for comment management)
            g.db.blog_comments.create_index("comment_author")
            # Create unique index for user names
            g.db.users.create_index("name", unique=True)
            # Create index for user email (used for authentication)
            g.db.users.create_index("email")
            # Create index for user status fields (used frequently in queries)
            g.db.users.create_index("is_active")
            g.db.users.create_index("is_admin")
            g.db.users.create_index("is_publisher")

        # Initialize GridFS for file storage
        try:
            g.gfs = neosqlite.gridfs.GridFSBucket(g.db.db)
        except Exception as e:
            print(f"Warning: Failed to initialize GridFS: {e}")
            g.gfs = None

    return g.db


def get_gridfs():
    """Get GridFS instance for the current request."""
    if "gfs" not in g:
        get_db()  # This will initialize both db and gfs
        if "gfs" not in g:
            # If gfs wasn't initialized in get_db, try to initialize it now
            try:
                g.gfs = neosqlite.gridfs.GridFSBucket(g.db.db)
            except Exception as e:
                print(f"Warning: Failed to initialize GridFS: {e}")
                g.gfs = None
    return g.get("gfs", None)


@app.teardown_appcontext
def close_db(error):
    """Close database connection at the end of the request."""
    if "db" in g:
        g.db.close()
        g.pop("db", None)
    # GridFS doesn't need explicit closing as it uses the same database connection


def get_current_user():
    """
    Get the current logged-in user from session.
    Returns None if no user is logged in or if there's an issue.
    """
    if "user" not in session:
        return None

    try:
        db = get_db()
        user = db.users.find_one({"name": session["user"]})
        # Check if user exists and is active
        if user and user.get("is_active", True):
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
            flash("You need to login to access this page.")
            return redirect(url_for("login"))
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
            flash("You need to login to access this page.")
            return redirect(url_for("login"))
        if not current_user.get("is_admin", False):
            flash("You don't have permission to access this page.")
            return redirect(url_for("get_all_posts"))
        return f(current_user=current_user, *args, **kwargs)

    return decorated_function


@app.context_processor
def inject_site_details():
    """Inject site details into all templates."""
    # Get current user if logged in
    user = get_current_user()

    # Update session if user is logged in
    if user:
        session["user"] = user["name"]

    return {
        "site_title": config.get("app", {}).get("site_title", "Neo Bloggy"),
        "site_author": config.get("app", {}).get("site_author", "Neo Bloggy"),
        "site_description": config.get("app", {}).get(
            "site_description", "Blogging Ireland; journalism"
        ),
        "user": user,
        "csp_nonce": get_csp_nonce(),
    }


# ---------------- #
#   FILE UPLOAD    #
# ---------------- #


@app.route("/gridfs/<file_id>")
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

        # Convert file_id to appropriate format for GridFS operations
        # Use the same logic as get_id_for_query for consistency
        gridfs_id = get_id_for_query(file_id)

        # For GridFS operations, we might still need an ObjectId object in some cases
        # So let's ensure it's properly converted
        if isinstance(gridfs_id, str):
            try:
                import neosqlite

                # If it's a 24-character hex string, create an ObjectId
                if len(gridfs_id) == 24 and all(
                    c in "0123456789abcdefABCDEF" for c in gridfs_id
                ):
                    gridfs_id = neosqlite.objectid.ObjectId(gridfs_id)
                else:
                    # If it's not a hex string, try to convert to int
                    gridfs_id = int(gridfs_id)
            except ValueError:
                return "Invalid file ID format", 400
        elif isinstance(gridfs_id, int):
            # If it's already an integer, that's fine for GridFS operations
            pass
        else:
            # If it's already an ObjectId (or other unexpected type), use as-is
            pass

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
        import hashlib

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
                print(f"Error converting WebP to JPG: {e}")
                import traceback

                traceback.print_exc()
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
    except neosqlite.gridfs.errors.NoFile:
        return "File not found", 404
    except Exception as e:
        print(f"Error serving GridFS file: {e}")
        import traceback

        traceback.print_exc()
        return "Error retrieving file", 500


@app.route("/upload", methods=["POST"])
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
                        "error": "File is not a valid image. Please upload PNG, JPG, JPEG, GIF, or WebP images."
                    }
                ),
                400,
            )

        # Generate a unique filename with user prefix and WebP extension
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{session['user']}_{name}_{uuid.uuid4().hex}.webp"

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
                    "original_filename": filename,
                    "uploaded_at": time.time(),
                    "content_type": "image/webp",  # All uploads are converted to WebP
                },
            )

            # Generate URL for the uploaded file (with appropriate extension for social media compatibility)
            content_type = "image/webp"  # All uploads are converted to WebP
            url = url_for(
                "gridfs_file", file_id=file_id, _external=True
            ) + get_file_extension_from_content_type(content_type)

            # Return success response in format expected by markdown editor
            return jsonify({"data": {"filePath": url}})
        except Exception as e:
            return jsonify({"error": f"Upload failed: {str(e)}"}), 500
    else:
        return (
            jsonify(
                {
                    "error": "File type not allowed. Please upload PNG, JPG, JPEG, GIF, or WebP images."
                }
            ),
            400,
        )


@app.route("/api/images")
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
                "gridfs_file", file_id=file_id, _external=True
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
                    "pages": (total + per_page - 1)
                    // per_page,  # Ceiling division
                },
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload-image", methods=["GET", "POST"])
@login_required
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
            name, ext = os.path.splitext(filename)
            unique_filename = (
                f"{current_user['name']}_{name}_{uuid.uuid4().hex}.webp"
            )

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
                        "original_filename": filename,
                        "uploaded_at": time.time(),
                        "content_type": "image/webp",  # All uploads are converted to WebP
                    },
                )

                flash("File uploaded successfully!")
                # Use a special marker for the URL line so the template can handle it differently
                content_type = "image/webp"  # All uploads are converted to WebP
                flash(
                    f"URL_LINE:{url_for('gridfs_file', file_id=file_id, _external=True)}{get_file_extension_from_content_type(content_type)}"
                )
            except Exception as e:
                flash(f"Upload failed: {str(e)}")
        else:
            flash(
                "File type not allowed. Please upload PNG, JPG, JPEG, GIF, or WebP images."
            )

        return redirect(url_for("upload_image"))

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


# ---------------- #
#    APP ROUTES    #
# ---------------- #


# ----- HOME ----- #
def get_publisher_users(db):
    """Get list of publisher users from the database."""
    return [user["name"] for user in db.users.find({"is_publisher": True})]


@app.route("/")
def get_all_posts():
    """
    Read all blog posts from the database.
    Show all posts to logged-in users, only publisher posts to anonymous users.
    Admins see all posts including from inactive users.
    """
    # Get current user with robust session checking
    current_user = get_current_user()

    # Ensure session is updated with current user info
    if current_user:
        session["user"] = current_user["name"]
    elif "user" in session:
        # If we have a session but no user, clear the session
        session.pop("user", None)

    if CACHE_ENABLED and not current_user:
        # Only cache for non-logged-in users
        # Create a cache key for the main posts list
        cache_key = get_cache_key("get_all_posts")
        current_time = time.time()

        # Check if we have a cached result that hasn't expired
        if cache_key in cache_storage:
            result, timestamp = cache_storage[cache_key]
            if current_time - timestamp < CACHE_TIMEOUT:
                response = make_response(result)
                # Add cache control for anonymous users
                response.headers["Cache-Control"] = (
                    "public, max-age=300"  # Cache for 5 minutes
                )
                return response

        # Generate new result and cache it
        db = get_db()
        # For anonymous users, only show posts from publisher users
        publisher_users = get_publisher_users(db)
        posts = list(
            db.blog_posts.find({"author": {"$in": publisher_users}}).sort(
                "datetime", -1
            )
        )
        result = render_template("index.html", all_posts=posts)
        cache_storage[cache_key] = (result, current_time)
        response = make_response(result)
        # Add cache control for anonymous users
        response.headers["Cache-Control"] = (
            "public, max-age=300"  # Cache for 5 minutes
        )
        return response
    else:
        db = get_db()
        # For logged-in users, show posts from active users (regardless of publisher status)
        # Admins see all posts including from inactive users, others see posts from active users only
        if current_user and current_user.get("is_admin", False):
            # Admins see all posts
            posts = list(db.blog_posts.find().sort("datetime", -1))
        else:
            # Regular users see posts from active users only
            active_users = get_active_users(db)
            posts = list(
                db.blog_posts.find({"author": {"$in": active_users}}).sort(
                    "datetime", -1
                )
            )
        response = make_response(
            render_template("index.html", all_posts=posts, user=current_user)
        )
        # Don't cache for logged-in users
        if current_user:
            response.headers["Cache-Control"] = (
                "no-cache, no-store, must-revalidate"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# ----- REGISTER ----- #
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Sign up for a new account.
    """
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            db = get_db()
            users = db.users

            # check if email already exists in database
            existing_user = users.find_one({"email": form.email.data})

            if existing_user:
                flash(
                    "You've already signed up with that email, log in instead!"
                )
                return redirect(url_for("login"))

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
            return redirect(url_for("profile", username=session["user"]))
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


def ensure_first_admin_is_publisher():
    """
    Function to ensure that if there's only one admin user in the system,
    they also have publisher status (for existing installations that may have been affected
    by the bug where first admin didn't get publisher status).
    """
    db = get_db()
    # Get all admin users
    admin_users = list(db.users.find({"is_admin": True}))

    # If there's only one admin user, make sure they're also a publisher
    if len(admin_users) == 1:
        admin_user = admin_users[0]
        if not admin_user.get("is_publisher", False):
            # Update the admin user to also be a publisher
            try:
                db.users.update_one(
                    {"_id": get_id_for_query(admin_user["_id"])},
                    {"$set": {"is_publisher": True}},
                )
                print(
                    f"Updated admin user '{admin_user['name']}' to also have publisher status."
                )
            except Exception as e:
                print(f"Failed to update admin user to publisher: {e}")


# ----- LOGIN ----- #
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login to the site.

    Validation included.
    Prevent disabled users from logging in.
    """
    form = LoginForm()
    if form.validate_on_submit():
        try:
            db = get_db()
            users = db.users
            email = form.email.data
            password = form.password.data

            # check if email already exists
            existing_user = users.find_one({"email": email})
            # if email doesn't exist or password incorrect
            if not existing_user:
                flash(
                    "That email or password does not exist, please try again."
                )
                return redirect(url_for("login"))
            elif not check_password_hash(existing_user["password"], password):
                flash("That email and password dont match, please try again.")
                return redirect(url_for("login"))
            # Check if user account is disabled
            elif not existing_user.get("is_active", True):
                flash(
                    "Your account has been disabled. Please contact an administrator."
                )
                return redirect(url_for("login"))
            else:
                session.permanent = True  # Make the session permanent
                session["user"] = existing_user["name"]
                flash(f"Welcome Back, {existing_user['name'].title()}")
                return redirect(url_for("profile", username=session["user"]))
        except Exception as e:
            flash(f"Login failed: {str(e)}")
            return render_template("login.html", form=form)
    return render_template("login.html", form=form)


# ----- PROFILE PAGE ----- #
@app.route("/profile/<username>", methods=["GET", "POST"])
@login_required
def profile(current_user, username):
    """
    Direct the user to their Profile page.

    Retrieve all the users Posts.
    """
    # Security check: Only allow users to view their own profile
    if current_user["name"] != username:
        flash("You can only view your own profile.")
        return redirect(url_for("login"))

    db = get_db()
    user = db.users.find_one({"name": username})
    if not user:
        flash("User not found.")
        return redirect(url_for("login"))

    posts = db.blog_posts.find({"author": username}).sort("datetime", -1)
    return render_template(
        "profile.html", username=username, posts=posts, user=user
    )


# ----- EDIT PROFILE ----- #
@app.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile(current_user):
    """
    Edit the user's profile.
    Prevent disabled users from editing their profile.
    """
    # Check if user is active (this is already checked in get_current_user, but being thorough)
    if not current_user.get("is_active", True):
        flash("Your account has been disabled. You cannot edit your profile.")
        return redirect(url_for("get_all_posts"))

    form = EditProfileForm()
    # Populate form fields manually, except for name field (which was removed)
    if request.method == "GET":
        form.email.data = current_user["email"]
        form.security_question.data = current_user.get("security_question", "")
        # Note: We don't populate security_answer for security reasons

    if form.validate_on_submit():
        db = get_db()
        # Check if the new email already exists (excluding current user)
        if form.email.data != current_user["email"]:
            if db.users.find_one(
                {
                    "email": form.email.data,
                    "_id": {"$ne": get_id_for_query(current_user["_id"])},
                }
            ):
                flash("That email is already in use.", "error")
                return render_template("edit_profile.html", form=form)

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
        # Try to update with processed ID first
        try:
            db.users.update_one(
                {"_id": get_id_for_query(current_user["_id"])},
                {"$set": update_data},
            )
        except Exception as e:
            # If parameter binding fails, try with ObjectId directly
            if "Error binding parameter" in str(e) and "ObjectId" in str(e):
                import neosqlite

                # Convert to ObjectId if it's a valid hex string
                try:
                    object_id = neosqlite.objectid.ObjectId(current_user["_id"])
                    db.users.update_one(
                        {"_id": object_id},
                        {"$set": update_data},
                    )
                except Exception:
                    # If all else fails, re-raise the original error
                    raise e
            else:
                # Not the specific error we're handling, re-raise
                raise e

        session.permanent = True  # Make sure session remains permanent
        flash("Profile updated successfully!")
        return redirect(url_for("profile", username=current_user["name"]))
    elif request.method == "GET":
        form.email.data = current_user["email"]
        form.security_question.data = current_user.get("security_question", "")

    return render_template("edit_profile.html", form=form)


# ----- LOGOUT ----- #
@app.route("/logout")
def logout():
    """
    Logout the user.

    Redirect the user to the home page.
    """
    # Clear all session data
    session.clear()

    # Clear cache to ensure no cached content shows logged-in state
    if CACHE_ENABLED:
        clear_cache()

    response = redirect(url_for("get_all_posts"))
    # Add cache control headers to prevent caching of redirect response
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ----- READ A POST BY ITS ID ----- #
@app.route("/post/<post_id>", methods=["GET", "POST"])
def show_post(post_id):
    """
    Read a Post by Id.

    Allow the user to Comment if logged in.
    Only show posts and comments from active users.
    """
    try:
        form = CommentForm()
        db = get_db()

        # Get current user with robust session checking
        current_user = get_current_user()

        # For GET requests, we can use caching
        if request.method == "GET":
            requested_post, requested_post_comments = get_post_with_comments(
                post_id
            )
        else:
            # For POST requests (comments), we need fresh data
            requested_post = db.blog_posts.find_one(
                {"_id": get_id_for_query(post_id)}
            )
            requested_post_comments = db.blog_comments.find(
                {"parent_post": get_id_for_query(post_id)}
            ).sort("datetime", -1)

        # Handle case where post is not found
        if not requested_post:
            flash("Post not found.")
            return redirect(url_for("get_all_posts"))

        # Check if the post author is active (except for admins)
        post_author = db.users.find_one({"name": requested_post["author"]})
        if not post_author:
            flash("The requested post is not available.")
            return redirect(url_for("get_all_posts"))

        # Non-admin users cannot view posts from inactive users
        is_admin = current_user and current_user.get("is_admin", False)
        if not is_admin and not post_author.get("is_active", True):
            flash("The requested post is not available.")
            return redirect(url_for("get_all_posts"))

        # For anonymous users or non-admin users, check if the post author is a publisher
        # Non-publisher posts should only be visible to the author and admins
        if not is_admin and not post_author.get("is_publisher", False):
            # Only the author of the post or admins can view non-publisher posts
            if (
                not current_user
                or current_user.get("name") != requested_post["author"]
            ):
                flash("The requested post is not available.")
                return redirect(url_for("get_all_posts"))

        # Filter comments to only show those from active users
        active_users = get_active_users(db)
        if hasattr(requested_post_comments, "__iter__"):
            requested_post_comments = filter_active_user_content(
                requested_post_comments, active_users, "comment_author"
            )
        else:
            # If it's a cursor, convert to list and filter
            requested_post_comments = filter_active_user_content(
                list(requested_post_comments), active_users, "comment_author"
            )

        # commenting on a post
        if form.validate_on_submit():
            # Get current user with robust session checking
            current_user = get_current_user()
            if not current_user:
                flash("You need to login or register to comment.")
                return redirect(url_for("login"))

            new_comment = {
                "text": form.comment_text.data,
                "comment_author": current_user["name"],
                "parent_post": get_id_for_query(post_id),
                "datetime": datetime.now().isoformat(),
            }

            db.blog_comments.insert_one(new_comment)
            # Clear cache for this post since we've added a comment
            if CACHE_ENABLED:
                cache_key = get_cache_key("get_post_with_comments", post_id)
                if cache_key in cache_storage:
                    del cache_storage[cache_key]
            flash("Comment added successfully!")
            return redirect(url_for("show_post", post_id=post_id))

        # Get author information to check if author is a publisher
        post_author_info = db.users.find_one({"name": requested_post["author"]})

        return render_template(
            "post.html",
            post=requested_post,
            comments=requested_post_comments,
            form=form,
            post_author_info=post_author_info,
            user=current_user,
        )
    except Exception as e:
        flash(f"Error loading post: {str(e)}")
        return redirect(url_for("get_all_posts"))


# ----- CREATE A NEW POST ----- #
@app.route("/create-post", methods=["GET", "POST"])
@login_required
def create_post(current_user):
    """
    Create a new Post.

    Inject all form data to a new blog post document on submit.
    Prevent disabled users from creating posts.
    """
    # create a Form for data entry
    form = CreatePostForm()
    if form.validate_on_submit():
        try:
            db = get_db()
            # Process tags: split by comma and clean up
            tags = []
            if form.tags.data:
                tags = [
                    tag.strip()
                    for tag in form.tags.data.split(",")
                    if tag.strip()
                ]
            new_post = {
                "title": form.title.data,
                "subtitle": form.subtitle.data,
                "body": form.body.data,
                "img_url": form.img_url.data,
                "author": current_user["name"],
                "datetime": datetime.now().isoformat(),
                "tags": tags,  # Add tags to the post
            }
            db.blog_posts.insert_one(new_post)
            flash("Post Successfully Added")
            # Clear cache since we've added a new post
            if CACHE_ENABLED:
                # Only clear the main posts list cache
                cache_key = get_cache_key("get_all_posts")
                if cache_key in cache_storage:
                    del cache_storage[cache_key]
            return redirect(url_for("get_all_posts"))
        except Exception as e:
            flash(f"Failed to create post: {str(e)}")
            return render_template("create_post.html", form=form)
    return render_template("create_post.html", form=form)


# ----- EDIT A POST BY ID ----- #
@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
@login_required
def edit_post(current_user, post_id):
    """
    Edit a Post by Id.

    Update all Post data on submit.
    Prevent disabled users from editing posts.
    Admins can edit any post.
    """
    try:
        db = get_db()
        post = db.blog_posts.find_one({"_id": get_id_for_query(post_id)})

        if not post:
            flash("Post not found.")
            return redirect(url_for("get_all_posts"))

        # Check if user is the author of the post or an admin
        is_admin = current_user.get("is_admin", False)
        is_post_author = post["author"] == current_user["name"]

        if not is_admin and not is_post_author:
            flash("You can only edit your own posts.")
            return redirect(url_for("get_all_posts"))

        # Prevent disabled non-admin users from editing posts
        if not is_admin and not current_user.get("is_active", True):
            flash("Your account has been disabled. You cannot edit posts.")
            return redirect(url_for("get_all_posts"))

        edit_form = CreatePostForm(
            title=post["title"],
            subtitle=post["subtitle"],
            img_url=post["img_url"],
            author=current_user["name"],
            body=post["body"],
            tags=", ".join(
                post.get("tags", [])
            ),  # Populate existing tags if they exist
        )
        if edit_form.validate_on_submit():
            # Process tags: split by comma and clean up
            tags = []
            if edit_form.tags.data:
                tags = [
                    tag.strip()
                    for tag in edit_form.tags.data.split(",")
                    if tag.strip()
                ]
            # Try to update with processed ID first
            try:
                db.blog_posts.update_one(
                    {"_id": get_id_for_query(post_id)},
                    {
                        "$set": {
                            "title": edit_form.title.data,
                            "subtitle": edit_form.subtitle.data,
                            "img_url": edit_form.img_url.data,
                            "body": edit_form.body.data,
                            "tags": tags,  # Update tags as well
                        }
                    },
                )
            except Exception as e:
                # If parameter binding fails, try with ObjectId directly
                if "Error binding parameter" in str(e) and "ObjectId" in str(e):
                    import neosqlite

                    # Convert to ObjectId if it's a valid hex string
                    try:
                        object_id = neosqlite.objectid.ObjectId(post_id)
                        db.blog_posts.update_one(
                            {"_id": object_id},
                            {
                                "$set": {
                                    "title": edit_form.title.data,
                                    "subtitle": edit_form.subtitle.data,
                                    "img_url": edit_form.img_url.data,
                                    "body": edit_form.body.data,
                                }
                            },
                        )
                    except Exception:
                        # If all else fails, re-raise the original error
                        raise e
                else:
                    # Not the specific error we're handling, re-raise
                    raise e
            # Clear cache since we've modified a post
            if CACHE_ENABLED:
                # Clear cache for this specific post
                cache_key = get_cache_key("get_post_with_comments", post_id)
                if cache_key in cache_storage:
                    del cache_storage[cache_key]
                # Also clear main posts list cache
                cache_key = get_cache_key("get_all_posts")
                if cache_key in cache_storage:
                    del cache_storage[cache_key]
            flash("Post Successfully Updated")
            return redirect(url_for("show_post", post_id=post_id))
        return render_template(
            "create_post.html", form=edit_form, is_edit=True, post=post
        )
    except Exception as e:
        flash(f"Failed to edit post: {str(e)}")
        return redirect(url_for("get_all_posts"))


# ----- DELETE A POST BY ID ----- #
@app.route("/delete/<post_id>")
@login_required
def delete_post(current_user, post_id):
    """
    Delete a Post by Id.

    Redirect back to main page on submit.
    Prevent disabled users from deleting posts.
    Admins can delete any post.
    """
    try:
        db = get_db()
        # Verify the post exists and get it
        post = db.blog_posts.find_one({"_id": get_id_for_query(post_id)})
        if not post:
            flash("Post not found.")
            return redirect(url_for("get_all_posts"))

        # Check if the current user is the author of the post or an admin
        is_admin = current_user.get("is_admin", False)
        is_post_author = post["author"] == current_user["name"]

        if not is_admin and not is_post_author:
            flash("You can only delete your own posts.")
            return redirect(url_for("get_all_posts"))

        # Prevent disabled non-admin users from deleting posts
        if not is_admin and not current_user.get("is_active", True):
            flash("Your account has been disabled. You cannot delete posts.")
            return redirect(url_for("get_all_posts"))

        # Try to delete with processed ID first
        try:
            db.blog_posts.delete_one({"_id": get_id_for_query(post_id)})
        except Exception as e:
            # If parameter binding fails, try with ObjectId directly
            if "Error binding parameter" in str(e) and "ObjectId" in str(e):
                import neosqlite

                # Convert to ObjectId if it's a valid hex string
                try:
                    object_id = neosqlite.objectid.ObjectId(post_id)
                    db.blog_posts.delete_one({"_id": object_id})
                except Exception:
                    # If all else fails, re-raise the original error
                    raise e
            else:
                # Not the specific error we're handling, re-raise
                raise e
        flash("Post Successfully Deleted")
        # Clear cache since we've deleted a post
        if CACHE_ENABLED:
            # Clear cache for this specific post
            cache_key = get_cache_key("get_post_with_comments", post_id)
            if cache_key in cache_storage:
                del cache_storage[cache_key]
            # Also clear main posts list cache
            cache_key = get_cache_key("get_all_posts")
            if cache_key in cache_storage:
                del cache_storage[cache_key]
        return redirect(url_for("get_all_posts"))
    except Exception as e:
        flash(f"Failed to delete post: {str(e)}")
        return redirect(url_for("get_all_posts"))


# ----- DELETE A COMMENT BY ID ----- #
@app.route("/delete_comment/<comment_id>")
@login_required
def delete_comment(current_user, comment_id):
    """
    Delete a Comment by Id.
    Only allow the comment author (if active) or admins to delete comments.
    """
    db = get_db()

    # Get the comment to delete
    comment = db.blog_comments.find_one({"_id": get_id_for_query(comment_id)})
    if not comment:
        flash("Comment not found.")
        post_id = request.args.get("post_id")
        return redirect(url_for("show_post", post_id=post_id))

    # Check if user is admin or the comment author
    is_admin = current_user.get("is_admin", False)
    is_comment_author = comment["comment_author"] == current_user["name"]

    # If user is not admin and not the comment author, deny access
    if not is_admin and not is_comment_author:
        flash("You can only delete your own comments.")
        post_id = request.args.get("post_id")
        return redirect(url_for("show_post", post_id=post_id))

    # If user is not admin but is the comment author, check if they're active
    if not is_admin and is_comment_author:
        if not current_user.get("is_active", True):
            flash("Your account has been disabled. You cannot delete comments.")
            post_id = request.args.get("post_id")
            return redirect(url_for("show_post", post_id=post_id))

    # Proceed with deletion
    # Try to delete with processed ID first
    try:
        db.blog_comments.delete_one({"_id": get_id_for_query(comment_id)})
    except Exception as e:
        # If parameter binding fails, try with ObjectId directly
        if "Error binding parameter" in str(e) and "ObjectId" in str(e):
            import neosqlite

            # Convert to ObjectId if it's a valid hex string
            try:
                object_id = neosqlite.objectid.ObjectId(comment_id)
                db.blog_comments.delete_one({"_id": object_id})
            except Exception:
                # If all else fails, re-raise the original error
                raise e
        else:
            # Not the specific error we're handling, re-raise
            raise e
    flash("Comment Successfully Deleted")
    post_id = request.args.get("post_id")
    # Clear cache for this post since we've deleted a comment
    if CACHE_ENABLED:
        cache_key = get_cache_key("get_post_with_comments", post_id)
        if cache_key in cache_storage:
            del cache_storage[cache_key]
    return redirect(url_for("show_post", post_id=post_id))


# ----- DISPLAY POSTS BY TAG ----- #
@app.route("/tag/<tag>")
def posts_by_tag(tag):
    """
    Display all posts with a specific tag.
    Using NeoSQLite $elemMatch operator to find tags in the array.
    """
    # Get current user with robust session checking
    current_user = get_current_user()

    db = get_db()

    # Build the search filter based on user status
    # Use $elemMatch to find if tag exists in the tags array
    # $elemMatch was fixed in NeoSQLite v1.2.2 to work with simple arrays
    tag_filter = {"tags": {"$elemMatch": tag}}

    if current_user:
        if current_user.get("is_admin", False):
            # Admins can see all posts by tag
            search_filter = tag_filter
        else:
            # Regular logged-in users can see posts from active users by tag
            active_users = get_active_users(db)
            search_filter = {
                "$and": [tag_filter, {"author": {"$in": active_users}}]
            }
    else:
        # Anonymous users can only see posts from publisher users
        publisher_users = get_publisher_users(db)
        search_filter = {
            "$and": [tag_filter, {"author": {"$in": publisher_users}}]
        }

    # Find posts with the specified tag
    posts = list(db.blog_posts.find(search_filter).sort("datetime", -1))

    # Also get related tags for this tag to show related tags
    # First find all unique tags used in posts with this tag
    all_posts_with_tag = list(db.blog_posts.find(search_filter))
    all_tags = set()
    for post in all_posts_with_tag:
        for post_tag in post.get("tags", []):
            if (
                post_tag and post_tag.lower() != tag.lower()
            ):  # Exclude the current tag
                all_tags.add(post_tag)

    related_tags = sorted(list(all_tags))[:10]  # Limit to 10 related tags

    response = make_response(
        render_template(
            "index.html",
            all_posts=posts,
            search_query=f"tag: {tag}",
            user=current_user,
            tag=tag,
            related_tags=related_tags,
        )
    )
    # Don't cache tag results as they may change frequently
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ----- SEARCH FOR A POST BY TITLE, SUBTITLE, BODY ----- #
@app.route("/search", methods=["GET", "POST"])
def search():
    """
    Search for a Post by Title, Subtitle, and Body Content.
    Show posts to logged-in users, only publisher posts to anonymous users.
    Admins can search all posts including from inactive users.
    """
    # Get current user with robust session checking
    current_user = get_current_user()

    db = get_db()
    query = request.form.get("query")

    # Security check: Reject URLs and code patterns
    if query and is_suspicious_input(query):
        flash("Invalid search query. Please use only text in search.")
        return redirect(url_for("get_all_posts"))

    # Get active users for regular users, publisher users for anonymous users
    if current_user:
        if current_user.get("is_admin", False):
            # Admins can search all posts
            relevant_users = []
            search_filter_base = {}
        else:
            # Regular logged-in users can search posts from active users
            active_users = get_active_users(db)
            relevant_users = active_users
            search_filter_base = {"author": {"$in": active_users}}
    else:
        # Anonymous users can only search posts from publisher users
        publisher_users = get_publisher_users(db)
        relevant_users = publisher_users
        search_filter_base = {"author": {"$in": publisher_users}}

    # For neosqlite, we'll use the $text operator with FTS for efficient text search
    if query:
        try:
            # Use neosqlite's $text with $search for FTS-based search
            # This will search across all FTS-indexed fields (title, subtitle, and body)

            # Add the author filter to the search filter
            search_filter = (
                {"$and": [{"$text": {"$search": query}}, search_filter_base]}
                if relevant_users
                else {"$text": {"$search": query}}
            )

            posts = list(db.blog_posts.find(search_filter).sort("datetime", -1))

            # Add search relevance scoring
            # NeoSQLite provides a textScore metadata field when using $text search
            for post in posts:
                if hasattr(post, "_meta") and "textScore" in post._meta:
                    post["search_score"] = post._meta["textScore"]
                else:
                    post["search_score"] = 0

            # Sort by search relevance (highest score first), but maintain datetime order for ties
            posts.sort(
                key=lambda x: (x.get("search_score", 0), x.get("datetime", "")),
                reverse=True,
            )

        except Exception:
            # If FTS query fails due to special characters, fall back to regex search
            # This is a more basic search but will handle special characters
            import re

            escaped_query = re.escape(query)

            # Build the search filter based on user status
            if relevant_users:
                search_filter = {
                    "$and": [
                        {
                            "$or": [
                                {
                                    "title": {
                                        "$regex": escaped_query,
                                        "$options": "i",
                                    }
                                },
                                {
                                    "subtitle": {
                                        "$regex": escaped_query,
                                        "$options": "i",
                                    }
                                },
                                {
                                    "body": {
                                        "$regex": escaped_query,
                                        "$options": "i",
                                    }
                                },
                            ]
                        },
                        {"author": {"$in": relevant_users}},
                    ]
                }
            else:
                # For admins with no user filter
                search_filter = {
                    "$or": [
                        {
                            "title": {
                                "$regex": escaped_query,
                                "$options": "i",
                            }
                        },
                        {
                            "subtitle": {
                                "$regex": escaped_query,
                                "$options": "i",
                            }
                        },
                        {
                            "body": {
                                "$regex": escaped_query,
                                "$options": "i",
                            }
                        },
                    ]
                }

            posts = list(db.blog_posts.find(search_filter).sort("datetime", -1))
    else:
        # Show posts based on user status (active users for logged-in, publisher users for anonymous)
        if relevant_users:
            posts = list(
                db.blog_posts.find({"author": {"$in": relevant_users}})
            )
        else:
            # Admin viewing all posts
            posts = list(db.blog_posts.find())

    response = make_response(
        render_template(
            "index.html", all_posts=posts, search_query=query, user=current_user
        )
    )
    # Don't cache search results
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def is_suspicious_input(text):
    """
    Check if the input text contains URLs or programming code patterns.

    Returns True if suspicious content is detected.
    """

    # Check for URLs (more precise patterns)
    url_patterns = [
        r"https?://[^\s]+",
        r"www\.[^\s]+",
        r"[^\s]+\.(?:com|org|net|edu|gov|mil|int|co|uk|de|fr|jp|cn|au|ca|ru|br|in|it|es)[^\s]*",
    ]

    for pattern in url_patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error:
            # Skip invalid patterns
            continue

    # Check for common code patterns
    code_patterns = [
        # HTML/JS tags
        r"<\s*(script|iframe|object|embed|link|style|meta|form)\b",
        # SQL injection patterns (more precise)
        r"\b(union\s+select|insert\s+into|update\s+\w+\s+set|delete\s+from|drop\s+table|create\s+table|alter\s+table)\b",
        # JavaScript dangerous functions
        r"\b(eval|document\.cookie|window\.location|location\.href)\s*\(",
        # CSS expressions
        r"expression\s*\(",
        # PHP tags
        r"<\?php",
        r"<\?",
        # Shell commands
        r"\b(rm\s+-rf|chmod\s+\d{3,4}|wget\s+http|curl\s+http)\b",
        # File paths (Unix/Windows)
        r"\b(?:[A-Za-z]:[\/\\]|\/|\.{0,2}\/)[\w\/\\.-]+(?:[\/\\][\w\/\\.-]+)*\b",
    ]

    for pattern in code_patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error:
            # Skip invalid patterns
            continue

    # Check for excessive special characters (potential obfuscation)
    # Only apply this check for longer texts to avoid false positives
    if len(text) > 20:
        special_chars = len(re.findall(r"[^\w\s]", text))
        if special_chars / len(text) > 0.3:  # More than 30% special chars
            return True

    return False


# ----- PASSWORD RECOVERY ----- #
@app.route("/recover-password", methods=["GET", "POST"])
def recover_password():
    """
    Recover password using security question.
    Prevent disabled users from recovering password.
    """
    form = PasswordRecoveryForm()
    if form.validate_on_submit():
        db = get_db()
        users = db.users

        # check if email exists in database
        user = users.find_one({"email": form.email.data})

        if not user:
            flash("No account found with that email address.")
            return render_template("recover_password.html", form=form)

        # Check if user account is disabled
        if not user.get("is_active", True):
            flash(
                "Your account has been disabled. Please contact an administrator."
            )
            return render_template("recover_password.html", form=form)

        # check if security question and answer match
        if form.security_question.data == user.get(
            "security_question"
        ) and check_password_hash(
            user["security_answer"], form.security_answer.data.lower()
        ):

            # Update password
            new_password_hash = generate_password_hash(
                form.password.data, method="pbkdf2:sha256", salt_length=8
            )
            users.update_one(
                {"_id": user["_id"]}, {"$set": {"password": new_password_hash}}
            )

            flash(
                "Password successfully reset. You can now log in with your new password."
            )
            return redirect(url_for("login"))
        else:
            flash("Security question or answer is incorrect.")

    return render_template("recover_password.html", form=form)


# ----- ADMIN PANEL ----- #
@app.route("/admin")
@admin_required
def admin_panel(current_user):
    """
    Admin panel to manage users and content.
    """
    db = get_db()
    # Get all users (except the current admin)
    users = list(db.users.find({"name": {"$ne": current_user["name"]}}))

    return render_template("admin.html", users=users)


@app.route("/admin/toggle_user_status/<user_id>", methods=["POST"])
@admin_required
def toggle_user_status(current_user, user_id):
    """
    Toggle a user's active status (enable/disable).
    """
    db = get_db()
    # Find the user to toggle
    user_to_toggle = db.users.find_one({"_id": get_id_for_query(user_id)})

    if not user_to_toggle:
        flash("User not found.")
        return redirect(url_for("admin_panel"))

    # Prevent admins from disabling other admins
    if user_to_toggle.get("is_admin", False):
        flash("You cannot disable another admin user.")
        return redirect(url_for("admin_panel"))

    # Toggle the user's active status
    # Toggle the user's active status
    new_status = not user_to_toggle.get("is_active", True)
    # Try to update with processed ID first
    try:
        db.users.update_one(
            {"_id": get_id_for_query(user_id)},
            {"$set": {"is_active": new_status}},
        )
    except Exception as e:
        # If parameter binding fails, try with ObjectId directly
        if "Error binding parameter" in str(e) and "ObjectId" in str(e):
            import neosqlite

            # Convert to ObjectId if it's a valid hex string
            try:
                object_id = neosqlite.objectid.ObjectId(user_id)
                db.users.update_one(
                    {"_id": object_id}, {"$set": {"is_active": new_status}}
                )
            except Exception:
                # If all else fails, re-raise the original error
                raise e
        else:
            # Not the specific error we're handling, re-raise
            raise e

    status_text = "enabled" if new_status else "disabled"
    flash(f"User '{user_to_toggle['name']}' has been {status_text}.")

    # Clear cache since we've modified user status
    if CACHE_ENABLED:
        clear_cache()

    return redirect(url_for("admin_panel"))


@app.route("/admin/make_admin/<user_id>", methods=["POST"])
@admin_required
def make_admin(current_user, user_id):
    """
    Make a user an admin.
    """
    db = get_db()
    # Find the user to make admin
    user_to_make_admin = db.users.find_one({"_id": get_id_for_query(user_id)})

    if not user_to_make_admin:
        flash("User not found.")
        return redirect(url_for("admin_panel"))

    # Make the user an admin
    # Try to update with processed ID first
    try:
        db.users.update_one(
            {"_id": get_id_for_query(user_id)}, {"$set": {"is_admin": True}}
        )
    except Exception as e:
        # If parameter binding fails, try with ObjectId directly
        if "Error binding parameter" in str(e) and "ObjectId" in str(e):
            import neosqlite

            # Convert to ObjectId if it's a valid hex string
            try:
                object_id = neosqlite.objectid.ObjectId(user_id)
                db.users.update_one(
                    {"_id": object_id}, {"$set": {"is_admin": True}}
                )
            except Exception:
                # If all else fails, re-raise the original error
                raise e
        else:
            # Not the specific error we're handling, re-raise
            raise e

    flash(f"User '{user_to_make_admin['name']}' is now an admin.")

    # Clear cache since we've modified user permissions
    if CACHE_ENABLED:
        clear_cache()

    return redirect(url_for("admin_panel"))


@app.route("/admin/toggle_publisher/<user_id>", methods=["POST"])
@admin_required
def toggle_publisher(current_user, user_id):
    """
    Toggle a user's publisher status.
    """
    db = get_db()
    # Find the user to toggle
    user_to_toggle = db.users.find_one({"_id": get_id_for_query(user_id)})

    if not user_to_toggle:
        flash("User not found.")
        return redirect(url_for("admin_panel"))

    # Toggle the user's publisher status
    new_publisher_status = not user_to_toggle.get("is_publisher", False)
    # Try to update with processed ID first
    try:
        db.users.update_one(
            {"_id": get_id_for_query(user_id)},
            {"$set": {"is_publisher": new_publisher_status}},
        )
    except Exception as e:
        # If parameter binding fails, try with ObjectId directly
        if "Error binding parameter" in str(e) and "ObjectId" in str(e):
            import neosqlite

            # Convert to ObjectId if it's a valid hex string
            try:
                object_id = neosqlite.objectid.ObjectId(user_id)
                db.users.update_one(
                    {"_id": object_id},
                    {"$set": {"is_publisher": new_publisher_status}},
                )
            except Exception:
                # If all else fails, re-raise the original error
                raise e
        else:
            # Not the specific error we're handling, re-raise
            raise e

    status_text = "published" if new_publisher_status else "unpublished"
    flash(f"User '{user_to_toggle['name']}' has been marked as {status_text}.")

    # Clear cache since we've modified user status
    if CACHE_ENABLED:
        clear_cache()

    return redirect(url_for("admin_panel"))


@app.route("/admin/rebuild-search-indexes", methods=["POST"])
@admin_required
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

    return redirect(url_for("admin_panel"))


@app.route("/admin/unpublished-posts")
@admin_required
def unpublished_posts(current_user):
    """
    Admin view to see all unpublished posts.
    Includes posts from non-publisher users, regardless of active status.
    """
    db = get_db()

    # Get all users who are not publishers
    non_publisher_users = [
        user["name"] for user in db.users.find({"is_publisher": False})
    ]

    # Get all posts by non-publisher users
    posts = list(
        db.blog_posts.find({"author": {"$in": non_publisher_users}}).sort(
            "datetime", -1
        )
    )

    # Get user information for each post author
    post_authors = {}
    for post in posts:
        if post["author"] not in post_authors:
            author = db.users.find_one({"name": post["author"]})
            post_authors[post["author"]] = author

    return render_template(
        "unpublished_posts.html", posts=posts, post_authors=post_authors
    )


# ----- SITEMAP ----- #
@app.route("/sitemap.xml")
def sitemap():
    """Generate a sitemap for the blog."""
    db = get_db()
    posts = list(db.blog_posts.find().sort("datetime", -1))

    # Get the current date for the sitemap
    current_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Process posts to ensure proper datetime formatting
    for post in posts:
        # Check for datetime field first, then fallback to date for backward compatibility
        datetime_value = post.get("datetime") or post.get("date")

        if datetime_value:
            # The datetime could be in ISO format datetime string
            try:
                if isinstance(datetime_value, str):
                    # Parse the ISO format datetime string
                    date_obj = datetime.fromisoformat(
                        datetime_value.replace("Z", "+00:00")
                    )
                else:
                    # If it's already a datetime object, use it directly
                    date_obj = datetime_value

                # Format it as YYYY-MM-DD for sitemap
                post["lastmod"] = date_obj.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                # If parsing fails, use current date as fallback
                post["lastmod"] = current_date
        else:
            post["lastmod"] = current_date

    return (
        render_template("sitemap.xml", posts=posts, current_date=current_date),
        200,
        {"Content-Type": "application/xml"},
    )


# ----- FAVICON ----- #
@app.route("/favicon.ico")
def favicon():
    """Serve the favicon.ico file."""
    return send_from_directory(
        os.path.join(app.root_path, "static", "img"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


# ----- ROBOTS.TXT ----- #
@app.route("/robots.txt")
def robots_txt():
    """Generate a dynamic robots.txt file with absolute sitemap URL."""
    # Get the base URL from the request
    base_url = request.url_root

    # Generate the absolute sitemap URL
    sitemap_url = base_url + "sitemap.xml"

    # Render the robots.txt template with the sitemap URL
    return (
        render_template("robots.txt", sitemap_url=sitemap_url),
        200,
        {"Content-Type": "text/plain"},
    )


# ----- HANDLE 404 ERROR ----- #
@app.errorhandler(404)
def page_not_found_404(e):
    return render_template("404.html"), 404


# ----- HANDLE 403 ERROR ----- #
@app.errorhandler(403)
def page_not_found_403(e):
    return render_template("403.html"), 403


# ----- HANDLE 500 ERROR ----- #
@app.errorhandler(500)
def page_not_found_500(e):
    return render_template("500.html"), 500


def ensure_tags_field_on_posts():
    """
    Ensure all existing posts have a tags field. Add an empty array if missing.
    """
    db = get_db()
    # Find all posts that don't have a tags field and add an empty array
    posts_without_tags = list(db.blog_posts.find({"tags": {"$exists": False}}))

    updated_count = 0
    for post in posts_without_tags:
        try:
            db.blog_posts.update_one(
                {"_id": post["_id"]}, {"$set": {"tags": []}}
            )
            updated_count += 1
        except Exception as e:
            print(f"Error updating post {post['_id']}: {e}")

    if updated_count > 0:
        print(f"Updated {updated_count} posts to include empty tags array")
    else:
        print("All posts already have the tags field")


if __name__ == "__main__":
    # Check if we're running in Docker by looking for the FLASK_RUN_HOST environment variable
    host = os.environ.get(
        "FLASK_RUN_HOST", config.get("app", {}).get("ip", "127.0.0.1")
    )
    app.run(
        host=host,
        port=int(config.get("app", {}).get("port", 5000)),
        debug=True,
    )

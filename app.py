import os
from flask import (
    Flask,
    flash,
    render_template,
    redirect,
    request,
    session,
    url_for,
    g,
    jsonify,
    send_from_directory,
    after_this_request,
)
from flask_bootstrap import Bootstrap5
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date
import neosqlite
import uuid
import markdown
import bleach
from bleach.css_sanitizer import CSSSanitizer
import re
from functools import lru_cache
import time
import requests
from PIL import Image
import io

# Configuration flags
HTML_FORMATTING = False  # Set to True for formatting, False for minification
CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "False").lower() == "true"
CACHE_TIMEOUT = int(os.environ.get("CACHE_TIMEOUT", "300"))  # Default 5 minutes

if os.path.exists("env.py"):
    import env

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")
bootstrap = Bootstrap5(app)

from forms import (
    RegisterForm,
    LoginForm,
    CreatePostForm,
    CommentForm,
    EditProfileForm,
    PasswordRecoveryForm,
)

# Configure file upload settings
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Allowed file extensions (for upload validation only, all files are converted to WebP)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Database configuration
DB_PATH = os.environ.get("DB_PATH", "/tmp/neosqlite.db")
TOKENIZER_NAME = os.environ.get("TOKENIZER_NAME", None)
TOKENIZER_PATH = os.environ.get("TOKENIZER_PATH", None)


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
        "p",
        "br",
        "strong",
        "em",
        "u",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "code",
        "pre",
        "ul",
        "ol",
        "li",
        "a",
        "img",
        "hr",
        "div",
        "span",
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


def get_cache_key(*args, **kwargs):
    """Generate a cache key from arguments."""
    return str(args) + str(sorted(kwargs.items()))


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


# Example of how to use caching for expensive operations
@cached_result
def get_post_with_comments(post_id):
    """Get a post with its comments, cached for performance."""
    db = get_db()
    post = db.blog_posts.find_one({"_id": int(post_id)})
    if post:
        comments = list(db.blog_comments.find({"parent_post": int(post_id)}))
        return post, comments
    return None, []


# Add custom filter for markdown
@app.template_filter("markdown")
def markdown_filter(markdown_text):
    """Jinja2 filter to convert markdown to HTML."""
    return markdown_to_html(markdown_text)


def minify_html(html):
    """Simple HTML minification to remove empty lines and whitespace-only lines while preserving content indentation."""
    # Split into lines
    lines = html.split("\n")

    # Filter out empty lines and lines with only whitespace
    filtered_lines = []
    for line in lines:
        # If line has content (not just whitespace), keep it
        if line.strip():
            filtered_lines.append(line)

    # Join back with newlines
    minified_html = "\n".join(filtered_lines)

    return minified_html


@app.after_request
def after_request(response):
    """Process HTML responses for minification and clean up expired cache."""
    # Clean up expired cache entries periodically
    if CACHE_ENABLED and int(time.time()) % 60 == 0:  # Roughly every minute
        clear_expired_cache()

    # Minify HTML responses
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
        except Exception as e:
            # Fallback to connection without tokenizers
            print(f"Warning: Failed to initialize with tokenizers: {e}")
            g.db = neosqlite.Connection(DB_PATH, tokenizers=None)
            # Create FTS indexes without specific tokenizer
            g.db.blog_posts.create_index("title", fts=True)
            g.db.blog_posts.create_index("subtitle", fts=True)
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection at the end of the request."""
    if "db" in g:
        g.db.close()
        g.pop("db", None)


@app.context_processor
def inject_site_details():
    """Inject site details into all templates."""
    return {
        "site_title": os.environ.get("SITE_TITLE", "Medium Bloggy"),
        "site_author": os.environ.get("SITE_AUTHOR", "Medium Bloggy"),
        "site_description": os.environ.get(
            "SITE_DESCRIPTION", "Blogging Ireland; journalism"
        ),
    }


# ---------------- #
#   FILE UPLOAD    #
# ---------------- #


@app.route("/files/<path:filename>")
def uploaded_files(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


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

        # Save file as WebP
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

            # Save as WebP with good quality
            img.save(
                os.path.join(app.config["UPLOAD_FOLDER"], unique_filename),
                "WEBP",
                quality=85,
                method=6,
            )

            # Generate URL for the uploaded file
            url = url_for(
                "uploaded_files", filename=unique_filename, _external=True
            )

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
    """API endpoint to list uploaded images for the current user."""
    # Check if user is logged in
    if "user" not in session:
        return jsonify({"error": "You must be logged in to view images"}), 403

    try:
        # Get all uploaded files
        files = os.listdir(app.config["UPLOAD_FOLDER"])
        # Filter only image files that belong to the current user
        user_prefix = f"{session['user']}_"
        image_files = [
            f for f in files if allowed_file(f) and f.startswith(user_prefix)
        ]
        # Sort by modification time (newest first)
        image_files.sort(
            key=lambda x: os.path.getmtime(
                os.path.join(app.config["UPLOAD_FOLDER"], x)
            ),
            reverse=True,
        )

        # Create list of image data
        images = []
        for filename in image_files:
            # Display name without user prefix
            display_name = filename[len(user_prefix) :]
            file_url = url_for(
                "uploaded_files", filename=filename, _external=True
            )
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file_size = os.path.getsize(file_path)
            file_modified = os.path.getmtime(file_path)

            images.append(
                {
                    "name": display_name,
                    "url": file_url,
                    "size": file_size,
                    "modified": file_modified,
                }
            )

        return jsonify({"images": images})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload-image", methods=["GET", "POST"])
def upload_image():
    """Handle image uploads from the web interface."""
    # Check if user is logged in
    if "user" not in session:
        return redirect(url_for("login"))

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
                f"{session['user']}_{name}_{uuid.uuid4().hex}.webp"
            )

            # Save file as WebP
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

                # Save as WebP with good quality
                img.save(
                    os.path.join(app.config["UPLOAD_FOLDER"], unique_filename),
                    "WEBP",
                    quality=85,
                    method=6,
                )
                flash("File uploaded successfully!")
                # Use a special marker for the URL line so the template can handle it differently
                flash(
                    f"URL_LINE:{url_for('uploaded_files', filename=unique_filename, _external=True)}"
                )
            except Exception as e:
                flash(f"Upload failed: {str(e)}")
        else:
            flash(
                "File type not allowed. Please upload PNG, JPG, JPEG, GIF, or WebP images."
            )

        return redirect(url_for("upload_image"))

    # GET request - show upload form and list of uploaded files for current user
    try:
        uploaded_files = os.listdir(app.config["UPLOAD_FOLDER"])
        # Filter only image files that belong to the current user
        user_prefix = f"{session['user']}_"
        image_files = [
            f
            for f in uploaded_files
            if allowed_file(f) and f.startswith(user_prefix)
        ]
        # Sort by modification time (newest first)
        image_files.sort(
            key=lambda x: os.path.getmtime(
                os.path.join(app.config["UPLOAD_FOLDER"], x)
            ),
            reverse=True,
        )
        # Limit to last 12 files and create display structure
        image_files = image_files[:12]
        # Create list with display names and full names
        formatted_files = []
        for filename in image_files:
            formatted_files.append(
                {
                    "full_name": filename,
                    "display_name": filename[len(user_prefix) :],
                }
            )
    except Exception:
        formatted_files = []

    return render_template("upload.html", uploaded_files=formatted_files)


# ---------------- #
#    APP ROUTES    #
# ---------------- #


# ----- HOME ----- #
@app.route("/")
def get_all_posts():
    """
    Read all blog posts from the database.
    """
    if CACHE_ENABLED:
        # Create a cache key for the main posts list
        cache_key = get_cache_key("get_all_posts")
        current_time = time.time()

        # Check if we have a cached result that hasn't expired
        if cache_key in cache_storage:
            result, timestamp = cache_storage[cache_key]
            if current_time - timestamp < CACHE_TIMEOUT:
                return result

        # Generate new result and cache it
        db = get_db()
        posts = list(db.blog_posts.find())
        result = render_template("index.html", all_posts=posts)
        cache_storage[cache_key] = (result, current_time)
        return result
    else:
        db = get_db()
        posts = list(db.blog_posts.find())
        return render_template("index.html", all_posts=posts)


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
            }
            # insert new_user into the database
            users.insert_one(new_user)

            # put the new user into 'session' cookie
            session["user"] = form.name.data
            flash("Registration Successful")
            return redirect(url_for("profile", username=session["user"]))
        except Exception as e:
            flash(f"Registration failed: {str(e)}")
            return render_template("register.html", form=form)
    return render_template("register.html", form=form)


# ----- LOGIN ----- #
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login to the site.

    Validation included.
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
            else:
                session["user"] = existing_user["name"]
                flash(f"Welcome Back, {existing_user['name'].title()}")
                return redirect(url_for("profile", username=session["user"]))
        except Exception as e:
            flash(f"Login failed: {str(e)}")
            return render_template("login.html", form=form)
    return render_template("login.html", form=form)


# ----- PROFILE PAGE ----- #
@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    """
    Direct the user to their Profile page.

    Retrieve all the users Posts.
    """
    # Security check: Only allow users to view their own profile
    if "user" not in session or session["user"] != username:
        flash("You can only view your own profile.")
        return redirect(url_for("login"))

    db = get_db()
    user = db.users.find_one({"name": username})
    if not user:
        flash("User not found.")
        return redirect(url_for("login"))

    posts = db.blog_posts.find({"author": username})
    return render_template("profile.html", username=username, posts=posts)


# ----- EDIT PROFILE ----- #
@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    """
    Edit the user's profile.
    """
    if "user" not in session:
        return redirect(url_for("login"))

    db = get_db()
    user = db.users.find_one({"name": session["user"]})
    form = EditProfileForm(obj=user)

    if form.validate_on_submit():
        # Check if the new email already exists
        if form.email.data != user["email"]:
            if db.users.find_one({"email": form.email.data}):
                flash("That email is already in use.", "error")
                return render_template("edit_profile.html", form=form)

        update_data = {
            "name": form.name.data,
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

        db.users.update_one({"_id": user["_id"]}, {"$set": update_data})
        session["user"] = form.name.data  # Update session with new name
        flash("Profile updated successfully!")
        return redirect(url_for("profile", username=session["user"]))
    elif request.method == "GET":
        form.name.data = user["name"]
        form.email.data = user["email"]
        form.security_question.data = user.get("security_question", "")

    return render_template("edit_profile.html", form=form)


# ----- LOGOUT ----- #
@app.route("/logout")
def logout():
    """
    Logout the user.

    Redirect the user to the home page.
    """
    session.pop("user")
    return redirect(url_for("get_all_posts"))


# ----- READ A POST BY ITS ID ----- #
@app.route("/post/<post_id>", methods=["GET", "POST"])
def show_post(post_id):
    """
    Read a Post by Id.

    Allow the user to Comment if logged in.
    """
    try:
        form = CommentForm()
        db = get_db()

        # For GET requests, we can use caching
        if request.method == "GET":
            requested_post, requested_post_comments = get_post_with_comments(
                post_id
            )
        else:
            # For POST requests (comments), we need fresh data
            requested_post = db.blog_posts.find_one({"_id": int(post_id)})
            requested_post_comments = db.blog_comments.find(
                {"parent_post": int(post_id)}
            )

        # Handle case where post is not found
        if not requested_post:
            flash("Post not found.")
            return redirect(url_for("get_all_posts"))

        # commenting on a post
        if form.validate_on_submit():
            if not session.get("user"):
                flash("You need to login or register to comment.")
                return redirect(url_for("login"))

            new_comment = {
                "text": form.comment_text.data,
                "comment_author": session["user"],
                "parent_post": int(post_id),
            }

            db.blog_comments.insert_one(new_comment)
            # Clear cache for this post since we've added a comment
            if CACHE_ENABLED:
                cache_key = get_cache_key("get_post_with_comments", post_id)
                if cache_key in cache_storage:
                    del cache_storage[cache_key]
            flash("Comment added successfully!")
            return redirect(url_for("show_post", post_id=post_id))

        return render_template(
            "post.html",
            post=requested_post,
            comments=requested_post_comments,
            form=form,
        )
    except Exception as e:
        flash(f"Error loading post: {str(e)}")
        return redirect(url_for("get_all_posts"))


# ----- CREATE A NEW POST ----- #
@app.route("/create-post", methods=["GET", "POST"])
def create_post():
    """
    Create a new Post.

    Inject all form data to a new blog post document on submit.
    """
    if "user" in session:
        # create a Form for data entry
        form = CreatePostForm()
        if form.validate_on_submit():
            try:
                db = get_db()
                new_post = {
                    "title": form.title.data,
                    "subtitle": form.subtitle.data,
                    "body": form.body.data,
                    "img_url": form.img_url.data,
                    "author": session["user"],
                    "date": date.today().strftime("%B %d, %Y"),
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
    else:
        return redirect(url_for("login"))


# ----- EDIT A POST BY ID ----- #
@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    """
    Edit a Post by Id.

    Update all Post data on submit.
    """
    try:
        db = get_db()
        post = db.blog_posts.find_one({"_id": int(post_id)})

        if not post:
            flash("Post not found.")
            return redirect(url_for("get_all_posts"))

        edit_form = CreatePostForm(
            title=post["title"],
            subtitle=post["subtitle"],
            img_url=post["img_url"],
            author=session["user"],
            body=post["body"],
        )
        if edit_form.validate_on_submit():
            db.blog_posts.update_one(
                {"_id": int(post_id)},
                {
                    "$set": {
                        "title": edit_form.title.data,
                        "subtitle": edit_form.subtitle.data,
                        "img_url": edit_form.img_url.data,
                        "body": edit_form.body.data,
                    }
                },
            )
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
def delete_post(post_id):
    """
    Delete a Post by Id.

    Redirect back to main page on submit.
    """
    try:
        db = get_db()
        # Verify the post exists and get it
        post = db.blog_posts.find_one({"_id": int(post_id)})
        if not post:
            flash("Post not found.")
            return redirect(url_for("get_all_posts"))

        # Check if the current user is the author of the post
        if post["author"] != session.get("user"):
            flash("You can only delete your own posts.")
            return redirect(url_for("get_all_posts"))

        db.blog_posts.delete_one({"_id": int(post_id)})
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
def delete_comment(comment_id):
    """
    Delete a Comment by Id.
    """
    db = get_db()
    db.blog_comments.delete_one({"_id": int(comment_id)})
    flash("Comment Successfully Deleted")
    post_id = request.args.get("post_id")
    # Clear cache for this post since we've deleted a comment
    if CACHE_ENABLED:
        cache_key = get_cache_key("get_post_with_comments", post_id)
        if cache_key in cache_storage:
            del cache_storage[cache_key]
    return redirect(url_for("show_post", post_id=post_id))


# ----- SEARCH FOR A POST BY TITLE, SUBTITLE ----- #
@app.route("/search", methods=["GET", "POST"])
def search():
    """
    Search for a Post by Title, Subtitle.
    """
    db = get_db()
    query = request.form.get("query")

    # Security check: Reject URLs and code patterns
    if query and is_suspicious_input(query):
        flash("Invalid search query. Please use only text in search.")
        return redirect(url_for("get_all_posts"))

    # For neosqlite, we'll use the $text operator with FTS for efficient text search
    if query:
        try:
            # Use neosqlite's $text with $search for FTS-based search
            # This will search across all FTS-indexed fields (title and subtitle)
            posts = list(db.blog_posts.find({"$text": {"$search": query}}))
        except Exception as e:
            # If FTS query fails due to special characters, fall back to regex search
            # This is a more basic search but will handle special characters
            import re

            escaped_query = re.escape(query)
            posts = list(
                db.blog_posts.find(
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
                        ]
                    }
                )
            )
    else:
        posts = list(db.blog_posts.find())
    return render_template("index.html", all_posts=posts, search_query=query)


def is_suspicious_input(text):
    """
    Check if the input text contains URLs or programming code patterns.

    Returns True if suspicious content is detected.
    """
    import re

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


# ----- SITEMAP ----- #
@app.route("/sitemap.xml")
def sitemap():
    """Generate a sitemap for the blog."""
    db = get_db()
    posts = list(db.blog_posts.find())

    # Get the current date for the sitemap
    from datetime import datetime

    current_date = datetime.utcnow().strftime("%Y-%m-%d")

    return (
        render_template("sitemap.xml", posts=posts, current_date=current_date),
        200,
        {"Content-Type": "application/xml"},
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


if __name__ == "__main__":
    app.run(
        host=os.environ.get("IP", "127.0.0.1"),
        port=int(os.environ.get("PORT", 5000)),
        debug=True,
    )

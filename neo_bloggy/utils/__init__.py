"""Utilities module for Neo Bloggy application."""

from bleach.css_sanitizer import CSSSanitizer
import bleach
import markdown
import os
import re
from PIL import Image
from flask import flash, redirect, url_for, request
from werkzeug.security import check_password_hash
from neo_bloggy.models import User


def allowed_file(filename):
    """Check if the file extension is allowed."""
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
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
            "tables",
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
            "border",
            "padding",
            "text-align",
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
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    ]
    allowed_attributes = {
        "a": ["href", "title"],
        "img": ["src", "alt", "title", "width", "height", "style"],
        "div": ["class"],
        "span": ["class"],
        "pre": ["class"],
        "td": ["align", "style"],
        "th": ["align", "style"],
    }

    return bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        css_sanitizer=css_sanitizer,
    )


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
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
            ".docx"
        ),
        "text/plain": ".txt",
        "application/zip": ".zip",
    }
    return extension_map.get(content_type, "")


def get_content_type_from_file_extension(filename):
    """Get the content type based on file extension."""
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
        ".docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        ".txt": "text/plain",
        ".zip": "application/zip",
    }
    return content_type_map.get(
        ext, "application/octet-stream"
    )  # Default to binary


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


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class UserValidator:
    """Validation class for user-related operations."""

    @staticmethod
    def validate_registration(form):
        """Validate user registration data."""
        # check if email already exists in database
        existing_user = User.find_by_email(form.email.data)

        if existing_user:
            flash("You've already signed up with that email, log in instead!")
            return False

        return True

    @staticmethod
    def validate_login(form):
        """Validate user login credentials."""
        email = form.email.data
        password = form.password.data

        # check if email already exists
        existing_user = User.find_by_email(email)
        # if email doesn't exist or password incorrect
        if not existing_user:
            flash("That email or password does not exist, please try again.")
            return None
        elif not check_password_hash(existing_user["password"], password):
            flash("That email and password dont match, please try again.")
            return None
        # Check if user account is disabled
        elif not existing_user.get("is_active", True):
            flash(
                "Your account has been disabled. Please contact an administrator."
            )
            return None

        return existing_user

    @staticmethod
    def validate_profile_update(form, current_user):
        """Validate profile update data."""
        # Check if the new email already exists (excluding current user)
        if form.email.data != current_user["email"]:
            if User.find_one(
                {
                    "email": form.email.data,
                    "_id": {
                        "$ne": current_user["_id"]
                    },  # Using the raw ID here
                }
            ):
                flash("That email is already in use.", "error")
                return False
        return True

    @staticmethod
    def validate_password_recovery(form):
        """Validate password recovery data."""
        # check if email exists in database
        user = User.find_by_email(form.email.data)

        if not user:
            flash("No account found with that email address.")
            return None

        # Check if user account is disabled
        if not user.get("is_active", True):
            flash(
                "Your account has been disabled. Please contact an administrator."
            )
            return None

        # check if security question and answer match
        if form.security_question.data == user.get(
            "security_question"
        ) and check_password_hash(
            user["security_answer"], form.security_answer.data.lower()
        ):
            return user
        else:
            flash("Security question or answer is incorrect.")
            return None


class PostValidator:
    """Validation class for post-related operations."""

    @staticmethod
    def validate_post_access(current_user, post):
        """Validate if current user can access/edit/delete a post."""
        if not post:
            flash("Post not found.")
            return False

        # Check if user is the author of the post or an admin
        is_admin = current_user.get("is_admin", False)
        is_post_author = post["author"] == current_user["name"]

        if not is_admin and not is_post_author:
            flash("You can only edit your own posts.")
            return False

        # Prevent disabled non-admin users from editing posts
        if not is_admin and not current_user.get("is_active", True):
            flash("Your account has been disabled. You cannot edit posts.")
            return False

        return True

    @staticmethod
    def validate_comment_access(current_user, comment):
        """Validate if current user can delete a comment."""
        if not comment:
            flash("Comment not found.")
            post_id = request.args.get("post_id")
            return redirect(url_for("posts.show_post", post_id=post_id))

        # Check if user is admin or the comment author
        is_admin = current_user.get("is_admin", False)
        is_comment_author = comment["comment_author"] == current_user["name"]

        # If user is not admin and not the comment author, deny access
        if not is_admin and not is_comment_author:
            flash("You can only delete your own comments.")
            post_id = request.args.get("post_id")
            return redirect(url_for("posts.show_post", post_id=post_id))

        # If user is not admin but is the comment author, check if they're active
        if not is_admin and is_comment_author:
            if not current_user.get("is_active", True):
                flash(
                    "Your account has been disabled. You cannot delete comments."
                )
                post_id = request.args.get("post_id")
                return redirect(url_for("posts.show_post", post_id=post_id))

        return True


class InputValidator:
    """Validation class for general input validation."""

    @staticmethod
    def validate_search_query(query):
        """Validate search query for malicious content."""
        # Security check: Reject URLs and code patterns
        if query and query.strip() and is_suspicious_input(query):
            flash("Invalid search query. Please use only text in search.")
            return False
        return True

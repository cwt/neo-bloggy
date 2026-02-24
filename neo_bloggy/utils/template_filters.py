"""Template filters module for Neo Bloggy application."""

from datetime import datetime
from neo_bloggy.utils import markdown_to_html
from neo_bloggy.database import get_gridfs, get_objectid_for_gridfs


def register_template_filters(app):
    """Register all template filters with the Flask app."""

    @app.template_filter("markdown")
    def markdown_filter(markdown_text):
        """Jinja2 filter to convert markdown to HTML."""
        return markdown_to_html(markdown_text)

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

    @app.template_filter("get_datetime")
    def get_datetime_filter(obj):
        """Jinja2 filter to get datetime field from an object, falling back to date if needed."""
        if isinstance(obj, dict):
            # Try 'datetime' first, then fall back to 'date'
            return obj.get("datetime") or obj.get("date") or ""
        # If it's already a string/datetime, return as is
        return obj

    @app.template_filter("get_alt_text")
    def get_alt_text_filter(img_url):
        """Jinja2 filter to get alt text from GridFS image URL.

        Extracts file_id from the URL and retrieves alt_text from GridFS metadata.
        Falls back to the original filename if alt_text is not set.
        Returns empty string if URL is not a GridFS URL or file not found.
        """
        if not img_url:
            return ""

        try:
            # Extract file_id from URL pattern: /gridfs/<file_id>.webp or /gridfs/<file_id>
            # The URL can be like: /gridfs/698ec1e7b6aecc234282eb75.webp
            if "/gridfs/" not in img_url:
                return ""

            # Extract the file_id part
            parts = img_url.split("/gridfs/")
            if len(parts) < 2:
                return ""

            file_id_with_ext = parts[1].rstrip("/")
            # Remove extension (.webp, .jpg, etc.)
            file_id = (
                file_id_with_ext.rsplit(".", 1)[0]
                if "." in file_id_with_ext
                else file_id_with_ext
            )

            if not file_id:
                return ""

            # Get GridFS instance
            gfs = get_gridfs()
            if gfs is None:
                return ""

            # Convert file_id to ObjectId
            try:
                gridfs_id = get_objectid_for_gridfs(file_id)
            except ValueError:
                return ""

            # Find the file in GridFS
            cursor = gfs.find({"_id": gridfs_id})
            files = list(cursor)

            if not files:
                return ""

            file_doc = files[0]
            metadata = getattr(file_doc, "metadata", {}) or {}

            # Return alt_text if available, otherwise fall back to original_filename
            alt_text = metadata.get("alt_text")
            return alt_text or metadata.get("original_filename")

        except Exception:
            # On any error, return empty string to not break the page
            return ""

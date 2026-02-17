"""Template filters module for Neo Bloggy application."""

from datetime import datetime
from neo_bloggy.utils import markdown_to_html


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

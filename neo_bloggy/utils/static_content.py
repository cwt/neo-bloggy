"""Static content handlers module for Neo Bloggy application."""

from flask import render_template, send_from_directory, request
from neo_bloggy.database import get_db
from neo_bloggy.config import BASE_URL
from datetime import datetime


def register_static_routes(app):
    """Register all static content routes with the Flask app."""

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

        # Use configured base URL if available, otherwise fall back to request.url_root
        site_url = BASE_URL if BASE_URL else request.url_root
        # Ensure site_url ends with a slash for the sitemap homepage entry
        if not site_url.endswith("/"):
            site_url += "/"

        return (
            render_template(
                "sitemap.xml",
                posts=posts,
                current_date=current_date,
                site_url=site_url,
            ),
            200,
            {"Content-Type": "application/xml"},
        )

    @app.route("/favicon.ico")
    def favicon():
        """Serve the favicon.ico file."""
        import os

        return send_from_directory(
            os.path.join(app.static_folder, "img"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    @app.route("/robots.txt")
    def robots_txt():
        """Generate a dynamic robots.txt file with absolute sitemap URL."""
        # Use configured base URL if available, otherwise fall back to request.url_root
        base_url = BASE_URL if BASE_URL else request.url_root
        # Ensure base_url ends with a slash for proper URL construction
        if not base_url.endswith("/"):
            base_url += "/"

        # Generate the absolute sitemap URL
        sitemap_url = base_url + "sitemap.xml"

        # Render the robots.txt template with the sitemap URL
        return (
            render_template("robots.txt", sitemap_url=sitemap_url),
            200,
            {"Content-Type": "text/plain"},
        )


def register_error_handlers(app):
    """Register error handlers with the Flask app."""

    @app.errorhandler(404)
    def page_not_found_404(e):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def page_not_found_403(e):
        return render_template("403.html"), 403

    @app.errorhandler(500)
    def page_not_found_500(e):
        return render_template("500.html"), 500

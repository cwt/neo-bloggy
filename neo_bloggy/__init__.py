from flask import Flask, session
from flask_bootstrap import Bootstrap5
from werkzeug.middleware.proxy_fix import ProxyFix
import os


def create_app(config_class=None):
    app = Flask(
        __name__, static_folder="../static", template_folder="../templates"
    )

    # Import configuration
    from neo_bloggy.config import SECRET_KEY, MAX_CONTENT_LENGTH, config

    # Configure the app to trust proxy headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)  # type: ignore

    app.secret_key = SECRET_KEY
    # Configure session handling
    # SESSION_COOKIE_SECURE should only be True when running behind HTTPS
    # Check for production environment indicators
    is_production = (
        os.environ.get("FLASK_ENV") == "production"
        or os.environ.get("NEO_BLOGGY_PRODUCTION") == "true"
        or config.get("app", {}).get("use_https", False)
    )
    app.config["SESSION_COOKIE_SECURE"] = is_production
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24 hours
    app.config["SESSION_REFRESH_EACH_REQUEST"] = True

    # Configure file upload settings
    app.config["UPLOAD_FOLDER"] = os.path.join(app.static_folder, "uploads")
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # Create upload directory
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    Bootstrap5(app)

    # Database teardown
    from neo_bloggy.database import close_db

    app.teardown_appcontext(close_db)

    # Context processor
    @app.context_processor
    def inject_site_details():
        from neo_bloggy.auth import (
            get_current_user,
            get_csp_nonce,
            get_absolute_url,
            get_canonical_url,
        )

        user = get_current_user()
        if user:
            session["user"] = user["name"]

        return {
            "site_title": config.get("app", {}).get("site_title", "Neo Bloggy"),
            "site_author": config.get("app", {}).get(
                "site_author", "Neo Bloggy"
            ),
            "site_description": (
                config.get("app", {}).get(
                    "site_description", "Blogging Ireland; journalism"
                )
            ),
            "user": user,
            "csp_nonce": get_csp_nonce(),
            "get_absolute_url": get_absolute_url,
            "get_canonical_url": get_canonical_url,
        }

    # After request (middleware)
    @app.after_request
    def after_request(response):
        from neo_bloggy.middleware import Middleware

        response = Middleware.after_request(response)

        if response.content_type.startswith("text/html"):
            from neo_bloggy.utils import minify_html

            response.set_data(minify_html(response.get_data(as_text=True)))
        return response

    # Register template filters
    from neo_bloggy.utils.template_filters import register_template_filters

    register_template_filters(app)

    # Register static routes and error handlers
    from neo_bloggy.utils.static_content import (
        register_static_routes,
        register_error_handlers,
    )

    register_static_routes(app)
    register_error_handlers(app)

    # Register Blueprints
    from neo_bloggy.auth.routes import auth_bp
    from neo_bloggy.admin.routes import admin_bp
    from neo_bloggy.posts.routes import posts_bp
    from neo_bloggy.search.routes import search_bp
    from neo_bloggy.file_upload.routes import file_upload_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(file_upload_bp)

    # Initialize app-level tasks
    from neo_bloggy.caching import on_app_ready

    with app.app_context():
        on_app_ready()

    return app

"""Configuration module for Neo Bloggy application."""

import os
import tomllib


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

# Posts configuration
POSTS_PER_PAGE = config.get("posts", {}).get("posts_per_page", 10)
MAX_POSTS_PER_PAGE = config.get("posts", {}).get("max_posts_per_page", 50)

# Site configuration
BASE_URL = config.get("app", {}).get("base_url", "")

# Database configuration
DB_PATH = config.get("database", {}).get("db_path", "neo-bloggy.db")
TOKENIZER_NAME = config.get("database", {}).get("tokenizer_name", None)
TOKENIZER_PATH = config.get("database", {}).get("tokenizer_path", None)

# File upload configuration
MAX_CONTENT_LENGTH = config.get("file_uploads", {}).get(
    "max_content_length", 16 * 1024 * 1024
)  # 16MB max file size

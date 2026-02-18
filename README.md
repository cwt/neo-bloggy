# Neo Bloggy

![Neo Bloggy Responsive](static/img/am-i-responsive.PNG)

## Overview

Neo Bloggy is a modern blogging platform for amateur writers to showcase their work. This standalone project was originally forked from [Medium Bloggy](https://github.com/leithdm/medium-bloggy) but has been completely rebranded and modernized with significant enhancements.

## Live Demo

Experience Neo Bloggy in action at [https://neo.bashell.com/](https://neo.bashell.com/) - a fully functional production instance of the platform showcasing all features including user authentication, blog management, commenting system, search functionality, and admin panel controls.

The project has been fundamentally transformed to use **[NeoSQLite](https://github.com/cwt/neosqlite)** as the database backend, replacing MongoDB/PyMongo entirely. This demonstrates that NeoSQLite can effectively replace MongoDB in a Flask application while providing a lightweight alternative without requiring external database servers.

## Key Changes from Original Project

We've significantly modified this project to work with NeoSQLite, demonstrating that NeoSQLite can literally replace PyMongo and MongoDB while maintaining all existing functionality:

1. **Complete Database Migration**: Replaced MongoDB/PyMongo with NeoSQLite for all database operations
2. **Modern API Compatibility**: Leveraged NeoSQLite's MongoDB-like API to minimize code changes
3. **Enhanced Performance**: Improved performance by eliminating external database dependencies
4. **Simplified Deployment**: Removed MongoDB Atlas requirements for a truly standalone experience
5. **Modern Features**: Updated to Bootstrap 5.3, Flask 3.1, and modern Python practices
6. **Modular Architecture**: Refactored the monolithic `app.py` into a clean, modular structure using the Application Factory pattern and Flask Blueprints for better maintainability and scalability

## Technologies Used

### Front-End Technologies
- HTML5
- CSS3 (Bootstrap 5.3)
- JavaScript (Cash.js for DOM manipulation)
- Google Fonts (IBM Plex)
- Font Awesome 6.5

### Back-End Technologies
- Python 3.x
- Flask 3.1
- NeoSQLite 1.2.0 or newer
- Flask-Bootstrap5 2.5.0
- Flask-WTF 1.2.2

## Features

- **User Authentication**: Register, login, and logout functionality with security questions for password recovery
- **Blog Management**: Create, read, update, and delete blog posts with Markdown support
- **Draft System**: Save posts as drafts before publishing, with drafts displayed separately on your profile
- **Comment System**: Users can comment on posts with Markdown support
- **Search Functionality**: Full-text search across posts using NeoSQLite's FTS capabilities, with optional support for Asian languages (Chinese, Japanese, Korean, Thai, etc.) through custom FTS5 tokenizers
- **File Uploads**: Image upload functionality with automatic WebP conversion for posts
- **Responsive Design**: Mobile-friendly interface
- **Admin Panel**: Administrators can manage users and content
- **Security Features**: XSS protection, input validation, and secure password handling
- **Caching**: Optional caching mechanism for improved performance

## Admin Panel Features

The admin panel provides administrators with tools to manage the platform:

1. **User Management**:
   - View all registered users
   - Enable/disable user accounts
   - Promote users to administrator status
   - Disabled users cannot login, create posts, or comment

2. **Content Control**:
   - Posts and comments from disabled users are automatically hidden from public view
   - Content remains in the database for auditing purposes
   - Only administrators can view content from disabled users

3. **Automatic Admin Assignment**:
   - The first user to register is automatically made an administrator
   - Administrators can promote other users to admin status

4. **Search Index Management**:
   - Administrators can rebuild FTS indexes for optimal search performance, including when using custom tokenizers for Asian language support

To access the admin panel, navigate to `/admin` or click "Admin Panel" in the navigation menu (only visible to administrators).

## Draft System

Neo Bloggy includes a comprehensive draft system for content creators:

1. **Creating Drafts**:
   - Click "Save as Draft" when creating or editing a post to save it without publishing
   - Drafts are visible only to the author and administrators
   - Image URL is optional for drafts (required for published posts)

2. **Managing Drafts**:
   - All drafts appear at the top of your "Your Posts" section on your profile page
   - Drafts are marked with a "Draft" badge for easy identification
   - Edit and delete drafts just like published posts

3. **Publishing Drafts**:
   - Edit a draft and click "Publish" to make it visible to the public
   - Published posts require an image URL
   - Once published, posts appear on the homepage and in search results

4. **Profile Page**:
   - Unified "Your Posts" table shows both drafts and published posts
   - Drafts listed first, followed by published posts
   - Subtitle displayed below title for posts that have one
   - Edit and Delete buttons grouped together for easy access

## NeoSQLite Advantages Demonstrated

This project demonstrates several key advantages of [NeoSQLite](https://github.com/cwt/neosqlite):

1. **MongoDB-like API**: Familiar syntax for developers transitioning from MongoDB
2. **Zero Configuration**: No external database servers required
3. **Document Storage**: Native support for JSON-like documents
4. **Query Operators**: Support for MongoDB-style query operators including `$or`, `$elemMatch`, `$text`, etc.
5. **Performance**: Faster local operations without network latency
6. **Full-Text Search**: Advanced text search capabilities with support for custom FTS5 tokenizers (enabling Asian language search)
7. **GridFS Support**: Built-in GridFS-like functionality for file storage

## Asian Language Search Support

This functionality is provided by [NeoSQLite](https://github.com/cwt/neosqlite), which includes support for custom FTS5 tokenizers. To enable Asian language search support in Neo Bloggy:

1. Build the [FTS5 ICU Tokenizer](https://github.com/cwt/fts5-icu-tokenizer) for your target language
2. Configure the tokenizer in your `config.toml`:

```toml
[database]
# Path to the NeoSQLite database file
# Default: neo-bloggy.db in the project directory
db_path = "neo-bloggy.db"

# Configure custom FTS5 tokenizer for Asian language support
tokenizer_name = "icu_th"  # For Thai
tokenizer_path = "/path/to/fts5_icu_th.so"  # Path to the compiled tokenizer
```

For detailed instructions on building and configuring the FTS5 ICU Tokenizer, please refer to the [FTS5 ICU Tokenizer README](https://github.com/cwt/fts5-icu-tokenizer).

After configuring the tokenizer, you may need to rebuild the search indexes from the Admin Panel to ensure that the new tokenizer is used for existing content.

## Modern Features

This application includes several modern web development features:

### Bootstrap 5.3
- Updated from Bootstrap 4 to the latest Bootstrap 5.3
- Modern CSS framework with improved components and utilities
- Better responsive design capabilities
- Replaced jQuery with Cash.js for lighter DOM manipulation

### Performance Optimizations
- HTML minification to reduce bandwidth usage
- Optional caching mechanism for improved response times
- Modern dependency versions for better security and performance
- WebP image conversion for optimized file sizes

### Code Modernization
- Updated to Flask 3.1 with modern Python practices
- Implemented **Application Factory pattern** and **Flask Blueprints** for a clean, modular codebase
- Separated concerns into dedicated modules: `auth`, `admin`, `posts`, `search`, and `file_upload`
- Introduced a **Service Layer** to separate business logic from request handling
- Improved code structure and maintainability
- Enhanced security with input validation and XSS protection

### Security and Performance Features
This application includes several security and performance features:

#### Content Security Policy (CSP)
- **Balanced Security**: The application uses a CSP policy that balances security with practical usability
- **Trusted Sources**: Scripts and styles are allowed from `'self'`, `'unsafe-inline'`, and trusted CDNs (jsdelivr, cdnjs, Font Awesome, Google Fonts, Twitter, Google Tag Manager)
- **Font Awesome Support**: Includes support for Font Awesome icons used by the EasyMDE editor
- **Flexible Deployment**: Administrators can implement more restrictive CSP policies via web servers (nginx, Apache) or CDNs as needed

#### Caching
Optional caching mechanism to improve performance:
- **Configurable**: Enable/disable caching and set timeout via configuration file
- **Automatic Invalidation**: Cache is automatically cleared when content is modified
- **Memory Efficient**: Simple LRU-like cache with timeout support

To enable caching, modify the following values in your `config.toml`:

```toml
[caching]
# Enable or disable caching mechanism
# Options: true or false
cache_enabled = true

# Cache timeout in seconds (default: 5 minutes)
cache_timeout = 300
```

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/cwt/neo-bloggy.git
   ```

2. Navigate to the project directory:
   ```
   cd neo-bloggy
   ```

3. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install requirements:
   ```
   pip install -r requirements.txt
   ```

5. Create a `config.toml` file with the following content:
   ```toml
   # Neo Bloggy Configuration File
   # This file contains all the configuration options for the Neo Bloggy application.
   
   [app]
   # Secret key for Flask sessions and CSRF protection
   # Generate a strong secret key using: python -c "import secrets; print(secrets.token_urlsafe(32))"
   secret_key = "your-secret-key-here"
   
   # IP address to bind the server to
   ip = "127.0.0.1"
   
   # Port to run the server on
   port = 5000
   
   # Site metadata
   site_title = "Neo Bloggy"
   site_author = "Neo Bloggy"
   site_description = "Modern Blogging Platform"
   
   [database]
   # Path to the NeoSQLite database file
   # Default: neo-bloggy.db in the project directory
   db_path = "neo-bloggy.db"
   
   # Optional: Configure custom FTS5 tokenizer (NeoSQLite v0.3.5+)
   # tokenizer_name = "icu"
   # tokenizer_path = "/path/to/libfts5_icu.so"
   
   [caching]
   # Enable or disable caching mechanism
   # Options: true or false
   cache_enabled = false
   
   # Cache timeout in seconds (default: 5 minutes)
   cache_timeout = 300
   
   [file_uploads]
   # Maximum file upload size in bytes (16MB = 16 * 1024 * 1024)
   max_content_length = 16777216
   ```
   
   Modify the values as needed for your environment.

6. Run the application:
   ```
   python app.py
   ```

7. Visit `http://127.0.0.1:5000` in your browser

## Configuration Path

By default, Neo Bloggy looks for a `config.toml` file in the project directory. For Docker deployments or custom installations, you can specify a custom configuration file path using the `NEO_BLOGGY_CONFIG_PATH` environment variable:

```bash
NEO_BLOGGY_CONFIG_PATH=/data/config.toml python app.py
```

This allows you to place your configuration file in any location, making it easier to manage configurations in containerized environments.

## Deployment

Neo Bloggy is designed for flexible deployment on any cloud or hosting platform:

### Key Deployment Concepts

1. **No External Database Required**: The NeoSQLite database is a single file that can be stored anywhere accessible to your application

2. **Configuration via Environment**: Use `NEO_BLOGGY_CONFIG_PATH` environment variable to specify your config file location:
   ```bash
   NEO_BLOGGY_CONFIG_PATH=/path/to/config.toml python app.py
   ```

3. **Persistent Storage**: Ensure the database file and any uploaded files are stored on persistent storage (not ephemeral container storage)

4. **WSGI Server**: For production, use a WSGI server like Gunicorn:
   ```bash
   gunicorn -c gunicorn.conf.py app:app
   ```

### Platform-Specific Notes

- **Docker**: Mount volumes for `/data` (database) and your config file
- **Heroku/Render/Railway**: Use their persistent storage addons for the database file
- **VPS/Cloud VMs**: Standard deployment with systemd or supervisor
- **Shared Hosting**: Works with any Python hosting that supports WSGI

The application automatically adapts to your environment through the `config.toml` file.

## Database Migrations

This project includes several migration scripts to help manage database schema changes, located in the `scripts/` directory:

- `scripts/migrate_to_gridfs.py`: Migrates existing file uploads to GridFS storage
- `scripts/migrate_to_objectid.py`: Migrates old integer IDs to MongoDB-style ObjectIds
- `scripts/migrate_admin_publisher.py`: Ensures the first admin user also has publisher status
- `scripts/update_user.py`: Command-line tool for user management (enable/disable, admin status)

These scripts should be run manually as needed when upgrading the application or when specific database changes are required. They can be run as standalone Python scripts from the project root:

```bash
python scripts/migrate_admin_publisher.py
```

### Automatic Migrations

The application automatically handles the following migrations on startup via the `on_app_ready` hook:

- **Tags Field**: Ensures all posts have a `tags` field (defaults to empty array)
- **Status Field**: Ensures all posts have a `status` field (defaults to "published" for backward compatibility with existing posts)

These automatic migrations ensure backward compatibility when upgrading from older versions.

## Debug Package

Neo Bloggy includes a comprehensive debug package with various testing and troubleshooting scripts:

- `debug/`: Contains debugging scripts for different aspects of the application
  - `debug_detailed.py`: Detailed debugging for main application flow
  - `debug_post_detailed.py`: Post-specific functionality testing
  - `debug_post_route.py`: Post route functionality testing
  - `debug_simulate_flow.py`: Simulates request flows to identify pipeline issues

These scripts can be run independently to troubleshoot specific functionality:

```bash
python -m debug.debug_detailed
python -m debug.debug_simulate_flow
```

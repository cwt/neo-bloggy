# Neo Bloggy

![Neo Bloggy Responsive](static/img/am-i-responsive.PNG)

## Overview

Neo Bloggy is a modern blogging platform for amateur writers to showcase their work. This standalone project was originally forked from [Medium Bloggy](https://github.com/leithdm/medium-bloggy) but has been completely rebranded and modernized with significant enhancements.

The project has been fundamentally transformed to use **[NeoSQLite](https://github.com/cwt/neosqlite)** as the database backend, replacing MongoDB/PyMongo entirely. This demonstrates that NeoSQLite can effectively replace MongoDB in a Flask application while providing a lightweight alternative without requiring external database servers.

## Key Changes from Original Project

We've significantly modified this project to work with NeoSQLite, demonstrating that NeoSQLite can literally replace PyMongo and MongoDB while maintaining all existing functionality:

1. **Complete Database Migration**: Replaced MongoDB/PyMongo with NeoSQLite for all database operations
2. **Modern API Compatibility**: Leveraged NeoSQLite's MongoDB-like API to minimize code changes
3. **Enhanced Performance**: Improved performance by eliminating external database dependencies
4. **Simplified Deployment**: Removed MongoDB Atlas requirements for a truly standalone experience
5. **Modern Features**: Updated to Bootstrap 5.3, Flask 3.1, and modern Python practices

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
- NeoSQLite 0.4.0 or newer
- Flask-Bootstrap5 2.5.0
- Flask-WTF 1.2.2

## Features

- **User Authentication**: Register, login, and logout functionality with security questions for password recovery
- **Blog Management**: Create, read, update, and delete blog posts with Markdown support
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

## NeoSQLite Advantages Demonstrated

This project demonstrates several key advantages of [NeoSQLite](https://github.com/cwt/neosqlite):

1. **MongoDB-like API**: Familiar syntax for developers transitioning from MongoDB
2. **Zero Configuration**: No external database servers required
3. **Document Storage**: Native support for JSON-like documents
4. **Query Operators**: Support for MongoDB-style query operators including `$or`, `$contains`, `$text`, etc.
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
- Removed deprecated libraries and methods
- Improved code structure and maintainability
- Enhanced security with input validation and XSS protection

### Caching
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

## Deployment

This application can be easily deployed to platforms like Heroku without requiring a separate MongoDB database. The NeoSQLite database file will be created automatically when the application runs.

## Original Project

This project was originally forked from [Medium Bloggy](https://github.com/leithdm/medium-bloggy), a project by [leithdm](https://github.com/leithdm). For information about the original project that used MongoDB, please see [ORIGINAL_README.md](ORIGINAL_README.md).

The original project was transformed into Neo Bloggy as a standalone project with the ultimate objective to modernize in everything possible while using NeoSQLite as the only database backend.
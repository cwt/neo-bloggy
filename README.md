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
- **Search Functionality**: Full-text search across posts using NeoSQLite's FTS capabilities
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
   - Administrators can rebuild FTS indexes for optimal search performance

To access the admin panel, navigate to `/admin` or click "Admin Panel" in the navigation menu (only visible to administrators).

## NeoSQLite Advantages Demonstrated

This project demonstrates several key advantages of [NeoSQLite](https://github.com/cwt/neosqlite):

1. **MongoDB-like API**: Familiar syntax for developers transitioning from MongoDB
2. **Zero Configuration**: No external database servers required
3. **Document Storage**: Native support for JSON-like documents
4. **Query Operators**: Support for MongoDB-style query operators including `$or`, `$contains`, `$text`, etc.
5. **Performance**: Faster local operations without network latency
6. **Full-Text Search**: Advanced text search capabilities with customizable tokenizers
7. **GridFS Support**: Built-in GridFS-like functionality for file storage

## Modern Features (2025)

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

## Performance Optimizations

This application includes several performance optimizations:

### HTML Minification
The application automatically minifies HTML output by removing empty lines and lines with only whitespace while preserving content indentation. This reduces bandwidth usage while maintaining readable HTML structure.

### Caching
Optional caching mechanism to improve performance:
- **Configurable**: Enable/disable caching and set timeout via environment variables
- **Automatic Invalidation**: Cache is automatically cleared when content is modified
- **Memory Efficient**: Simple LRU-like cache with timeout support

To enable caching, set the following environment variables in your `env.py`:

```python
os.environ.setdefault("CACHE_ENABLED", "True")   # Enable caching
os.environ.setdefault("CACHE_TIMEOUT", "300")   # Cache timeout in seconds (5 minutes)
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

5. Create an `env.py` file with the following content:
   ```python
   import os

   os.environ.setdefault("SECRET_KEY", "your-secret-key")
   os.environ.setdefault("IP", "127.0.0.1")
   os.environ.setdefault("PORT", "5000")
   os.environ.setdefault("DB_PATH", "neo-bloggy.db")  # Optional, defaults to neo-bloggy.db

   # Optional: Configure custom FTS5 tokenizer (NeoSQLite v0.3.5+)
   # os.environ.setdefault("TOKENIZER_NAME", "icu")
   # os.environ.setdefault(
   #     "TOKENIZER_PATH",
   #     "/path/to/libfts5_icu.so",
   # )

   # Optional: Configure caching (default: disabled)
   # os.environ.setdefault("CACHE_ENABLED", "True")   # Enable caching
   # os.environ.setdefault("CACHE_TIMEOUT", "300")   # Cache timeout in seconds (5 minutes)

   # Optional: Configure site-wide meta tags
   # os.environ.setdefault("SITE_TITLE", "Neo Bloggy")
   # os.environ.setdefault("SITE_AUTHOR", "Neo Bloggy")
   # os.environ.setdefault("SITE_DESCRIPTION", "Modern Blogging Platform")
   ```

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

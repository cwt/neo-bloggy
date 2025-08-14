# Medium Bloggy - NeoSQLite Edition

![Medium Bloggy Responsive](static/img/am-i-responsive.PNG)

## Overview

Medium Bloggy is a blogging platform for amateur writers to showcase their work. This version has been modified to use **NeoSQLite** instead of MongoDB, demonstrating that NeoSQLite can effectively replace PyMongo and MongoDB in a Flask application.

This project showcases how NeoSQLite, a document-oriented database with a MongoDB-like API, can be used as a drop-in replacement for MongoDB in Python web applications, providing a lightweight alternative without requiring external database servers.

## Key Changes

We've modified this project to work with NeoSQLite, demonstrating that NeoSQLite can literally replace PyMongo and MongoDB while maintaining all existing functionality:

1. **Database Migration**: Replaced MongoDB/PyMongo with NeoSQLite for all database operations
2. **API Compatibility**: Leveraged NeoSQLite's MongoDB-like API to minimize code changes
3. **Performance**: Improved performance by eliminating external database dependencies
4. **Deployment**: Simplified deployment by removing MongoDB Atlas requirements

## Technologies Used

### Front-End Technologies
- HTML5
- CSS3 (Bootstrap 5.3)
- JavaScript
- Google Fonts (Lora and Open Sans)
- Font Awesome 6.5

### Back-End Technologies
- Python 3.x
- Flask 3.1
- NeoSQLite 0.3.5
- Flask-Bootstrap5 5.3.3
- Flask-WTF 1.2.2

## Features

- **User Authentication**: Register, login, and logout functionality
- **Blog Management**: Create, read, update, and delete blog posts
- **Comment System**: Users can comment on posts
- **Search Functionality**: Search posts by title or subtitle using NeoSQLite's `$or` and `$contains` operators
- **Rich Text Editing**: Markdown support for blog posts
- **File Uploads**: Image upload functionality for posts
- **Responsive Design**: Mobile-friendly interface

## NeoSQLite Advantages Demonstrated

This project demonstrates several key advantages of NeoSQLite:

1. **MongoDB-like API**: Familiar syntax for developers transitioning from MongoDB
2. **Zero Configuration**: No external database servers required
3. **Document Storage**: Native support for JSON-like documents
4. **Query Operators**: Support for MongoDB-style query operators including `$or`, `$contains`, etc.
5. **Performance**: Faster local operations without network latency
6. **Full-Text Search**: Advanced text search capabilities with customizable tokenizers

## Modern Features (2025)

This application includes several modern web development features:

### Bootstrap 5.3
- Updated from Bootstrap 4 to the latest Bootstrap 5.3
- Modern CSS framework with improved components and utilities
- Better responsive design capabilities

### Dark Mode Support
- User preference-based dark/light mode toggle
- System preference detection (prefers-color-scheme)
- Persistent theme selection using localStorage
- Custom CSS variables for consistent styling

### Performance Optimizations
- HTML minification to reduce bandwidth usage
- Optional caching mechanism for improved response times
- Modern dependency versions for better security and performance

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
   git clone https://github.com/your-username/medium-bloggy.git
   ```

2. Navigate to the project directory:
   ```
   cd medium-bloggy
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
   os.environ.setdefault("DB_PATH", "medium-bloggy.db")  # Optional, defaults to medium-bloggy.db
   
   # Optional: Configure custom FTS5 tokenizer (NeoSQLite v0.3.5+)
   # os.environ.setdefault("TOKENIZER_NAME", "icu")
   # os.environ.setdefault(
   #     "TOKENIZER_PATH",
   #     "/path/to/libfts5_icu.so",
   # )
   
   # Optional: Configure caching (default: disabled)
   # os.environ.setdefault("CACHE_ENABLED", "True")   # Enable caching
   # os.environ.setdefault("CACHE_TIMEOUT", "300")   # Cache timeout in seconds (5 minutes)
   ```

6. Run the application:
   ```
   python app.py
   ```

7. Visit `http://127.0.0.1:5000` in your browser

## Deployment

This application can be easily deployed to platforms like Heroku without requiring a separate MongoDB database. The NeoSQLite database file will be created automatically when the application runs.

## Original Project

For information about the original project that used MongoDB, please see [ORIGINAL_README.md](ORIGINAL_README.md).

"""
File-based cache system for Neo Bloggy application.
This module provides a shared cache that works across multiple Gunicorn workers.
"""

from threading import Lock
import hashlib
import os
import pickle
import time


class FileCache:
    """
    A file-based cache implementation that can be shared across Gunicorn workers.
    """

    def __init__(self, cache_dir="cache/", max_size_mb=100, cache_timeout=300):
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
        self.cache_timeout = cache_timeout  # Timeout in seconds
        self.lock = Lock()  # Thread lock for file operations

        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, key):
        """Get file path for a cache key."""
        # Create a safe filename from the key
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")

    def _get_cache_size(self):
        """Calculate total cache size in bytes."""
        total_size = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".cache"):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except OSError:
                    pass  # File might have been deleted
        return total_size

    def _clean_oldest(self):
        """Clean up oldest cache files if size exceeds limit."""
        files_with_time = []
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".cache"):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    mtime = os.path.getmtime(file_path)
                    size = os.path.getsize(file_path)
                    files_with_time.append((mtime, size, file_path))
                except OSError:
                    pass  # File might have been deleted by another process

        # Sort by modification time (oldest first)
        files_with_time.sort(key=lambda x: x[0])

        # Remove oldest files until we're under the size limit
        current_size = sum(item[1] for item in files_with_time)
        for mtime, size, file_path in files_with_time:
            if current_size <= self.max_size_bytes:
                break
            try:
                os.remove(file_path)
                current_size -= size
            except OSError:
                pass  # File might have been deleted by another process

    def get(self, key):
        """Get a value from the cache."""
        with self.lock:
            cache_path = self._get_cache_path(key)
            if not os.path.exists(cache_path):
                return None

            try:
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)

                # Check if cache is expired
                value, timestamp = data
                if time.time() - timestamp > self.cache_timeout:
                    os.remove(cache_path)  # Remove expired cache
                    return None

                return value
            except (pickle.PickleError, EOFError, OSError):
                # If there's an error reading the file, remove it
                try:
                    os.remove(cache_path)
                except OSError:
                    pass
                return None

    def set(self, key, value):
        """Set a value in the cache."""
        with self.lock:
            # Check if cache size would exceed limit after adding this item
            item_size = len(pickle.dumps((value, time.time())))
            if item_size > self.max_size_bytes:
                # If a single item is larger than max size, don't cache it
                return

            cache_path = self._get_cache_path(key)
            try:
                with open(cache_path, "wb") as f:
                    pickle.dump((value, time.time()), f)

                # Clean up if necessary
                if self._get_cache_size() > self.max_size_bytes:
                    self._clean_oldest()
            except OSError:
                pass  # If we can't write, just skip caching this item

    def delete(self, key):
        """Delete a specific cache entry."""
        with self.lock:
            cache_path = self._get_cache_path(key)
            try:
                if os.path.exists(cache_path):
                    os.remove(cache_path)
            except OSError:
                pass  # File might have been deleted by another process

    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".cache"):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass  # File might have been deleted by another process

    def clear_expired(self):
        """Remove expired cache entries."""
        with self.lock:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".cache"):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        with open(file_path, "rb") as f:
                            data = pickle.load(f)

                        # Check if cache is expired
                        _, timestamp = data
                        if time.time() - timestamp > self.cache_timeout:
                            os.remove(file_path)
                    except (OSError, pickle.PickleError):
                        # If there's an error reading the file, remove it
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass


def get_cache_instance(config, cache_timeout=300):
    """
    Create and return a cache instance based on configuration.

    Args:
        config: Configuration dictionary
        cache_timeout: Default cache timeout in seconds

    Returns:
        Cache instance (FileCache or dict for in-memory fallback)
    """
    cache_type = (
        config.get("caching", {}).get("storage", {}).get("type", "memory")
    )
    cache_dir = (
        config.get("caching", {}).get("storage", {}).get("cache_dir", "cache/")
    )
    max_cache_size_mb = (
        config.get("caching", {}).get("storage", {}).get("max_size_mb", 100)
    )

    if cache_type == "file":
        return FileCache(
            cache_dir=cache_dir,
            max_size_mb=max_cache_size_mb,
            cache_timeout=cache_timeout,
        )
    else:
        # Fallback to in-memory cache
        return {}


def get_cache_key(*args, **kwargs):
    """Generate a cache key from arguments."""
    return str(args) + str(sorted(kwargs.items()))


def cached_result(cache_storage, cache_timeout=300):
    """
    Decorator to cache function results with timeout.

    Args:
        cache_storage: Cache instance (FileCache or dict)
        cache_timeout: Cache timeout in seconds
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # For functions that have a way to determine if caching is enabled
            cache_key = get_cache_key(func.__name__, *args, **kwargs)
            current_time = time.time()

            # Check if we have a cached result that hasn't expired
            if isinstance(cache_storage, FileCache):
                result = cache_storage.get(cache_key)
                if result is not None:
                    return result
            else:
                # In-memory cache
                if cache_key in cache_storage:
                    result, timestamp = cache_storage[cache_key]
                    if current_time - timestamp < cache_timeout:
                        return result

            # Generate new result and cache it
            result = func(*args, **kwargs)
            if isinstance(cache_storage, FileCache):
                cache_storage.set(cache_key, result)
            else:
                cache_storage[cache_key] = (result, current_time)
            return result

        return wrapper

    return decorator


def clear_expired_cache(cache_storage, cache_timeout=300):
    """Remove expired cache entries."""
    if isinstance(cache_storage, FileCache):
        cache_storage.clear_expired()
    else:
        # In-memory cache
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in cache_storage.items()
            if current_time - timestamp >= cache_timeout
        ]
        for key in expired_keys:
            del cache_storage[key]


def delete_cache_key(cache_storage, key):
    """Delete a specific cache key."""
    if isinstance(cache_storage, FileCache):
        cache_storage.delete(key)
    else:
        if key in cache_storage:
            del cache_storage[key]


def clear_cache(cache_storage):
    """Clear all cache entries."""
    if isinstance(cache_storage, FileCache):
        cache_storage.clear()
    else:
        cache_storage.clear()

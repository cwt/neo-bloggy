# Gunicorn configuration file for Neo Bloggy

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes - only 2 workers with gevent for low memory and better I/O handling
workers = 2
worker_class = "gevent"
worker_connections = 1000
timeout = 120
keepalive = 2
max_requests = 500
max_requests_jitter = 50
preload_app = True

# Gevent specific settings to improve shutdown
worker_tmp_dir = "/dev/shm"  # Use memory for temporary files if available

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
)

# Process naming
proc_name = "neo_bloggy"

# Server mechanics
# user = "appuser"
# group = "appuser"
tmp_upload_dir = None

# Debugging
reload = False


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Neo Bloggy server is ready. Preloading cache...")


def on_exit(server):
    """Called just before the server is shut down."""
    server.log.info("Neo Bloggy server is shutting down. Cleaning up...")
    server.log.info("Cleanup completed.")


def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    worker.log.info(
        "Worker received interrupt signal. Shutting down gracefully..."
    )


def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("Worker received abort signal.")


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

    # Import the app and preload cache when worker is forked
    # In preload mode, the app is already loaded, so we can call our cache preloading function
    try:
        from app import app, on_app_ready

        server.log.info(
            "About to create application context and run on_app_ready"
        )
        # Create an application context to allow database operations
        with app.app_context():
            server.log.info("Application context created, calling on_app_ready")
            on_app_ready()
            server.log.info("on_app_ready completed successfully")
    except Exception as e:
        server.log.error("Error preloading cache: %s", str(e))
        import traceback

        traceback.print_exc()

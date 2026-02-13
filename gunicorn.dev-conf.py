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

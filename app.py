from neo_bloggy import create_app
import os

app = create_app()

if __name__ == "__main__":
    from neo_bloggy.config import config

    # Check if we're running in Docker by looking for the FLASK_RUN_HOST environment variable
    host = os.environ.get(
        "FLASK_RUN_HOST", config.get("app", {}).get("ip", "127.0.0.1")
    )
    app.run(
        host=host,
        port=int(config.get("app", {}).get("port", 5000)),
        debug=True,
    )

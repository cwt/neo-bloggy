# Debug Scripts for Neo Bloggy

This directory contains various debugging and testing scripts for troubleshooting different aspects of the Neo Bloggy application.

## Available Debug Scripts

### `debug_detailed.py`
Provides detailed debugging for the main application flow, including testing authentication, post retrieval, and various application components.

### `debug_post_detailed.py`
Focuses specifically on post-related functionality, testing post creation, retrieval, and display mechanisms.

### `debug_post_route.py`
Tests the post route functionality, including direct access to post-related endpoints and database queries.

### `debug_simulate_flow.py`
Simulates the exact request flow for the post route to help identify issues in the request handling pipeline.

## Usage

Each script can be run independently to test specific functionality:

```bash
python -m debug.debug_detailed
python -m debug.debug_post_detailed
python -m debug.debug_post_route
python -m debug.debug_simulate_flow
```

## Purpose

These scripts are designed to:
- Reproduce specific error conditions
- Test individual components in isolation
- Verify fixes for reported issues
- Aid in troubleshooting production-like scenarios
#!/bin/bash

# Format Python files with black
black -t py312 -l 80 app.py
black -t py312 -l 80 neo_bloggy/
black -t py312 -l 80 tests/
black -t py312 -l 80 scripts/*.py

# Remove trailing whitespace in all .py files
find . -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} \;

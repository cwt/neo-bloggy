#!/bin/bash

black -t py312 -l 80 *.py
black -t py312 -l 80 tests/*.py

# Remove trailing whitespace in all .py files
find . -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} \;

#!/bin/bash

# Exit on any error
set -e

# Check if virtualenv exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
fi

# Install test requirements if they exist
if [ -f "requirements-test.txt" ]; then
    echo "Installing test requirements..."
    pip install -r requirements-test.txt
fi

# Run tests
echo "Running tests..."
cd src
SRC_PATH=$(pwd)
cd ..
PYTHONPATH=$SRC_PATH python3 -m unittest tests/test_getcolors.py tests/utils/test_transaction_parser.py -v

# Store the exit code
exit_code=$?

# Deactivate virtual environment
deactivate

# Exit with the test exit code
exit $exit_code 
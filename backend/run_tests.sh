#!/bin/bash

# Exit on any error
set -e

# Help message function
show_help() {
    echo "Usage: $0 [test_name]"
    echo "  test_name: Optional. The specific test file to run (e.g., tests/utils/test_transaction_parser.py)"
    echo "  If no test name is provided, all tests will be run."
    exit 1
}

# Show help if -h or --help is passed
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
fi

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

# Set up Python path
cd src
SRC_PATH=$(pwd)
cd ..

# Run tests with logging configuration
echo "Running tests..."
if [ -n "$1" ]; then
    # Run specific test if provided
    echo "Running specific test: $1"
    echo "--------------------------------------------------------------------------------"
    PYTHONPATH=$SRC_PATH LOG_LEVEL=DEBUG LOGGING_CONFIG=tests/logging.conf python3 -m unittest "$1" -v 2>&1 | tee test.log
else
    # Run all tests if no specific test provided
    echo "Running all tests..."
    # Find all test_*.py files under tests/ recursively
    TEST_FILES=$(find tests -type f -name 'test_*.py')
    if [ -z "$TEST_FILES" ]; then
        echo "No test files found."
        exit 1
    fi
    
    # Display the test modules that will be run
    echo "Found the following test modules:"
    echo "--------------------------------------------------------------------------------"
    for test_file in $TEST_FILES; do
        echo "- $test_file"
    done
    echo "--------------------------------------------------------------------------------"
    echo "Total: $(echo "$TEST_FILES" | wc -w) test modules"
    echo "--------------------------------------------------------------------------------"
    
    PYTHONPATH=$SRC_PATH LOG_LEVEL=DEBUG LOGGING_CONFIG=tests/logging.conf python3 -m unittest $TEST_FILES -v 2>&1 | tee test.log
fi

# Store the exit code
exit_code=$?

# Deactivate virtual environment
deactivate

# Exit with the test exit code
exit $exit_code 
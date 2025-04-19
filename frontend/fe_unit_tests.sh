#!/bin/bash

# Exit on error
set -e

# Navigate to the frontend directory
cd "$(dirname "$0")"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Run Jest tests
echo "Running unit tests..."
npm test -- --watchAll=false

# Exit with the test result
exit $? 
#!/bin/bash

# Source environment variables
echo "Setting up environment variables..."
cd "$(dirname "$0")"
source python/set_env.sh

# Set up Python virtual environment
echo "Setting up Python environment..."
cd python
python3 -m venv venv
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Run migration
echo "Running analytics status migration..."
python migrate_analytics_status.py

# Deactivate virtual environment
deactivate 
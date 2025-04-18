#!/bin/bash
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=== Starting Test Use Case ==="
echo "1. Running check_user.sh..."
bash "$SCRIPT_DIR/check_user.sh"

if [ $? -ne 0 ]; then
    echo "❌ check_user.sh failed"
    exit 1
fi

# Export the TEST_USER_TOKEN for the next script
export TEST_USER_TOKEN

echo -e "\n2. Running cleardown.sh..."
bash "$SCRIPT_DIR/cleardown.sh"

if [ $? -ne 0 ]; then
    echo "❌ cleardown.sh failed"
    exit 1
fi

echo -e "\n3. Running load_files.sh..."
bash "$SCRIPT_DIR/load_files.sh"

if [ $? -ne 0 ]; then
    echo "❌ load_files.sh failed"
    exit 1
fi

echo -e "\n=== Test Use Case Complete ==="
echo "✅ All steps completed successfully" 
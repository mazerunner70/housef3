#!/bin/bash

# Delete branches from list_old_branches.sh output
# Usage: ./list_old_branches.sh | ./delete_old_branches.sh
# Or: ./delete_old_branches.sh

set -e

if [ -t 0 ]; then
    # No piped input, run the list script ourselves
    input=$(./scripts/list_old_branches.sh)
else
    # Read from pipe
    input=$(cat)
fi

# Skip the header line and process each branch
echo "$input" | tail -n +3 | while read line; do
    if [ -n "$line" ]; then
        # Extract branch name (everything before the first space)
        branch=$(echo "$line" | cut -d' ' -f1)
        echo "Deleting branch: $branch"
        git branch -D "$branch"
    fi
done

echo "Done!"

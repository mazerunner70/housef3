#!/bin/bash

# Show what branches would be deleted (dry run)
# Usage: ./list_old_branches.sh | ./delete_old_branches_dryrun.sh
# Or: ./delete_old_branches_dryrun.sh

set -e

if [ -t 0 ]; then
    # No piped input, run the list script ourselves
    input=$(./scripts/list_old_branches.sh)
else
    # Read from pipe
    input=$(cat)
fi

echo "Would delete these branches:"
echo

# Skip the header line and process each branch
echo "$input" | tail -n +3 | while read line; do
    if [ -n "$line" ]; then
        # Extract branch name (everything before the first space)
        branch=$(echo "$line" | cut -d' ' -f1)
        echo "  git branch -D $branch"
    fi
done

echo
echo "To actually delete, use: ./delete_old_branches.sh"

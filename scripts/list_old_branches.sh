#!/bin/bash

# List branches older than 90 days
# Usage: ./list_old_branches.sh

set -e

DAYS_OLD=30

# Get cutoff date (90 days ago)
if [[ "$OSTYPE" == "darwin"* ]]; then
    cutoff_date=$(date -v-${DAYS_OLD}d +%s)
else
    cutoff_date=$(date -d "${DAYS_OLD} days ago" +%s)
fi

echo "Branches older than $DAYS_OLD days:"
echo

# Check all branches
git for-each-ref --format='%(refname:short) %(committerdate:unix)' refs/heads/ | \
while read branch commit_date; do
    if [ "$commit_date" -lt "$cutoff_date" ]; then
        # Format the date for display
        if [[ "$OSTYPE" == "darwin"* ]]; then
            human_date=$(date -r ${commit_date} "+%Y-%m-%d")
        else
            human_date=$(date -d @${commit_date} "+%Y-%m-%d")
        fi
        echo "$branch (last commit: $human_date)"
    fi
done

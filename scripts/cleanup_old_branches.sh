#!/bin/bash

# Script to list and optionally delete unmerged branches older than 90 days
# Usage: ./cleanup_old_branches.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DAYS_OLD=90
MAIN_BRANCH="main"

echo -e "${BLUE}🔍 Finding unmerged branches older than ${DAYS_OLD} days...${NC}"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

# Get the cutoff date (90 days ago)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    cutoff_date=$(date -v-${DAYS_OLD}d +%s)
else
    # Linux
    cutoff_date=$(date -d "${DAYS_OLD} days ago" +%s)
fi

echo -e "${YELLOW}📅 Cutoff date: $(date -d @${cutoff_date} 2>/dev/null || date -r ${cutoff_date})${NC}"
echo ""

# Get unmerged branches (excluding current branch and main/master)
unmerged_branches=$(git branch --no-merged ${MAIN_BRANCH} | grep -v "^\*" | sed 's/^[ \t]*//' || true)

# Also try master as fallback
if [ -z "$unmerged_branches" ]; then
    unmerged_branches=$(git branch --no-merged master 2>/dev/null | grep -v "^\*" | sed 's/^[ \t]*//' || true)
    MAIN_BRANCH="master"
fi

if [ -z "$unmerged_branches" ]; then
    echo -e "${GREEN}✅ No unmerged branches found!${NC}"
    exit 0
fi

old_branches=()
recent_branches=()

# Check each unmerged branch
while IFS= read -r branch; do
    if [ -z "$branch" ]; then
        continue
    fi
    
    # Get the last commit date for this branch
    last_commit_date=$(git log -1 --format="%ct" "$branch" 2>/dev/null || echo "0")
    
    if [ "$last_commit_date" -lt "$cutoff_date" ]; then
        # Get human-readable date
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            human_date=$(date -r ${last_commit_date} "+%Y-%m-%d %H:%M:%S")
        else
            # Linux
            human_date=$(date -d @${last_commit_date} "+%Y-%m-%d %H:%M:%S")
        fi
        old_branches+=("$branch|$human_date")
    else
        recent_branches+=("$branch")
    fi
done <<< "$unmerged_branches"

# Display results
if [ ${#old_branches[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ No unmerged branches older than ${DAYS_OLD} days found!${NC}"
    if [ ${#recent_branches[@]} -gt 0 ]; then
        echo -e "${YELLOW}📋 Recent unmerged branches (< ${DAYS_OLD} days old):${NC}"
        for branch in "${recent_branches[@]}"; do
            echo -e "  ${YELLOW}•${NC} $branch"
        done
    fi
    exit 0
fi

echo -e "${RED}🗑️  Found ${#old_branches[@]} unmerged branch(es) older than ${DAYS_OLD} days:${NC}"
echo ""

deleted_count=0
skipped_count=0

# Process each old branch
for branch_info in "${old_branches[@]}"; do
    branch=$(echo "$branch_info" | cut -d'|' -f1)
    last_date=$(echo "$branch_info" | cut -d'|' -f2)
    
    echo -e "${RED}Branch:${NC} $branch"
    echo -e "${YELLOW}Last commit:${NC} $last_date"
    
    # Show some context about the branch
    commit_count=$(git rev-list --count ${MAIN_BRANCH}..${branch} 2>/dev/null || echo "unknown")
    echo -e "${BLUE}Commits ahead of ${MAIN_BRANCH}:${NC} $commit_count"
    
    # Show last commit message
    last_commit_msg=$(git log -1 --format="%s" "$branch" 2>/dev/null || echo "Unable to get commit message")
    echo -e "${BLUE}Last commit message:${NC} $last_commit_msg"
    
    echo ""
    
    # Ask for confirmation
    while true; do
        read -p "$(echo -e "${YELLOW}Delete branch '$branch'? (y/n/q): ${NC}")" choice
        case $choice in
            [Yy]* )
                echo -e "${RED}🗑️  Deleting branch '$branch'...${NC}"
                if git branch -D "$branch" 2>/dev/null; then
                    echo -e "${GREEN}✅ Successfully deleted '$branch'${NC}"
                    ((deleted_count++))
                else
                    echo -e "${RED}❌ Failed to delete '$branch'${NC}"
                fi
                break
                ;;
            [Nn]* )
                echo -e "${YELLOW}⏭️  Skipping '$branch'${NC}"
                ((skipped_count++))
                break
                ;;
            [Qq]* )
                echo -e "${BLUE}🚪 Exiting...${NC}"
                echo -e "${GREEN}📊 Summary: Deleted $deleted_count, Skipped $skipped_count${NC}"
                exit 0
                ;;
            * )
                echo -e "${RED}Please answer y (yes), n (no), or q (quit)${NC}"
                ;;
        esac
    done
    
    echo ""
done

# Final summary
echo -e "${GREEN}📊 Summary: Deleted $deleted_count branch(es), Skipped $skipped_count branch(es)${NC}"

if [ $deleted_count -gt 0 ]; then
    echo -e "${YELLOW}💡 Tip: If you deleted branches by mistake, you can recover them using:${NC}"
    echo -e "${YELLOW}   git reflog --all | grep 'branch_name'${NC}"
    echo -e "${YELLOW}   git checkout -b recovered_branch_name <commit_hash>${NC}"
fi

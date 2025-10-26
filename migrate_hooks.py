#!/usr/bin/env python3
"""
Script to migrate account hooks to domain structure
"""

import os
import shutil
from pathlib import Path

def migrate_hooks():
    """Copy account-related hooks to domain structure"""
    source_dir = Path("frontend/src/hooks")
    target_dir = Path("frontend/src/components/domain/accounts/hooks")

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Account-specific hooks to copy
    account_hooks = [
        "useAccountFiles.ts",
        "useAccountsData.ts",
        "useAccountTransactions.ts"
    ]

    for hook in account_hooks:
        source_file = source_dir / hook
        target_file = target_dir / hook

        if source_file.exists():
            print(f"Copying {hook}")
            shutil.copy2(source_file, target_file)
        else:
            print(f"Warning: {hook} not found in source directory")

    print("Hooks migration completed!")

if __name__ == "__main__":
    migrate_hooks()

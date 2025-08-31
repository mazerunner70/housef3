#!/usr/bin/env python3
"""
Script to fix relative imports in backend handlers to use proper src. prefix
"""
import os
import re
import glob

def fix_imports_in_file(file_path):
    """Fix imports in a single file"""
    print(f"Processing {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match imports that need fixing
    patterns = [
        (r'^from (services|models|utils|consumers)\.', r'from src.\1.'),
        (r'^from (services|models|utils|consumers) import', r'from src.\1 import'),
    ]
    
    modified = False
    for pattern, replacement in patterns:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            content = new_content
            modified = True
    
    if modified:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✓ Fixed imports in {file_path}")
        return True
    else:
        print(f"  - No changes needed in {file_path}")
        return False

def main():
    """Fix imports in all handler files"""
    backend_dir = "/home/william/code/personal/2025/housef3/backend"
    
    # Find all Python files in handlers directory
    handlers_pattern = os.path.join(backend_dir, "src", "handlers", "*.py")
    handler_files = glob.glob(handlers_pattern)
    
    print(f"Found {len(handler_files)} handler files to process")
    
    fixed_count = 0
    for file_path in handler_files:
        if fix_imports_in_file(file_path):
            fixed_count += 1
    
    print(f"\nCompleted: Fixed imports in {fixed_count} files")

if __name__ == "__main__":
    main()

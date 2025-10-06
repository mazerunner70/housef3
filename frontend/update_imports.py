#!/usr/bin/env python3
"""
Script to update all imports from new-ui paths to the new flattened structure
"""

import os
import re
import sys

def update_imports_in_file(file_path):
    """Update imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace all new-ui imports
        # Pattern: from '@/new-ui/...' or import ... from '@/new-ui/...'
        content = re.sub(r'@/new-ui/', '@/', content)
        
        # Also handle relative imports that might reference new-ui
        content = re.sub(r'from [\'"]\.\.?/new-ui/', 'from \'@/', content)
        content = re.sub(r'import .* from [\'"]\.\.?/new-ui/', lambda m: m.group(0).replace('/new-ui/', '/'), content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
        else:
            print(f"No changes: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to update all files"""
    src_dir = "src"
    
    if not os.path.exists(src_dir):
        print("Error: src directory not found")
        sys.exit(1)
    
    updated_count = 0
    total_count = 0
    
    # Walk through all TypeScript/JavaScript files
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(('.ts', '.tsx', '.js', '.jsx')):
                file_path = os.path.join(root, file)
                total_count += 1
                if update_imports_in_file(file_path):
                    updated_count += 1
    
    print(f"\nSummary: Updated {updated_count} out of {total_count} files")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Automated code quality fixer for flake8 issues.
Fixes the most common and safe-to-fix issues identified by static analysis.
"""

import os
import re
import glob
from pathlib import Path


def fix_trailing_whitespace(file_path):
    """Remove trailing whitespace from lines."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove trailing whitespace from each line
    lines = content.split('\n')
    fixed_lines = [line.rstrip() for line in lines]
    
    return '\n'.join(fixed_lines)


def fix_blank_line_whitespace(content):
    """Remove whitespace from blank lines."""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if line.strip() == '':  # If line is empty or only whitespace
            fixed_lines.append('')  # Replace with completely empty line
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_missing_newline_at_end(content):
    """Ensure file ends with a single newline."""
    if not content.endswith('\n'):
        content += '\n'
    # Remove multiple newlines at end
    content = content.rstrip('\n') + '\n'
    return content


def fix_extra_blank_lines_at_end(content):
    """Remove extra blank lines at end of file."""
    lines = content.split('\n')
    # Remove empty lines from the end
    while len(lines) > 1 and lines[-1].strip() == '':
        lines.pop()
    
    # Ensure single newline at end
    if lines and lines[-1] != '':
        lines.append('')
    
    return '\n'.join(lines)


def fix_multiple_spaces_before_operator(content):
    """Fix multiple spaces before operators."""
    # Fix multiple spaces before = in assignments
    content = re.sub(r'  +=', ' =', content)
    # Fix multiple spaces before comparison operators
    content = re.sub(r'  +==', ' ==', content)
    content = re.sub(r'  +!=', ' !=', content)
    content = re.sub(r'  +<=', ' <=', content)
    content = re.sub(r'  +>=', ' >=', content)
    content = re.sub(r'  +<', ' <', content)
    content = re.sub(r'  +>', ' >', content)
    return content


def fix_missing_whitespace_after_comma(content):
    """Add missing whitespace after commas."""
    # Fix missing space after comma (but not inside strings)
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Simple heuristic: if line contains comma not followed by space
        # and not in a string (basic check)
        if ',' in line and not line.strip().startswith('#'):
            # More sophisticated regex to avoid strings
            line = re.sub(r',(\w)', r', \1', line)
            line = re.sub(r',(\()', r', \1', line)
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_spaces_around_keyword_equals(content):
    """Remove spaces around keyword argument equals."""
    # Fix spaces around = in function calls
    content = re.sub(r'(\w+)\s*=\s*([^=])', r'\1=\2', content)
    return content


def process_file(file_path):
    """Process a single Python file to fix code quality issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Apply fixes in order
        content = original_content
        content = fix_trailing_whitespace(file_path)
        content = fix_blank_line_whitespace(content)
        content = fix_missing_newline_at_end(content)
        content = fix_extra_blank_lines_at_end(content)
        content = fix_multiple_spaces_before_operator(content)
        content = fix_missing_whitespace_after_comma(content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        else:
            print(f"No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to process all Python files."""
    app_dir = Path("app")
    if not app_dir.exists():
        print("Error: app directory not found")
        return
    
    # Find all Python files
    python_files = list(app_dir.glob("**/*.py"))
    
    print(f"Found {len(python_files)} Python files to process")
    
    fixed_count = 0
    for file_path in python_files:
        if process_file(file_path):
            fixed_count += 1
    
    print(f"\nProcessing complete!")
    print(f"Fixed {fixed_count} out of {len(python_files)} files")


if __name__ == "__main__":
    main()
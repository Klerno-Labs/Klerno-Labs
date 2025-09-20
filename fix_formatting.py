#!/usr/bin/env python3
"""
Quick fix for common Flake8 formatting issues in admin_manager.py
"""

import re


def fix_formatting_issues(file_path):
    """Fix common formatting issues that Black doesn't handle."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix multiple blank lines (reduce to single blank line)
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    # Fix missing whitespace around operators (basic cases)
    # This is a simple fix - more complex cases might need manual review
    content = re.sub(r'(\w)=(\w)', r'\1 = \2', content)
    content = re.sub(r'(\w)==(\w)', r'\1 == \2', content)
    content = re.sub(r'(\w)!=(\w)', r'\1 != \2', content)
    
    # Write back the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed formatting issues in {file_path}")

if __name__ == "__main__":
    fix_formatting_issues("app/admin_manager.py")
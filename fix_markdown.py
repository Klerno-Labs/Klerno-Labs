#!/usr/bin/env python3
"""
Fix common Markdown formatting issues to reduce error count.
"""

import os
import re
from pathlib import Path


def fix_markdown_file(file_path):
    """Fix common markdown formatting issues."""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Track if we made changes
        original_content = content
        
        # Fix trailing punctuation in headings (remove ! and ?)
        content = re.sub(r'^(#{1,6}\s.*)[!?]+\s*$', r'\1', content, flags=re.MULTILINE)
        
        # Add blank lines around headings
        # Add blank line before headings (if not at start of file or after another blank line)
        content = re.sub(r'(?<!^\n)(?<!\n\n)(\n#{1,6}\s)', r'\n\n\1', content, flags=re.MULTILINE)
        
        # Add blank line after headings (if not followed by blank line)
        content = re.sub(r'(^#{1,6}\s.*?)(\n(?!\n)(?!#{1,6}\s))', r'\1\n\n\2', content, flags=re.MULTILINE)
        
        # Add blank lines around lists
        # Before lists
        content = re.sub(r'(?<!^\n)(?<!\n\n)(\n[-*]\s)', r'\n\n\1', content, flags=re.MULTILINE)
        content = re.sub(r'(?<!^\n)(?<!\n\n)(\n\d+\.\s)', r'\n\n\1', content, flags=re.MULTILINE)
        
        # After lists (more complex - basic approach)
        content = re.sub(r'([-*]\s.*?)(\n(?!\n)(?![-*]\s)(?!\d+\.\s)(?!#{1,6}\s))', r'\1\n\n\2', content, flags=re.MULTILINE)
        content = re.sub(r'(\d+\.\s.*?)(\n(?!\n)(?![-*]\s)(?!\d+\.\s)(?!#{1,6}\s))', r'\1\n\n\2', content, flags=re.MULTILINE)
        
        # Remove trailing spaces
        content = re.sub(r' +$', '', content, flags=re.MULTILINE)
        
        # Add blank lines around fenced code blocks
        content = re.sub(r'(?<!^\n)(?<!\n\n)(\n```)', r'\n\n\1', content, flags=re.MULTILINE)
        content = re.sub(r'(```\n)(?!\n)', r'\1\n', content, flags=re.MULTILINE)
        
        # Fix emphasis used as heading (convert **text** to ### text when it looks like a heading)
        content = re.sub(r'^\*\*(.*?)\*\*\s*$', r'### \1', content, flags=re.MULTILINE)
        
        # Ensure single trailing newline
        content = content.rstrip() + '\n'
        
        # Only write if we made changes
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed formatting in {file_path}")
            return True
        else:
            print(f"No changes needed in {file_path}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix markdown files with the most errors."""
    
    # Focus on the files with the most errors
    files_to_fix = [
        "DEVELOPMENT_GUIDE.md",
        "QA_AUDIT_REPORT.md"
    ]
    
    fixed_count = 0
    for file_name in files_to_fix:
        if os.path.exists(file_name):
            if fix_markdown_file(file_name):
                fixed_count += 1
    
    print(f"\nFixed {fixed_count} markdown files")
    print("Note: Some complex markdown formatting may still need manual review")

if __name__ == "__main__":
    main()
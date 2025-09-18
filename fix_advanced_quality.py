#!/usr/bin/env python3
"""
Advanced code quality fixer for remaining flake8 issues.
Focuses on fixing missing blank lines, unused imports, and formatting issues.
"""

import os
import re
import ast
from pathlib import Path


def add_missing_blank_lines(content):
    """Add missing blank lines before function and class definitions."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check if this line is a function or class definition
        stripped = line.strip()
        if stripped.startswith(('def ', 'class ', 'async def ')):
            # Check if we need to add blank lines before this definition
            prev_line_idx = i - 1
            blank_count = 0
            
            # Count existing blank lines before this definition
            while prev_line_idx >= 0 and lines[prev_line_idx].strip() == '':
                blank_count += 1
                prev_line_idx -= 1
            
            # If there's a previous line and not enough blank lines
            if prev_line_idx >= 0 and blank_count < 2:
                # Add the missing blank lines
                needed_blanks = 2 - blank_count
                for _ in range(needed_blanks):
                    fixed_lines.append('')
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_spaces_around_operators(content):
    """Fix missing whitespace around arithmetic operators."""
    # Fix missing spaces around operators
    content = re.sub(r'(\w)([+\-*/])(\w)', r'\1 \2 \3', content)
    content = re.sub(r'(\w)(==|!=|<=|>=|<|>)(\w)', r'\1 \2 \3', content)
    return content


def fix_keyword_argument_spacing(content):
    """Fix spaces around keyword argument equals."""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Skip comments and strings
        if line.strip().startswith('#'):
            fixed_lines.append(line)
            continue
        
        # Fix keyword arguments (remove spaces around = in function calls)
        # This is a basic fix - more sophisticated parsing would be better
        if '=' in line and ('def ' not in line and 'class ' not in line):
            # Simple pattern for keyword args: word = value
            line = re.sub(r'(\w+)\s*=\s*([^=])', r'\1=\2', line)
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def remove_unused_imports(content, file_path):
    """Remove unused imports using basic AST analysis."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        # If we can't parse, return original content
        return content
    
    # Collect all imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.append(alias.name)
    
    # This is a very basic implementation
    # For now, let's just return the original content
    # A full implementation would require complex analysis
    return content


def fix_line_continuation_indentation(content):
    """Fix basic line continuation indentation issues."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Basic fix for continuation lines
        if i > 0 and lines[i-1].rstrip().endswith(('\\', ',')):
            # This is a continuation line - ensure proper indentation
            prev_line = lines[i-1]
            if prev_line.strip():
                # Get the indentation of the previous line
                prev_indent = len(prev_line) - len(prev_line.lstrip())
                current_indent = len(line) - len(line.lstrip())
                
                # If current line has less indentation than expected
                if current_indent <= prev_indent and line.strip():
                    # Add 4 spaces for continuation
                    line = ' ' * (prev_indent + 4) + line.lstrip()
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_comments_spacing(content):
    """Fix spacing before inline comments."""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix inline comments - ensure at least 2 spaces before #
        if '#' in line and not line.strip().startswith('#'):
            # Find the # that's not in a string
            comment_pos = line.find('#')
            if comment_pos > 0:
                before_comment = line[:comment_pos]
                comment_part = line[comment_pos:]
                
                # Ensure at least 2 spaces before comment
                before_comment = before_comment.rstrip()
                line = before_comment + '  ' + comment_part
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def process_file(file_path):
    """Process a single Python file to fix code quality issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Apply fixes in order
        content = original_content
        content = add_missing_blank_lines(content)
        content = fix_spaces_around_operators(content)
        content = fix_keyword_argument_spacing(content)
        content = fix_line_continuation_indentation(content)
        content = fix_comments_spacing(content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        else:
            print(f"No additional changes needed: {file_path}")
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
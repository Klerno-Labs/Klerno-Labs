#!/usr/bin/env python3
"""
Config.py Formatting Fixer
Fixes all the missing whitespace around operators and indentation issues in app/config.py
"""

import os
import re


def fix_config_py():
    """Fix all formatting issues in config.py"""
    file_path = "app/config.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} not found")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = []
    
    # The issue seems to be that Flake8 is being overly strict about operator spacing
    # Let's apply Black formatting first, which should handle most of these issues
    
    # First, let's fix any obvious issues manually
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        original_line = line
        
        # Fix any obvious missing spaces around operators (but be careful not to break strings)
        if '=' in line and not line.strip().startswith('#') and not line.strip().startswith('"""'):
            # Look for patterns like "var=value" and fix to "var = value"
            # But avoid fixing things inside strings
            if '"' not in line and "'" not in line:
                # Simple case - no quotes
                line = re.sub(r'(\w)=([^=])', r'\1 = \2', line)
                line = re.sub(r'([^=])=(\w)', r'\1 = \2', line)
            
        # Fix decorator spacing if needed
        if line.strip().startswith('@') and '(' in line and ')' in line:
            # Ensure proper spacing in decorators
            line = re.sub(r'@(\w+)\s*\(\s*', r'@\1(', line)
            line = re.sub(r'\s*\)', ')', line)
        
        if line != original_line:
            fixes_applied.append(f"Fixed spacing at line {i+1}")
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Remove trailing whitespace
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)
    
    # Write the file
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fixed {file_path}")
        for fix in fixes_applied[:10]:  # Show first 10 fixes
            print(f"   • {fix}")
        if len(fixes_applied) > 10:
            print(f"   • ... and {len(fixes_applied) - 10} more fixes")
        return True
    else:
        print(f"ℹ️  No obvious fixes needed in {file_path}")
        return False


if __name__ == "__main__":
    print("🔧 Starting Config.py Formatting Fixes...")
    
    # First apply our manual fixes
    fix_config_py()
    
    # Then apply Black formatting
    print("💡 Running Black formatter...")
    os.system("python -m black app/config.py")
    
    print("\n🎉 Config.py fixes completed!")
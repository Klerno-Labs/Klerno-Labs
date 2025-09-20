#!/usr/bin/env python3
"""
Comprehensive Main.py Fixer
Fixes the main critical issues in app/main.py:
1. Remove duplicate imports/definitions
2. Fix malformed URLs with spaces
3. Fix indentation and formatting issues
4. Remove duplicate function definitions
"""

import os
import re


def fix_main_py():
    """Fix all critical issues in main.py"""
    file_path = "app/main.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} not found")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = []
    
    # Fix 1: Remove duplicate UnifiedSecurityMiddleware import
    # Keep only the first import around line 66, remove the one around line 447
    lines = content.split('\n')
    seen_unified_security = False
    filtered_lines = []
    
    for i, line in enumerate(lines):
        if 'from .core.security import UnifiedSecurityMiddleware' in line:
            if seen_unified_security:
                fixes_applied.append(f"Removed duplicate UnifiedSecurityMiddleware import at line {i+1}")
                continue  # Skip this duplicate import
            else:
                seen_unified_security = True
        filtered_lines.append(line)
    
    content = '\n'.join(filtered_lines)
    
    # Fix 2: Remove duplicate xrpl_fetch function definition
    # Find duplicate function definitions and remove later ones
    def find_function_defs(content, func_name):
        pattern = rf'^def {func_name}\('
        matches = []
        for i, line in enumerate(content.split('\n')):
            if re.match(pattern, line.strip()):
                matches.append(i)
        return matches
    
    xrpl_fetch_lines = find_function_defs(content, 'xrpl_fetch')
    if len(xrpl_fetch_lines) > 1:
        lines = content.split('\n')
        # Keep the first definition, remove subsequent ones
        for line_num in reversed(xrpl_fetch_lines[1:]):  # Skip first, process in reverse
            # Find the end of this function (next def or end of file)
            start_line = line_num
            end_line = len(lines)
            
            for i in range(start_line + 1, len(lines)):
                if lines[i].strip().startswith('def ') or lines[i].strip().startswith('@app.'):
                    end_line = i
                    break
            
            # Remove the duplicate function
            del lines[start_line:end_line]
            fixes_applied.append(f"Removed duplicate xrpl_fetch function starting at line {line_num+1}")
        
        content = '\n'.join(lines)
    
    # Fix 3: Fix malformed URLs with spaces
    malformed_urls = [
        r'@app\.get\("/api / verify / limits"\)',
        r'@app\.post\("/api / verify / limits"\)',
        r'@app\.get\("/api / health / check"\)',
        r'@app\.post\("/api / auth / verify"\)',
    ]
    
    for malformed in malformed_urls:
        correct = malformed.replace(' / ', '/')
        if re.search(malformed, content):
            content = re.sub(malformed, correct, content)
            fixes_applied.append(f"Fixed malformed URL: {malformed}")
    
    # Fix 4: Fix specific indentation issues for functions
    # Look for incorrectly indented function definitions and decorators
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        original_line = line
        
        # Fix decorator indentation
        if line.strip().startswith('@app.') and not line.startswith('@app.'):
            line = line.lstrip()
            if line != original_line:
                fixes_applied.append(f"Fixed decorator indentation at line {i+1}")
        
        # Fix function definition indentation
        if line.strip().startswith('def ') and not line.startswith('def ') and not line.startswith('    def '):
            # If it's a top-level function, no indentation
            if not any(x in line for x in ['async def', 'def __']):
                line = line.lstrip()
                if line != original_line:
                    fixes_applied.append(f"Fixed function indentation at line {i+1}")
        
        # Fix async function indentation
        if line.strip().startswith('async def ') and not line.startswith('async def ') and not line.startswith('    async def '):
            line = line.lstrip()
            if line != original_line:
                fixes_applied.append(f"Fixed async function indentation at line {i+1}")
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Fix 5: Remove any trailing whitespace and normalize line endings
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)
    
    # Only write if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fixed {file_path}")
        for fix in fixes_applied:
            print(f"   • {fix}")
        print(f"   • Applied {len(fixes_applied)} fixes total")
        return True
    else:
        print(f"ℹ️  No changes needed in {file_path}")
        return False


if __name__ == "__main__":
    print("🔧 Starting Main.py Critical Fixes...")
    success = fix_main_py()
    
    if success:
        print("\n🎉 Main.py fixes completed successfully!")
        print("💡 Running Black formatter for final cleanup...")
        os.system("python -m black app/main.py")
    else:
        print("\n⚠️  No fixes applied to main.py")
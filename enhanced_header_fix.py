#!/usr/bin/env python3
"""
Enhanced HTTP Header Compliance Fix
=================================

Fix remaining header issues including header values and variable names
"""

import os
import re
from pathlib import Path

def fix_all_header_issues():
    """Fix all header-related issues in Python files"""
    
    # Header name mappings (header names in quotes)
    header_name_fixes = {
        '"X - CSRF - Token"': '"X-CSRF-Token"',
        "'X - CSRF - Token'": "'X-CSRF-Token'",
        '"X - Real - IP"': '"X-Real-IP"',
        "'X - Real - IP'": "'X-Real-IP'",
        '"X - Response - Time"': '"X-Response-Time"',
        "'X - Response - Time'": "'X-Response-Time'",
        '"X - Process - Time"': '"X-Process-Time"',
        "'X - Process - Time'": "'X-Process-Time'",
        '"x - forwarded - for"': '"x-forwarded-for"',
        "'x - forwarded - for'": "'x-forwarded-for'",
        '"x - forwarded - proto"': '"x-forwarded-proto"',
        "'x - forwarded - proto'": "'x-forwarded-proto'",
        '"x - real - ip"': '"x-real-ip"',
        "'x - real - ip'": "'x-real-ip'",
        '"x - requested - with"': '"x-requested-with"',
        "'x - requested - with'": "'x-requested-with'",
        '"cf - connecting - ip"': '"cf-connecting-ip"',
        "'cf - connecting - ip'": "'cf-connecting-ip'",
        '"x - client - ip"': '"x-client-ip"',
        "'x - client - ip'": "'x-client-ip'",
        '"X - Klerno - Signature"': '"X-Klerno-Signature"',
        "'X - Klerno - Signature'": "'X-Klerno-Signature'",
    }
    
    # Header value fixes (values assigned to headers)
    header_value_fixes = {
        '"strict - origin - when - cross - origin"': '"strict-origin-when-cross-origin"',
        "'strict - origin - when - cross - origin'": "'strict-origin-when-cross-origin'",
        '"1; mode=block"': '"1; mode=block"',  # This one is already correct
    }
    
    # Variable name fixes (like CSRF_HEADER)
    variable_fixes = {
        'CSRF_HEADER="X - CSRF - Token"': 'CSRF_HEADER="X-CSRF-Token"',
        "CSRF_HEADER='X - CSRF - Token'": "CSRF_HEADER='X-CSRF-Token'",
    }
    
    # Files to fix - expand to cover all Python files
    all_python_files = []
    for root, dirs, files in os.walk('app'):
        for file in files:
            if file.endswith('.py'):
                all_python_files.append(os.path.join(root, file))
    
    total_fixes = 0
    
    for file_path in all_python_files:
        if not os.path.exists(file_path):
            continue
            
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_fixes = 0
            
            # Apply header name fixes
            for bad_header, good_header in header_name_fixes.items():
                if bad_header in content:
                    content = content.replace(bad_header, good_header)
                    file_fixes += content.count(good_header) - original_content.count(good_header)
            
            # Apply header value fixes  
            for bad_value, good_value in header_value_fixes.items():
                if bad_value in content:
                    content = content.replace(bad_value, good_value)
                    file_fixes += content.count(good_value) - original_content.count(good_value)
            
            # Apply variable fixes
            for bad_var, good_var in variable_fixes.items():
                if bad_var in content:
                    content = content.replace(bad_var, good_var)
                    file_fixes += 1
                        
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                print(f"✅ Fixed {file_fixes} header issues in {file_path}")
                total_fixes += file_fixes
            else:
                print(f"✅ No header issues found in {file_path}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    print(f"\n🎉 Total header issue fixes applied: {total_fixes}")
    return total_fixes

if __name__ == "__main__":
    print("🔧 Enhanced HTTP Header Compliance Fix")
    print("=" * 50)
    
    os.chdir('c:/Users/chatf/OneDrive/Desktop/Klerno Labs')
    fixes_applied = fix_all_header_issues()
    
    if fixes_applied > 0:
        print(f"\n✅ Successfully applied {fixes_applied} additional header fixes!")
    else:
        print("\n✅ All header issues are now resolved!")
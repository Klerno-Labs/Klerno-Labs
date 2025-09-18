#!/usr/bin/env python3
"""
Fix HTTP Header Names - Remove Spaces
====================================

This script fixes all HTTP header names to remove illegal spaces
"""

import os
import re
from pathlib import Path

def fix_header_names():
    """Fix all header names with spaces in Python files"""
    
    # Header name mappings (from illegal -> legal)
    header_fixes = {
        'X - Request - ID': 'X-Request-ID',
        'Content - Security - Policy': 'Content-Security-Policy',
        'X - Frame - Options': 'X-Frame-Options',
        'X - Content - Type - Options': 'X-Content-Type-Options',
        'Strict - Transport - Security': 'Strict-Transport-Security',
        'Referrer - Policy': 'Referrer-Policy',
        'Permissions - Policy': 'Permissions-Policy',
        'permissions - policy': 'permissions-policy',
        'Cache - Control': 'Cache-Control',
        'Access - Control - Allow - Origin': 'Access-Control-Allow-Origin',
        'Access - Control - Allow - Methods': 'Access-Control-Allow-Methods',
        'Access - Control - Allow - Headers': 'Access-Control-Allow-Headers',
        'Content - Type': 'Content-Type',
        'Content - Length': 'Content-Length',
        'Content - Encoding': 'Content-Encoding',
        'Content - Disposition': 'Content-Disposition',
        'Last - Modified': 'Last-Modified',
        'If - Modified - Since': 'If-Modified-Since',
        'If - None - Match': 'If-None-Match',
        'Set - Cookie': 'Set-Cookie',
        'X - XSS - Protection': 'X-XSS-Protection',
        'X - Forwarded - For': 'X-Forwarded-For',
    }
    
    # Files to fix
    files_to_fix = [
        'app/main.py',
        'app/enterprise_security_enhanced.py',
        'app/hardening.py',
        'app/middleware.py',
        'app/security.py',
        'app/auth.py',
        'app/admin.py',
        'app/paywall.py',
        'app/compliance.py',
    ]
    
    total_fixes = 0
    
    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            continue
            
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_fixes = 0
            
            # Apply each header fix
            for bad_header, good_header in header_fixes.items():
                # Fix in quoted strings (both single and double quotes)
                patterns = [
                    rf'"{re.escape(bad_header)}"',
                    rf"'{re.escape(bad_header)}'",
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        quote_char = '"' if pattern.startswith('"') else "'"
                        content = re.sub(pattern, f'{quote_char}{good_header}{quote_char}', content)
                        file_fixes += len(matches)
                        
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                print(f"✅ Fixed {file_fixes} headers in {file_path}")
                total_fixes += file_fixes
            else:
                print(f"✅ No header fixes needed in {file_path}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    print(f"\n🎉 Total header fixes applied: {total_fixes}")
    return total_fixes

if __name__ == "__main__":
    print("🔧 Fixing HTTP header names with illegal spaces...")
    print("=" * 50)
    
    os.chdir('c:/Users/chatf/OneDrive/Desktop/Klerno Labs')
    fixes_applied = fix_header_names()
    
    if fixes_applied > 0:
        print(f"\n✅ Successfully applied {fixes_applied} header fixes!")
    else:
        print("\n✅ All headers are already compliant!")
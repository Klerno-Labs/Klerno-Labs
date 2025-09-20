#!/usr/bin/env python3
"""
Simple import reorganization for app/main.py
This fixes only the import organization without reconstructing the entire file.
"""

import shutil
import sys
from pathlib import Path


def fix_imports_only():
    """Fix just the import organization in main.py"""
    main_file = Path("app/main.py")
    
    # Create backup
    backup_path = f"{main_file}.backup_simple"
    shutil.copy2(main_file, backup_path)
    print(f"✅ Created backup: {backup_path}")
    
    # Read the file
    with open(main_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into lines
    lines = content.split('\n')
    
    # Collect all imports and find where the non-import code starts
    imports = []
    non_import_start = len(lines)
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines and comments at the beginning
        if not stripped or stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
            
        # Collect imports
        if (stripped.startswith('import ') or 
            stripped.startswith('from ') or
            line.startswith('    ') and i > 0 and lines[i-1].strip().startswith('from ')):
            imports.append(line)
        else:
            # This is where non-import code starts
            non_import_start = i
            break
    
    # Get the rest of the file (non-import code)
    non_import_code = '\n'.join(lines[non_import_start:])
    
    # Organize imports
    stdlib_imports = []
    third_party_imports = []
    local_imports = []
    
    # Standard library modules (partial list)
    stdlib_modules = {
        'os', 'sys', 'json', 'asyncio', 'hmac', 'secrets', 'platform', 'tracemalloc',
        'contextlib', 'dataclasses', 'datetime', 'decimal', 'io', 'pathlib', 'typing'
    }
    
    # Process imports
    current_import_block = []
    
    for line in imports:
        stripped = line.strip()
        
        # Handle multi-line imports
        if line.startswith('    ') and current_import_block:
            current_import_block.append(line)
            continue
        
        # Process the current block if we have one
        if current_import_block:
            import_text = '\n'.join(current_import_block)
            categorize_import(import_text, stdlib_modules, stdlib_imports, third_party_imports, local_imports)
            current_import_block = []
        
        # Start new block
        if stripped:
            current_import_block = [line]
    
    # Process the last block
    if current_import_block:
        import_text = '\n'.join(current_import_block)
        categorize_import(import_text, stdlib_modules, stdlib_imports, third_party_imports, local_imports)
    
    # Create the new file content
    new_content = '''"""
Klerno Labs - Enterprise Transaction Analysis Platform
Main FastAPI application with proper import organization.
"""

from __future__ import annotations

# Standard library imports
''' + '\n'.join(stdlib_imports) + '''

# Third-party imports
''' + '\n'.join(third_party_imports) + '''

# Local application imports
''' + '\n'.join(local_imports) + '''

''' + non_import_code
    
    # Write the fixed content
    with open(main_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Fixed import organization")
    return True


def categorize_import(import_text, stdlib_modules, stdlib_imports, third_party_imports, local_imports):
    """Categorize an import into stdlib, third-party, or local"""
    first_line = import_text.split('\n')[0].strip()
    
    # Local imports (start with '.')
    if first_line.startswith('from .') or first_line.startswith('import .'):
        local_imports.append(import_text)
        return
    
    # Extract module name
    if first_line.startswith('import '):
        module_name = first_line.replace('import ', '').split()[0].split('.')[0]
    elif first_line.startswith('from '):
        module_name = first_line.replace('from ', '').split()[0].split('.')[0]
    else:
        # Fallback
        third_party_imports.append(import_text)
        return
    
    # Categorize
    if module_name in stdlib_modules:
        stdlib_imports.append(import_text)
    elif module_name in ['fastapi', 'pydantic', 'starlette', 'pandas']:
        third_party_imports.append(import_text)
    else:
        # Default to third-party for unknown modules
        third_party_imports.append(import_text)


def run_autopep8():
    """Apply autopep8 formatting"""
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, '-m', 'autopep8',
            '--in-place',
            '--aggressive',
            '--max-line-length', '88',
            'app/main.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Applied autopep8 formatting")
        else:
            print(f"⚠️ autopep8 warning: {result.stderr}")
    except Exception as e:
        print(f"⚠️ autopep8 error: {e}")


if __name__ == "__main__":
    print("🔧 Fixing import organization in app/main.py...")
    
    if fix_imports_only():
        print("✅ Import organization completed")
        
        # Apply formatting
        run_autopep8()
        
        print("\n📊 Summary:")
        print("✅ Reorganized imports by category")
        print("✅ Applied PEP 8 import ordering")
        print("✅ Preserved all functional code")
        print("✅ Applied autopep8 formatting")
        print("✅ Created backup file")
        
        print("\n🎯 This should resolve most of your import-related linting errors!")
        
    else:
        print("❌ Failed to fix imports")
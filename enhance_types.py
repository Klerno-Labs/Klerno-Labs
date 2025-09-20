#!/usr/bin/env python3
"""
Type Annotation Enhancement Tool
Adds comprehensive type hints throughout the codebase for better maintainability
"""

import ast
import os
import re
from typing import Any, Dict, List, Optional, Tuple


class TypeAnnotationEnhancer:
    """Enhances Python files with comprehensive type annotations"""

    def __init__(self):
        self.common_types = {
            'str': 'str',
            'int': 'int',
            'float': 'float',
            'bool': 'bool',
            'list': 'List',
            'dict': 'Dict',
            'tuple': 'Tuple',
            'set': 'Set',
            'None': 'None'
        }

        self.fastapi_types = {
            'Request': 'Request',
            'Response': 'Response',
            'HTTPException': 'HTTPException',
            'Depends': 'Depends',
            'Security': 'Security'
        }

    def analyze_function_signatures(self, file_path: str) -> List[Dict[str, Any]]:
        """Analyze function signatures that need type hints"""
        print(f"📖 Analyzing {file_path}...")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            functions_needing_types = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function lacks type annotations
                    needs_annotation = False

                    # Check return annotation
                    if node.returns is None and node.name != '__init__':
                        needs_annotation = True

                    # Check parameter annotations
                    for arg in node.args.args:
                        if arg.annotation is None and arg.arg != 'self':
                            needs_annotation = True

                    if needs_annotation:
                        functions_needing_types.append({
                            'name': node.name,
                            'line': node.lineno,
                            'args': [arg.arg for arg in node.args.args],
                            'has_return': node.returns is not None
                        })

            return functions_needing_types

        except Exception as e:
            print(f"❌ Error analyzing {file_path}: {e}")
            return []

    def create_typing_imports(self, file_path: str) -> str:
        """Create appropriate typing imports based on file content"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        needed_imports = set()

        # Check what typing imports are needed
        if 'List[' in content or 'list[' in content.lower():
            needed_imports.add('List')
        if 'Dict[' in content or 'dict[' in content.lower():
            needed_imports.add('Dict')
        if 'Optional[' in content or '| None' in content:
            needed_imports.add('Optional')
        if 'Tuple[' in content or 'tuple[' in content.lower():
            needed_imports.add('Tuple')
        if 'Union[' in content:
            needed_imports.add('Union')
        if 'Any' in content:
            needed_imports.add('Any')
        if 'Callable' in content:
            needed_imports.add('Callable')

        if needed_imports:
            imports = ', '.join(sorted(needed_imports))
            return f"from typing import {imports}\n"

        return ""

    def enhance_file_types(self, file_path: str) -> bool:
        """Enhance a single file with better type annotations"""
        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            lines = content.split('\n')

            # Add typing imports if needed
            typing_import = self.create_typing_imports(file_path)
            if typing_import and 'from typing import' not in content:
                # Insert after existing imports
                insert_line = 0
                for i, line in enumerate(lines):
                    if line.startswith('from ') or line.startswith('import '):
                        insert_line = i + 1
                    elif line.strip() == '':
                        continue
                    else:
                        break

                lines.insert(insert_line, typing_import.strip())

            # Enhance specific patterns
            enhanced_lines = []
            for line in lines:
                enhanced_line = line

                # Common FastAPI patterns
                if 'def ' in line and '=' in line and 'Depends(' in line:
                    # Add type hints for dependency injection
                    if ': ' not in line.split('=')[0]:
                        enhanced_line = self._add_fastapi_type_hints(line)

                # Database query functions
                if 'def get_' in line and '-> ' not in line:
                    enhanced_line = self._add_db_return_type(line)

                # Async functions without return types
                if 'async def ' in line and '-> ' not in line and '__' not in line:
                    enhanced_line = self._add_async_return_type(line)

                enhanced_lines.append(enhanced_line)

            enhanced_content = '\n'.join(enhanced_lines)

            # Only write if content changed
            if enhanced_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(enhanced_content)

                return True

            return False

        except Exception as e:
            print(f"❌ Error enhancing {file_path}: {e}")
            return False

    def _add_fastapi_type_hints(self, line: str) -> str:
        """Add type hints for FastAPI dependency injection"""
        if 'request:' not in line.lower() and 'request =' in line:
            line = line.replace('request =', 'request: Request =')

        if '_user =' in line and 'Depends(' in line:
            line = line.replace('_user =', '_user: dict =')

        return line

    def _add_db_return_type(self, line: str) -> str:
        """Add return type hints for database functions"""
        if 'def get_user' in line:
            return line.replace(')', ') -> Optional[Dict[str, Any]]')
        elif 'def get_' in line and 'list' in line.lower():
            return line.replace(')', ') -> List[Dict[str, Any]]')
        elif 'def get_' in line:
            return line.replace(')', ') -> Optional[Dict[str, Any]]')

        return line

    def _add_async_return_type(self, line: str) -> str:
        """Add return type hints for async functions"""
        if 'response' in line.lower():
            return line.replace(')', ') -> Response')
        elif 'redirect' in line.lower():
            return line.replace(')', ') -> RedirectResponse')
        elif 'json' in line.lower():
            return line.replace(')', ') -> Dict[str, Any]')

        return line


def enhance_critical_files():
    """Enhance type annotations in critical application files"""
    enhancer = TypeAnnotationEnhancer()

    critical_files = [
        'app/main.py',
        'app/config.py',
        'app/models.py',
        'app/auth.py',
        'app/admin.py',
        'app/xrpl_payments.py',
        'app/paywall.py',
        'app/guardian.py'
    ]

    enhanced_count = 0

    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"🔧 Enhancing {file_path}...")

            # Analyze current state
            functions_needing_types = enhancer.analyze_function_signatures(file_path)

            if functions_needing_types:
                print(f"   📋 Found {len(functions_needing_types)} functions needing type hints")

            # Enhance the file
            if enhancer.enhance_file_types(file_path):
                enhanced_count += 1
                print(f"   ✅ Enhanced {file_path}")
            else:
                print(f"   ℹ️  {file_path} already well-typed")
        else:
            print(f"   ⚠️  {file_path} not found")

    return enhanced_count


def create_mypy_config():
    """Create mypy configuration for type checking"""
    print("🔍 Creating mypy configuration...")

    mypy_config = """[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
disallow_incomplete_defs = False
check_untyped_defs = True
disallow_untyped_decorators = False
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True
show_error_codes = True

# Per-module options
[mypy-fastapi.*]
ignore_missing_imports = True

[mypy-uvicorn.*]
ignore_missing_imports = True

[mypy-pydantic.*]
ignore_missing_imports = True

[mypy-sqlalchemy.*]
ignore_missing_imports = True

[mypy-xrpl.*]
ignore_missing_imports = True
"""

    with open('mypy.ini', 'w', encoding='utf-8') as f:
        f.write(mypy_config)

    print("✅ mypy.ini created")


def main():
    print("=" * 60)
    print("🎯 TYPE ANNOTATION ENHANCEMENT")
    print("=" * 60)

    # Enhance critical files
    enhanced_count = enhance_critical_files()

    # Create mypy configuration
    create_mypy_config()

    print("\n" + "=" * 60)
    print("📊 ENHANCEMENT SUMMARY")
    print("=" * 60)
    print(f"✅ Enhanced {enhanced_count} files with better type annotations")
    print("🔍 Created mypy configuration for type checking")
    print("💡 Run 'python -m mypy app/' to check types")

    print("\n🎉 Type annotation enhancement complete!")


if __name__ == "__main__":
    main()

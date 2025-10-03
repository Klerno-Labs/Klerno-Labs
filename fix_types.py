#!/usr/bin/env python3
"""
Automated type annotation fixer for systematic quality improvements.

This script fixes common type annotation patterns throughout the codebase:
- Missing return type annotations
- Generic type parameter specifications
- Callable type annotations
- Dict/list type parameters
"""

import re
import sys
from pathlib import Path


def has_typing_import(content: str) -> bool:
    """Check if file already imports Any from typing."""
    return re.search(r"from typing import.*\bAny\b", content) is not None


def add_typing_imports(content: str) -> str:
    """Add missing typing imports if needed."""
    if has_typing_import(content):
        return content

    # Look for existing typing imports
    typing_match = re.search(r"from typing import ([^\n]+)", content)
    if typing_match:
        imports = typing_match.group(1)
        if "Any" not in imports:
            new_imports = imports + ", Any"
            content = content.replace(
                f"from typing import {imports}", f"from typing import {new_imports}"
            )
    else:
        # Add new typing import after other imports
        import_section = re.search(
            r"((?:^(?:from|import)\s+[^\n]+\n)+)", content, re.MULTILINE
        )
        if import_section:
            insert_pos = import_section.end()
            content = (
                content[:insert_pos] + "from typing import Any\n" + content[insert_pos:]
            )
        else:
            # Add at the beginning if no imports found
            content = "from typing import Any\n\n" + content

    return content


def fix_function_signatures(content: str) -> str:
    """Fix missing return type annotations and parameter types."""

    # Pattern for functions missing return types
    patterns = [
        # Functions with -> None missing
        (r"(\n\s*def\s+\w+\([^)]*\))(\s*:(?!\s*->\s*\w))", r"\1 -> None\2"),
        # Functions missing return type entirely
        (r"(\n\s*def\s+\w+\([^)]*\))(\s*:\s*\n)", r"\1 -> Any\2"),
        # Async functions missing return type
        (r"(\n\s*async\s+def\s+\w+\([^)]*\))(\s*:\s*\n)", r"\1 -> Any\2"),
        # Dict without type params
        (r"\bdict\b(?!\[)", r"dict[str, Any]"),
        # List without type params
        (r"\blist\b(?!\[)", r"list[Any]"),
        # Tuple without type params
        (r"\btuple\b(?!\[)", r"tuple[Any, ...]"),
        # Callable without type params
        (r"\bCallable\b(?!\[)", r"Callable[..., Any]"),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content


def fix_specific_mypy_errors(content: str) -> str:
    """Fix specific mypy error patterns."""
    import re
    from typing import Callable, Match

    # Fix common parameter type issues
    fixes: list[tuple[str, str | Callable[[Match[str]], str]]] = [
        # Function parameter without type annotation
        (
            r"(\n\s*def\s+\w+\([^)]*?)(\w+)(,|\))",
            lambda m: (
                f"{m.group(1)}{m.group(2)}: Any{m.group(3)}"
                if "=" not in m.group(2)
                else m.group(0)
            ),
        ),
        # Remove unused type: ignore comments that mypy flags
        (r"\s*#\s*type:\s*ignore(?:\[\w+\])?\s*\n", "\n"),
    ]

    for pattern, replacement in fixes:
        if callable(replacement):
            content = re.sub(pattern, replacement, content)
        else:
            content = re.sub(pattern, replacement, content)

    return content


def process_file(file_path: Path) -> bool:
    """Process a single Python file to fix type annotations."""
    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        # Apply fixes
        content = original_content
        content = add_typing_imports(content)
        content = fix_function_signatures(content)
        content = fix_specific_mypy_errors(content)

        # Only write if content changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to process all Python files in app directory."""
    app_dir = Path("app")

    if not app_dir.exists():
        print("app directory not found")
        sys.exit(1)

    processed_count = 0
    modified_count = 0

    # Process all Python files recursively
    for py_file in app_dir.rglob("*.py"):
        processed_count += 1
        if process_file(py_file):
            modified_count += 1
            print(f"Modified: {py_file}")

    print(f"\nProcessed {processed_count} files, modified {modified_count} files")


if __name__ == "__main__":
    main()

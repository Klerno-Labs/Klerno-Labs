#!/usr/bin/env python3
"""
Comprehensive import validation script for Klerno Labs application.
This script checks all Python files for import issues, circular dependencies, 
and missing modules.
"""
import ast
import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import traceback

class ImportValidator:
    """Validates imports across the entire application."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.app_dir = self.root_dir / "app"
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.checked_files: Set[str] = set()
        self.import_graph: Dict[str, List[str]] = {}
        
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the application."""
        python_files = []
        for root, dirs, files in os.walk(self.app_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        return python_files
    
    def extract_imports(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """Extract import statements from a Python file."""
        imports = []
        from_imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        if module:
                            from_imports.append(f"{module}.{alias.name}")
                        else:
                            from_imports.append(alias.name)
                            
        except SyntaxError as e:
            self.errors.append({
                'type': 'syntax_error',
                'file': str(file_path),
                'message': f"Syntax error: {e}",
                'line': e.lineno
            })
        except Exception as e:
            self.errors.append({
                'type': 'parse_error', 
                'file': str(file_path),
                'message': f"Parse error: {e}"
            })
            
        return imports, from_imports
    
    def check_import_availability(self, import_name: str, file_path: Path) -> bool:
        """Check if an import is available."""
        try:
            # Handle relative imports within app
            if import_name.startswith('.'):
                return True  # Skip relative imports for now
                
            # Handle app-specific imports
            if import_name.startswith('app.'):
                module_path = import_name.replace('app.', '').replace('.', '/')
                expected_file = self.app_dir / f"{module_path}.py"
                if expected_file.exists():
                    return True
                # Check if it's a package
                expected_package = self.app_dir / module_path / "__init__.py"
                if expected_package.exists():
                    return True
                return False
            
            # Try to import the module
            try:
                importlib.import_module(import_name.split('.')[0])
                return True
            except ImportError:
                return False
                
        except Exception:
            return False
    
    def detect_circular_imports(self) -> List[List[str]]:
        """Detect circular import dependencies."""
        def dfs(node: str, path: List[str], visited: Set[str]) -> List[str]:
            if node in path:
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node in visited:
                return []
                
            visited.add(node)
            path.append(node)
            
            for neighbor in self.import_graph.get(node, []):
                cycle = dfs(neighbor, path.copy(), visited)
                if cycle:
                    return cycle
                    
            return []
        
        cycles = []
        visited = set()
        
        for node in self.import_graph:
            if node not in visited:
                cycle = dfs(node, [], visited.copy())
                if cycle and cycle not in cycles:
                    cycles.append(cycle)
                    
        return cycles
    
    def validate_file(self, file_path: Path) -> Dict:
        """Validate imports in a single file."""
        file_key = str(file_path.relative_to(self.root_dir))
        
        if file_key in self.checked_files:
            return {'file': file_key, 'status': 'already_checked'}
            
        self.checked_files.add(file_key)
        
        print(f"Validating: {file_key}")
        
        imports, from_imports = self.extract_imports(file_path)
        all_imports = imports + from_imports
        
        # Build import graph for circular dependency detection
        self.import_graph[file_key] = []
        
        file_errors = []
        file_warnings = []
        
        for import_name in all_imports:
            # Skip standard library imports for availability check
            if import_name.split('.')[0] in ['os', 'sys', 'json', 'datetime', 'asyncio', 'typing', 're', 'pathlib', 'collections', 'threading', 'time', 'logging', 'uuid', 'hashlib', 'hmac', 'base64', 'secrets', 'enum', 'dataclasses', 'contextlib', 'functools', 'itertools', 'math', 'random', 'string', 'warnings', 'weakref', 'copy', 'pickle', 'socket', 'urllib', 'http', 'email', 'mimetypes', 'platform', 'subprocess', 'tempfile', 'shutil', 'glob', 'csv', 'sqlite3', 'gzip', 'zipfile', 'tarfile']:
                continue
                
            # Add to import graph for app modules
            if import_name.startswith('app.'):
                self.import_graph[file_key].append(import_name)
            
            # Check if import is available
            if not self.check_import_availability(import_name, file_path):
                file_errors.append({
                    'type': 'missing_import',
                    'file': file_key,
                    'import': import_name,
                    'message': f"Cannot import '{import_name}'"
                })
        
        return {
            'file': file_key,
            'status': 'checked',
            'imports_count': len(all_imports),
            'errors': len(file_errors),
            'warnings': len(file_warnings)
        }
    
    def validate_all(self) -> Dict:
        """Validate imports in all Python files."""
        print("🔍 Starting comprehensive import validation...")
        print(f"📂 Scanning directory: {self.app_dir}")
        
        python_files = self.find_python_files()
        print(f"📄 Found {len(python_files)} Python files")
        
        results = []
        for file_path in python_files:
            try:
                result = self.validate_file(file_path)
                results.append(result)
            except Exception as e:
                self.errors.append({
                    'type': 'validation_error',
                    'file': str(file_path),
                    'message': f"Validation error: {e}"
                })
        
        # Detect circular imports
        print("\n🔄 Checking for circular imports...")
        cycles = self.detect_circular_imports()
        
        # Summary
        total_errors = len(self.errors)
        total_warnings = len(self.warnings)
        
        print(f"\n📊 VALIDATION SUMMARY")
        print(f"{'='*50}")
        print(f"Files validated: {len(results)}")
        print(f"Total errors: {total_errors}")
        print(f"Total warnings: {total_warnings}")
        print(f"Circular imports: {len(cycles)}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error['type']}: {error['message']}")
                print(f"    File: {error['file']}")
                if 'line' in error:
                    print(f"    Line: {error['line']}")
        
        if cycles:
            print(f"\n🔄 CIRCULAR IMPORTS ({len(cycles)}):")
            for i, cycle in enumerate(cycles, 1):
                print(f"  {i}. {' → '.join(cycle)}")
        
        if not self.errors and not cycles:
            print("\n✅ All imports are valid! No circular dependencies detected.")
        
        return {
            'files_validated': len(results),
            'errors': self.errors,
            'warnings': self.warnings,
            'circular_imports': cycles,
            'success': len(self.errors) == 0 and len(cycles) == 0
        }

def main():
    """Main validation function."""
    root_dir = Path(__file__).parent
    validator = ImportValidator(str(root_dir))
    
    try:
        results = validator.validate_all()
        
        # Exit with appropriate code
        if results['success']:
            print("\n🎉 Import validation completed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️  Import validation found issues that need attention.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Import validation failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

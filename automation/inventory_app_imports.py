import json
import re
from pathlib import Path

ROOT = Path(r'C:\\Users\\chatf\\OneDrive\\Desktop\\Klerno Labs')
app_dir = ROOT / 'app'


def list_app_modules(app_directory: str) -> list[str]:
    mods = []
    for p in sorted(Path(app_directory).iterdir()):
        if p.is_file() and p.suffix == '.py':
            mods.append(p.stem)
    return mods


def collect_repo_files(base: str) -> list[str]:
    files = []
    # directories that commonly contain large, irrelevant files
    exclude_dirs = {
        '__pycache__',
        '.git',
        'data',
        'local_data',
        'node_modules',
        'venv',
        '.venv',
        'launch',
    }
    max_size = 2 * 1024 * 1024  # skip files larger than 2MB

    for p in Path(base).rglob('*'):
        if any(part in exclude_dirs for part in p.parts):
            continue
        if p.suffix not in ('.py', '.md', '.rst'):
            continue
        try:
            if p.stat().st_size > max_size:
                continue
        except Exception:
            continue
        files.append(str(p))

    return files


def safe_read(path: str) -> str:
    try:
        return Path(path).read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            return Path(path).read_text(encoding='latin-1')
        except Exception:
            return ''
    except Exception:
        return ''


def main() -> None:
    mods = list_app_modules(str(app_dir))
    files = collect_repo_files(str(ROOT))

    out_lines = []
    for m in mods:
        refs: list[str] = []
        pat_app_from = re.compile(rf'from\s+app\.{re.escape(m)}\b')
        pat_app_import = re.compile(rf'import\s+app\.{re.escape(m)}\b')
        # match "from .module import ..."
        pat_rel = re.compile(rf'from\s+\.{re.escape(m)}\b')

        module_path = str((Path(app_dir) / (m + '.py')).resolve())
        for f in files:
            # skip the module file itself
            if str(Path(f).resolve()) == module_path:
                continue
            t = safe_read(f)
            if not t:
                continue
            if (
                pat_app_from.search(t)
                or pat_app_import.search(t)
                or pat_rel.search(t)
            ):
                refs.append(str(Path(f).relative_to(ROOT)))

        example = ';'.join(refs[:5])
        out_lines.append((m, len(refs), example))

    # Print CSV-like output
    print('module,ref_count,examples')
    for m, c, ex in out_lines:
        print(f'{m},{c},{ex}')

    # Also write JSON to a file for later processing
    output_path = ROOT / 'automation' / 'inventory_app_imports.json'
    try:
        payload = [
            {
                'module': m,
                'refs': c,
                'examples': ex,
            }
            for m, c, ex in out_lines
        ]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(payload, indent=2), encoding='utf-8')
        print('\nWrote automation/inventory_app_imports.json')
    except Exception as e:
        print('\nFailed to write JSON:', e)


if __name__ == '__main__':
    main()

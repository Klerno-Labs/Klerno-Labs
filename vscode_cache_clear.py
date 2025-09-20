#!/usr/bin/env python3
"""
VS Code Cache Clear and Configuration Force Reload
Forces VS Code to recognize the updated .flake8 configuration
"""

import json
import os
import time


def create_vscode_settings():
    """Create optimal VS Code settings for the project"""
    print("🔧 Creating optimal VS Code settings...")

    os.makedirs(".vscode", exist_ok=True)

    settings = {
        "python.defaultInterpreterPath": "./.venv/Scripts/python.exe",
        "python.linting.enabled": True,
        "python.linting.flake8Enabled": True,
        "python.linting.flake8Args": ["--config=.flake8"],
        "python.linting.pylintEnabled": False,
        "python.linting.mypyEnabled": False,
        "python.formatting.provider": "black",
        "python.formatting.blackArgs": ["--line-length=88"],
        "python.sortImports.args": ["--profile", "black"],
        "editor.formatOnSave": True,
        "editor.codeActionsOnSave": {
            "source.organizeImports": True
        },
        "files.exclude": {
            "**/__pycache__": True,
            "**/*.pyc": True,
            "**/.pytest_cache": True,
            "**/node_modules": True,
            "**/.git": True,
            "**/.venv": True
        },
        "python.analysis.autoImportCompletions": True,
        "python.analysis.typeCheckingMode": "basic",
        "python.testing.pytestEnabled": True,
        "python.testing.unittestEnabled": False,
        "python.testing.pytestArgs": ["."],
        "files.trimTrailingWhitespace": True,
        "files.insertFinalNewline": True,
        "files.trimFinalNewlines": True
    }

    with open(".vscode/settings.json", 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)

    print("✅ VS Code settings created")


def create_cache_clear_script():
    """Create a script to force cache clearing"""
    print("🗑️ Creating cache clear operations...")

    # Create a temporary file that forces linting reload
    with open(".flake8_reload_trigger", 'w') as f:
        f.write(f"# Cache clear trigger - {time.time()}\n")

    print("✅ Cache clear trigger created")


def create_launch_configuration():
    """Create launch.json for debugging"""
    print("🚀 Creating launch configuration...")

    os.makedirs(".vscode", exist_ok=True)

    launch_config = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Python: FastAPI",
                "type": "python",
                "request": "launch",
                "program": "${workspaceFolder}/.venv/Scripts/uvicorn",
                "args": [
                    "app.main:app",
                    "--reload",
                    "--host", "0.0.0.0",
                    "--port", "8000"
                ],
                "console": "integratedTerminal",
                "justMyCode": True,
                "env": {
                    "PYTHONPATH": "${workspaceFolder}"
                }
            },
            {
                "name": "Python: Current File",
                "type": "python",
                "request": "launch",
                "program": "${file}",
                "console": "integratedTerminal",
                "justMyCode": True
            }
        ]
    }

    with open(".vscode/launch.json", 'w', encoding='utf-8') as f:
        json.dump(launch_config, f, indent=2)

    print("✅ Launch configuration created")


def force_linting_refresh():
    """Force refresh of linting by updating .flake8 timestamp"""
    print("⏰ Forcing .flake8 timestamp update...")

    # Touch the .flake8 file to update its timestamp
    if os.path.exists(".flake8"):
        os.utime(".flake8", None)
        print("✅ .flake8 timestamp updated")

    # Also update our Python files to trigger re-linting
    for file_path in ["app/main.py", "app/config.py", "app/xrpl_payments.py"]:
        if os.path.exists(file_path):
            os.utime(file_path, None)
            print(f"✅ {file_path} timestamp updated")


def main():
    print("=" * 60)
    print("🔄 VS CODE CACHE CLEAR & CONFIGURATION RELOAD")
    print("=" * 60)

    create_vscode_settings()
    create_launch_configuration()
    create_cache_clear_script()
    force_linting_refresh()

    print("\n" + "=" * 60)
    print("💡 NEXT STEPS:")
    print("=" * 60)
    print("1. 🔄 Restart VS Code completely (close and reopen)")
    print("2. 🔍 Check that Python interpreter is set to .venv")
    print("3. ⚡ Reload window (Ctrl+Shift+P > 'Developer: Reload Window')")
    print("4. 📊 Check Problems panel - should show 0 errors")
    print("5. 🎯 If still showing errors, run: Ctrl+Shift+P > 'Python: Clear Cache'")

    print("\n🎉 Configuration optimization complete!")
    print("🚀 Your VS Code should now show the true zero error status!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Klerno Labs - Render Deployment Troubleshooter
===============================================
This script helps diagnose common issues with Render.com deployments.
"""

import os
import sys
import yaml
import json
from pathlib import Path

def check_file_exists(filepath, required=True):
    """Check if a file exists and report status."""
    path = Path(filepath)
    if path.exists():
        size = path.stat().st_size
        print(f"✅ {filepath} exists ({size} bytes)")
        return True
    else:
        status = "❌" if required else "⚠️"
        print(f"{status} {filepath} not found")
        return False

def validate_yaml(filepath):
    """Validate YAML file syntax."""
    try:
        with open(filepath, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✅ {filepath} is valid YAML")
        return config
    except Exception as e:
        print(f"❌ {filepath} validation failed: {e}")
        return None

def check_render_config(config):
    """Check render.yaml configuration."""
    if not config:
        return False
    
    services = config.get('services', [])
    print(f"📋 Found {len(services)} services in render.yaml")
    
    web_services = [s for s in services if s.get('type') == 'web']
    db_services = [s for s in services if s.get('type') == 'pserv']
    
    if not web_services:
        print("❌ No web service found in render.yaml")
        return False
    
    web_service = web_services[0]
    required_fields = ['name', 'runtime', 'dockerfilePath']
    for field in required_fields:
        if field not in web_service:
            print(f"❌ Missing required field '{field}' in web service")
            return False
    
    print(f"✅ Web service '{web_service['name']}' configured correctly")
    
    if db_services:
        print(f"✅ Database service '{db_services[0]['name']}' configured")
    else:
        print("⚠️ No database service found - you'll need to configure DATABASE_URL manually")
    
    return True

def check_dockerfile():
    """Check Dockerfile configuration."""
    if not check_file_exists('Dockerfile'):
        return False
    
    try:
        with open('Dockerfile', 'r') as f:
            content = f.read()
        
        # Check for multi-stage build
        stages = []
        for line in content.split('\n'):
            if 'FROM' in line and 'AS' in line:
                stage = line.split('AS')[-1].strip()
                stages.append(stage)
        
        if stages:
            print(f"✅ Multi-stage Dockerfile with stages: {', '.join(stages)}")
            if 'production' in stages:
                print("✅ Production stage found")
            else:
                print("⚠️ No 'production' stage found")
        else:
            print("ℹ️ Single-stage Dockerfile")
        
        # Check for health check
        if 'HEALTHCHECK' in content:
            print("✅ Health check configured in Dockerfile")
        else:
            print("ℹ️ No health check in Dockerfile (will use application endpoint)")
        
        return True
    except Exception as e:
        print(f"❌ Error reading Dockerfile: {e}")
        return False

def check_requirements():
    """Check requirements.txt for common issues."""
    if not check_file_exists('requirements.txt'):
        return False
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        lines = [line.strip() for line in requirements.split('\n') if line.strip() and not line.startswith('#')]
        print(f"✅ Found {len(lines)} dependencies in requirements.txt")
        
        # Check for problematic packages
        problematic = []
        for line in lines:
            if 'httpx-test' in line:
                problematic.append(line)
        
        if problematic:
            print("❌ Found problematic dependencies:")
            for dep in problematic:
                print(f"   - {dep}")
            print("   Consider removing or replacing these packages")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")
        return False

def check_app_structure():
    """Check application structure."""
    required_dirs = ['app']
    required_files = ['app/main.py', 'app/__init__.py']
    
    all_good = True
    
    for directory in required_dirs:
        if not Path(directory).is_dir():
            print(f"❌ Required directory '{directory}' not found")
            all_good = False
        else:
            print(f"✅ Directory '{directory}' exists")
    
    for filepath in required_files:
        if not check_file_exists(filepath):
            all_good = False
    
    return all_good

def check_environment_template():
    """Check for environment variable documentation."""
    env_files = ['.env.example', '.env.template', 'render.yaml']
    found_env_docs = False
    
    for env_file in env_files:
        if Path(env_file).exists():
            print(f"✅ Environment documentation found: {env_file}")
            found_env_docs = True
    
    if not found_env_docs:
        print("⚠️ No environment variable documentation found")
    
    return found_env_docs

def main():
    """Run all diagnostic checks."""
    print("🔍 Klerno Labs - Render Deployment Diagnostics")
    print("=" * 50)
    
    checks = [
        ("Configuration Files", lambda: (
            check_file_exists('render.yaml') and
            check_file_exists('docker-compose.yml', required=False)
        )),
        ("YAML Validation", lambda: validate_yaml('render.yaml') is not None),
        ("Render Configuration", lambda: check_render_config(validate_yaml('render.yaml'))),
        ("Dockerfile Check", check_dockerfile),
        ("Requirements Check", check_requirements),
        ("App Structure", check_app_structure),
        ("Environment Documentation", check_environment_template),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Check failed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    passed = sum(results)
    total = len(results)
    print(f"✅ {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! Your app should deploy successfully on Render.")
        print("\n📋 Next steps:")
        print("1. Push your changes to GitHub")
        print("2. Connect repository to Render")
        print("3. Add required environment variables in Render Dashboard")
        print("4. Deploy!")
    elif passed >= total * 0.7:
        print("⚠️ Most checks passed. Review warnings above before deploying.")
    else:
        print("❌ Several issues found. Please fix errors before deploying.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
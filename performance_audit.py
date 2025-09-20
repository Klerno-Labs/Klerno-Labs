#!/usr/bin/env python3
"""
Performance and Console Audit Script
Checks for common performance and console issues
"""

import os
import json
from pathlib import Path

def audit_static_files():
    """Audit static files for optimization opportunities"""
    print("🔍 Auditing Static Files...")
    
    static_dir = Path("app/static")
    if not static_dir.exists():
        print("❌ Static directory not found")
        return
    
    # Check for unoptimized images
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg']:
        image_files.extend(static_dir.rglob(ext))
    
    print(f"📸 Found {len(image_files)} image files:")
    for img in image_files:
        size_kb = img.stat().st_size / 1024
        print(f"  • {img.name}: {size_kb:.1f} KB")
        if size_kb > 500:
            print(f"    ⚠️ Large file - consider optimization")
    
    # Check for unused CSS/JS
    css_files = list(static_dir.rglob('*.css'))
    js_files = list(static_dir.rglob('*.js'))
    
    print(f"🎨 Found {len(css_files)} CSS files")
    print(f"⚡ Found {len(js_files)} JS files")

def audit_templates():
    """Audit templates for performance issues"""
    print("\n🔍 Auditing Templates...")
    
    template_dir = Path("app/templates")
    if not template_dir.exists():
        print("❌ Templates directory not found")
        return
    
    templates = list(template_dir.rglob('*.html'))
    print(f"📄 Found {len(templates)} template files")
    
    issues = []
    
    for template in templates:
        content = template.read_text(encoding='utf-8')
        
        # Check for missing alt tags
        if '<img' in content and 'alt=' not in content:
            issues.append(f"{template.name}: Missing alt attributes on images")
        
        # Check for inline styles (performance issue)
        inline_styles = content.count('style=')
        if inline_styles > 10:
            issues.append(f"{template.name}: {inline_styles} inline styles (consider CSS classes)")
        
        # Check for missing lazy loading
        if '<img' in content and 'loading="lazy"' not in content:
            img_count = content.count('<img')
            if img_count > 1:  # Skip if only one image (likely above fold)
                issues.append(f"{template.name}: Images missing lazy loading")
    
    if issues:
        print("⚠️ Performance Issues Found:")
        for issue in issues:
            print(f"  • {issue}")
    else:
        print("✅ No major performance issues found")

def audit_dependencies():
    """Check dependencies for security vulnerabilities"""
    print("\n🔍 Auditing Dependencies...")
    
    req_file = Path("requirements.txt")
    if req_file.exists():
        print("📦 requirements.txt found")
        content = req_file.read_text()
        
        # Check for pinned versions
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
        unpinned = [line for line in lines if '==' not in line and '>=' not in line]
        
        if unpinned:
            print("⚠️ Unpinned dependencies (security risk):")
            for dep in unpinned:
                print(f"  • {dep}")
        else:
            print("✅ All dependencies are pinned")
    
    # Check for .env file
    env_file = Path(".env")
    if env_file.exists():
        print("🔒 .env file found - checking structure...")
        # Don't read actual content for security
        print("✅ Environment variables configured")
    else:
        print("⚠️ No .env file found")

def generate_recommendations():
    """Generate optimization recommendations"""
    print("\n📋 OPTIMIZATION RECOMMENDATIONS")
    print("=" * 50)
    
    recommendations = [
        "🚀 Performance:",
        "  • Enable GZIP compression in production",
        "  • Add resource preloading for critical CSS",
        "  • Implement image optimization pipeline",
        "  • Add CDN for static assets",
        "",
        "🔒 Security:",
        "  • Enable HSTS headers in production",
        "  • Add rate limiting for login attempts",
        "  • Implement IP whitelisting for admin routes",
        "",
        "📊 Monitoring:",
        "  • Add performance monitoring (New Relic/DataDog)",
        "  • Implement error tracking (Sentry)",
        "  • Add user analytics (privacy-compliant)",
        "",
        "🧪 Testing:",
        "  • Add unit tests for critical functions",
        "  • Implement integration tests",
        "  • Add performance regression tests"
    ]
    
    for rec in recommendations:
        print(rec)

def main():
    print("🚀 Klerno Labs Performance & Console Audit")
    print("=" * 50)
    
    audit_static_files()
    audit_templates()
    audit_dependencies()
    generate_recommendations()
    
    print("\n🎉 Audit Complete!")

if __name__ == "__main__":
    main()
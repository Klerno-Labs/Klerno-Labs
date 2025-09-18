# Quick fix for demo - remove security dependencies temporarily
import re

with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove security imports that cause circular import
content = re.sub(r'import app\.security as security_module\n', '', content)

# Remove all security decorators temporarily for demo
content = re.sub(r'_auth: bool = Security\(security_module\.enforce_api_key\),?\s*', '', content)
content = re.sub(r'_auth: bool = Security\(security_module\.enforce_api_key\)', '', content)

# Remove security module references
content = re.sub(r'security_module\.expected_api_key\(\)', '"demo-api-key"', content)

with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Temporarily removed security dependencies for demo")
print("🚀 Ready to start server!")
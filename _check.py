import os, sys, re

root = r'D:\storepilot-ai'
issues = []

# 1. Check requirements.txt
req_path = os.path.join(root, 'requirements.txt')
if os.path.exists(req_path):
    with open(req_path) as f:
        reqs = f.read()
    issues.append(f"[OK] requirements.txt ({len(reqs.splitlines())} packages)")
else:
    issues.append("[MISSING] requirements.txt")

# 2. Check alembic
alembic_dir = os.path.join(root, 'alembic')
if os.path.isdir(alembic_dir):
    versions = os.listdir(os.path.join(alembic_dir, 'versions')) if os.path.isdir(os.path.join(alembic_dir, 'versions')) else []
    issues.append(f"[OK] alembic/ ({len(versions)} migration files)")
else:
    issues.append("[MISSING] alembic/")

# 3. Check seed script
seed = os.path.join(root, 'scripts', 'seed.py')
if os.path.exists(seed):
    issues.append("[OK] scripts/seed.py")
else:
    issues.append("[MISSING] scripts/seed.py")

# 4. Check docker files
for f in ['docker-compose.yml', 'Dockerfile']:
    p = os.path.join(root, f)
    if os.path.exists(p):
        issues.append(f"[OK] {f}")
    else:
        issues.append(f"[MISSING] {f}")

# 5. Check README
readme = os.path.join(root, 'README.md')
if os.path.exists(readme):
    with open(readme) as f:
        content = f.read()
    issues.append(f"[OK] README.md ({len(content)} chars)")
else:
    issues.append("[MISSING] README.md")

# 6. Check all module files
modules_dir = os.path.join(root, 'app', 'modules')
expected_module_files = {
    'products': ['__init__.py', 'models.py', 'schemas.py', 'service.py', 'router.py'],
    'inventory': ['__init__.py', 'models.py', 'schemas.py', 'service.py', 'router.py'],
    'sales': ['__init__.py', 'models.py', 'schemas.py', 'service.py', 'router.py'],
    'auth': ['__init__.py', 'models.py', 'schemas.py', 'service.py', 'router.py'],
    'approvals': ['__init__.py', 'models.py', 'schemas.py', 'service.py', 'router.py'],
    'tasks': ['__init__.py', 'models.py', 'schemas.py', 'service.py', 'router.py'],
    'dashboard': ['__init__.py', 'schemas.py', 'service.py', 'router.py'],
    'operational_analysis': ['__init__.py', 'models.py', 'schemas.py', 'service.py', 'router.py'],
    'ai_engine': ['__init__.py', '__init___service.py', 'exceptions.py', 'fallback_service.py', 'json_parser.py', 'mock_provider.py', 'prompts.py', 'provider_base.py', 'router.py', 'schemas.py', 'service.py'],
}

for module, files in expected_module_files.items():
    mod_dir = os.path.join(modules_dir, module)
    if not os.path.isdir(mod_dir):
        issues.append(f"[MISSING] app/modules/{module}/")
        continue
    for f in files:
        fp = os.path.join(mod_dir, f)
        if not os.path.exists(fp):
            issues.append(f"[MISSING] app/modules/{module}/{f}")

# 7. Check core files
core_dir = os.path.join(root, 'app', 'core')
for f in ['__init__.py', 'config.py', 'database.py', 'error_handlers.py', 'exceptions.py', 'middleware.py', 'pagination.py', 'auth.py', 'security.py']:
    fp = os.path.join(core_dir, f)
    if os.path.exists(fp):
        issues.append(f"[OK] app/core/{f}")
    else:
        issues.append(f"[MISSING] app/core/{f}")

# 8. Check tests
tests_dir = os.path.join(root, 'tests')
if os.path.isdir(tests_dir):
    tests = [f for f in os.listdir(tests_dir) if f.endswith('.py') and f != '__init__.py']
    issues.append(f"[OK] tests/ ({len(tests)} test files)")
else:
    issues.append("[MISSING] tests/")

# 9. Check frontend files
frontend_dir = os.path.join(root, 'StorePilot AI')
if os.path.isdir(frontend_dir):
    for f in ['index.html', 'js/api.js', 'js/app.js', 'js/components.js', 'js/utils.js']:
        fp = os.path.join(frontend_dir, f)
        if os.path.exists(fp):
            issues.append(f"[OK] StorePilot AI/{f}")
        else:
            issues.append(f"[MISSING] StorePilot AI/{f}")
    # Check pages
    pages_dir = os.path.join(frontend_dir, 'pages')
    if os.path.isdir(pages_dir):
        for p in ['dashboard.html', 'analysis.html', 'findings.html', 'approvals.html', 'tasks.html', 'inventory.html', 'sales.html']:
            if os.path.exists(os.path.join(pages_dir, p)):
                issues.append(f"[OK] StorePilot AI/pages/{p}")
            else:
                issues.append(f"[MISSING] StorePilot AI/pages/{p}")
else:
    issues.append("[MISSING] StorePilot AI/")

# 10. Check .env.example
if os.path.exists(os.path.join(root, '.env.example')):
    issues.append("[OK] .env.example")
else:
    issues.append("[MISSING] .env.example")

# 11. Check .gitignore
if os.path.exists(os.path.join(root, '.gitignore')):
    issues.append("[OK] .gitignore")
else:
    issues.append("[MISSING] .gitignore")

# Print summary
print("=" * 60)
print("STOREPILOT AI — COMPLETENESS CHECK")
print("=" * 60)

ok = [i for i in issues if i.startswith("[OK]")]
missing = [i for i in issues if i.startswith("[MISSING]")]

print(f"\n✅ OK: {len(ok)} item")
print(f"❌ MISSING: {len(missing)} item\n")

if missing:
    print("--- ISSUES ---")
    for m in missing:
        print(f"  ❌ {m}")
    print()
else:
    print("✅ Semua file lengkap!\n")

print("--- FULL INFO ---")
for i in sorted(issues):
    print(f"  {i}")

# GitHub Actions Workflow - Consolidated Pipeline

## Single Unified Workflow

We've consolidated all CI/CD processes into a single workflow file: `.github/workflows/main.yml`

### What This Solves
- ✅ **No more duplicate pipeline runs** (CI #1, CI #2, Klerno Labs CI #10, etc.)
- ✅ **Single source of truth** for all validation
- ✅ **Faster, more efficient pipelines**
- ✅ **Smart conditional execution** based on changed files

### Pipeline Features

#### **Smart Triggers**
- Runs on pushes to `main`
- Runs on pull requests to `main`
- Can be manually triggered via `workflow_dispatch`

#### **Conditional Validation**
- **Code validation**: Only runs when app files change
- **Documentation validation**: Only runs when markdown files change
- **Universal validation**: Always runs dependency installation and basic checks

#### **Error Handling**
- Linting warnings don't fail the build
- Test failures are reported but don't block
- Security issues are flagged but allow continuation
- Import validation ensures basic app functionality

### Expected Results
- **50-70% reduction** in total pipeline runs
- **Single workflow name** in GitHub Actions UI
- **Clear, consolidated reporting** in one place
- **Faster feedback loops** for developers

### Pipeline Steps
1. **Setup**: Python 3.11 + dependency installation with caching
2. **Dev Dependencies**: Install linting and testing tools
3. **Code Validation**: Ruff linting, pytest testing (with coverage), bandit security scan, import validation, build script validation
4. **Documentation Validation**: Basic markdown file validation
5. **Artifact Upload**: Test results, coverage reports, and security scan results
6. **Summary**: Detailed completion status with run metadata

### Enhanced Features
- **Dependency Caching**: Faster subsequent runs with pip cache
- **Test Coverage Reports**: XML coverage output for analysis
- **Security Scan Artifacts**: JSON reports for security review
- **Build Script Integration**: Validates build.py functionality
- **Comprehensive Logging**: Detailed run information and metadata
- **Artifact Retention**: 30-day retention for test results and reports

# Klerno Labs Final - Unified CI/CD Pipeline

This repository now has a **single consolidated workflow** that replaces all previous duplicate pipelines.

## Overview

The new workflow is named **"Klerno Labs Final"** and will show as a single, unified entry in your GitHub Actions.

## GitHub Actions Badge

Add this badge to your main README.md to show the pipeline status:

```markdown
[![Klerno Labs Final](https://github.com/auricrypt-ux/custowell-copilot/actions/workflows/main.yml/badge.svg)](https://github.com/auricrypt-ux/custowell-copilot/actions/workflows/main.yml)
```

## Manual Trigger

You can manually trigger the pipeline from the GitHub Actions UI using the "Run workflow" button, or via the GitHub CLI:

```bash
gh workflow run main.yml
```

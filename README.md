# Klerno Labs - Clean Application

This is the **clean, consolidated version** of the Klerno Labs Enterprise Transaction Analysis Platform. This version contains only the essential core functionality without the duplicate files found in the main project.

## ✨ What's Different

- **Single Authentication System**: Consolidated from 5 conflicting auth files to 1 clean auth.py
- **Unified Landing Page**: One cohesive design instead of multiple conflicting templates
- **Streamlined Codebase**: Essential functionality only, no duplicates
- **Clean Architecture**: FastAPI + SQLite + Bootstrap for simplicity

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Application**:
   ```bash
   python start_clean.py
   ```

3. **Access the Application**:
   - **Landing Page**: [http://localhost:8000](http://localhost:8000)
   - **Login**: [http://localhost:8000/auth/login](http://localhost:8000/auth/login)
   - **Admin Dashboard**: [http://localhost:8000/admin](http://localhost:8000/admin) (after login as admin)

## Development

Dev / test notes
---------------

For local testing we use a Python 3.11 virtual environment to keep
dependency wheels compatible with the project's pinned packages. A
recommended workflow on Windows PowerShell:

```powershell
python -m venv .venv-py311
. .\.venv-py311\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

The `requirements.txt` is runtime-only. Test and developer-only packages
are listed in `dev-requirements.txt`. To install just the test helpers
locally run:

```powershell
python -m pip install -r dev-requirements.txt
```

### Migration note

`app/legacy_helpers.py` is retained as a small compatibility shim for
older tests that import `create_access_token`/`verify_token` from
builtins. Teams should migrate tests and code to import the functions
directly from `app.auth` or `app.security_session` and then the shim can
be removed. For local installs of only the test helpers use:

```powershell
python -m pip install -r dev-requirements.txt
```

### CI status

![CI - tests](https://github.com/auricrypt-ux/custowell-copilot/actions/workflows/pytest.yml/badge.svg)

## 👤 First Time Setup

1. Visit [http://localhost:8000/auth/signup](http://localhost:8000/auth/signup)
2. Create your account (first user becomes admin automatically)
3. Login and access the admin dashboard

## 📁 Project Structure

```
CLEAN_APP/
├── app/
│   ├── __init__.py          # Package init
│   ├── main.py             # FastAPI application
│   ├── auth.py             # Authentication system
│   ├── admin.py            # Admin panel
│   ├── models.py           # Data models
│   ├── store.py            # Database operations
│   └── settings.py         # Configuration
├── templates/
│   ├── base.html           # Base template
│   ├── landing.html        # Landing page
│   ├── login.html          # Login form
│   ├── signup.html         # Signup form
│   ├── admin.html          # Admin dashboard
│   └── dashboard.html      # User dashboard
├── static/                 # Static files (CSS, JS, images)
├── data/                   # SQLite database (auto-created)
├── requirements.txt        # Python dependencies
├── start_clean.py         # Startup script
└── README.md              # This file
```

## 🔧 Key Features

- **Authentication**: Secure login/signup with bcrypt password hashing
- **Admin Panel**: User management and system administration
- **Responsive Design**: Bootstrap-based responsive UI
- **Database**: SQLite for simplicity (easily upgradeable to PostgreSQL)
- **API**: RESTful FastAPI backend

## 🛡️ Security Features

- **Password Hashing**: bcrypt for secure password storage
- **Session Management**: FastAPI session middleware
- **Role-Based Access**: Admin/User role separation
- **Input Validation**: Pydantic models for API validation

## 🔄 Migration from Original Project

This clean version was created by:
1. Identifying and removing 254 duplicate files from the original 256-file project
2. Consolidating conflicting authentication systems
3. Creating a unified landing page design
4. Streamlining the database schema
5. Removing unnecessary complexity

## 📈 Next Steps

From this clean foundation, you can:

- Add blockchain analysis features
- Implement transaction monitoring
- Add more sophisticated user management
- Integrate with external APIs
- Add real-time dashboard features

## 🆘 Support

This clean application provides the same core functionality as the original project but with:

- 99% fewer files
- No conflicting systems
- Clear architecture
- Easy maintenance

The original project structure remains available for reference in the parent directory.

## Run locally (Windows PowerShell)

If you want to start the app locally and quickly verify the login flow (dev-only admin credentials are created automatically on first run), follow these steps in PowerShell:

```powershell
# Create and activate a Python 3.11 venv (one-time)
python -m venv .venv-py311
. .\.venv-py311\Scripts\Activate.ps1

# Install runtime deps (use dev-requirements for test helpers if needed)
python -m pip install -r requirements.txt

# Start the server in the background (keeps this shell free)
Start-Process -FilePath ".\.venv-py311\Scripts\python.exe" -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--log-level','info' -NoNewWindow

# Run a small smoke-test (optional)
. .\.venv-py311\Scripts\python.exe scripts\smoke_test.py
```

Default dev admin credentials (local development only):

- email: `klerno@outlook.com`
- password: `Labs2025`

Troubleshooting:

- If the server exits immediately, inspect the terminal that started uvicorn for startup logs. Common causes: missing python packages, or a locked port; install requirements and retry.
- If templates fail to render, ensure the working directory is the project root so the `templates/` folder is on the app path.

"""
Render deployment test endpoint
This module provides test endpoints to verify Render deployment fixes
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
import os
import sys
import platform
import json
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Mock data models
class MockTransaction(BaseModel):
    id: str
    timestamp: datetime
    amount: float
    sender: str
    receiver: str
    status: str
    currency: str
    description: Optional[str] = None
    
class MockReport(BaseModel):
    report_id: str
    generated_at: datetime
    transactions: List[MockTransaction]
    total_amount: float
    currency: str

# Create router
router = APIRouter(
    prefix="/render-test",
    tags=["render-test"],
    responses={404: {"description": "Not found"}},
)

# Get base directory 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Generate mock data
def get_mock_transactions() -> List[MockTransaction]:
    """Generate some mock transaction data for testing"""
    return [
        MockTransaction(
            id=f"tx-{i}",
            timestamp=datetime.now(),
            amount=100.0 * i,
            sender=f"sender-{i}@example.com",
            receiver=f"receiver-{i}@example.com",
            status="completed",
            currency="USD",
            description=f"Test transaction {i}"
        )
        for i in range(1, 6)
    ]

def get_mock_report() -> MockReport:
    """Generate a mock report with transactions for testing"""
    transactions = get_mock_transactions()
    total_amount = sum(tx.amount for tx in transactions)
    
    return MockReport(
        report_id="report-render-test",
        generated_at=datetime.now(),
        transactions=transactions,
        total_amount=total_amount,
        currency="USD"
    )

# Routes
@router.get("/", response_class=HTMLResponse)
async def render_test_home(request: Request):
    """Render test home page using the template system"""
    context = {
        "request": request,
        "title": "Render Deployment Test",
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": platform.python_version(),
        "system_info": {
            "platform": platform.platform(),
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "cwd": os.getcwd(),
        }
    }
    return templates.TemplateResponse("render_test.html", context)

@router.get("/api/transactions")
async def get_transactions():
    """API endpoint returning mock transactions data"""
    transactions = get_mock_transactions()
    return [tx.dict() for tx in transactions]

@router.get("/api/report")
async def get_report():
    """API endpoint returning a mock report"""
    report = get_mock_report()
    return report.dict()

@router.get("/api/environment")
async def get_environment():
    """Return environment information for diagnostics"""
    env_info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "cwd": os.getcwd(),
        "env_vars": {k: v for k, v in os.environ.items() if not k.lower().startswith(('secret', 'password', 'key', 'token'))},
        "static_files_path": os.path.join(BASE_DIR, "static"),
        "static_files_exist": os.path.isdir(os.path.join(BASE_DIR, "static")),
        "static_files_content": [f for f in os.listdir(os.path.join(BASE_DIR, "static"))] if os.path.isdir(os.path.join(BASE_DIR, "static")) else [],
        "templates_path": os.path.join(BASE_DIR, "templates"),
        "templates_exist": os.path.isdir(os.path.join(BASE_DIR, "templates")),
        "render_test_template_exists": os.path.isfile(os.path.join(BASE_DIR, "templates", "render_test.html")),
    }
    return env_info

@router.get("/error")
async def test_error_handling():
    """Intentionally raise an error to test error handling"""
    raise HTTPException(status_code=500, detail="Test error for Render deployment")

@router.get("/csp-test")
async def test_csp():
    """Return a simple page that loads resources to test CSP"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CSP Test</title>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script>
            console.log("Inline script executed successfully");
            
            // Test fetch to our own API
            fetch('/render-test/api/transactions')
                .then(response => response.json())
                .then(data => {
                    console.log("API data loaded:", data);
                    document.getElementById('api-data').textContent = JSON.stringify(data, null, 2);
                })
                .catch(err => {
                    console.error("API fetch error:", err);
                    document.getElementById('api-data').textContent = "Error: " + err.message;
                });
        </script>
    </head>
    <body>
        <div class="container mt-5">
            <h1>CSP Test Page</h1>
            <p>This page tests if Content Security Policy allows loading various resources.</p>
            
            <h2>External CSS Test</h2>
            <p class="text-primary">This text should be blue if Bootstrap CSS loaded successfully.</p>
            
            <h2>External JavaScript Test</h2>
            <button class="btn btn-primary" onclick="alert('Button click works!')">Click Me</button>
            
            <h2>API Data Test</h2>
            <pre id="api-data">Loading...</pre>
            
            <h2>Image Test</h2>
            <img src="/static/klerno-logo.png" alt="Klerno Logo" style="max-width: 200px;">
            
            <h2>Direct Image URL Test (Fallback)</h2>
            <img src="../../static/klerno-logo.png" alt="Klerno Logo Direct Path" style="max-width: 200px;">
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
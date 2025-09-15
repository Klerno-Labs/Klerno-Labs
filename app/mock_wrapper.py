"""
Mock wrapper for Klerno Labs - provides fallback functionality when dependencies are missing
"""
import os
import sys
import argparse
import importlib.util
import logging
import shutil
import platform
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mock-wrapper")

def create_mock_module():
    """Create a mock XRPL module if it doesn't exist"""
    mock_dir = Path(__file__).parent / "mocks"
    mock_dir.mkdir(exist_ok=True)
    
    init_path = mock_dir / "__init__.py"
    if not init_path.exists():
        init_path.write_text("")
    
    mock_path = mock_dir / "xrpl_mock.py"
    if not mock_path.exists():
        mock_content = '''
# Mock implementation of XRPL functionality
import random
from datetime import datetime

class XRPLError(Exception):
    """Base exception for XRPL errors"""
    pass

def create_payment_request(amount, recipient, sender=None, memo=None):
    """Create a mock payment request"""
    request_id = f"req_{random.randint(100000, 999999)}"
    return {
        "request_id": request_id,
        "amount": amount,
        "recipient": recipient,
        "sender": sender,
        "memo": memo,
        "timestamp": str(datetime.now()),
        "expiration": str(datetime.now().timestamp() + 3600),
        "status": "pending",
        "network": "testnet",
        "mock": True
    }

def verify_payment(request_id):
    """Verify a mock payment"""
    # Always return success for mock payments
    return {
        "request_id": request_id,
        "verified": True,
        "amount_received": random.uniform(0.1, 100.0),
        "timestamp": str(datetime.now()),
        "transaction_hash": f"mock_tx_{random.randint(100000, 999999)}",
        "mock": True
    }

def get_network_info():
    """Get mock network info"""
    return {
        "network": "testnet",
        "status": "online",
        "fee": random.uniform(0.00001, 0.0001),
        "last_ledger": random.randint(10000000, 99999999),
        "validators_online": random.randint(20, 30),
        "mock": True
    }
'''
        mock_path.write_text(mock_content)
    
    return str(mock_dir)

def patch_sys_path(mock_dir):
    """Add mock directory to sys.path"""
    if mock_dir not in sys.path:
        sys.path.insert(0, mock_dir)
        logger.info(f"Added mock directory to sys.path: {mock_dir}")

def start_app(port=8000):
    """Start the application with mocks in place"""
    mock_dir = create_mock_module()
    patch_sys_path(mock_dir)
    
    logger.info("Starting application with mock modules available")
    
    # Import and run uvicorn
    try:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
    except ImportError:
        logger.error("uvicorn not installed. Installing...")
        os.system(f"{sys.executable} -m pip install uvicorn")
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

def main():
    parser = argparse.ArgumentParser(description="Klerno Labs Mock Wrapper")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()
    
    logger.info(f"Mock wrapper starting (Python {platform.python_version()})")
    start_app(port=args.port)

if __name__ == "__main__":
    main()
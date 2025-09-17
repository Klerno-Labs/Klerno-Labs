"""
Mock wrapper for Klerno Labs - provides fallback functionality when dependencies are missing
"""
import os
import sys
import argparse
import logging
import platform
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mock-wrapper")

def create_mock_module() -> str:
    """Ensure mock XRPL module exists and is importable."""
    mock_dir = Path(__file__).parent / "mocks"
    mock_dir.mkdir(exist_ok=True)

    init_path = mock_dir / "__init__.py"
    if not init_path.exists():
        init_path.write_text("")

    # The canonical mock implementation is in app/mocks/xrpl_mock.py
    # This function just ensures the directory structure exists for imports
    return str(mock_dir)

def patch_sys_path(mock_dir: str) -> None:
    """Add mock directory to sys.path if missing."""
    if mock_dir not in sys.path:
        sys.path.insert(0, mock_dir)
        logger.info(f"Added mock directory to sys.path: {mock_dir}")

def start_app(port: int = 8000) -> None:
    """Start the application with mocks in place."""
    mock_dir = create_mock_module()
    patch_sys_path(mock_dir)

    logger.info("Starting application with mock modules available")

    try:
        import uvicorn  # type: ignore
    except ImportError:
        logger.error("uvicorn not installed. Installing...")
        os.system(f"{sys.executable} -m pip install uvicorn")
        import uvicorn  # type: ignore

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

def main() -> None:
    parser = argparse.ArgumentParser(description="Klerno Labs Mock Wrapper")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()

    logger.info(f"Mock wrapper starting (Python {platform.python_version()})")
    start_app(port=args.port)

if __name__ == "__main__":
    main()
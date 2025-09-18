#!/usr/bin/env python3
"""
Klerno Labs - Production Deployment Script (Windows Compatible)
For 0.01% quality applications - Zero tolerance for failures
"""

import os
import sys
import time
import argparse
import logging
import subprocess
import signal
from pathlib import Path
from datetime import datetime

# Configure logging without emojis for Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('deployment.log')
    ]
)
logger = logging.getLogger(__name__)

class ProductionDeployment:
    """Enterprise-grade deployment manager with zero-downtime capabilities."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.deployment_id = f"deploy_{int(time.time())}"
        self.process = None
        
    def validate_environment(self) -> bool:
        """Validate all required environment variables and dependencies."""
        logger.info("[VALIDATE] Checking production environment...")
        
        required_vars = [
            'JWT_SECRET',
            'SECRET_KEY', 
            'ADMIN_EMAIL',
            'ADMIN_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"[ERROR] Missing required environment variables: {missing_vars}")
            logger.error("Please set these variables before deployment:")
            for var in missing_vars:
                logger.error(f"  $env:{var}=\"your_value_here\"")
            return False
            
        # Validate JWT secret length
        jwt_secret = os.getenv('JWT_SECRET', '')
        if len(jwt_secret) < 32:
            logger.error("[ERROR] JWT_SECRET must be at least 32 characters long")
            return False
            
        logger.info("[OK] Environment validation passed")
        return True
    
    def validate_application(self) -> bool:
        """Validate application can import and initialize properly."""
        logger.info("[VALIDATE] Testing application imports...")
        
        try:
            # Test basic imports
            from app.main import app
            logger.info("[OK] Application imports successfully")
            
            # Count routes
            route_count = len([r for r in app.routes if hasattr(r, 'path')])
            logger.info(f"[OK] Application has {route_count} routes configured")
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Application validation failed: {e}")
            return False
    
    def setup_directories(self) -> bool:
        """Ensure all required directories exist."""
        logger.info("[SETUP] Creating directories...")
        
        directories = [
            'data',
            'logs', 
            'temp',
            'backups'
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True, parents=True)
            logger.info(f"[OK] Directory created/verified: {directory}")
            
        return True
    
    def create_health_monitor(self, host: str, port: int) -> None:
        """Create health monitoring script."""
        monitor_script = f'''
import requests
import time
import sys

def check_health():
    try:
        response = requests.get('http://{host}:{port}/healthz', timeout=5)
        if response.status_code == 200:
            print(f"[OK] Health check passed: {{response.status_code}}")
            return True
        else:
            print(f"[ERROR] Health check failed: {{response.status_code}}")
            return False
    except Exception as e:
        print(f"[ERROR] Health check error: {{e}}")
        return False

if __name__ == "__main__":
    for i in range(10):
        if check_health():
            sys.exit(0)
        time.sleep(2)
    sys.exit(1)
'''
        
        with open('health_monitor.py', 'w') as f:
            f.write(monitor_script)
    
    def start_application(self, host: str, port: int, workers: int = 1) -> bool:
        """Start the application with production settings."""
        logger.info(f"[START] Starting Klerno Labs on {host}:{port} with {workers} workers...")
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update({
                'APP_ENV': 'production',
                'HOST': host,
                'PORT': str(port),
                'WORKERS': str(workers)
            })
            
            # Start uvicorn with production settings
            cmd = [
                sys.executable, '-m', 'uvicorn',
                'app.main:app',
                '--host', host,
                '--port', str(port),
                '--workers', str(workers),
                '--access-log',
                '--log-level', 'info'
            ]
            
            logger.info(f"[EXEC] {' '.join(cmd)}")
            
            # Start process
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Give the server time to start
            logger.info("[WAIT] Waiting for server to initialize...")
            time.sleep(5)
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to start application: {e}")
            return False
    
    def run_health_checks(self, host: str, port: int) -> bool:
        """Run comprehensive health checks."""
        logger.info("[HEALTH] Running health checks...")
        
        # Create and run health monitor
        self.create_health_monitor(host, port)
        
        try:
            result = subprocess.run([
                sys.executable, 'health_monitor.py'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("[OK] All health checks passed")
                return True
            else:
                logger.error(f"[ERROR] Health checks failed: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("[ERROR] Health checks timed out")
            return False
        except Exception as e:
            logger.error(f"[ERROR] Health check error: {e}")
            return False
    
    def monitor_application(self) -> None:
        """Monitor application output and health."""
        logger.info("[MONITOR] Monitoring application...")
        
        if not self.process:
            logger.error("[ERROR] No process to monitor")
            return
            
        try:
            while self.process.poll() is None:
                output = self.process.stdout.readline()
                if output:
                    print(output.strip())
                time.sleep(0.1)
                    
        except KeyboardInterrupt:
            logger.info("[STOP] Received shutdown signal")
            self.shutdown()
    
    def shutdown(self) -> None:
        """Gracefully shutdown the application."""
        logger.info("[STOP] Shutting down application...")
        
        if self.process:
            try:
                # Send SIGTERM first
                self.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                    logger.info("[OK] Application shut down gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if necessary
                    logger.warning("[WARN] Forcing application shutdown")
                    self.process.kill()
                    self.process.wait()
                    
            except Exception as e:
                logger.error(f"[ERROR] Error during shutdown: {e}")
        
        # Cleanup
        if os.path.exists('health_monitor.py'):
            os.remove('health_monitor.py')
            
        elapsed = datetime.now() - self.start_time
        logger.info(f"[STATS] Total deployment time: {elapsed.total_seconds():.2f} seconds")

def main():
    """Main deployment entry point."""
    parser = argparse.ArgumentParser(description='Klerno Labs Production Deployment')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--workers', type=int, default=1, help='Number of worker processes')
    parser.add_argument('--validate-only', action='store_true', help='Only run validation')
    parser.add_argument('--health-check-only', action='store_true', help='Only run health checks')
    
    args = parser.parse_args()
    
    deployment = ProductionDeployment()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        deployment.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("[START] Klerno Labs Enterprise Deployment Starting...")
        logger.info(f"[INFO] Deployment ID: {deployment.deployment_id}")
        
        # Validation phase
        if not deployment.validate_environment():
            sys.exit(1)
            
        if not deployment.setup_directories():
            sys.exit(1)
            
        if not deployment.validate_application():
            sys.exit(1)
            
        if args.validate_only:
            logger.info("[OK] Validation complete - application ready for deployment")
            sys.exit(0)
        
        # Health check only mode
        if args.health_check_only:
            if deployment.run_health_checks(args.host, args.port):
                sys.exit(0)
            else:
                sys.exit(1)
        
        # Full deployment
        if not deployment.start_application(args.host, args.port, args.workers):
            sys.exit(1)
            
        if not deployment.run_health_checks(args.host, args.port):
            logger.error("[ERROR] Health checks failed - aborting deployment")
            deployment.shutdown()
            sys.exit(1)
            
        logger.info("[SUCCESS] Deployment successful - application is running!")
        logger.info(f"[URL] Application available at: http://{args.host}:{args.port}")
        logger.info("[MONITOR] Monitoring application (Ctrl+C to stop)...")
        
        # Monitor until shutdown
        deployment.monitor_application()
        
    except Exception as e:
        logger.error(f"[FATAL] Deployment failed: {e}")
        deployment.shutdown()
        sys.exit(1)

if __name__ == '__main__':
    main()
"""
Klerno Labs - Test Runner with Server Management
Starts the server and runs tests, then provides results.
"""

import subprocess
import time
import requests
import json
import os
import signal
from datetime import datetime

class TestRunner:
    def __init__(self):
        self.server_process = None
        self.base_url = "http://localhost:8000"
        
    def start_server(self):
        """Start the server process."""
        print("🚀 Starting Klerno Labs Server...")
        try:
            # Start the server
            self.server_process = subprocess.Popen(
                ["python", "zero_warning_startup.py"],
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # Wait for server to start
            print("⏳ Waiting for server to initialize...")
            for i in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get(f"{self.base_url}/healthz", timeout=2)
                    if response.status_code == 200:
                        print("✅ Server is ready!")
                        return True
                except:
                    time.sleep(1)
                    if i % 5 == 0:
                        print(f"   Still waiting... ({i}/30 seconds)")
            
            print("❌ Server failed to start in 30 seconds")
            return False
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def run_tests(self):
        """Run comprehensive tests."""
        print("\n🧪 Running Comprehensive Tests...")
        
        # Core endpoints to test
        test_cases = [
            {"name": "Health Check", "url": "/healthz", "expected": [200]},
            {"name": "API Health", "url": "/health", "expected": [200]},
            {"name": "Landing Page", "url": "/", "expected": [200]},
            {"name": "Login Page", "url": "/login", "expected": [200]},
            {"name": "Signup Page", "url": "/signup", "expected": [200]},
            {"name": "API Documentation", "url": "/docs", "expected": [200]},
            {"name": "OpenAPI Spec", "url": "/openapi.json", "expected": [200]},
            {"name": "API Status", "url": "/api/status", "expected": [200, 401]},
            {"name": "Static Logo", "url": "/static/klerno-logo.png", "expected": [200]},
            {"name": "Favicon", "url": "/static/favicon.ico", "expected": [200]},
            {"name": "Robots.txt", "url": "/robots.txt", "expected": [200]},
            {"name": "Enterprise Health", "url": "/enterprise/health", "expected": [200, 401, 403]},
            {"name": "Admin Dashboard", "url": "/admin/dashboard", "expected": [200, 401, 403]},
        ]
        
        results = []
        passed = 0
        
        for test in test_cases:
            try:
                response = requests.get(f"{self.base_url}{test['url']}", timeout=5)
                success = response.status_code in test["expected"]
                status = "PASS" if success else "FAIL"
                
                print(f"  {status} {test['name']}: {response.status_code}")
                
                results.append({
                    "name": test["name"],
                    "url": test["url"],
                    "status_code": response.status_code,
                    "success": success,
                    "response_size": len(response.content)
                })
                
                if success:
                    passed += 1
                    
            except Exception as e:
                print(f"  FAIL {test['name']}: ERROR - {str(e)[:50]}")
                results.append({
                    "name": test["name"],
                    "url": test["url"],
                    "status_code": "ERROR",
                    "success": False,
                    "error": str(e)
                })
        
        # Print summary
        total = len(test_cases)
        print(f"\n📊 Test Results:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {total - passed}")
        print(f"   📈 Success Rate: {(passed/total)*100:.1f}%")
        
        # Save results
        with open("test_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "success_rate": (passed/total)*100
                },
                "results": results
            }, f, indent=2)
        
        return passed >= total * 0.8  # 80% success rate
    
    def stop_server(self):
        """Stop the server process."""
        if self.server_process:
            print("\n🛑 Stopping server...")
            try:
                if os.name == 'nt':  # Windows
                    self.server_process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    self.server_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
                    
                print("✅ Server stopped")
            except Exception as e:
                print(f"⚠️ Error stopping server: {e}")
    
    def run_full_test_suite(self):
        """Run the complete test suite."""
        print("=" * 60)
        print("🧪 KLERNO LABS COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        print(f"⏰ Started at: {datetime.now().isoformat()}")
        
        try:
            # Start server
            if not self.start_server():
                return False
            
            # Run tests
            success = self.run_tests()
            
            # Show final result
            print("\n" + "=" * 60)
            if success:
                print("🎉 ALL TESTS PASSED! Klerno Labs is working perfectly!")
            else:
                print("⚠️ Some tests failed. Check results above.")
            print("=" * 60)
            
            return success
            
        finally:
            # Always stop server
            self.stop_server()

def main():
    """Main function."""
    runner = TestRunner()
    success = runner.run_full_test_suite()
    
    if success:
        print("\n✅ Test suite completed successfully!")
        exit(0)
    else:
        print("\n❌ Test suite completed with failures!")
        exit(1)

if __name__ == "__main__":
    main()
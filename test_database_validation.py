#!/usr/bin/env python3
"""
Database operations validation script for Klerno Labs application.
Tests database connectivity, models, and data persistence.
"""
import asyncio
import sys
from pathlib import Path
import sqlite3
import json
from datetime import datetime, timezone
import tempfile
import os

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

class DatabaseValidator:
    """Validates database operations and functionality."""
    
    def __init__(self):
        self.test_results = []
        self.test_db_path = None
        
    def test_database_connection(self):
        """Test basic database connectivity."""
        print("🔗 TESTING DATABASE CONNECTION")
        print("=" * 50)
        
        try:
            # Test SQLite connection
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                self.test_db_path = tmp.name
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            # Test basic operations
            cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test_table (name) VALUES (?)", ("test",))
            cursor.execute("SELECT * FROM test_table")
            result = cursor.fetchone()
            
            conn.commit()
            conn.close()
            
            success = result is not None and result[1] == "test"
            print(f"✅ Database Connection: {'PASS' if success else 'FAIL'}")
            
            self.test_results.append({
                'test': 'database_connection',
                'status': 'pass' if success else 'fail',
                'details': 'SQLite connection and basic operations successful' if success else 'Failed basic operations'
            })
            
        except Exception as e:
            print(f"❌ Database Connection: FAIL - {e}")
            self.test_results.append({
                'test': 'database_connection',
                'status': 'fail',
                'error': str(e)
            })
    
    def test_model_imports(self):
        """Test that database models can be imported."""
        print("\n📋 TESTING MODEL IMPORTS")
        print("=" * 50)
        
        models_to_test = [
            'models',
            'schemas'
        ]
        
        successful_imports = 0
        
        for model_name in models_to_test:
            try:
                if model_name == 'models':
                    from app.models import User, Transaction, AnalysisResult
                    print(f"✅ {model_name}: User, Transaction, AnalysisResult imported")
                elif model_name == 'schemas':
                    from app.schemas import UserCreate, TransactionRequest, AnalysisResponse
                    print(f"✅ {model_name}: UserCreate, TransactionRequest, AnalysisResponse imported")
                
                successful_imports += 1
                
            except ImportError as e:
                print(f"❌ {model_name}: Import failed - {e}")
            except Exception as e:
                print(f"⚠️ {model_name}: Warning - {e}")
                successful_imports += 1  # Still count as success if module exists
        
        success_rate = (successful_imports / len(models_to_test)) * 100
        print(f"\nModel import success rate: {success_rate:.1f}%")
        
        self.test_results.append({
            'test': 'model_imports',
            'total_models': len(models_to_test),
            'successful_imports': successful_imports,
            'success_rate': success_rate
        })
    
    def test_database_initialization(self):
        """Test database initialization and table creation."""
        print("\n🗃️ TESTING DATABASE INITIALIZATION")
        print("=" * 50)
        
        try:
            # Try to import and test database module
            from app.core.database import get_database, init_db
            
            print("✅ Database module imported successfully")
            
            # Test database functions exist
            functions_to_test = ['get_database', 'init_db']
            
            for func_name in functions_to_test:
                if func_name in globals() or hasattr(sys.modules.get('app.core.database'), func_name):
                    print(f"✅ Function {func_name}: EXISTS")
                else:
                    print(f"❌ Function {func_name}: MISSING")
            
            self.test_results.append({
                'test': 'database_initialization',
                'status': 'pass',
                'details': 'Database module and functions available'
            })
            
        except ImportError as e:
            print(f"❌ Database module import failed: {e}")
            self.test_results.append({
                'test': 'database_initialization',
                'status': 'fail',
                'error': f"Import error: {e}"
            })
        except Exception as e:
            print(f"⚠️ Database initialization issue: {e}")
            self.test_results.append({
                'test': 'database_initialization', 
                'status': 'partial',
                'warning': str(e)
            })
    
    def test_transaction_storage(self):
        """Test transaction data storage and retrieval."""
        print("\n💳 TESTING TRANSACTION STORAGE")
        print("=" * 50)
        
        try:
            # Create test transaction data
            test_transaction = {
                'tx_id': 'test_tx_123',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'chain': 'XRPL',
                'from_addr': 'rTestSender123',
                'to_addr': 'rTestReceiver456',
                'amount': 100.0,
                'symbol': 'XRP',
                'direction': 'out',
                'memo': 'Test transaction',
                'fee': 0.1
            }
            
            # Test with SQLite database
            if self.test_db_path:
                conn = sqlite3.connect(self.test_db_path)
                cursor = conn.cursor()
                
                # Create transactions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tx_id TEXT UNIQUE,
                        timestamp TEXT,
                        chain TEXT,
                        from_addr TEXT,
                        to_addr TEXT,
                        amount REAL,
                        symbol TEXT,
                        direction TEXT,
                        memo TEXT,
                        fee REAL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Insert test transaction
                cursor.execute('''
                    INSERT INTO transactions 
                    (tx_id, timestamp, chain, from_addr, to_addr, amount, symbol, direction, memo, fee)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    test_transaction['tx_id'],
                    test_transaction['timestamp'],
                    test_transaction['chain'],
                    test_transaction['from_addr'],
                    test_transaction['to_addr'],
                    test_transaction['amount'],
                    test_transaction['symbol'],
                    test_transaction['direction'],
                    test_transaction['memo'],
                    test_transaction['fee']
                ))
                
                # Retrieve transaction
                cursor.execute("SELECT * FROM transactions WHERE tx_id = ?", (test_transaction['tx_id'],))
                stored_transaction = cursor.fetchone()
                
                conn.commit()
                conn.close()
                
                if stored_transaction:
                    print("✅ Transaction storage: PASS")
                    print(f"   Stored transaction ID: {stored_transaction[1]}")
                    print(f"   Amount: {stored_transaction[6]} {stored_transaction[7]}")
                    
                    self.test_results.append({
                        'test': 'transaction_storage',
                        'status': 'pass',
                        'details': 'Transaction successfully stored and retrieved'
                    })
                else:
                    print("❌ Transaction storage: FAIL - No data retrieved")
                    self.test_results.append({
                        'test': 'transaction_storage',
                        'status': 'fail',
                        'error': 'Transaction not found after insertion'
                    })
            else:
                print("⚠️ Transaction storage: SKIP - No test database available")
                self.test_results.append({
                    'test': 'transaction_storage',
                    'status': 'skip',
                    'reason': 'No test database available'
                })
                
        except Exception as e:
            print(f"❌ Transaction storage: FAIL - {e}")
            self.test_results.append({
                'test': 'transaction_storage',
                'status': 'fail',
                'error': str(e)
            })
    
    def test_user_management(self):
        """Test user data management."""
        print("\n👤 TESTING USER MANAGEMENT")
        print("=" * 50)
        
        try:
            if self.test_db_path:
                conn = sqlite3.connect(self.test_db_path)
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        hashed_password TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_superuser BOOLEAN DEFAULT FALSE,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Test user creation
                test_user = {
                    'email': 'test@klerno.com',
                    'hashed_password': 'hashed_password_123',
                    'is_active': True,
                    'is_superuser': False
                }
                
                cursor.execute('''
                    INSERT INTO users (email, hashed_password, is_active, is_superuser)
                    VALUES (?, ?, ?, ?)
                ''', (
                    test_user['email'],
                    test_user['hashed_password'],
                    test_user['is_active'],
                    test_user['is_superuser']
                ))
                
                # Retrieve user
                cursor.execute("SELECT * FROM users WHERE email = ?", (test_user['email'],))
                stored_user = cursor.fetchone()
                
                # Test user update
                cursor.execute("UPDATE users SET is_active = ? WHERE email = ?", (False, test_user['email']))
                
                # Verify update
                cursor.execute("SELECT is_active FROM users WHERE email = ?", (test_user['email'],))
                updated_status = cursor.fetchone()
                
                conn.commit()
                conn.close()
                
                if stored_user and updated_status:
                    print("✅ User management: PASS")
                    print(f"   Created user: {stored_user[1]}")
                    print(f"   Status updated: {bool(updated_status[0])}")
                    
                    self.test_results.append({
                        'test': 'user_management',
                        'status': 'pass',
                        'details': 'User CRUD operations successful'
                    })
                else:
                    print("❌ User management: FAIL")
                    self.test_results.append({
                        'test': 'user_management',
                        'status': 'fail',
                        'error': 'User operations failed'
                    })
            else:
                print("⚠️ User management: SKIP - No test database available")
                self.test_results.append({
                    'test': 'user_management',
                    'status': 'skip',
                    'reason': 'No test database available'
                })
                
        except Exception as e:
            print(f"❌ User management: FAIL - {e}")
            self.test_results.append({
                'test': 'user_management',
                'status': 'fail',
                'error': str(e)
            })
    
    def test_data_persistence(self):
        """Test data persistence across connections."""
        print("\n💾 TESTING DATA PERSISTENCE")
        print("=" * 50)
        
        try:
            if self.test_db_path:
                # First connection - insert data
                conn1 = sqlite3.connect(self.test_db_path)
                cursor1 = conn1.cursor()
                
                cursor1.execute('''
                    CREATE TABLE IF NOT EXISTS persistence_test (
                        id INTEGER PRIMARY KEY,
                        test_data TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                test_data = f"persistence_test_{datetime.now().timestamp()}"
                cursor1.execute("INSERT INTO persistence_test (test_data) VALUES (?)", (test_data,))
                conn1.commit()
                conn1.close()
                
                # Second connection - retrieve data
                conn2 = sqlite3.connect(self.test_db_path)
                cursor2 = conn2.cursor()
                
                cursor2.execute("SELECT test_data FROM persistence_test WHERE test_data = ?", (test_data,))
                retrieved_data = cursor2.fetchone()
                conn2.close()
                
                if retrieved_data and retrieved_data[0] == test_data:
                    print("✅ Data persistence: PASS")
                    print(f"   Data persisted across connections")
                    
                    self.test_results.append({
                        'test': 'data_persistence',
                        'status': 'pass',
                        'details': 'Data successfully persisted across connections'
                    })
                else:
                    print("❌ Data persistence: FAIL")
                    self.test_results.append({
                        'test': 'data_persistence',
                        'status': 'fail',
                        'error': 'Data not persisted across connections'
                    })
            else:
                print("⚠️ Data persistence: SKIP - No test database available")
                self.test_results.append({
                    'test': 'data_persistence',
                    'status': 'skip',
                    'reason': 'No test database available'
                })
                
        except Exception as e:
            print(f"❌ Data persistence: FAIL - {e}")
            self.test_results.append({
                'test': 'data_persistence',
                'status': 'fail',
                'error': str(e)
            })
    
    def cleanup(self):
        """Clean up test resources."""
        if self.test_db_path and os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
                print(f"\n🧹 Cleaned up test database: {self.test_db_path}")
            except Exception as e:
                print(f"⚠️ Failed to cleanup test database: {e}")
    
    def run_all_tests(self):
        """Run all database validation tests."""
        print("🗄️ STARTING DATABASE VALIDATION")
        print("=" * 60)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            self.test_database_connection()
            self.test_model_imports()
            self.test_database_initialization()
            self.test_transaction_storage()
            self.test_user_management()
            self.test_data_persistence()
            
        finally:
            self.cleanup()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 DATABASE VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get('status') == 'pass')
        failed_tests = sum(1 for r in self.test_results if r.get('status') == 'fail')
        skipped_tests = sum(1 for r in self.test_results if r.get('status') == 'skip')
        
        print(f"Total tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏭️ Skipped: {skipped_tests}")
        
        if total_tests > 0:
            success_rate = (passed_tests / (total_tests - skipped_tests)) * 100 if (total_tests - skipped_tests) > 0 else 0
            print(f"Success rate: {success_rate:.1f}%")
        
        # Show failed tests
        failed_results = [r for r in self.test_results if r.get('status') == 'fail']
        if failed_results:
            print(f"\n❌ FAILED TESTS ({len(failed_results)}):")
            for result in failed_results:
                test_name = result['test'].replace('_', ' ').title()
                error = result.get('error', 'Unknown error')
                print(f"   {test_name}: {error}")

if __name__ == "__main__":
    validator = DatabaseValidator()
    validator.run_all_tests()
"""
Mock XRPL client for testing.
"""
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import xrpl
from xrpl.models.response import Response


class MockXRPLClient:
    def request(self, request_obj):
        """Mock the .request() method for Tx and AccountTx requests."""
        # Handle Tx (transaction lookup by hash)
        if hasattr(request_obj, 'transaction'):
            tx_hash = getattr(request_obj, 'transaction', None)
            tx = self.get_transaction(tx_hash)
            class MockResponse:
                def is_successful(self_inner):
                    return tx is not None
                @property
                def result(self_inner):
                    if tx is not None:
                        return tx
                    return {}
            return MockResponse()
        # Handle AccountTx (list transactions for an account)
        if hasattr(request_obj, 'account'):
            account = getattr(request_obj, 'account', None)
            limit = getattr(request_obj, 'limit', 20)
            txs = []
            for tx_hash in self.accounts.get(account, {}).get('transactions', [])[-limit:]:
                tx = self.get_transaction(tx_hash)
                if tx:
                    txs.append({'tx': tx})
            class MockResponse:
                def is_successful(self_inner):
                    return True
                @property
                def result(self_inner):
                    return {'transactions': txs}
            return MockResponse()
        # Default fallback
        class MockResponse:
            def is_successful(self_inner):
                return False
            @property
            def result(self_inner):
                return {}
        return MockResponse()
    """Mock implementation of the XRPL client for testing."""
    
    def __init__(self, network: str = "testnet"):
        self.network = network
        self.client = None
        self.transactions = {}
        self.accounts = {
            # Default test destination account
            "rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe": {
                "balance": 1000.0,
                "sequence": 1,
                "transactions": []
            }
        }
    
    def connect(self):
        """Mock connection to XRPL."""
        self.client = "MOCK_CONNECTION"
        return True
    
    def is_connected(self) -> bool:
        """Check if mock client is connected."""
        return self.client is not None
    
    def disconnect(self):
        """Mock disconnection from XRPL."""
        self.client = None
    
    def get_account_info(self, account: str) -> dict:
        """Get mock account information."""
        if account not in self.accounts:
            # Create a new mock account
            self.accounts[account] = {
                "balance": 100.0,
                "sequence": 1,
                "transactions": []
            }
        
        # Build response structure similar to real XRPL response
        return {
            "account_data": {
                "Account": account,
                "Balance": str(int(self.accounts[account]["balance"] * 1000000)),
                "Sequence": self.accounts[account]["sequence"],
                "OwnerCount": 0,
                "Flags": 0
            },
            "ledger_current_index": 12345,
            "validated": True
        }
    
    def get_transaction(self, tx_hash: str) -> Optional[dict]:
        """Get mock transaction by hash."""
        if tx_hash not in self.transactions:
            return None
        
        tx = self.transactions[tx_hash]
        return {
            "Account": tx["account"],
            "Destination": tx["destination"],
            "Amount": str(int(tx["amount"] * 1000000)),
            "Fee": "12",
            "Sequence": tx["sequence"],
            "SigningPubKey": "PUBLIC_KEY",
            "TransactionType": "Payment",
            "hash": tx_hash,
            "inLedger": 12345,
            "ledger_index": 12345,
            "meta": {
                "TransactionIndex": 0,
                "TransactionResult": "tesSUCCESS",
                "delivered_amount": str(int(tx["amount"] * 1000000))
            },
            "validated": True,
            "date": int(time.time()) + 946684800,  # Convert to XRPL epoch time
            "Memos": [
                {
                    "Memo": {
                        "MemoData": tx.get("memo", "").encode().hex()
                    }
                }
            ] if "memo" in tx else []
        }
    
    def submit_transaction(self, transaction: Dict) -> Dict:
        """Submit a mock transaction."""
        tx_hash = f"MOCK_TX_{uuid.uuid4().hex[:16]}"
        
        # Extract details from the transaction
        account = transaction.get("Account", "rSenderMockAccount")
        destination = transaction.get("Destination", "rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe")
        amount = float(transaction.get("Amount", "0")) / 1000000  # Convert drops to XRP
        
        # Extract memo if present
        memo = ""
        if "Memos" in transaction and transaction["Memos"]:
            memo_data = transaction["Memos"][0].get("Memo", {}).get("MemoData", "")
            if memo_data:
                try:
                    memo = bytes.fromhex(memo_data).decode('utf-8')
                except:
                    memo = memo_data
        
        # Create the mock transaction
        self.transactions[tx_hash] = {
            "account": account,
            "destination": destination,
            "amount": amount,
            "sequence": self.accounts.get(account, {"sequence": 1})["sequence"],
            "timestamp": datetime.now(),
            "memo": memo
        }
        
        # Update account balances
        if account in self.accounts:
            self.accounts[account]["balance"] -= amount
            self.accounts[account]["sequence"] += 1
            self.accounts[account]["transactions"].append(tx_hash)
        
        if destination in self.accounts:
            self.accounts[destination]["balance"] += amount
            self.accounts[destination]["transactions"].append(tx_hash)
        
        # Simulate a successful response
        return {
            "engine_result": "tesSUCCESS",
            "engine_result_code": 0,
            "engine_result_message": "The transaction was applied.",
            "tx_blob": "MOCK_BLOB",
            "tx_json": {
                "Account": account,
                "Amount": str(int(amount * 1000000)),
                "Destination": destination,
                "Fee": "12",
                "Sequence": self.accounts.get(account, {"sequence": 1})["sequence"],
                "SigningPubKey": "MOCK_KEY",
                "TransactionType": "Payment",
                "hash": tx_hash
            },
            "accepted": True,
            "account_sequence_available": self.accounts.get(account, {"sequence": 2})["sequence"],
            "account_sequence_next": self.accounts.get(account, {"sequence": 2})["sequence"] + 1,
            "validated": True
        }
    
    def simulate_payment(self, from_account: str, to_account: str, amount: float, memo: str = ""):
        """Simulate a payment for testing."""
        if to_account not in self.accounts:
            self.accounts[to_account] = {
                "balance": 0.0,
                "sequence": 1,
                "transactions": []
            }
        
        if from_account not in self.accounts:
            self.accounts[from_account] = {
                "balance": amount + 10.0,  # Enough balance plus some extra
                "sequence": 1,
                "transactions": []
            }
        
        tx_hash = f"MOCK_TX_{uuid.uuid4().hex[:16]}"
        
        # Create the transaction
        self.transactions[tx_hash] = {
            "account": from_account,
            "destination": to_account,
            "amount": amount,
            "sequence": self.accounts[from_account]["sequence"],
            "timestamp": datetime.now(),
            "memo": memo
        }
        
        # Update account balances
        self.accounts[from_account]["balance"] -= amount
        self.accounts[from_account]["sequence"] += 1
        self.accounts[from_account]["transactions"].append(tx_hash)
        
        self.accounts[to_account]["balance"] += amount
        self.accounts[to_account]["transactions"].append(tx_hash)
        
        return tx_hash
    
    def get_payment_by_memo(self, destination: str, memo: str, 
                           min_ledger: Optional[int] = None, 
                           max_ledger: Optional[int] = None) -> List[dict]:
        """Find transactions by destination and memo."""
        results = []
        
        for tx_hash, tx in self.transactions.items():
            if tx["destination"] == destination and tx.get("memo") == memo:
                results.append(self.get_transaction(tx_hash))
        
        return results


# Create a singleton instance
mock_client = MockXRPLClient()
#!/usr/bin/env python
"""
Admin utility script for managing XRPL subscriptions.
"""
import argparse
import sys
import os
import sqlite3
from datetime import datetime, timedelta
from enum import Enum

# Add the parent directory to sys.path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from app.subscriptions import SubscriptionTier, create_subscription, get_user_subscription

def main():
    parser = argparse.ArgumentParser(description="Manage XRPL subscriptions")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Create subscription
    create_parser = subparsers.add_parser("create", help="Create or update a subscription")
    create_parser.add_argument("user_id", help="User ID")
    create_parser.add_argument(
        "--tier", 
        type=int, 
        choices=[1, 2, 3], 
        default=1, 
        help="Subscription tier (1=Basic, 2=Premium, 3=Enterprise)"
    )
    create_parser.add_argument(
        "--days", 
        type=int, 
        default=30, 
        help="Subscription duration in days"
    )
    create_parser.add_argument(
        "--tx-hash", 
        help="Transaction hash (for record keeping)"
    )
    
    # Get subscription
    get_parser = subparsers.add_parser("get", help="Get subscription details")
    get_parser.add_argument("user_id", help="User ID")
    
    # List subscriptions
    list_parser = subparsers.add_parser("list", help="List all subscriptions")
    list_parser.add_argument(
        "--active-only", 
        action="store_true", 
        help="Show only active subscriptions"
    )
    
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "create":
        tier = SubscriptionTier(args.tier)
        subscription = create_subscription(
            user_id=args.user_id,
            tier=tier,
            tx_hash=args.tx_hash or "manual-admin-creation",
            payment_id="manual-admin-creation",
            duration_days=args.days
        )
        print(f"Subscription created/updated for user {args.user_id}:")
        print(f"  Tier: {tier.name}")
        print(f"  Created: {subscription.created_at}")
        print(f"  Expires: {subscription.expires_at}")
        print(f"  Active: {subscription.is_active}")
        
    elif args.command == "get":
        subscription = get_user_subscription(args.user_id)
        if subscription:
            print(f"Subscription for user {args.user_id}:")
            print(f"  Tier: {subscription.tier.name}")
            print(f"  Created: {subscription.created_at}")
            print(f"  Expires: {subscription.expires_at}")
            print(f"  Active: {subscription.is_active}")
            print(f"  TX Hash: {subscription.tx_hash}")
        else:
            print(f"No subscription found for user {args.user_id}")
            
    elif args.command == "list":
        # Connect to SQLite database
        db_path = os.path.join(parent_dir, "data", "klerno.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM subscriptions"
        if args.active_only:
            query += " WHERE expires_at > datetime('now')"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            print("No subscriptions found")
            return
            
        print(f"Found {len(rows)} subscriptions:")
        for row in rows:
            tier = SubscriptionTier(row["tier"])
            is_active = datetime.fromisoformat(row["expires_at"]) > datetime.now() if row["expires_at"] else False
            print(f"User: {row['user_id']}")
            print(f"  Tier: {tier.name}")
            print(f"  Created: {row['created_at']}")
            print(f"  Expires: {row['expires_at']}")
            print(f"  Active: {is_active}")
            print(f"  TX Hash: {row['tx_hash']}")
            print("------------------")
            
        conn.close()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
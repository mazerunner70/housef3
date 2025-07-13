#!/usr/bin/env python3
import os
import sys
import boto3
from datetime import datetime, date
from decimal import Decimal
import json

# Set up DynamoDB client
dynamodb = boto3.resource('dynamodb')
transactions_table = dynamodb.Table(os.environ['TRANSACTIONS_TABLE'])

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError

def scan_transactions():
    """Scan transactions table and analyze amounts"""
    try:
        response = transactions_table.scan()
        transactions = response['Items']
        
        # Analyze transactions
        total_count = len(transactions)
        positive_amounts = [t for t in transactions if Decimal(t.get('amount', 0)) > 0]
        negative_amounts = [t for t in transactions if Decimal(t.get('amount', 0)) < 0]
        
        print(f"\nTransaction Analysis:")
        print(f"Total transactions: {total_count}")
        print(f"Positive amounts (income): {len(positive_amounts)}")
        print(f"Negative amounts (expenses): {len(negative_amounts)}")
        
        if positive_amounts:
            print("\nSample positive transactions:")
            for t in positive_amounts[:3]:
                print(json.dumps(t, indent=2, default=decimal_default))
                
        if negative_amounts:
            print("\nSample negative transactions:")
            for t in negative_amounts[:3]:
                print(json.dumps(t, indent=2, default=decimal_default))
                
    except Exception as e:
        print(f"Error scanning transactions: {e}")
        sys.exit(1)

if __name__ == "__main__":
    scan_transactions() 
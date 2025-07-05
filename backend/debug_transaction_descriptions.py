#!/usr/bin/env python3
"""
Debug script to analyze transaction descriptions and find potential Sainsburys matches.
This helps understand why the SAINSBURYS pattern didn't match any transactions.
"""

import os
import sys
import logging
from typing import List, Dict

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.db_utils import list_user_transactions

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_transaction_descriptions(user_id: str, search_term: str = 'SAINSBURY') -> None:
    """
    Analyze transaction descriptions to find potential matches for a search term.
    
    Args:
        user_id: The user ID to search transactions for
        search_term: The term to search for (default: SAINSBURY)
    """
    print(f"\n=== Analyzing Transaction Descriptions for User: {user_id} ===")
    print(f"Search term: '{search_term}' (case-insensitive)")
    
    try:
        # Get all uncategorized transactions
        print("\nFetching uncategorized transactions...")
        transactions, _, _ = list_user_transactions(user_id, uncategorized_only=True)
        
        if not transactions:
            print("❌ No uncategorized transactions found!")
            return
        
        print(f"✅ Found {len(transactions)} uncategorized transactions")
        
        # Analyze descriptions
        exact_matches = []
        partial_matches = []
        similar_matches = []
        empty_descriptions = []
        
        # Sample some descriptions for manual inspection
        sample_descriptions = []
        
        search_term_upper = search_term.upper()
        
        for i, tx in enumerate(transactions):
            desc = getattr(tx, 'description', '') or ''
            
            if not desc.strip():
                empty_descriptions.append(tx)
                continue
            
            # Collect sample for manual inspection
            if len(sample_descriptions) < 20:
                sample_descriptions.append({
                    'index': i,
                    'description': desc,
                    'amount': str(tx.amount),
                    'date': tx.date
                })
            
            desc_upper = desc.upper()
            
            # Check for exact match
            if search_term_upper in desc_upper:
                exact_matches.append({
                    'description': desc,
                    'amount': str(tx.amount),
                    'transaction_id': str(tx.transaction_id)
                })
            
            # Check for partial matches (removing common variations)
            elif any(variant in desc_upper for variant in [
                search_term_upper[:-1],  # Remove last character
                search_term_upper[:-2],  # Remove last 2 characters
                search_term_upper.replace('S', ''),  # Remove S
                search_term_upper.replace('Y', 'IE'),  # Y -> IE variation
                'SAINSBURY',  # Without S
                'SAINSBURYS',  # Full name
                'TESCO',  # Common alternative
                'ASDA',  # Common alternative
                'MORRISONS'  # Common alternative
            ]):
                partial_matches.append({
                    'description': desc,
                    'amount': str(tx.amount),
                    'transaction_id': str(tx.transaction_id)
                })
            
            # Check for similar grocery store patterns
            elif any(grocery in desc_upper for grocery in [
                'SUPERMARKET', 'GROCERY', 'FOOD', 'STORE', 'MARKET',
                'SHOP', 'RETAIL', 'PURCHASE'
            ]):
                similar_matches.append({
                    'description': desc,
                    'amount': str(tx.amount),
                    'transaction_id': str(tx.transaction_id)
                })
        
        # Print results
        print(f"\n=== Analysis Results ===")
        print(f"Total transactions analyzed: {len(transactions)}")
        print(f"Empty descriptions: {len(empty_descriptions)}")
        print(f"Exact matches for '{search_term}': {len(exact_matches)}")
        print(f"Partial matches: {len(partial_matches)}")
        print(f"Similar grocery-related: {len(similar_matches)}")
        
        # Show exact matches
        if exact_matches:
            print(f"\n✅ EXACT MATCHES FOUND ({len(exact_matches)}):")
            for match in exact_matches[:10]:  # Show first 10
                print(f"  - '{match['description']}' (${match['amount']})")
        else:
            print(f"\n❌ No exact matches found for '{search_term}'")
        
        # Show partial matches
        if partial_matches:
            print(f"\n🔍 PARTIAL MATCHES ({len(partial_matches)}):")
            for match in partial_matches[:10]:  # Show first 10
                print(f"  - '{match['description']}' (${match['amount']})")
        
        # Show similar matches
        if similar_matches:
            print(f"\n🛒 GROCERY-RELATED MATCHES ({len(similar_matches)}):")
            for match in similar_matches[:10]:  # Show first 10
                print(f"  - '{match['description']}' (${match['amount']})")
        
        # Show sample descriptions for manual inspection
        print(f"\n📋 SAMPLE DESCRIPTIONS (first 20):")
        for sample in sample_descriptions:
            print(f"  {sample['index']+1:3}: '{sample['description']}' (${sample['amount']})")
        
        # Suggestions
        print(f"\n💡 SUGGESTIONS:")
        if exact_matches:
            print(f"  ✅ Found exact matches! The rule should have worked.")
            print(f"  🔍 Check backend logs for why these weren't applied.")
        elif partial_matches:
            print(f"  🔄 Try these alternative patterns:")
            for match in partial_matches[:5]:
                words = match['description'].upper().split()
                if words:
                    print(f"    - Pattern: '{words[0]}' for '{match['description']}'")
        else:
            print(f"  ❓ No grocery-related transactions found.")
            print(f"  📝 Consider checking if transactions are from different time periods.")
            print(f"  🔍 Review sample descriptions above for actual merchant names.")
    
    except Exception as e:
        print(f"❌ Error analyzing transactions: {str(e)}")
        logger.error(f"Error in analyze_transaction_descriptions: {str(e)}")

def main():
    """Main function to run the analysis"""
    if len(sys.argv) < 2:
        print("Usage: python debug_transaction_descriptions.py <user_id> [search_term]")
        print("Example: python debug_transaction_descriptions.py 2602f254-70f1-7064-c637-fd69dbe4e8b3")
        sys.exit(1)
    
    user_id = sys.argv[1]
    search_term = sys.argv[2] if len(sys.argv) > 2 else 'SAINSBURY'
    
    analyze_transaction_descriptions(user_id, search_term)

if __name__ == '__main__':
    main() 
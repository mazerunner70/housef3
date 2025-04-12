import unittest
import os
from datetime import datetime
from src.utils.transaction_parser import (
    parse_transactions,
    parse_csv_transactions,
    parse_ofx_transactions,
    parse_date,
    find_column_index
)
from src.models.transaction_file import FileFormat

class TestTransactionParser(unittest.TestCase):
    def setUp(self):
        # Set up test data directory
        self.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        
    def read_test_file(self, filename):
        """Helper to read test data files."""
        with open(os.path.join(self.test_data_dir, filename), 'rb') as f:
            return f.read()

    def test_find_column_index(self):
        header = ['Transaction Date', 'Description', 'Amount', 'Category']
        self.assertEqual(find_column_index(header, ['date', 'transaction date']), 0)
        self.assertEqual(find_column_index(header, ['desc', 'description']), 1)
        self.assertEqual(find_column_index(header, ['amount']), 2)
        self.assertIsNone(find_column_index(header, ['balance']))

    def test_parse_date(self):
        # Test various date formats
        test_cases = [
            ('2024-03-15', '2024-03-15'),
            ('03/15/2024', '2024-03-15'),
            ('15/03/2024', '2024-03-15'),
            ('20240315', '2024-03-15'),
            ('03-15-2024', '2024-03-15'),
            ('invalid date', None)
        ]
        
        for input_date, expected in test_cases:
            self.assertEqual(parse_date(input_date), expected)

    def test_parse_csv_from_file(self):
        content = self.read_test_file('sample_transactions.csv')
        transactions = parse_csv_transactions(content, 100.0)
        
        self.assertEqual(len(transactions), 6)
        
        # Check first transaction
        self.assertEqual(transactions[0]['date'], '2024-03-15')
        self.assertEqual(transactions[0]['description'], 'Grocery Store')
        self.assertEqual(transactions[0]['amount'], -50.25)
        self.assertEqual(transactions[0]['running_total'], 49.75)
        self.assertEqual(transactions[0]['transaction_type'], 'DEBIT')
        self.assertEqual(transactions[0]['category'], 'Food')
        self.assertEqual(transactions[0]['memo'], 'Weekly groceries')
        
        # Check running total calculation
        expected_total = 100.0  # Opening balance
        for t in transactions:
            expected_total += t['amount']
            self.assertEqual(t['running_total'], expected_total)

    def test_parse_ofx_from_file(self):
        content = self.read_test_file('sample_transactions.ofx')
        transactions = parse_ofx_transactions(content, 100.0)
        
        self.assertEqual(len(transactions), 4)
        
        # Check first transaction
        self.assertEqual(transactions[0]['date'], '2024-03-15')
        self.assertEqual(transactions[0]['description'], 'Grocery Store')
        self.assertEqual(transactions[0]['amount'], -50.25)
        self.assertEqual(transactions[0]['running_total'], 49.75)
        self.assertEqual(transactions[0]['transaction_type'], 'DEBIT')
        self.assertEqual(transactions[0]['memo'], 'Weekly groceries')
        
        # Check running total calculation
        expected_total = 100.0  # Opening balance
        for t in transactions:
            expected_total += t['amount']
            self.assertEqual(t['running_total'], expected_total)

    def test_parse_qfx_from_file(self):
        content = self.read_test_file('sample_transactions.qfx')
        transactions = parse_ofx_transactions(content, 100.0)
        
        self.assertEqual(len(transactions), 4)
        
        # Check first transaction
        self.assertEqual(transactions[0]['date'], '2024-03-15')
        self.assertEqual(transactions[0]['description'], 'Grocery Store')
        self.assertEqual(transactions[0]['amount'], -50.25)
        self.assertEqual(transactions[0]['running_total'], 49.75)
        self.assertEqual(transactions[0]['transaction_type'], 'DEBIT')
        self.assertEqual(transactions[0]['memo'], 'Weekly groceries')
        
        # Check running total calculation
        expected_total = 100.0  # Opening balance
        for t in transactions:
            expected_total += t['amount']
            self.assertEqual(t['running_total'], expected_total)

    def test_parse_csv_invalid_format(self):
        csv_content = '''Invalid,Header,Format
bad,data,here'''.encode('utf-8')
        
        transactions = parse_csv_transactions(csv_content, 100.0)
        self.assertEqual(transactions, [])

    def test_parse_transactions_dispatcher(self):
        # Test CSV format
        content = self.read_test_file('sample_transactions.csv')
        transactions = parse_transactions(content, FileFormat.CSV, 100.0)
        self.assertEqual(len(transactions), 6)
        
        # Test OFX format
        content = self.read_test_file('sample_transactions.ofx')
        transactions = parse_transactions(content, FileFormat.OFX, 100.0)
        self.assertEqual(len(transactions), 4)
        
        # Test QFX format
        content = self.read_test_file('sample_transactions.qfx')
        transactions = parse_transactions(content, FileFormat.QFX, 100.0)
        self.assertEqual(len(transactions), 4)
        
        # Test unsupported format
        transactions = parse_transactions(b'', 'UNSUPPORTED', 100.0)
        self.assertEqual(transactions, []) 
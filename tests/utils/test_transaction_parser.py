import datetime
import unittest
from decimal import Decimal
from utils.transaction_parser import (
    parse_date,
    parse_csv_transactions,
    parse_ofx_transactions,
    apply_field_mapping
)
from models.field_map import FieldMap, FieldMapping
from models.transaction_file import FileFormat

class TestTransactionParser(unittest.TestCase):
    def test_parse_date(self):
        """Test date parsing with various formats."""
        test_cases = [
            ('2024-03-15', 1710460800000),
            ('03/15/2024', 1710460800000),
            ('15/03/2024', 1710460800000),
            ('20240315', 1710460800000),
            ('03-15-2024', 1710460800000),
            ('invalid date', None)
        ]
        for input_date, expected in test_cases:
            with self.subTest(input_date=input_date):
                self.assertEqual(parse_date(input_date), expected)

    def test_parse_csv_from_file(self):
        """Test parsing CSV transactions from file."""
        content = self.read_test_file('sample_transactions.csv')
        transactions = parse_csv_transactions(content, 100.0)
        self.assertEqual(len(transactions), 6)
        # Check first transaction
        self.assertEqual(transactions[0]['date'], 1710460800000)
        self.assertEqual(transactions[0]['description'], 'Grocery Store')
        self.assertEqual(transactions[0]['amount'], '-50.25')
        self.assertEqual(transactions[0]['balance'], '49.75')
        self.assertEqual(transactions[0]['transaction_type'], 'DEBIT')
        self.assertEqual(transactions[0]['category'], 'Food')
        self.assertEqual(transactions[0]['memo'], 'Weekly groceries')
        # Check running total calculation
        expected_total = Decimal('100.0')  # Opening balance
        for t in transactions:
            expected_total += Decimal(t['amount'])
            self.assertEqual(t['balance'], str(expected_total))

    def test_parse_csv_with_field_map(self):
        """Test parsing CSV transactions with field mapping."""
        transactions = parse_csv_transactions(self.csv_content, 1000.0, self.field_map)
        self.assertEqual(len(transactions), 3)
        # Check first transaction
        first_tx = transactions[0]
        self.assertEqual(first_tx["date"], 1704067200000)
        self.assertEqual(first_tx["description"], "Grocery Store")
        self.assertEqual(first_tx["amount"], str(Decimal("123.45")))
        self.assertEqual(first_tx["balance"], str(Decimal("1123.45")))

    def test_parse_ofx_from_file(self):
        """Test parsing OFX transactions from file."""
        content = self.read_test_file('sample_transactions.ofx')
        transactions = parse_ofx_transactions(content, 100.0)
        self.assertEqual(len(transactions), 4)
        # Check first transaction
        self.assertEqual(transactions[0]['date'], 1710460800000)
        self.assertEqual(transactions[0]['description'], 'Grocery Store')
        self.assertEqual(transactions[0]['amount'], '-50.25')
        self.assertEqual(transactions[0]['balance'], '49.75')
        self.assertEqual(transactions[0]['transaction_type'], 'DEBIT')
        self.assertEqual(transactions[0]['memo'], 'Weekly groceries')
        # Check running total calculation
        expected_total = Decimal('100.0')  # Opening balance
        for t in transactions:
            expected_total += Decimal(t['amount'])
            self.assertEqual(t['balance'], str(expected_total))

    def test_parse_qfx_from_file(self):
        """Test parsing QFX transactions from file."""
        content = self.read_test_file('sample_transactions.qfx')
        transactions = parse_ofx_transactions(content, 100.0)
        self.assertEqual(len(transactions), 4)
        # Check first transaction
        self.assertEqual(transactions[0]['date'], 1710460800000)
        self.assertEqual(transactions[0]['description'], 'Grocery Store')
        self.assertEqual(transactions[0]['amount'], '-50.25')
        self.assertEqual(transactions[0]['balance'], '49.75')
        self.assertEqual(transactions[0]['transaction_type'], 'DEBIT')
        self.assertEqual(transactions[0]['memo'], 'Weekly groceries')
        # Check running total calculation
        expected_total = Decimal('100.0')  # Opening balance
        for t in transactions:
            expected_total += Decimal(t['amount'])
            self.assertEqual(t['balance'], str(expected_total))

    def test_parse_ofx_inline(self):
        """Test parsing OFX transactions from inline content."""
        transactions = parse_ofx_transactions(self.ofx_content, 1000.0)
        self.assertEqual(len(transactions), 2)
        # Check first transaction
        first_tx = transactions[0]
        self.assertEqual(first_tx["date"], 1704067200000)
        self.assertEqual(first_tx["description"], "Grocery Store")
        self.assertEqual(first_tx["amount"], str(Decimal("-123.45")))
        self.assertEqual(first_tx["balance"], str(Decimal("876.55")))  # 1000 - 123.45
        self.assertEqual(first_tx.get("memo"), "Purchase at Store")
        self.assertEqual(first_tx.get("transaction_type"), "DEBIT") 
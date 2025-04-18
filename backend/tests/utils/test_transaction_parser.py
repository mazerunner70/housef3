import os
import unittest
from decimal import Decimal
from datetime import datetime
from models.transaction_file import FileFormat
from models.field_map import FieldMap, FieldMapping
from utils.transaction_parser import (
    parse_transactions,
    parse_csv_transactions,
    parse_ofx_transactions,
    apply_field_mapping,
    find_column_index,
    parse_date
)

class TestTransactionParser(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        # Set up test data directory
        self.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        
        # Sample field map for testing
        self.field_map = FieldMap(
            field_map_id="test-map-1",
            name="Test Bank Statement",
            description="Test mapping for bank statements",
            user_id="test-user",
            mappings=[
                FieldMapping(source_field="Date", target_field="date"),
                FieldMapping(source_field="Description", target_field="description"),
                FieldMapping(source_field="Amount", target_field="amount", transformation="float(value.replace('$', '').replace(',', ''))")
            ]
        )
        
        # Sample CSV content for inline tests
        self.csv_content = b"""Date,Description,Amount,Balance
2024-01-01,Grocery Store,$123.45,"$1,000.00"
2024-01-02,Gas Station,$45.67,"$954.33"
2024-01-03,Restaurant,$67.89,"$886.44"
"""

        # Sample OFX content for inline tests
        self.ofx_content = b"""OFXHEADER:100
DATA:OFXSGML
<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20240101</DTPOSTED>
<TRNAMT>-123.45</TRNAMT>
<n>Grocery Store</n>
<MEMO>Purchase at Store</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20240102</DTPOSTED>
<TRNAMT>-45.67</TRNAMT>
<n>Gas Station</n>
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

    def read_test_file(self, filename):
        """Helper to read test data files."""
        with open(os.path.join(self.test_data_dir, filename), 'rb') as f:
            return f.read()

    def test_find_column_index(self):
        """Test finding column indices with various header formats."""
        header = ['Transaction Date', 'Description', 'Amount', 'Category']
        
        test_cases = [
            (["date", "transaction date"], 0),  # Exact match with case insensitive
            (["desc", "description"], 1),       # Exact match
            (["amount"], 2),                    # Simple match
            (["balance"], None),                # No match
            (["category"], 3),                  # Direct match
        ]
        
        for possible_names, expected_index in test_cases:
            with self.subTest(possible_names=possible_names):
                result = find_column_index(header, possible_names)
                self.assertEqual(result, expected_index)

    def test_parse_date(self):
        """Test date parsing with various formats."""
        test_cases = [
            ('2024-03-15', '2024-03-15'),
            ('03/15/2024', '2024-03-15'),
            ('15/03/2024', '2024-03-15'),
            ('20240315', '2024-03-15'),
            ('03-15-2024', '2024-03-15'),
            ('invalid date', None)
        ]
        
        for input_date, expected in test_cases:
            with self.subTest(input_date=input_date):
                self.assertEqual(parse_date(input_date), expected)

    def test_apply_field_mapping(self):
        """Test applying field mappings to row data."""
        row_data = {
            "Date": "2024-01-01",
            "Description": "Test Transaction",
            "Amount": "$123.45",
            "Extra": "Additional Info"
        }
        
        result = apply_field_mapping(row_data, self.field_map)
        
        self.assertEqual(result["date"], "2024-01-01")
        self.assertEqual(result["description"], "Test Transaction")
        self.assertEqual(result["amount"], 123.45)
        self.assertNotIn("Extra", result)

    def test_parse_csv_from_file(self):
        """Test parsing CSV transactions from file."""
        content = self.read_test_file('sample_transactions.csv')
        transactions = parse_csv_transactions(content, 100.0)
        
        self.assertEqual(len(transactions), 6)
        
        # Check first transaction
        self.assertEqual(transactions[0]['date'], '2024-03-15')
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
        self.assertEqual(first_tx["date"], "2024-01-01")
        self.assertEqual(first_tx["description"], "Grocery Store")
        self.assertEqual(first_tx["amount"], str(Decimal("123.45")))
        self.assertEqual(first_tx["balance"], str(Decimal("1123.45")))

    def test_parse_ofx_from_file(self):
        """Test parsing OFX transactions from file."""
        content = self.read_test_file('sample_transactions.ofx')
        transactions = parse_ofx_transactions(content, 100.0)
        
        self.assertEqual(len(transactions), 4)
        
        # Check first transaction
        self.assertEqual(transactions[0]['date'], '2024-03-15')
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
        self.assertEqual(transactions[0]['date'], '2024-03-15')
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
        self.assertEqual(first_tx["date"], "2024-01-01")
        self.assertEqual(first_tx["description"], "Grocery Store")
        self.assertEqual(first_tx["amount"], str(Decimal("-123.45")))
        self.assertEqual(first_tx["balance"], str(Decimal("876.55")))  # 1000 - 123.45
        self.assertEqual(first_tx.get("memo"), "Purchase at Store")
        self.assertEqual(first_tx.get("transaction_type"), "DEBIT")

    def test_parse_transactions_dispatcher(self):
        """Test the main parse_transactions dispatcher function."""
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

    def test_invalid_csv_content(self):
        """Test handling of invalid CSV content."""
        csv_content = '''Invalid,Header,Format
bad,data,here'''.encode('utf-8')
        
        transactions = parse_csv_transactions(csv_content, 100.0)
        self.assertEqual(transactions, [])

    def test_invalid_ofx_content(self):
        """Test handling of invalid OFX content."""
        invalid_ofx = b"invalid OFX content"
        transactions = parse_ofx_transactions(invalid_ofx, 1000.0)
        self.assertEqual(transactions, [])

    def test_field_mapping_with_missing_fields(self):
        """Test field mapping when source fields are missing."""
        row_data = {
            "Date": "2024-01-01",
            # Missing Description field
            "Amount": "$123.45"
        }
        
        result = apply_field_mapping(row_data, self.field_map)
        self.assertNotIn("description", result)

    def test_field_mapping_with_invalid_transformation(self):
        """Test field mapping with invalid transformation."""
        field_map_with_bad_transform = FieldMap(
            field_map_id="test-map-2",
            name="Bad Transform",
            description="Map with invalid transformation",
            user_id="test-user",
            mappings=[
                FieldMapping(
                    source_field="Amount",
                    target_field="amount",
                    transformation="invalid_function(value)"
                )
            ]
        )
        
        row_data = {"Amount": "$123.45"}
        result = apply_field_mapping(row_data, field_map_with_bad_transform)
        self.assertNotIn("amount", result) 
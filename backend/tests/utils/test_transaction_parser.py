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
    parse_date,
    detect_date_order,
    preprocess_csv_text
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
        expected = {
            'date': 1710460800000,
            'description': 'Grocery Store',
            'amount': Decimal('-50.25'),
            'balance': Decimal('49.75'),
            'transaction_type': 'DEBIT',
            'category': 'Food',
            'memo': 'Weekly groceries',
        }
        self.assert_transaction_fields(transactions[0], expected)
        
        # Check running total calculation
        expected_total = Decimal('100.0')  # Opening balance
        for t in transactions:
            expected_total += Decimal(t['amount'])
            self.assertEqual(t['balance'], expected_total)

    def test_parse_csv_with_field_map(self):
        """Test parsing CSV transactions with field mapping."""
        transactions = parse_csv_transactions(self.csv_content, 1000.0, self.field_map)
        
        self.assertEqual(len(transactions), 3)
        
        # Check first transaction
        first_tx = transactions[0]
        self.assertEqual(first_tx["date"], 1704067200000)
        self.assertEqual(first_tx["description"], "Grocery Store")
        self.assertEqual(first_tx["amount"], Decimal("123.45"))
        self.assertEqual(first_tx["balance"], Decimal("1123.45"))

    def test_parse_ofx_from_file(self):
        """Test parsing OFX transactions from file."""
        content = self.read_test_file('sample_transactions.ofx')
        transactions = parse_ofx_transactions(content, 100.0)
        
        self.assertEqual(len(transactions), 4)
        
        # Check first transaction
        expected = {
            'date': 1710460800000,
            'description': 'Grocery Store',
            'amount': Decimal('-50.25'),
            'balance': Decimal('49.75'),
            'transaction_type': 'DEBIT',
            'memo': 'Weekly groceries',
        }
        self.assert_transaction_fields(transactions[0], expected)
        
        # Check running total calculation
        expected_total = Decimal('100.0')  # Opening balance
        for t in transactions:
            expected_total += Decimal(t['amount'])
            self.assertEqual(t['balance'], expected_total)

    def test_parse_qfx_from_file(self):
        """Test parsing QFX transactions from file."""
        content = self.read_test_file('sample_transactions.qfx')
        transactions = parse_ofx_transactions(content, 100.0)
        
        self.assertEqual(len(transactions), 4)
        
        # Check first transaction
        expected = {
            'date': 1710460800000,
            'description': 'Grocery Store',
            'amount': Decimal('-50.25'),
            'balance': Decimal('49.75'),
            'transaction_type': 'DEBIT',
            'memo': 'Weekly groceries',
        }
        self.assert_transaction_fields(transactions[0], expected)
        
        # Check running total calculation
        expected_total = Decimal('100.0')  # Opening balance
        for t in transactions:
            expected_total += Decimal(t['amount'])
            self.assertEqual(t['balance'], expected_total)

    def test_parse_ofx_inline(self):
        """Test parsing OFX transactions from inline content."""
        transactions = parse_ofx_transactions(self.ofx_content, 1000.0)
        
        self.assertEqual(len(transactions), 2)
        
        # Check first transaction
        first_tx = transactions[0]
        self.assertEqual(first_tx["date"], 1704067200000)
        self.assertEqual(first_tx["description"], "Grocery Store")
        self.assertEqual(first_tx["amount"], Decimal("-123.45"))
        self.assertEqual(first_tx["balance"], Decimal("876.55"))  # 1000 - 123.45
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

    def test_detect_date_order_ascending(self):
        """Test detection of ascending date order."""
        dates = [
            "2024-01-01",
            "2024-01-02",
            "2024-01-03",
            "2024-01-04"
        ]
        result = detect_date_order(dates)
        self.assertEqual(result, "asc")

    def test_detect_date_order_descending(self):
        """Test detection of descending date order."""
        dates = [
            "2024-01-04",
            "2024-01-03",
            "2024-01-02",
            "2024-01-01"
        ]
        result = detect_date_order(dates)
        self.assertEqual(result, "desc")

    def test_detect_date_order_mixed(self):
        """Test detection with mixed date order (should default to ascending)."""
        dates = [
            "2024-01-01",
            "2024-01-03",
            "2024-01-02",
            "2024-01-04"
        ]
        result = detect_date_order(dates)
        self.assertEqual(result, "asc")

    def test_detect_date_order_single_date(self):
        """Test detection with single date (should default to ascending)."""
        dates = ["2024-01-01"]
        result = detect_date_order(dates)
        self.assertEqual(result, "asc")

    def test_detect_date_order_empty(self):
        """Test detection with empty list (should default to ascending)."""
        dates = []
        result = detect_date_order(dates)
        self.assertEqual(result, "asc")

    def test_detect_date_order_invalid_dates(self):
        """Test detection with invalid dates (should skip invalid dates)."""
        dates = [
            "2024-01-01",
            "invalid-date",
            "2024-01-03",
            "2024-01-02"
        ]
        result = detect_date_order(dates)
        self.assertEqual(result, "asc")

    def test_detect_date_order_real_dates(self):
        """Test detection real dates."""
        dates = [
            '2024-12-16', '2024-12-03', '2024-12-01', '2024-12-01', '2024-11-03', '2024-11-01', '2024-11-01', '2024-10-13', '2024-10-03', '2024-10-01', '2024-10-01', '2024-09-24', '2024-09-03', '2024-09-01', '2024-09-01', '2024-08-28', '2024-08-05', '2024-08-05', '2024-08-04', '2024-08-01', '2024-08-01', '2024-07-21', '2024-07-03', '2024-07-03', '2024-07-01', '2024-07-01', '2024-06-20', '2024-06-03', '2024-06-02', '2024-06-02', '2024-05-19'
        ]
        result = detect_date_order(dates)
        self.assertEqual(result, "desc")

    def test_dates_with_equal_timestamps(self):
        """Test dates with equal timestamps."""
        dates = [
            '2024-12-03', '2024-12-01', '2024-12-01'
        ]
        result = detect_date_order(dates)
        self.assertEqual(result, "desc")

    def test_equality(self):
        """Test equality of two dates."""
        date1 = datetime.strptime("2024-12-01", "%Y-%m-%d")
        date2 = datetime.strptime("2024-12-01", "%Y-%m-%d")
        self.assertEqual(date1, date2)

    def test_parse_csv_with_commas_in_field_with_trailing_comma(self):
        """Test parsing CSV where a field contains a comma and is not quoted, causing extra columns."""
        # Header has an empty field due to extra comma in the data row
        csv_content = b"Date,Description,Amount,Merchant City,\n2024-08-04,GITHUB,INC.,78.72,SAN FRANCISCO\n2024-08-05,Normal Merchant,12.34,London,\n2024-08-06,Another Merchant,56.78,Paris,\n"
        # The first row should merge 'GITHUB,INC.' into one field for Description
        # We'll assume the parser is fixed to handle this, or this test will fail until fixed
        transactions = parse_csv_transactions(csv_content, 100.0)
        self.assertEqual(len(transactions), 3)
        # Check the problematic row
        self.assertIn('description', transactions[0])
        self.assertEqual(transactions[0]['description'], '"GITHUB,INC."')
        self.assertEqual(transactions[0]['amount'], Decimal('78.72'))
        self.assertEqual(transactions[0]['balance'], Decimal('178.72'))
        # Check a normal row
        self.assertEqual(transactions[1]['description'], 'Normal Merchant')
        self.assertEqual(transactions[1]['amount'], Decimal('12.34'))
        self.assertEqual(transactions[1]['balance'], Decimal('191.06'))

    def test_parse_csv_with_commas_in_field(self):
        """Test parsing CSV where a field contains a comma and is not quoted, causing extra columns in those rows alone"""
 
        csv_content = b"Date,Description,Amount,Merchant City\n2024-08-04,GITHUB,INC.,78.72,SAN FRANCISCO\n2024-08-05,Normal Merchant,12.34,London\n2024-08-06,Another Merchant,56.78,Paris\n"
        # The first row should merge 'GITHUB,INC.' into one field for Description
        # We'll assume the parser is fixed to handle this, or this test will fail until fixed
        transactions = parse_csv_transactions(csv_content, 100.0)
        self.assertEqual(len(transactions), 3)
        # Check the problematic row
        self.assertIn('description', transactions[0])
        self.assertEqual(transactions[0]['description'], '"GITHUB,INC."')
        self.assertEqual(transactions[0]['amount'], Decimal('78.72'))
        self.assertEqual(transactions[0]['balance'], Decimal('178.72'))
        # Check a normal row
        self.assertEqual(transactions[1]['description'], 'Normal Merchant')
        self.assertEqual(transactions[1]['amount'], Decimal('12.34'))
        self.assertEqual(transactions[1]['balance'], Decimal('191.06'))

    def assert_transaction_fields(self, transaction, expected):
        for key, value in expected.items():
            self.assertEqual(transaction[key], value)

    def test_preprocess_csv_text_merges_unquoted_commas(self):
        """Test that preprocess_csv_text merges unquoted commas in description and quotes the field."""
        csv_text = "Date,Description,Amount,Merchant City,\n2024-08-04,GITHUB,INC.,78.72,SAN FRANCISCO\n2024-08-05,Normal Merchant,12.34,London,\n"
        expected = (
            'Date,Description,Amount,Merchant City,\n'
            '2024-08-04,"GITHUB,INC.",78.72,SAN FRANCISCO,\n'
            '2024-08-05,Normal Merchant,12.34,London,\n'
        )
        # The expected output is that the first data row's description is quoted and merged
        processed = preprocess_csv_text(csv_text)
        self.assertIn('"GITHUB,INC."', processed)
        self.assertEqual(processed.count('"GITHUB,INC."'), 1)
        self.assertTrue(processed.startswith('Date,Description'))


if __name__ == '__main__':
    unittest.main() 
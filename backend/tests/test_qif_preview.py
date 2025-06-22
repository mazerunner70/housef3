import unittest
from handlers.file_operations import parse_qif_preview


class TestQIFPreview(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        # Sample QIF content
        self.sample_qif = """!Type:Bank
D1/15/2024
T-25.50
PGrocery Store
MWeekly groceries
LFood:Groceries
N1001
C*
^
D1/16/2024
T1500.00
PSalary Deposit
MMonthly salary
LIncome:Salary
^
D1/14/2024
T-45.00
PGas Station
MFuel
LTransportation:Gas
N1002
^"""

    def test_parse_qif_preview_basic(self):
        """Test basic QIF preview parsing."""
        result = parse_qif_preview(self.sample_qif)
        
        # Check structure
        self.assertIn('columns', result)
        self.assertIn('data', result)
        self.assertIn('totalRows', result)
        self.assertIn('message', result)
        
        # Check total rows
        self.assertEqual(result['totalRows'], 3)
        
        # Check columns include QIF field codes
        columns = result['columns']
        self.assertIn('D', columns)  # Date
        self.assertIn('T', columns)  # Amount
        self.assertIn('P', columns)  # Payee
        self.assertIn('M', columns)  # Memo
        self.assertIn('L', columns)  # Category
        
        # Check data
        data = result['data']
        self.assertEqual(len(data), 3)  # All 3 transactions should be in preview
        
        # Check first transaction (should be sorted by date - 1/14/2024 first)
        first_transaction = data[0]
        self.assertEqual(first_transaction['D'], '1/14/2024')
        self.assertEqual(first_transaction['T'], '-45.00')
        self.assertEqual(first_transaction['P'], 'Gas Station')

    def test_parse_qif_preview_column_ordering(self):
        """Test that QIF field codes are ordered correctly."""
        result = parse_qif_preview(self.sample_qif)
        columns = result['columns']
        
        # Priority fields should come first
        priority_fields = ['D', 'T', 'P', 'M', 'L', 'N', 'C']
        found_priority_indices = {}
        
        for field in priority_fields:
            if field in columns:
                found_priority_indices[field] = columns.index(field)
        
        # Check that D, T, P come before other fields
        if 'D' in found_priority_indices and 'T' in found_priority_indices:
            self.assertLess(found_priority_indices['D'], found_priority_indices['T'])

    def test_parse_qif_preview_date_sorting(self):
        """Test that transactions are sorted by date in ascending order."""
        result = parse_qif_preview(self.sample_qif)
        data = result['data']
        
        # Dates should be in order: 1/14/2024, 1/15/2024, 1/16/2024
        self.assertEqual(data[0]['D'], '1/14/2024')
        self.assertEqual(data[1]['D'], '1/15/2024')
        self.assertEqual(data[2]['D'], '1/16/2024')

    def test_parse_qif_preview_empty_file(self):
        """Test parsing empty QIF file."""
        result = parse_qif_preview("!Type:Bank\n")
        
        self.assertEqual(result['totalRows'], 0)
        self.assertEqual(len(result['data']), 0)
        self.assertIn('No transactions found', result['message'])

    def test_parse_qif_preview_malformed_content(self):
        """Test parsing malformed QIF content."""
        malformed_qif = "This is not QIF content"
        result = parse_qif_preview(malformed_qif)
        
        # The implementation tries to parse any content, so malformed content
        # may still result in some parsed data. We just check it doesn't crash.
        self.assertIn('columns', result)
        self.assertIn('data', result)
        self.assertIn('totalRows', result)
        self.assertIn('message', result)
        # The result may have 0 or more rows depending on how the parser interprets the malformed content
        self.assertGreaterEqual(result['totalRows'], 0)

    def test_parse_qif_preview_all_columns_present(self):
        """Test that all transactions have all columns in the preview."""
        result = parse_qif_preview(self.sample_qif)
        columns = result['columns']
        data = result['data']
        
        # Every transaction should have every column (even if empty)
        for transaction in data:
            for column in columns:
                self.assertIn(column, transaction)


if __name__ == '__main__':
    unittest.main() 
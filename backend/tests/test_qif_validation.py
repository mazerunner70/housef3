"""
Simple test to verify QIF format detection works correctly.
This tests the backend QIF detection logic.
"""
import unittest
from utils.transaction_parser import file_type_selector
from models.transaction_file import FileFormat


class TestQIFValidation(unittest.TestCase):
    def test_qif_detection_with_type_header(self):
        """Test QIF detection with !Type: header."""
        qif_content = b"""!Type:Bank
D1/15/2024
T-25.50
PGrocery Store
^"""
        result = file_type_selector(qif_content)
        self.assertEqual(result, FileFormat.QIF)

    def test_qif_detection_with_account_header(self):
        """Test QIF detection with !Account header."""
        qif_content = b"""!Account
NChecking Account
TBank
^
!Type:Bank
D1/15/2024
T-25.50
^"""
        result = file_type_selector(qif_content)
        self.assertEqual(result, FileFormat.QIF)

    def test_non_qif_content(self):
        """Test that non-QIF content is not detected as QIF."""
        csv_content = b"""Date,Amount,Description
1/15/2024,-25.50,Grocery Store"""
        result = file_type_selector(csv_content)
        self.assertEqual(result, FileFormat.CSV)

    def test_empty_content(self):
        """Test empty content handling."""
        result = file_type_selector(b"")
        self.assertEqual(result, FileFormat.OTHER)


if __name__ == '__main__':
    unittest.main() 
"""
Unit tests for transaction parser utilities.
"""
import unittest
from decimal import Decimal
from datetime import datetime
import xml.etree.ElementTree as ET
from unittest.mock import patch, mock_open
from models.account import Currency
from models.money import Money
from models.transaction import Transaction
from models.transaction_file import FileFormat, TransactionFile, ProcessingStatus
from models.file_map import FileMap, FieldMapping
from utils.transaction_parser import (
    parse_transactions,
    parse_csv_transactions,
    parse_ofx_transactions,
    parse_date,
    detect_date_order,
    file_type_selector,
    apply_field_mapping,
    find_column_index,
    preprocess_csv_text
)

class TestTransactionParser(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.sample_currency = Currency.USD
        self.sample_money = Money(Decimal('1000.00'), self.sample_currency)
        
        # Sample transaction file
        self.transaction_file = TransactionFile(
            file_id="test_file_id",
            user_id="test_user_id",
            account_id="test_account_id",
            file_format=FileFormat.CSV,
            file_map_id="test_map_id",
            opening_balance=self.sample_money,
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        
        # Sample field mapping
        self.field_map = FileMap(
            file_map_id="test_map_id",
            user_id="test_user_id",
            name="Test Map",
            description="Test mapping configuration",
            mappings=[
                FieldMapping(source_field="Date", target_field="date"),
                FieldMapping(source_field="Description", target_field="description"),
                FieldMapping(source_field="Amount", target_field="amount"),
                FieldMapping(source_field="Type", target_field="debitOrCredit"),
                FieldMapping(source_field="Currency", target_field="currency")
            ]
        )

    def test_parse_date(self):
        """Test date parsing function."""
        # Test various date formats
        test_cases = [
            ("2024-03-15", 1710460800000),  # YYYY-MM-DD
            ("03/15/2024", 1710460800000),  # MM/DD/YYYY
            ("15/03/2024", 1710460800000),  # DD/MM/YYYY
            ("20240315", 1710460800000),    # YYYYMMDD
            ("03-15-2024", 1710460800000),  # MM-DD-YYYY
            ("15-03-2024", 1710460800000)   # DD-MM-YYYY
        ]
        
        for date_str, expected_ms in test_cases:
            with self.subTest(date_str=date_str):
                result = parse_date(date_str)
                self.assertEqual(result, expected_ms)
        
        # Test invalid date format
        with self.assertRaises(ValueError):
            parse_date("invalid-date")

    def test_detect_date_order(self):
        """Test date order detection."""
        # Test ascending dates
        asc_dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        self.assertEqual(detect_date_order(asc_dates), "asc")
        
        # Test descending dates
        desc_dates = ["2024-01-03", "2024-01-02", "2024-01-01"]
        self.assertEqual(detect_date_order(desc_dates), "desc")
        
        # Test single date
        single_date = ["2024-01-01"]
        self.assertEqual(detect_date_order(single_date), "asc")
        
        # Test empty list
        self.assertEqual(detect_date_order([]), "asc")
        
        # Test invalid dates
        invalid_dates = ["invalid", "dates", "here"]
        self.assertEqual(detect_date_order(invalid_dates), "asc")

    def test_file_type_selector(self):
        """Test file format detection."""
        # Test CSV format
        csv_content = b"Date,Description,Amount\n2024-03-15,Test,100.00"
        self.assertEqual(file_type_selector(csv_content), FileFormat.CSV)
        
        # Test OFX format
        ofx_content = b"<OFX><STMTTRN><DTPOSTED>20240315</DTPOSTED></STMTTRN></OFX>"
        self.assertEqual(file_type_selector(ofx_content), FileFormat.OFX)
        
        # Test QFX format
        qfx_content = b"<QFX><STMTTRN><DTPOSTED>20240315</DTPOSTED></STMTTRN></QFX>"
        self.assertEqual(file_type_selector(qfx_content), FileFormat.QFX)
        
        # Test other format
        other_content = b"Some random content"
        self.assertEqual(file_type_selector(other_content), FileFormat.OTHER)

    def test_apply_field_mapping(self):
        """Test field mapping application."""
        row_data = {
            "Date": "2024-03-15",
            "Description": "Test Transaction",
            "Amount": "100.00",
            "Type": "DBIT",
            "Currency": "USD"
        }
        
        expected = {
            "date": "2024-03-15",
            "description": "Test Transaction",
            "amount": "100.00",
            "debitOrCredit": "DBIT",
            "currency": "USD"
        }
        
        result = apply_field_mapping(row_data, self.field_map)
        self.assertEqual(result, expected)
        
        # Test missing field
        row_data_missing = {"Date": "2024-03-15"}
        result = apply_field_mapping(row_data_missing, self.field_map)
        self.assertNotIn("description", result)

    def test_find_column_index(self):
        """Test column index finding."""
        header = ["Date", "Transaction Description", "Amount", "Balance"]
        
        # Test exact match
        self.assertEqual(find_column_index(header, ["Date"]), 0)
        
        # Test partial match
        self.assertEqual(find_column_index(header, ["Description"]), 1)
        
        # Test case insensitive
        self.assertEqual(find_column_index(header, ["date"]), 0)
        
        # Test multiple possible names
        self.assertEqual(find_column_index(header, ["Amt", "Amount"]), 2)
        
        # Test not found
        self.assertIsNone(find_column_index(header, ["Category"]))

    def test_preprocess_csv_text(self):
        """Test CSV preprocessing."""
        # Test normal CSV
        normal_csv = "Date,Description,Amount\n2024-03-15,Test,100.00"
        self.assertEqual(preprocess_csv_text(normal_csv), normal_csv)
        
        # Test CSV with unquoted commas in description
        messy_csv = 'Date,Description,Amount,\n2024-03-15,Test, with commas,100.00'
        expected = 'Date,Description,Amount\n2024-03-15,"Test, with commas",100.00'
        self.assertEqual(preprocess_csv_text(messy_csv), expected)
        
        # Test empty input
        self.assertEqual(preprocess_csv_text(""), "")

    def test_parse_csv_transactions(self):
        """Test CSV transaction parsing."""
        csv_content = b"""Date,Description,Amount,Type,Currency
2024-03-15,Test Transaction 1,100.00,DBIT,USD
2024-03-16,Test Transaction 2,-50.00,CRDT,USD"""
        
        transactions = parse_csv_transactions(self.transaction_file, csv_content, self.field_map)
        
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0].description, "Test Transaction 1")
        self.assertEqual(transactions[0].amount, Money(Decimal("-100.00"), Currency.USD))
        self.assertEqual(transactions[1].description, "Test Transaction 2")
        self.assertEqual(transactions[1].amount, Money(Decimal("-50.00"), Currency.USD))

    def test_parse_ofx_transactions(self):
        """Test OFX transaction parsing."""
        ofx_content = b"""
<OFX>
    <STMTTRN>
        <DTPOSTED>20240315</DTPOSTED>
        <TRNAMT>-100.00</TRNAMT>
        <NAME>Test Transaction 1</NAME>
        <TRNTYPE>DEBIT</TRNTYPE>
        <CURRENCY>USD</CURRENCY>
    </STMTTRN>
    <STMTTRN>
        <DTPOSTED>20240316</DTPOSTED>
        <TRNAMT>50.00</TRNAMT>
        <NAME>Test Transaction 2</NAME>
        <TRNTYPE>CREDIT</TRNTYPE>
        <CURRENCY>USD</CURRENCY>
    </STMTTRN>
</OFX>"""
        
        transactions = parse_ofx_transactions(self.transaction_file, ofx_content)
        
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0].description, "Test Transaction 1")
        self.assertEqual(transactions[0].amount, Money(Decimal("-100.00"), Currency.USD))
        self.assertEqual(transactions[1].description, "Test Transaction 2")
        self.assertEqual(transactions[1].amount, Money(Decimal("50.00"), Currency.USD))

    def test_parse_transactions_invalid_input(self):
        """Test transaction parsing with invalid input."""
        # Test missing file map
        invalid_file = TransactionFile(
            file_id="test_file_id",
            user_id="test_user_id",
            account_id="test_account_id",
            file_format=FileFormat.CSV,
            file_map_id=None,
            opening_balance=self.sample_money,
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        
        with self.assertRaises(ValueError):
            parse_transactions(invalid_file, b"", self.field_map)
        
        # Test missing opening balance
        invalid_file = TransactionFile(
            file_id="test_file_id",
            user_id="test_user_id",
            account_id="test_account_id",
            file_format=FileFormat.CSV,
            file_map_id="test_map_id",
            opening_balance=None,
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        
        with self.assertRaises(ValueError):
            parse_transactions(invalid_file, b"", self.field_map)
        
        # Test unsupported file format
        invalid_file = TransactionFile(
            file_id="test_file_id",
            user_id="test_user_id",
            account_id="test_account_id",
            file_format=FileFormat.OTHER,
            file_map_id="test_map_id",
            opening_balance=self.sample_money,
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        
        transactions = parse_transactions(invalid_file, b"", self.field_map)
        self.assertEqual(transactions, []) 
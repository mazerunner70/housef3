"""
Unit tests for file analyzer utilities.
"""
import unittest
from unittest.mock import patch, MagicMock, ANY
import os
from io import BytesIO, StringIO

from utils.file_analyzer import (
    analyze_file_format,
    detect_format_from_content,
    detect_format_from_extension
)
from models.transaction_file import FileFormat

class TestFileAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Sample file contents for different formats
        self.pdf_content = b'%PDF-1.4\n...'
        self.xlsx_content = b'PK\x03\x04...'
        self.ofx_content = b'''OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
</SONRS>
</SIGNONMSGSRSV1>
</OFX>'''
        self.qfx_content = b'''OFXHEADER:100
INTU.BID:12345
<QFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
</SONRS>
</SIGNONMSGSRSV1>
</QFX>'''
        self.csv_content = b'Date,Description,Amount\n2024-01-01,Test Transaction,100.00'
        self.json_content = b'{"transactions": [{"date": "2024-01-01", "amount": 100.00}]}'
        self.xml_content = b'<?xml version="1.0"?><root><transaction><date>2024-01-01</date></transaction></root>'

    @patch('utils.file_analyzer.get_object_content')
    def test_analyze_file_format_pdf(self, mock_get_object_content):
        """Test analyzing PDF file format."""
        # Setup
        mock_get_object_content.return_value = self.pdf_content

        # Execute
        result = analyze_file_format('test-bucket', 'test.pdf')

        # Verify
        self.assertEqual(result, FileFormat.PDF)
        mock_get_object_content.assert_called_with(
            'test.pdf',
            'test-bucket'
        )

    @patch('utils.file_analyzer.get_object_content')
    def test_analyze_file_format_xlsx(self, mock_get_object_content):
        """Test analyzing XLSX file format."""
        # Setup
        mock_get_object_content.return_value = self.xlsx_content

        # Execute
        result = analyze_file_format('test-bucket', 'test.xlsx')

        # Verify
        self.assertEqual(result, FileFormat.XLSX)

    @patch('utils.file_analyzer.get_object_content')
    def test_analyze_file_format_ofx(self, mock_get_object_content):
        """Test analyzing OFX file format."""
        # Setup
        mock_get_object_content.return_value = self.ofx_content

        # Execute
        result = analyze_file_format('test-bucket', 'test.ofx')

        # Verify
        self.assertEqual(result, FileFormat.OFX)

    @patch('utils.file_analyzer.get_object_content')
    def test_analyze_file_format_qfx(self, mock_get_object_content):
        """Test analyzing QFX file format."""
        # Setup
        mock_get_object_content.return_value = self.qfx_content

        # Execute
        result = analyze_file_format('test-bucket', 'test.qfx')

        # Verify
        self.assertEqual(result, FileFormat.QFX)

    @patch('utils.file_analyzer.get_object_content')
    def test_analyze_file_format_csv(self, mock_get_object_content):
        """Test analyzing CSV file format."""
        # Setup
        mock_get_object_content.return_value = self.csv_content

        # Execute
        result = analyze_file_format('test-bucket', 'test.csv')

        # Verify
        self.assertEqual(result, FileFormat.CSV)

    @patch('utils.file_analyzer.get_object_content')
    def test_analyze_file_format_json(self, mock_get_object_content):
        """Test analyzing JSON file format."""
        # Setup
        mock_get_object_content.return_value = self.json_content

        # Execute
        result = analyze_file_format('test-bucket', 'test.json')

        # Verify
        self.assertEqual(result, FileFormat.OTHER)

    @patch('utils.file_analyzer.get_object_content')
    def test_analyze_file_format_xml(self, mock_get_object_content):
        """Test analyzing XML file format."""
        # Setup
        mock_get_object_content.return_value = self.xml_content

        # Execute
        result = analyze_file_format('test-bucket', 'test.xml')

        # Verify
        self.assertEqual(result, FileFormat.OTHER)

    @patch('utils.file_analyzer.get_object_content')
    def test_analyze_file_format_s3_error(self, mock_get_object_content):
        """Test handling S3 client error."""
        # Setup
        mock_get_object_content.side_effect = Exception("S3 error")

        # Execute
        result = analyze_file_format('test-bucket', 'test.csv')

        # Verify
        self.assertEqual(result, FileFormat.CSV)  # Should fall back to extension-based detection

    @patch('utils.file_analyzer.get_object_content')
    def test_analyze_file_format_download_fails_fallback_to_extension(self, mock_get_object_content):
        """Test that analyze_file_format falls back to extension if download fails."""
        mock_get_object_content.return_value = None # Simulate download failure

        result = analyze_file_format('test-bucket', 'test_file.ofx')
        self.assertEqual(result, FileFormat.OFX) # Should use extension

        result = analyze_file_format('test-bucket', 'unknown_file.xyz')
        self.assertEqual(result, FileFormat.OTHER) # Extension unknown

    def test_detect_format_from_content(self):
        """Test format detection from file content."""
        # Test PDF detection
        result = detect_format_from_content(self.pdf_content)
        self.assertEqual(result, FileFormat.PDF)

        # Test XLSX detection
        result = detect_format_from_content(self.xlsx_content)
        self.assertEqual(result, FileFormat.XLSX)

        # Test OFX detection
        result = detect_format_from_content(self.ofx_content)
        self.assertEqual(result, FileFormat.OFX)

        # Test QFX detection
        result = detect_format_from_content(self.qfx_content)
        self.assertEqual(result, FileFormat.QFX)

        # Test CSV detection
        result = detect_format_from_content(self.csv_content)
        self.assertEqual(result, FileFormat.CSV)

        # Test JSON detection (should be OTHER)
        result = detect_format_from_content(self.json_content)
        self.assertEqual(result, FileFormat.OTHER)

        # Test XML detection (should be OTHER)
        result = detect_format_from_content(self.xml_content)
        self.assertEqual(result, FileFormat.OTHER)

    def test_detect_format_from_extension(self):
        """Test format detection from file extension."""
        # Test known extensions
        self.assertEqual(detect_format_from_extension('test.csv'), FileFormat.CSV)
        self.assertEqual(detect_format_from_extension('test.ofx'), FileFormat.OFX)
        self.assertEqual(detect_format_from_extension('test.qfx'), FileFormat.QFX)
        self.assertEqual(detect_format_from_extension('test.pdf'), FileFormat.PDF)
        self.assertEqual(detect_format_from_extension('test.xlsx'), FileFormat.XLSX)

        # Test unknown extension
        self.assertEqual(detect_format_from_extension('test.unknown'), FileFormat.OTHER)

        # Test no extension
        self.assertEqual(detect_format_from_extension('test'), FileFormat.OTHER)

        # Test case insensitivity
        self.assertEqual(detect_format_from_extension('test.CSV'), FileFormat.CSV)
        self.assertEqual(detect_format_from_extension('test.OFX'), FileFormat.OFX)

if __name__ == '__main__':
    unittest.main() 
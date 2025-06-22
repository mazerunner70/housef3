import unittest
from handlers.file_operations import parse_ofx_preview, format_ofx_transaction_for_preview
from models.transaction_file import FileFormat


class TestOFXPreview(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        # Sample OFX XML content
        self.sample_ofx_xml = """<?xml version="1.0" encoding="UTF-8"?>
<OFX>
    <SIGNONMSGSRSV1>
        <SONRS>
            <STATUS>
                <CODE>0</CODE>
                <SEVERITY>INFO</SEVERITY>
            </STATUS>
        </SONRS>
    </SIGNONMSGSRSV1>
    <BANKMSGSRSV1>
        <STMTTRNRS>
            <STMTRS>
                <BANKTRANLIST>
                    <STMTTRN>
                        <TRNTYPE>DEBIT</TRNTYPE>
                        <DTPOSTED>20240115</DTPOSTED>
                        <TRNAMT>-25.50</TRNAMT>
                        <FITID>12345</FITID>
                        <NAME>GROCERY STORE</NAME>
                        <MEMO>Weekly groceries</MEMO>
                    </STMTTRN>
                    <STMTTRN>
                        <TRNTYPE>CREDIT</TRNTYPE>
                        <DTPOSTED>20240116</DTPOSTED>
                        <TRNAMT>1500.00</TRNAMT>
                        <FITID>12346</FITID>
                        <NAME>SALARY DEPOSIT</NAME>
                        <MEMO>Monthly salary</MEMO>
                    </STMTTRN>
                </BANKTRANLIST>
            </STMTRS>
        </STMTTRNRS>
    </BANKMSGSRSV1>
</OFX>"""

        # Sample OFX colon-separated content
        self.sample_ofx_colon = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<STMTTRN>
TRNTYPE:DEBIT
DTPOSTED:20240115
TRNAMT:-25.50
FITID:12345
NAME:GROCERY STORE
MEMO:Weekly groceries
</STMTTRN>

<STMTTRN>
TRNTYPE:CREDIT
DTPOSTED:20240116
TRNAMT:1500.00
FITID:12346
NAME:SALARY DEPOSIT
MEMO:Monthly salary
</STMTTRN>"""

    def test_format_ofx_transaction_for_preview(self):
        """Test formatting OFX transaction data for preview."""
        data = {
            'DTPOSTED': '20240115',
            'TRNAMT': '-25.50',
            'NAME': 'GROCERY STORE',
            'MEMO': 'Weekly groceries',
            'TRNTYPE': 'DEBIT',
            'FITID': '12345'
        }
        
        result = format_ofx_transaction_for_preview(data)
        
        # The function returns OFX field codes as keys, not human-readable names
        self.assertEqual(result['DTPOSTED'], '01/15/2024')
        self.assertEqual(result['TRNAMT'], '-25.50')
        self.assertEqual(result['NAME'], 'GROCERY STORE')
        self.assertEqual(result['TRNTYPE'], 'DEBIT')
        self.assertEqual(result['MEMO'], 'Weekly groceries')
        self.assertEqual(result['FITID'], '12345')

    def test_parse_ofx_xml_preview(self):
        """Test parsing XML OFX content for preview."""
        result = parse_ofx_preview(self.sample_ofx_xml, FileFormat.OFX)
        
        self.assertEqual(len(result['columns']), 6)
        self.assertIn('Date', result['columns'])
        self.assertIn('Amount', result['columns'])
        self.assertIn('Description', result['columns'])
        
        self.assertEqual(result['totalRows'], 2)
        self.assertEqual(len(result['data']), 2)
        
        # Check first transaction - the data uses OFX field codes as keys
        first_transaction = result['data'][0]
        self.assertEqual(first_transaction['DTPOSTED'], '01/15/2024')
        self.assertEqual(first_transaction['TRNAMT'], '-25.50')
        self.assertEqual(first_transaction['NAME'], 'GROCERY STORE')
        self.assertEqual(first_transaction['TRNTYPE'], 'DEBIT')

    def test_parse_ofx_colon_separated_preview(self):
        """Test parsing colon-separated OFX content for preview."""
        result = parse_ofx_preview(self.sample_ofx_colon, FileFormat.OFX)
        
        self.assertEqual(len(result['columns']), 6)
        self.assertEqual(result['totalRows'], 2)
        self.assertEqual(len(result['data']), 2)
        
        # Check first transaction - the data uses OFX field codes as keys
        first_transaction = result['data'][0]
        self.assertEqual(first_transaction['DTPOSTED'], '01/15/2024')
        self.assertEqual(first_transaction['TRNAMT'], '-25.50')
        self.assertEqual(first_transaction['NAME'], 'GROCERY STORE')
        self.assertEqual(first_transaction['TRNTYPE'], 'DEBIT')

    def test_parse_ofx_empty_content(self):
        """Test parsing empty OFX content."""
        result = parse_ofx_preview("", FileFormat.OFX)
        
        self.assertEqual(len(result['columns']), 6)
        self.assertEqual(result['totalRows'], 0)
        self.assertEqual(len(result['data']), 0)
        # The actual implementation returns "Invalid XML format" for empty content
        self.assertIn('Invalid XML format', result['message'])

    def test_parse_ofx_invalid_xml(self):
        """Test parsing invalid XML OFX content."""
        invalid_xml = "<OFX><INVALID>unclosed tag"
        result = parse_ofx_preview(invalid_xml, FileFormat.OFX)
        
        self.assertEqual(len(result['columns']), 6)
        self.assertEqual(result['totalRows'], 0)
        self.assertEqual(len(result['data']), 0)
        self.assertIn('Invalid XML format', result['message'])


if __name__ == '__main__':
    unittest.main() 
"""
File analyzer utilities for detecting file formats based on content inspection.
"""
import os
import logging
import csv
import json
import xml.etree.ElementTree as ET
from io import BytesIO, StringIO
from models.transaction_file import FileFormat
from utils.s3_dao import get_object_content

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def analyze_file_format(bucket: str, key: str) -> FileFormat:
    """
    Analyze the actual file format based on content inspection.
    
    Args:
        bucket: S3 bucket name where the file is stored
        key: S3 object key for the file
        
    Returns:
        FileFormat enum value representing the detected format
    """
    try:
        # Get the file extension first for initial guess
        _, file_extension = os.path.splitext(key)
        file_extension = file_extension.lower()[1:] if file_extension else ""
        
        # Try to download the file content using s3_dao
        content_bytes = get_object_content(key, bucket)
        if content_bytes is None:
            logger.error(f"Could not download file content from S3: {key}")
            return detect_format_from_extension(key)
        
        # Try to detect format based on content signatures
        detected_format = detect_format_from_content(content_bytes)
        logger.info(f"File format detection result for {key}: {detected_format}")
        
        return detected_format
    except Exception as e:
        logger.error(f"Error analyzing file format: {str(e)}")
        # Fall back to extension-based detection
        return detect_format_from_extension(key)

def detect_format_from_content(content: bytes) -> FileFormat:
    """
    Detect file format based on content inspection.
    
    Args:
        content: File content as bytes
        
    Returns:
        FileFormat enum value
    """
    try:
        # Check for PDF signature first (before text decoding)
        if content.startswith(b'%PDF-'):
            return FileFormat.PDF

        # Check for XLSX signature (PK magic number for ZIP files)
        if content.startswith(b'PK\x03\x04'):
            # XLSX files are ZIP files containing specific XML files
            # We could do more thorough checking by unzipping and checking for xl/ directory
            # but for now, this basic check should suffice
            return FileFormat.XLSX

        # Try to decode as text first
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            # If not text, try as binary
            return FileFormat.OTHER

        # Check for QIF format
        if text_content.startswith('!Type:') or '!Type:' in text_content[:100]:
            return FileFormat.QIF

        # Check for OFX/QFX format
        if text_content.strip().startswith('OFXHEADER:100'):
            # Check if it's a QFX file
            if '<QFX>' in text_content:
                return FileFormat.QFX
            return FileFormat.OFX
        elif text_content.strip().startswith('<?OFX'):
            return FileFormat.OFX

        # Check for JSON format
        if text_content.strip().startswith('{') or text_content.strip().startswith('['):
            try:
                json.loads(text_content)
                return FileFormat.OTHER  # We treat JSON as OTHER format since we don't process it
            except json.JSONDecodeError:
                pass

        # Check for CSV format
        try:
            # Try to parse as CSV
            csv_reader = csv.reader(StringIO(text_content))
            # Read all rows up to 3 rows to confirm it's structured like a CSV
            rows = []
            for _ in range(3):
                try:
                    row = next(csv_reader)
                    rows.append(row)
                except StopIteration:
                    break
            
            # Check if we have at least one row with multiple columns
            if rows and all(len(row) > 1 for row in rows):
                return FileFormat.CSV
        except csv.Error:
            pass

        # Check for XML format - treat all XML as OTHER unless it's OFX/QFX
        try:
            ET.fromstring(text_content)
            # Check if it's an OFX/QFX file in XML format
            if '<OFX>' in text_content or '<QFX>' in text_content:
                return FileFormat.OFX if '<OFX>' in text_content else FileFormat.QFX
            return FileFormat.OTHER
        except ET.ParseError:
            pass

        return FileFormat.OTHER

    except Exception as e:
        logger.error(f"Error detecting file format: {str(e)}")
        return FileFormat.OTHER

def detect_format_from_extension(filename: str) -> FileFormat:
    """
    Detect file format based on file extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        FileFormat enum value
    """
    # Get the file extension
    _, extension = os.path.splitext(filename)
    extension = extension.lower()[1:] if extension else ""
    
    # Map extensions to formats
    format_map = {
        'csv': FileFormat.CSV,
        'ofx': FileFormat.OFX,
        'qfx': FileFormat.QFX,
        'qif': FileFormat.QIF,
        'pdf': FileFormat.PDF,
        'xlsx': FileFormat.XLSX,
        'xls': FileFormat.EXCEL,
        'json': FileFormat.JSON
    }
    
    return format_map.get(extension, FileFormat.OTHER) 
"""
File analyzer utilities for detecting file formats based on content inspection.
"""
import os
import logging
import csv
import json
import xml.etree.ElementTree as ET
from io import BytesIO, StringIO
import boto3
from botocore.exceptions import ClientError

from ..models.transaction_file import FileFormat

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

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
        
        # Try to download the file content
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content_bytes = response['Body'].read()
        
        # Try to detect format based on content signatures
        detected_format = detect_format_from_content(content_bytes, file_extension)
        logger.info(f"File format detection result for {key}: {detected_format}")
        
        return detected_format
    except ClientError as e:
        logger.error(f"Error downloading file from S3: {str(e)}")
        # Fall back to extension-based detection
        return detect_format_from_extension(key)
    except Exception as e:
        logger.error(f"Error analyzing file format: {str(e)}")
        # Fall back to extension-based detection
        return detect_format_from_extension(key)

def detect_format_from_content(content_bytes: bytes, extension: str) -> FileFormat:
    """
    Detect file format based on content inspection.
    
    Args:
        content_bytes: The file content as bytes
        extension: The file extension (for fallback)
        
    Returns:
        FileFormat enum value
    """
    # Check for PDF signature - most PDFs start with "%PDF-"
    if content_bytes.startswith(b'%PDF-'):
        return FileFormat.PDF
    
    # Check for Excel XLSX signature 
    # XLSX files are ZIP archives containing specific XML files
    if content_bytes.startswith(b'PK\x03\x04'):
        # This is a ZIP file signature, could be XLSX
        # More thorough check would unzip and check for specific files
        if extension == 'xlsx':
            return FileFormat.XLSX
    
    # Try to decode as text for other formats
    try:
        content_text = content_bytes.decode('utf-8')
        
        # Check for OFX/QFX signature (first look for SGML/XML format OFX)
        if '<OFX>' in content_text or '<ofx>' in content_text:
            return FileFormat.OFX
        
        # Check for the OFX headers in the older SGML format
        if 'OFXHEADER:' in content_text:
            return FileFormat.OFX
            
        # Check for QFX specific indicators
        if '<QFX>' in content_text or 'INTU.BID' in content_text:
            return FileFormat.QFX
            
        # Try to parse as CSV
        try:
            reader = csv.reader(StringIO(content_text))
            # Check if it has at least one row with multiple columns
            first_row = next(reader, None)
            if first_row and len(first_row) > 1:
                return FileFormat.CSV
        except:
            pass
        
        # Try to parse as JSON
        try:
            json.loads(content_text)
            return FileFormat.OTHER  # JSON is classified as OTHER
        except:
            pass
            
        # Try to parse as XML
        try:
            ET.parse(StringIO(content_text))
            return FileFormat.OTHER  # XML is classified as OTHER
        except:
            pass
            
    except UnicodeDecodeError:
        # If we can't decode as text, it's likely a binary format
        pass
    
    # Fall back to detection based on extension
    return detect_format_from_extension(os.path.basename(extension))

def detect_format_from_extension(filename: str) -> FileFormat:
    """
    Detect file format based on extension.
    
    Args:
        filename: The filename including extension
        
    Returns:
        FileFormat enum value
    """
    _, extension = os.path.splitext(filename)
    extension = extension.lower()[1:] if extension else ""
    
    # Map extensions to FileFormat
    extension_map = {
        'csv': FileFormat.CSV,
        'ofx': FileFormat.OFX,
        'qfx': FileFormat.QFX,
        'pdf': FileFormat.PDF,
        'xlsx': FileFormat.XLSX
    }
    
    return extension_map.get(extension, FileFormat.OTHER) 
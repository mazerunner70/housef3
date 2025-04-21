"""
Unit tests for the S3 DAO module.
"""
import unittest
import os
import boto3
from moto import mock_s3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from utils.s3_dao import (
    get_presigned_url,
    delete_object,
    get_object,
    get_object_content,
    put_object,
    FILE_STORAGE_BUCKET
)

class TestS3DAO(unittest.TestCase):
    """Test cases for S3 DAO operations."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock S3
        self.mock_s3 = mock_s3()
        self.mock_s3.start()
        
        # Create S3 client
        self.s3_client = boto3.client('s3')
        
        # Create test bucket
        self.s3_client.create_bucket(Bucket=FILE_STORAGE_BUCKET)
        
        # Test data
        self.test_key = 'test/test.txt'
        self.test_content = b'Hello, World!'
        self.test_content_type = 'text/plain'
        
    def tearDown(self):
        """Clean up test environment."""
        self.mock_s3.stop()
    
    def test_get_presigned_url_put(self):
        """Test generating presigned URL for PUT operation."""
        url = get_presigned_url(FILE_STORAGE_BUCKET, self.test_key, 'put')
        
        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith('https://'))
        self.assertIn(FILE_STORAGE_BUCKET, url)
        self.assertIn(self.test_key, url)
    
    def test_get_presigned_url_get(self):
        """Test generating presigned URL for GET operation."""
        url = get_presigned_url(FILE_STORAGE_BUCKET, self.test_key, 'get')
        
        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith('https://'))
        self.assertIn(FILE_STORAGE_BUCKET, url)
        self.assertIn(self.test_key, url)
    
    def test_get_presigned_url_invalid_operation(self):
        """Test generating presigned URL with invalid operation."""
        with self.assertRaises(ValueError):
            get_presigned_url(FILE_STORAGE_BUCKET, self.test_key, 'invalid')
    
    def test_get_presigned_url_invalid_bucket(self):
        """Test generating presigned URL with invalid bucket."""
        with self.assertRaises(ValueError):
            get_presigned_url('', self.test_key, 'put')
    
    def test_get_presigned_url_invalid_key(self):
        """Test generating presigned URL with invalid key."""
        with self.assertRaises(ValueError):
            get_presigned_url(FILE_STORAGE_BUCKET, '', 'put')
    
    def test_put_object(self):
        """Test uploading object to S3."""
        result = put_object(self.test_key, self.test_content, self.test_content_type)
        
        self.assertTrue(result)
        
        # Verify object exists
        response = self.s3_client.get_object(Bucket=FILE_STORAGE_BUCKET, Key=self.test_key)
        self.assertEqual(response['Body'].read(), self.test_content)
        self.assertEqual(response['ContentType'], self.test_content_type)
    
    def test_put_object_invalid_bucket(self):
        """Test uploading object to invalid bucket."""
        result = put_object(self.test_key, self.test_content, self.test_content_type, bucket='invalid-bucket')
        self.assertFalse(result)
    
    def test_get_object(self):
        """Test retrieving object from S3."""
        # First upload the object
        self.s3_client.put_object(
            Bucket=FILE_STORAGE_BUCKET,
            Key=self.test_key,
            Body=self.test_content,
            ContentType=self.test_content_type
        )
        
        response = get_object(self.test_key)
        
        self.assertIsNotNone(response)
        self.assertEqual(response['Body'].read(), self.test_content)
        self.assertEqual(response['ContentType'], self.test_content_type)
    
    def test_get_object_nonexistent(self):
        """Test retrieving nonexistent object from S3."""
        response = get_object('nonexistent.txt')
        self.assertIsNone(response)
    
    def test_get_object_content(self):
        """Test retrieving object content from S3."""
        # First upload the object
        self.s3_client.put_object(
            Bucket=FILE_STORAGE_BUCKET,
            Key=self.test_key,
            Body=self.test_content,
            ContentType=self.test_content_type
        )
        
        content = get_object_content(self.test_key)
        
        self.assertIsNotNone(content)
        self.assertEqual(content, self.test_content)
    
    def test_get_object_content_nonexistent(self):
        """Test retrieving content of nonexistent object from S3."""
        content = get_object_content('nonexistent.txt')
        self.assertIsNone(content)
    
    def test_delete_object(self):
        """Test deleting object from S3."""
        # First upload the object
        self.s3_client.put_object(
            Bucket=FILE_STORAGE_BUCKET,
            Key=self.test_key,
            Body=self.test_content,
            ContentType=self.test_content_type
        )
        
        result = delete_object(self.test_key)
        
        self.assertTrue(result)
        
        # Verify object is deleted
        with self.assertRaises(ClientError):
            self.s3_client.get_object(Bucket=FILE_STORAGE_BUCKET, Key=self.test_key)
    
    def test_delete_object_nonexistent(self):
        """Test deleting nonexistent object from S3."""
        result = delete_object('nonexistent.txt')
        self.assertFalse(result)
    
    def test_delete_object_invalid_bucket(self):
        """Test deleting object from invalid bucket."""
        result = delete_object(self.test_key, bucket='invalid-bucket')
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main() 
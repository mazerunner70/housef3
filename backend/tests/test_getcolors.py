import unittest
import json
import os
import sys
from typing import Dict, Any, Optional, Union
from decimal import Decimal


from handlers.getcolors import handler


class TestGetColors(unittest.TestCase):
    def setUp(self):
        """Set up test environment variables."""
        self.original_testing = os.environ.get("TESTING")
        os.environ["TESTING"] = "false"
        
        # Create mock event
        self.mock_event: Dict[str, Any] = {
            "version": "2.0",
            "routeKey": "GET /colors",
            "rawPath": "/colors",
            "rawQueryString": "",
            "headers": {
                "accept": "*/*",
                "content-length": "0",
                "host": "api.example.com",
                "user-agent": "curl/7.64.1",
                "x-amzn-trace-id": "Root=1-5e6722a7-cc56xmpl46db7ae02d4da47dd",
                "x-forwarded-for": "72.21.198.66",
                "x-forwarded-port": "443",
                "x-forwarded-proto": "https"
            },
            "requestContext": {
                "accountId": "123456789012",
                "apiId": "api-id",
                "http": {
                    "method": "GET",
                    "path": "/colors",
                    "protocol": "HTTP/1.1",
                    "sourceIp": "72.21.198.66",
                    "userAgent": "curl/7.64.1"
                },
                "requestId": "id",
                "routeKey": "GET /colors",
                "stage": "$default",
                "time": "12/Mar/2020:19:03:58 +0000",
                "timeEpoch": 1583348638390,
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "sub": "test-user-id",
                            "email": "test@example.com",
                            "auth_time": "2024-01-01T00:00:00Z"
                        }
                    }
                }
            },
            "isBase64Encoded": False
        }
        
        # Create mock context
        self.mock_context: Dict[str, Any] = {
            "aws_request_id": "test-request-id",
            "function_name": "test-function",
            "memory_limit_in_mb": 128,
            "invoked_function_arn": "arn:aws:lambda:us-east-1:123456789012:function:test-function",
            "log_group_name": "/aws/lambda/test-function",
            "log_stream_name": "2020/03/12/[$LATEST]abcdef123456",
        }

    def tearDown(self):
        """Clean up test environment variables."""
        if self.original_testing is not None:
            os.environ["TESTING"] = self.original_testing
        else:
            os.environ.pop("TESTING", None)

    def test_getcolors_success(self):
        """Test successful execution of getcolors handler"""
        os.environ["TESTING"] = "true"
        response = handler(self.mock_event, self.mock_context)
        
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        
        self.assertIn("colors", body)
        self.assertIsInstance(body["colors"], list)
        self.assertGreater(len(body["colors"]), 0)
        self.assertIn("metadata", body)
        self.assertIn("totalColors", body["metadata"])
        self.assertEqual(body["metadata"]["totalColors"], len(body["colors"]))
        self.assertIn("user", body)
        self.assertEqual(body["user"]["id"], "test-user-id")

    def test_getcolors_unauthorized(self):
        """Test unauthorized request"""
        # Remove authorizer from event
        event = dict(self.mock_event)
        event["requestContext"]["authorizer"] = {}
        
        response = handler(event, self.mock_context)
        self.assertEqual(response["statusCode"], 401)
        body = json.loads(response["body"])
        self.assertEqual(body["message"], "Unauthorized")

    def test_cors_headers(self):
        """Test that CORS headers are properly set"""
        os.environ["TESTING"] = "true"
        response = handler(self.mock_event, self.mock_context)

        headers = response["headers"]
        self.assertIn("Access-Control-Allow-Origin", headers)
        self.assertIn("Access-Control-Allow-Methods", headers)
        self.assertIn("Access-Control-Allow-Headers", headers)
        self.assertEqual(headers["Access-Control-Allow-Methods"], "GET,OPTIONS")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "*")
        self.assertIn("Content-Type", headers["Access-Control-Allow-Headers"])
        self.assertIn("Authorization", headers["Access-Control-Allow-Headers"])

    def test_options_request(self):
        """Test handling of OPTIONS request"""
        event: Dict[str, Any] = {
            "requestContext": {
                "http": {
                    "method": "OPTIONS"
                }
            }
        }

        response = handler(event, self.mock_context)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["message"], "OK")

    def test_error_handling_malformed_event(self):
        """Test error handling for malformed event"""
        malformed_event: Dict[str, Any] = {}
        response = handler(malformed_event, self.mock_context)
        self.assertEqual(response["statusCode"], 401)
        self.assertIn("Content-Type", response["headers"])
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        body = json.loads(response["body"])
        self.assertIn("message", body)
        self.assertEqual(body["message"], "Unauthorized")

if __name__ == '__main__':
    unittest.main() 
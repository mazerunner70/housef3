"""
Unit tests for authentication utilities.
"""
import unittest
from unittest.mock import patch, MagicMock
import logging

from utils.auth import (
    NotAuthorized,
    NotFound,
    get_user_from_event
)

class TestAuth(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Sample valid event with user information
        self.valid_event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "sub": "user123",
                            "email": "test@example.com",
                            "auth_time": "1616161616"
                        }
                    }
                }
            }
        }

    def test_not_authorized_exception(self):
        """Test NotAuthorized exception."""
        with self.assertRaises(NotAuthorized) as cm:
            raise NotAuthorized("Test unauthorized access")
        self.assertIsInstance(cm.exception, NotAuthorized)

    def test_not_found_exception(self):
        """Test NotFound exception."""
        with self.assertRaises(NotFound) as cm:
            raise NotFound("Test resource not found")
        self.assertIsInstance(cm.exception, NotFound)

    def test_get_user_from_valid_event(self):
        """Test extracting user from a valid event."""
        user_info = get_user_from_event(self.valid_event)
        
        # First verify we got a valid response
        self.assertIsNotNone(user_info, "Expected user_info to not be None")
        if user_info:  # Only check dictionary values if user_info is not None
            self.assertEqual(user_info["id"], "user123")
            self.assertEqual(user_info["email"], "test@example.com")
            self.assertEqual(user_info["auth_time"], "1616161616")

    def test_get_user_from_event_missing_request_context(self):
        """Test handling event with missing request context."""
        event = {}
        user_info = get_user_from_event(event)
        self.assertIsNone(user_info)

    def test_get_user_from_event_missing_authorizer(self):
        """Test handling event with missing authorizer."""
        event = {
            "requestContext": {}
        }
        user_info = get_user_from_event(event)
        self.assertIsNone(user_info)

    def test_get_user_from_event_missing_jwt(self):
        """Test handling event with missing JWT."""
        event = {
            "requestContext": {
                "authorizer": {}
            }
        }
        user_info = get_user_from_event(event)
        self.assertIsNone(user_info)

    def test_get_user_from_event_missing_claims(self):
        """Test handling event with missing claims."""
        event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {}
                }
            }
        }
        user_info = get_user_from_event(event)
        self.assertIsNone(user_info)

    def test_get_user_from_event_missing_sub(self):
        """Test handling event with missing sub claim."""
        event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "email": "test@example.com",
                            "auth_time": "1616161616"
                        }
                    }
                }
            }
        }
        user_info = get_user_from_event(event)
        self.assertIsNone(user_info)

    def test_get_user_from_event_with_minimal_claims(self):
        """Test extracting user with only required claims."""
        event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "sub": "user123"
                        }
                    }
                }
            }
        }
        user_info = get_user_from_event(event)
        
        # First verify we got a valid response
        self.assertIsNotNone(user_info, "Expected user_info to not be None")
        if user_info:  # Only check dictionary values if user_info is not None
            self.assertEqual(user_info["id"], "user123")
            self.assertEqual(user_info["email"], "unknown")
            self.assertIsNone(user_info["auth_time"])

    @patch('utils.auth.logger')
    def test_get_user_from_event_with_exception(self, mock_logger):
        """Test handling exceptions during user extraction."""
        # Create an event that will raise an exception when accessed
        event = MagicMock()
        event.get.side_effect = Exception("Test exception")
        
        user_info = get_user_from_event(event)
        
        self.assertIsNone(user_info)
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        self.assertIn("Error extracting user from event", error_msg)

    @patch('utils.auth.logger')
    def test_logging_in_get_user_from_event(self, mock_logger):
        """Test that appropriate logging occurs during user extraction."""
        user_info = get_user_from_event(self.valid_event)
        
        # Verify all logging calls
        self.assertEqual(mock_logger.info.call_count, 5)
        
        # Verify specific log messages
        log_calls = [args[0] for args, _ in mock_logger.info.call_args_list]
        self.assertIn("Request context:", log_calls[0])
        self.assertIn("Authorizer:", log_calls[1])
        self.assertIn("Claims:", log_calls[2])
        self.assertIn("User sub:", log_calls[3])
        self.assertIn("Returning user info:", log_calls[4])

    def test_get_user_from_event_with_empty_strings(self):
        """Test handling event with empty string values."""
        event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "sub": "",
                            "email": "",
                            "auth_time": ""
                        }
                    }
                }
            }
        }
        user_info = get_user_from_event(event)
        self.assertIsNone(user_info)

    def test_get_user_from_event_with_none_values(self):
        """Test handling event with None values."""
        event = {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "sub": None,
                            "email": None,
                            "auth_time": None
                        }
                    }
                }
            }
        }
        user_info = get_user_from_event(event)
        self.assertIsNone(user_info)

if __name__ == '__main__':
    unittest.main() 
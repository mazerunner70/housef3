"""
Unit tests for lambda utilities.
"""
import unittest
import json
from decimal import Decimal
from utils.lambda_utils import (
    DecimalEncoder,
    create_response,
    handle_error,
    optional_path_parameter,
    mandatory_path_parameter,
    optional_query_parameter,
    mandatory_query_parameter,
    optional_body_parameter,
    mandatory_body_parameter
)

class TestLambdaUtils(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.sample_event = {
            'pathParameters': {
                'id': '123',
                'empty': ''
            },
            'queryStringParameters': {
                'filter': 'active',
                'empty': ''
            },
            'body': json.dumps({
                'name': 'test',
                'value': 42,
                'empty': ''
            })
        }

    def test_decimal_encoder(self):
        """Test DecimalEncoder class."""
        # Test integer decimal
        data = {'amount': Decimal('100')}
        encoded = json.dumps(data, cls=DecimalEncoder)
        self.assertEqual(encoded, '{"amount": 100}')

        # Test float decimal
        data = {'amount': Decimal('100.50')}
        encoded = json.dumps(data, cls=DecimalEncoder)
        self.assertEqual(encoded, '{"amount": 100.5}')

        # Test regular types
        data = {'name': 'test', 'active': True}
        encoded = json.dumps(data, cls=DecimalEncoder)
        self.assertEqual(encoded, '{"name": "test", "active": true}')

        # Test unsupported type
        class UnsupportedType:
            pass
        data = {'unsupported': UnsupportedType()}
        with self.assertRaises(TypeError):
            json.dumps(data, cls=DecimalEncoder)

    def test_create_response(self):
        """Test create_response function."""
        # Test successful response
        response = create_response(200, {'message': 'success'})
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body']), {'message': 'success'})
        
        # Test response with decimal
        response = create_response(200, {'amount': Decimal('100.50')})
        self.assertEqual(json.loads(response['body']), {'amount': 100.50})
        
        # Test headers
        self.assertEqual(response['headers']['Content-Type'], 'application/json')
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        self.assertEqual(response['headers']['Access-Control-Allow-Headers'], 'Content-Type,Authorization')
        self.assertEqual(response['headers']['Access-Control-Allow-Methods'], 'GET,OPTIONS')

    def test_handle_error(self):
        """Test handle_error function."""
        # Test error response
        response = handle_error(400, 'Bad Request')
        self.assertEqual(response['statusCode'], 400)
        self.assertEqual(json.loads(response['body']), {'message': 'Bad Request'})
        
        # Test server error
        response = handle_error(500, 'Internal Server Error')
        self.assertEqual(response['statusCode'], 500)
        self.assertEqual(json.loads(response['body']), {'message': 'Internal Server Error'})

    def test_optional_path_parameter(self):
        """Test optional_path_parameter function."""
        # Test existing parameter
        result = optional_path_parameter(self.sample_event, 'id')
        self.assertEqual(result, '123')
        
        # Test missing parameter
        result = optional_path_parameter(self.sample_event, 'nonexistent')
        self.assertIsNone(result)
        
        # Test empty parameter
        result = optional_path_parameter(self.sample_event, 'empty')
        self.assertEqual(result, '')
        
        # Test with no pathParameters
        result = optional_path_parameter({}, 'id')
        self.assertIsNone(result)

    def test_mandatory_path_parameter(self):
        """Test mandatory_path_parameter function."""
        # Test existing parameter
        result = mandatory_path_parameter(self.sample_event, 'id')
        self.assertEqual(result, '123')
        
        # Test missing parameter
        with self.assertRaises(ValueError) as cm:
            mandatory_path_parameter(self.sample_event, 'nonexistent')
        self.assertIn('Path parameter nonexistent is required', str(cm.exception))
        
        # Test empty parameter name
        with self.assertRaises(ValueError) as cm:
            mandatory_path_parameter(self.sample_event, '')
        self.assertIn('Parameter name is required', str(cm.exception))
        
        # Test with no pathParameters
        with self.assertRaises(ValueError) as cm:
            mandatory_path_parameter({}, 'id')
        self.assertIn('Path parameter id is required', str(cm.exception))

    def test_optional_query_parameter(self):
        """Test optional_query_parameter function."""
        # Test existing parameter
        result = optional_query_parameter(self.sample_event, 'filter')
        self.assertEqual(result, 'active')
        
        # Test missing parameter
        result = optional_query_parameter(self.sample_event, 'nonexistent')
        self.assertIsNone(result)
        
        # Test empty parameter
        result = optional_query_parameter(self.sample_event, 'empty')
        self.assertEqual(result, '')
        
        # Test with no queryStringParameters
        result = optional_query_parameter({}, 'filter')
        self.assertIsNone(result)

    def test_mandatory_query_parameter(self):
        """Test mandatory_query_parameter function."""
        # Test existing parameter
        result = mandatory_query_parameter(self.sample_event, 'filter')
        self.assertEqual(result, 'active')
        
        # Test missing parameter
        with self.assertRaises(ValueError) as cm:
            mandatory_query_parameter(self.sample_event, 'nonexistent')
        self.assertIn('Query parameter nonexistent is required', str(cm.exception))
        
        # Test empty parameter name
        with self.assertRaises(ValueError) as cm:
            mandatory_query_parameter(self.sample_event, '')
        self.assertIn('Parameter name is required', str(cm.exception))
        
        # Test with no queryStringParameters
        with self.assertRaises(ValueError) as cm:
            mandatory_query_parameter({}, 'filter')
        self.assertIn('Query parameter filter is required', str(cm.exception))

    def test_optional_body_parameter(self):
        """Test optional_body_parameter function."""
        # Test existing parameter
        result = optional_body_parameter(self.sample_event, 'name')
        self.assertEqual(result, 'test')
        
        # Test missing parameter
        result = optional_body_parameter(self.sample_event, 'nonexistent')
        self.assertIsNone(result)
        
        # Test empty parameter
        result = optional_body_parameter(self.sample_event, 'empty')
        self.assertEqual(result, '')
        
        # Test with no body
        result = optional_body_parameter({}, 'name')
        self.assertIsNone(result)
        
        # Test with invalid JSON body
        event_with_invalid_body = {'body': 'invalid json'}
        with self.assertRaises(json.JSONDecodeError):
            optional_body_parameter(event_with_invalid_body, 'name')

    def test_mandatory_body_parameter(self):
        """Test mandatory_body_parameter function."""
        # Test existing parameter
        result = mandatory_body_parameter(self.sample_event, 'name')
        self.assertEqual(result, 'test')
        
        # Test missing parameter
        with self.assertRaises(ValueError) as cm:
            mandatory_body_parameter(self.sample_event, 'nonexistent')
        self.assertIn('Body parameter nonexistent is required', str(cm.exception))
        
        # Test with no body
        with self.assertRaises(ValueError) as cm:
            mandatory_body_parameter({}, 'name')
        self.assertIn('Body parameter name is required', str(cm.exception))
        
        # Test with invalid JSON body
        event_with_invalid_body = {'body': 'invalid json'}
        with self.assertRaises(json.JSONDecodeError):
            mandatory_body_parameter(event_with_invalid_body, 'name') 
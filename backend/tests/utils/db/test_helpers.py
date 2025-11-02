"""
Unit tests for database helper functions.
"""

import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

from utils.db.helpers import (
    # UUID conversion
    to_db_id,
    from_db_id,
    to_db_ids,
    from_db_ids,
    # Batch operations
    batch_delete_items,
    batch_write_items,
    batch_update_items,
    # Pagination
    paginated_query,
    paginated_scan,
    # Update expressions
    build_update_expression,
    build_condition_expression,
    # Timestamp helpers
    current_timestamp,
    timestamp_from_datetime,
    datetime_from_timestamp,
    # Decimal conversion
    decimal_to_float,
    float_to_decimal,
)


# ============================================================================
# UUID Conversion Tests
# ============================================================================

class TestUUIDConversion(unittest.TestCase):
    """Test UUID conversion helpers."""
    
    def test_to_db_id_with_uuid(self):
        """Test converting UUID to string."""
        test_uuid = uuid.UUID('12345678-1234-5678-1234-567812345678')
        result = to_db_id(test_uuid)
        self.assertEqual(result, '12345678-1234-5678-1234-567812345678')
    
    def test_to_db_id_with_string(self):
        """Test converting string UUID to string."""
        test_str = '12345678-1234-5678-1234-567812345678'
        result = to_db_id(test_str)
        self.assertEqual(result, test_str)
    
    def test_to_db_id_with_none(self):
        """Test converting None returns None."""
        result = to_db_id(None)
        self.assertIsNone(result)
    
    def test_from_db_id_with_valid_string(self):
        """Test converting valid UUID string to UUID."""
        test_str = '12345678-1234-5678-1234-567812345678'
        result = from_db_id(test_str)
        self.assertIsInstance(result, uuid.UUID)
        self.assertEqual(str(result), test_str)
    
    def test_from_db_id_with_none(self):
        """Test converting None returns None."""
        result = from_db_id(None)
        self.assertIsNone(result)
    
    def test_from_db_id_with_invalid_string(self):
        """Test converting invalid UUID string raises ValueError."""
        with self.assertRaises(ValueError):
            from_db_id('not-a-uuid')
    
    def test_to_db_ids(self):
        """Test converting list of UUIDs to strings."""
        uuids = [
            uuid.UUID('12345678-1234-5678-1234-567812345678'),
            uuid.UUID('87654321-4321-8765-4321-876543218765')
        ]
        result = to_db_ids(uuids)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(isinstance(x, str) for x in result))
        self.assertEqual(result[0], '12345678-1234-5678-1234-567812345678')
    
    def test_from_db_ids(self):
        """Test converting list of UUID strings to UUIDs."""
        strs = [
            '12345678-1234-5678-1234-567812345678',
            '87654321-4321-8765-4321-876543218765'
        ]
        result = from_db_ids(strs)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(isinstance(x, uuid.UUID) for x in result))
        self.assertEqual(str(result[0]), strs[0])


# ============================================================================
# Batch Operation Tests
# ============================================================================

class TestBatchOperations(unittest.TestCase):
    """Test batch operation helpers."""
    
    def test_batch_delete_items_empty_list(self):
        """Test batch delete with empty list."""
        mock_table = MagicMock()
        result = batch_delete_items(mock_table, [], lambda x: {'id': x.id})
        self.assertEqual(result, 0)
        mock_table.batch_writer.assert_not_called()
    
    def test_batch_delete_items_single_batch(self):
        """Test batch delete with items less than batch size."""
        mock_table = MagicMock()
        mock_table.table_name = 'test-table'
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = mock_writer
        
        items = [MagicMock(id=f'item-{i}') for i in range(10)]
        result = batch_delete_items(
            mock_table,
            items,
            lambda x: {'id': x.id}
        )
        
        self.assertEqual(result, 10)
        self.assertEqual(mock_writer.delete_item.call_count, 10)
    
    def test_batch_delete_items_multiple_batches(self):
        """Test batch delete with items requiring multiple batches."""
        mock_table = MagicMock()
        mock_table.table_name = 'test-table'
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = mock_writer
        
        # Create 60 items (should result in 3 batches of 25, 25, 10)
        items = [MagicMock(id=f'item-{i}') for i in range(60)]
        result = batch_delete_items(
            mock_table,
            items,
            lambda x: {'id': x.id},
            batch_size=25
        )
        
        self.assertEqual(result, 60)
        self.assertEqual(mock_writer.delete_item.call_count, 60)
        # Should have called batch_writer 3 times (once per batch)
        self.assertEqual(mock_table.batch_writer.call_count, 3)
    
    def test_batch_write_items_empty_list(self):
        """Test batch write with empty list."""
        mock_table = MagicMock()
        result = batch_write_items(mock_table, [])
        self.assertEqual(result, 0)
        mock_table.batch_writer.assert_not_called()
    
    def test_batch_write_items_single_batch(self):
        """Test batch write with items less than batch size."""
        mock_table = MagicMock()
        mock_table.table_name = 'test-table'
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = mock_writer
        
        items = [{'id': f'item-{i}', 'name': f'Name {i}'} for i in range(10)]
        result = batch_write_items(mock_table, items)
        
        self.assertEqual(result, 10)
        self.assertEqual(mock_writer.put_item.call_count, 10)
    
    def test_batch_update_items(self):
        """Test batch update items."""
        mock_table = MagicMock()
        mock_table.table_name = 'test-table'
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = mock_writer
        
        items = [MagicMock(id=f'item-{i}', status='pending') for i in range(5)]
        
        def updater(item):
            return {'id': item.id, 'status': 'completed'}
        
        result = batch_update_items(mock_table, items, updater)
        
        self.assertEqual(result, 5)
        self.assertEqual(mock_writer.put_item.call_count, 5)


# ============================================================================
# Pagination Tests
# ============================================================================

class TestPagination(unittest.TestCase):
    """Test pagination helpers."""
    
    def test_paginated_query_single_page(self):
        """Test paginated query with single page."""
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [{'id': 'item-1'}, {'id': 'item-2'}]
        }
        
        items, last_key = paginated_query(
            mock_table,
            {'KeyConditionExpression': 'userId = :userId'}
        )
        
        self.assertEqual(len(items), 2)
        self.assertIsNone(last_key)
        mock_table.query.assert_called_once()
    
    def test_paginated_query_multiple_pages(self):
        """Test paginated query with multiple pages."""
        mock_table = MagicMock()
        
        # Simulate two pages
        mock_table.query.side_effect = [
            {
                'Items': [{'id': 'item-1'}, {'id': 'item-2'}],
                'LastEvaluatedKey': {'id': 'item-2'}
            },
            {
                'Items': [{'id': 'item-3'}, {'id': 'item-4'}]
            }
        ]
        
        items, last_key = paginated_query(
            mock_table,
            {'KeyConditionExpression': 'userId = :userId'}
        )
        
        self.assertEqual(len(items), 4)
        self.assertIsNone(last_key)
        self.assertEqual(mock_table.query.call_count, 2)
    
    def test_paginated_query_with_transform(self):
        """Test paginated query with transform function."""
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [{'id': 'item-1', 'value': 1}, {'id': 'item-2', 'value': 2}]
        }
        
        def transform(item):
            return item['value'] * 2
        
        items, last_key = paginated_query(
            mock_table,
            {'KeyConditionExpression': 'userId = :userId'},
            transform=transform
        )
        
        self.assertEqual(items, [2, 4])
        self.assertIsNone(last_key)
    
    def test_paginated_query_with_max_items(self):
        """Test paginated query with max_items limit."""
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [{'id': f'item-{i}'} for i in range(100)],
            'LastEvaluatedKey': {'id': 'item-99'}
        }
        
        items, last_key = paginated_query(
            mock_table,
            {'KeyConditionExpression': 'userId = :userId'},
            max_items=50
        )
        
        self.assertEqual(len(items), 50)
        self.assertIsNotNone(last_key)
    
    def test_paginated_scan(self):
        """Test paginated scan."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [{'id': 'item-1'}, {'id': 'item-2'}]
        }
        
        items, last_key = paginated_scan(
            mock_table,
            {'FilterExpression': 'status = :status'}
        )
        
        self.assertEqual(len(items), 2)
        self.assertIsNone(last_key)
        mock_table.scan.assert_called_once()


# ============================================================================
# Update Expression Tests
# ============================================================================

class TestUpdateExpression(unittest.TestCase):
    """Test update expression builder."""
    
    def test_build_update_expression_basic(self):
        """Test building basic update expression."""
        updates = {'name': 'New Name', 'balance': Decimal('1000.00')}
        expr, names, values = build_update_expression(updates)
        
        self.assertIn('SET', expr)
        self.assertIn('#name', names)
        self.assertIn('#balance', names)
        self.assertEqual(names['#name'], 'name')
        self.assertEqual(names['#balance'], 'balance')
        self.assertEqual(values[':name'], 'New Name')
        self.assertEqual(values[':balance'], Decimal('1000.00'))
    
    def test_build_update_expression_with_timestamp(self):
        """Test building update expression with automatic timestamp."""
        updates = {'name': 'New Name'}
        _, names, values = build_update_expression(updates, timestamp_field='updatedAt')
        
        self.assertIn('#updatedAt', names)
        self.assertIn(':updatedAt', values)
        self.assertIsInstance(values[':updatedAt'], int)
    
    def test_build_update_expression_without_timestamp(self):
        """Test building update expression without timestamp."""
        updates = {'name': 'New Name'}
        _, names, values = build_update_expression(updates, timestamp_field=None)
        
        self.assertNotIn('#updatedAt', names)
        self.assertNotIn(':updatedAt', values)
    
    def test_build_update_expression_with_remove(self):
        """Test building update expression with REMOVE clause."""
        updates = {'name': 'New Name'}
        expr, names, values = build_update_expression(
            updates,
            remove_fields=['oldField', 'deprecated']
        )
        
        self.assertIn('SET', expr)
        self.assertIn('REMOVE', expr)
        self.assertIn('#oldField', names)
        self.assertIn('#deprecated', names)
        # Remove fields should not have values
        self.assertNotIn(':oldField', values)
    
    def test_build_update_expression_reserved_words(self):
        """Test update expression handles reserved words."""
        # 'status' is a DynamoDB reserved word
        updates = {'status': 'active', 'connection': 'stable'}
        _, names, _ = build_update_expression(updates, timestamp_field=None)
        
        self.assertIn('#status', names)
        self.assertEqual(names['#status'], 'status')
        self.assertIn('#connection', names)
        self.assertEqual(names['#connection'], 'connection')
    
    def test_build_update_expression_empty_raises(self):
        """Test building update expression with no updates raises ValueError."""
        with self.assertRaises(ValueError):
            build_update_expression({}, timestamp_field=None)
    
    def test_build_condition_expression(self):
        """Test building condition expression."""
        conditions = {'version': 5, 'status': 'active'}
        expr, names, values = build_condition_expression(conditions)
        
        self.assertIn('AND', expr)
        self.assertIn('#version', names)
        self.assertIn('#status', names)
        self.assertEqual(values[':version'], 5)
        self.assertEqual(values[':status'], 'active')
    
    def test_build_condition_expression_or(self):
        """Test building condition expression with OR operator."""
        conditions = {'status': 'active', 'enabled': True}
        expr, _, _ = build_condition_expression(conditions, operator='OR')
        
        self.assertIn('OR', expr)
        self.assertNotIn('AND', expr)
    
    def test_build_condition_expression_empty_raises(self):
        """Test building condition expression with no conditions raises ValueError."""
        with self.assertRaises(ValueError):
            build_condition_expression({})
    
    def test_build_condition_expression_invalid_operator(self):
        """Test building condition expression with invalid operator raises ValueError."""
        with self.assertRaises(ValueError):
            build_condition_expression({'field': 'value'}, operator='XOR')


# ============================================================================
# Timestamp Tests
# ============================================================================

class TestTimestamps(unittest.TestCase):
    """Test timestamp helper functions."""
    
    def test_current_timestamp(self):
        """Test current_timestamp returns integer milliseconds."""
        ts = current_timestamp()
        self.assertIsInstance(ts, int)
        self.assertGreater(ts, 0)
        # Should be close to current time (within 1 second)
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        self.assertLess(abs(ts - now_ts), 1000)
    
    def test_timestamp_from_datetime_with_tz(self):
        """Test converting timezone-aware datetime to timestamp."""
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        ts = timestamp_from_datetime(dt)
        self.assertIsInstance(ts, int)
        self.assertEqual(ts, int(dt.timestamp() * 1000))
    
    def test_timestamp_from_datetime_naive(self):
        """Test converting naive datetime to timestamp (assumes UTC)."""
        dt = datetime(2025, 1, 1, 12, 0, 0)
        ts = timestamp_from_datetime(dt)
        self.assertIsInstance(ts, int)
        # Should treat naive as UTC
        expected = int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        self.assertEqual(ts, expected)
    
    def test_datetime_from_timestamp(self):
        """Test converting timestamp to datetime."""
        # Known timestamp: 2025-01-01 12:00:00 UTC
        ts = 1735732800000
        dt = datetime_from_timestamp(ts)
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.hour, 12)
        self.assertEqual(dt.tzinfo, timezone.utc)
    
    def test_timestamp_roundtrip(self):
        """Test timestamp conversion roundtrip."""
        original_dt = datetime(2025, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        ts = timestamp_from_datetime(original_dt)
        converted_dt = datetime_from_timestamp(ts)
        
        # Should be equal (within microseconds precision)
        self.assertLess(abs((original_dt - converted_dt).total_seconds()), 0.001)


# ============================================================================
# Decimal Conversion Tests
# ============================================================================

class TestDecimalConversion(unittest.TestCase):
    """Test decimal conversion helpers."""
    
    def test_decimal_to_float_simple(self):
        """Test converting simple Decimal to float."""
        result = decimal_to_float(Decimal('123.45'))
        self.assertIsInstance(result, float)
        self.assertEqual(result, 123.45)
    
    def test_decimal_to_float_dict(self):
        """Test converting Decimal in dictionary."""
        data = {
            'price': Decimal('99.99'),
            'quantity': 5,
            'name': 'Product'
        }
        result = decimal_to_float(data)
        self.assertIsInstance(result['price'], float)
        self.assertEqual(result['price'], 99.99)
        self.assertEqual(result['quantity'], 5)
        self.assertEqual(result['name'], 'Product')
    
    def test_decimal_to_float_nested(self):
        """Test converting Decimal in nested structure."""
        data = {
            'items': [
                {'price': Decimal('10.00')},
                {'price': Decimal('20.00')}
            ],
            'total': Decimal('30.00')
        }
        result = decimal_to_float(data)
        self.assertIsInstance(result['items'][0]['price'], float)
        self.assertIsInstance(result['items'][1]['price'], float)
        self.assertIsInstance(result['total'], float)
    
    def test_decimal_to_float_list(self):
        """Test converting Decimal in list."""
        data = [Decimal('1.5'), Decimal('2.5'), Decimal('3.5')]
        result = decimal_to_float(data)
        self.assertTrue(all(isinstance(x, float) for x in result))
        self.assertEqual(result, [1.5, 2.5, 3.5])
    
    def test_decimal_to_float_none(self):
        """Test decimal_to_float with None."""
        result = decimal_to_float(None)
        self.assertIsNone(result)
    
    def test_float_to_decimal_simple(self):
        """Test converting simple float to Decimal."""
        result = float_to_decimal(123.45)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(float(result), 123.45)
    
    def test_float_to_decimal_dict(self):
        """Test converting float in dictionary."""
        data = {
            'price': 99.99,
            'quantity': 5,
            'name': 'Product'
        }
        result = float_to_decimal(data)
        self.assertIsInstance(result['price'], Decimal)
        self.assertEqual(float(result['price']), 99.99)
        self.assertEqual(result['quantity'], 5)
        self.assertEqual(result['name'], 'Product')
    
    def test_float_to_decimal_nested(self):
        """Test converting float in nested structure."""
        data = {
            'items': [
                {'price': 10.0},
                {'price': 20.0}
            ],
            'total': 30.0
        }
        result = float_to_decimal(data)
        self.assertIsInstance(result['items'][0]['price'], Decimal)
        self.assertIsInstance(result['items'][1]['price'], Decimal)
        self.assertIsInstance(result['total'], Decimal)
    
    def test_float_to_decimal_list(self):
        """Test converting float in list."""
        data = [1.5, 2.5, 3.5]
        result = float_to_decimal(data)
        self.assertTrue(all(isinstance(x, Decimal) for x in result))
    
    def test_decimal_conversion_roundtrip(self):
        """Test roundtrip conversion float -> Decimal -> float."""
        original = 123.456
        decimal_val = float_to_decimal(original)
        result = decimal_to_float(decimal_val)
        self.assertLess(abs(result - original), 0.0001)


if __name__ == '__main__':
    unittest.main()

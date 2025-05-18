import unittest
from datetime import datetime
import uuid
import json

from models.file_map import (
    FileMap,
    FieldMapping,
    validate_file_map_data
)


class TestFileMap(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.user_id = str(uuid.uuid4())
        self.file_map_id = str(uuid.uuid4())
        self.account_id = str(uuid.uuid4())
        self.name = "Bank CSV Import"
        self.description = "Mapping for bank CSV files"
        
        # Create sample field mappings
        self.mappings = [
            FieldMapping("date", "transactionDate"),
            FieldMapping("description", "description"),
            FieldMapping("amount", "amount", "abs"),
            FieldMapping("type", "transactionType")
        ]
        
        # Create a sample file map
        self.file_map = FileMap(
            file_map_id=self.file_map_id,
            user_id=self.user_id,
            name=self.name,
            mappings=self.mappings,
            account_id=self.account_id,
            description=self.description
        )

    def test_field_mapping_creation(self):
        """Test basic field mapping creation."""
        mapping = FieldMapping("source", "target", "transform")
        
        self.assertEqual(mapping.source_field, "source")
        self.assertEqual(mapping.target_field, "target")
        self.assertEqual(mapping.transformation, "transform")

    def test_field_mapping_to_dict(self):
        """Test field mapping dictionary conversion."""
        mapping = FieldMapping("source", "target", "transform")
        mapping_dict = mapping.to_dict()
        
        self.assertEqual(mapping_dict["sourceField"], "source")
        self.assertEqual(mapping_dict["targetField"], "target")
        self.assertEqual(mapping_dict["transformation"], "transform")
        
        # Test without transformation
        mapping = FieldMapping("source", "target")
        mapping_dict = mapping.to_dict()
        
        self.assertEqual(mapping_dict["sourceField"], "source")
        self.assertEqual(mapping_dict["targetField"], "target")
        self.assertNotIn("transformation", mapping_dict)

    def test_field_mapping_from_dict(self):
        """Test creating field mapping from dictionary."""
        mapping_dict = {
            "sourceField": "source",
            "targetField": "target",
            "transformation": "transform"
        }
        
        mapping = FieldMapping.from_dict(mapping_dict)
        self.assertEqual(mapping.source_field, "source")
        self.assertEqual(mapping.target_field, "target")
        self.assertEqual(mapping.transformation, "transform")
        
        # Test without transformation
        mapping_dict = {
            "sourceField": "source",
            "targetField": "target"
        }
        
        mapping = FieldMapping.from_dict(mapping_dict)
        self.assertEqual(mapping.source_field, "source")
        self.assertEqual(mapping.target_field, "target")
        self.assertIsNone(mapping.transformation)

    def test_file_map_creation(self):
        """Test basic file map creation."""
        self.assertEqual(self.file_map.file_map_id, self.file_map_id)
        self.assertEqual(self.file_map.user_id, self.user_id)
        self.assertEqual(self.file_map.name, self.name)
        self.assertEqual(len(self.file_map.mappings), 4)
        self.assertEqual(self.file_map.account_id, self.account_id)
        self.assertEqual(self.file_map.description, self.description)
        self.assertIsNotNone(self.file_map.created_at)
        self.assertIsNotNone(self.file_map.updated_at)

    def test_file_map_create_method(self):
        """Test FileMap.create class method."""
        mappings_dict = [
            {
                "sourceField": "date",
                "targetField": "transactionDate"
            },
            {
                "sourceField": "amount",
                "targetField": "amount",
                "transformation": "abs"
            }
        ]
        
        file_map = FileMap.create(
            user_id=self.user_id,
            name=self.name,
            mappings=mappings_dict,
            account_id=self.account_id,
            description=self.description
        )
        
        self.assertIsInstance(file_map, FileMap)
        self.assertEqual(file_map.user_id, self.user_id)
        self.assertEqual(file_map.name, self.name)
        self.assertEqual(len(file_map.mappings), 2)
        self.assertEqual(file_map.account_id, self.account_id)
        self.assertEqual(file_map.description, self.description)
        self.assertIsNotNone(file_map.file_map_id)

    def test_file_map_to_dict(self):
        """Test conversion to dictionary."""
        file_map_dict = self.file_map.to_dict()
        
        self.assertEqual(file_map_dict["fileMapId"], self.file_map_id)
        self.assertEqual(file_map_dict["userId"], self.user_id)
        self.assertEqual(file_map_dict["name"], self.name)
        self.assertEqual(len(file_map_dict["mappings"]), 4)
        self.assertEqual(file_map_dict["accountId"], self.account_id)
        self.assertEqual(file_map_dict["description"], self.description)
        self.assertIn("createdAt", file_map_dict)
        self.assertIn("updatedAt", file_map_dict)

    def test_file_map_from_dict(self):
        """Test creation from dictionary."""
        file_map_dict = self.file_map.to_dict()
        new_file_map = FileMap.from_dict(file_map_dict)
        
        self.assertEqual(new_file_map.file_map_id, self.file_map_id)
        self.assertEqual(new_file_map.user_id, self.user_id)
        self.assertEqual(new_file_map.name, self.name)
        self.assertEqual(len(new_file_map.mappings), 4)
        self.assertEqual(new_file_map.account_id, self.account_id)
        self.assertEqual(new_file_map.description, self.description)
        self.assertEqual(new_file_map.created_at, self.file_map.created_at)
        self.assertEqual(new_file_map.updated_at, self.file_map.updated_at)

    def test_file_map_update(self):
        """Test updating file map fields."""
        new_name = "Updated Map"
        new_description = "Updated description"
        new_mappings = [
            {
                "sourceField": "new_date",
                "targetField": "date"
            }
        ]
        
        original_updated_at = self.file_map.updated_at
        self.file_map.update(
            name=new_name,
            mappings=new_mappings,
            description=new_description
        )
        
        self.assertEqual(self.file_map.name, new_name)
        self.assertEqual(self.file_map.description, new_description)
        self.assertEqual(len(self.file_map.mappings), 1)
        self.assertEqual(self.file_map.mappings[0].source_field, "new_date")
        self.assertNotEqual(self.file_map.updated_at, original_updated_at)

    def test_validate_file_map_data(self):
        """Test file map data validation."""
        # Test valid data
        valid_data = {
            "userId": self.user_id,
            "name": self.name,
            "mappings": [
                {
                    "sourceField": "date",
                    "targetField": "transactionDate"
                }
            ]
        }
        validate_file_map_data(valid_data)  # Should not raise exception
        
        # Test missing required field
        invalid_data = valid_data.copy()
        del invalid_data["name"]
        with self.assertRaises(ValueError) as cm:
            validate_file_map_data(invalid_data)
        self.assertIn("Missing required field: name", str(cm.exception))
        
        # Test invalid mappings type
        invalid_data = valid_data.copy()
        invalid_data["mappings"] = "not a list"
        with self.assertRaises(ValueError) as cm:
            validate_file_map_data(invalid_data)
        self.assertIn("Mappings must be a list", str(cm.exception))
        
        # Test invalid mapping structure
        invalid_data = valid_data.copy()
        invalid_data["mappings"] = [{"invalid": "structure"}]
        with self.assertRaises(ValueError) as cm:
            validate_file_map_data(invalid_data)
        self.assertIn("Each mapping must have sourceField and targetField", str(cm.exception))
        
        # Test empty source field
        invalid_data = valid_data.copy()
        invalid_data["mappings"] = [
            {
                "sourceField": "",
                "targetField": "transactionDate"
            }
        ]
        with self.assertRaises(ValueError) as cm:
            validate_file_map_data(invalid_data)
        self.assertIn("sourceField must be a non-empty string", str(cm.exception))
        
        # Test empty target field
        invalid_data = valid_data.copy()
        invalid_data["mappings"] = [
            {
                "sourceField": "date",
                "targetField": ""
            }
        ]
        with self.assertRaises(ValueError) as cm:
            validate_file_map_data(invalid_data)
        self.assertIn("targetField must be a non-empty string", str(cm.exception))

    def test_empty_description_update(self):
        """Test updating with empty description."""
        self.file_map.update(description="")
        self.assertEqual(self.file_map.description, "")

    def test_partial_update(self):
        """Test partial update with only some fields."""
        original_name = self.file_map.name
        original_mappings = self.file_map.mappings
        
        self.file_map.update(description="New description")
        
        self.assertEqual(self.file_map.name, original_name)
        self.assertEqual(self.file_map.mappings, original_mappings)
        self.assertEqual(self.file_map.description, "New description")

if __name__ == '__main__':
    unittest.main() 
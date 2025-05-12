"""
Field mapping model for transaction file processing.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class FieldMapping:
    """Represents a mapping between a source field and a transaction field."""
    source_field: str
    target_field: str
    transformation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the field mapping to a dictionary."""
        result = {
            'sourceField': self.source_field,
            'targetField': self.target_field,
        }
        if self.transformation:
            result['transformation'] = self.transformation
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FieldMapping':
        """Create a FieldMapping instance from a dictionary."""
        return cls(
            source_field=data['sourceField'],
            target_field=data['targetField'],
            transformation=data.get('transformation')
        )

@dataclass
class FileMap:
    """Represents a field mapping configuration for transaction files."""
    field_map_id: str
    user_id: str
    name: str
    mappings: List[FieldMapping]
    account_id: Optional[str] = None
    description: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def create(cls, user_id: str, name: str, mappings: List[Dict[str, Any]], 
               account_id: Optional[str] = None, description: Optional[str] = None) -> 'FileMap':
        """Create a new FieldMap instance."""
        field_mappings = [FieldMapping.from_dict(m) for m in mappings]
        return cls(
            field_map_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            mappings=field_mappings,
            account_id=account_id,
            description=description
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the field map to a dictionary."""
        result = {
            'fieldMapId': self.field_map_id,
            'userId': self.user_id,
            'name': self.name,
            'mappings': [m.to_dict() for m in self.mappings],
            'createdAt': self.created_at,
            'updatedAt': self.updated_at
        }
        if self.account_id:
            result['accountId'] = self.account_id
        if self.description:
            result['description'] = self.description
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileMap':
        """Create a FieldMap instance from a dictionary."""
        mappings = [FieldMapping.from_dict(m) for m in data['mappings']]
        return cls(
            field_map_id=data['fieldMapId'],
            user_id=data['userId'],
            name=data['name'],
            mappings=mappings,
            account_id=data.get('accountId'),
            description=data.get('description'),
            created_at=data.get('createdAt', datetime.utcnow().isoformat()),
            updated_at=data.get('updatedAt', datetime.utcnow().isoformat())
        )

    def update(self, name: Optional[str] = None, mappings: Optional[List[Dict[str, Any]]] = None,
               description: Optional[str] = None) -> None:
        """Update the field map with new values."""
        if name:
            self.name = name
        if mappings:
            self.mappings = [FieldMapping.from_dict(m) for m in mappings]
        if description is not None:  # Allow empty string
            self.description = description
        self.updated_at = datetime.utcnow().isoformat()

def validate_file_map_data(data: Dict[str, Any]) -> None:
    """
    Validate file map data.
    
    Args:
        data: Dictionary containing field map data
        
    Raises:
        ValueError: If validation fails
    """
    required_fields = ['userId', 'name', 'mappings']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
            
    if not isinstance(data['mappings'], list):
        raise ValueError("Mappings must be a list")
    
    for mapping in data['mappings']:
        if not isinstance(mapping, dict):
            raise ValueError("Each mapping must be a dictionary")
            
        # Check for required mapping fields
        if 'sourceField' not in mapping or 'targetField' not in mapping:
            raise ValueError("Each mapping must have sourceField and targetField")
            
        # Validate field values
        if not isinstance(mapping['sourceField'], str) or not mapping['sourceField'].strip():
            raise ValueError("sourceField must be a non-empty string")
            
        if not isinstance(mapping['targetField'], str) or not mapping['targetField'].strip():
            raise ValueError("targetField must be a non-empty string")

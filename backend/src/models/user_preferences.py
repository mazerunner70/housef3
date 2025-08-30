"""
User preferences models for the financial account management system.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from typing_extensions import Self

# Configure logging
logger = logging.getLogger(__name__)


class UserPreferences(BaseModel):
    """
    Represents user preferences in the system using Pydantic.
    """
    user_id: str = Field(alias="userId")
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="createdAt")
    updated_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

    def update_preferences(self, update_data: 'UserPreferencesUpdate') -> bool:
        """
        Updates the user preferences with data from an UserPreferencesUpdate DTO.
        Returns True if any fields were changed, False otherwise.
        """
        updated_fields = False
        
        if update_data.preferences is not None:
            # Shallow merge - replace entire preference categories
            self.preferences.update(update_data.preferences)
            updated_fields = True
        
        if updated_fields:
            self.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        return updated_fields

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """
        Serializes the UserPreferences object to a dictionary suitable for DynamoDB.
        """
        return self.model_dump(mode='python', by_alias=True, exclude_none=True)

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """
        Deserializes a dictionary (from DynamoDB item) into a UserPreferences instance.
        """
        return cls.model_validate(data, context={'from_database': True})


class UserPreferencesCreate(BaseModel):
    """DTO for creating new user preferences."""
    user_id: str = Field(alias="userId")
    preferences: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class UserPreferencesUpdate(BaseModel):
    """DTO for updating existing user preferences. All fields are optional."""
    preferences: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


# Type definitions for common preference structures
class TransferPreferences(BaseModel):
    """Transfer-specific preferences."""
    default_date_range_days: Optional[int] = Field(default=7, alias="defaultDateRangeDays")
    last_used_date_ranges: Optional[list[int]] = Field(default_factory=lambda: [7, 14, 30], alias="lastUsedDateRanges")
    auto_expand_suggestion: Optional[bool] = Field(default=True, alias="autoExpandSuggestion")

    model_config = ConfigDict(populate_by_name=True)


class UIPreferences(BaseModel):
    """UI-specific preferences."""
    theme: Optional[str] = Field(default="light")
    compact_view: Optional[bool] = Field(default=False, alias="compactView")
    default_page_size: Optional[int] = Field(default=50, alias="defaultPageSize")

    model_config = ConfigDict(populate_by_name=True)


class TransactionPreferences(BaseModel):
    """Transaction-specific preferences."""
    default_sort_by: Optional[str] = Field(default="date", alias="defaultSortBy")
    default_sort_order: Optional[str] = Field(default="desc", alias="defaultSortOrder")
    default_page_size: Optional[int] = Field(default=50, alias="defaultPageSize")

    model_config = ConfigDict(populate_by_name=True)

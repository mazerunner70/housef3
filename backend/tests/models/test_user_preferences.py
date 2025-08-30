"""
Unit tests for user preferences models.
"""
import pytest
from datetime import datetime, timezone
from models.user_preferences import (
    UserPreferences,
    UserPreferencesCreate,
    UserPreferencesUpdate,
    TransferPreferences,
    UIPreferences,
    TransactionPreferences
)


class TestUserPreferences:
    """Test cases for UserPreferences model."""

    def test_create_user_preferences_with_defaults(self):
        """Test creating user preferences with default values."""
        prefs = UserPreferences(user_id="test-user-123")
        
        assert prefs.user_id == "test-user-123"
        assert prefs.preferences == {}
        assert isinstance(prefs.created_at, int)
        assert isinstance(prefs.updated_at, int)
        assert prefs.created_at == prefs.updated_at

    def test_create_user_preferences_with_initial_data(self):
        """Test creating user preferences with initial preference data."""
        initial_prefs = {
            "transfers": {
                "defaultDateRangeDays": 14,
                "lastUsedDateRanges": [14, 7, 30],
                "autoExpandSuggestion": True
            },
            "ui": {
                "theme": "dark",
                "compactView": True
            }
        }
        
        prefs = UserPreferences(
            user_id="test-user-123",
            preferences=initial_prefs
        )
        
        assert prefs.user_id == "test-user-123"
        assert prefs.preferences == initial_prefs
        assert prefs.preferences["transfers"]["defaultDateRangeDays"] == 14
        assert prefs.preferences["ui"]["theme"] == "dark"

    def test_update_preferences_replaces_entire_category(self):
        """Test that updating preferences replaces entire category while preserving others."""
        # Initial state with both transfers and UI preferences
        initial_prefs = {
            "transfers": {
                "defaultDateRangeDays": 7,
                "lastUsedDateRanges": [7, 14, 30],
                "autoExpandSuggestion": True
            },
            "ui": {
                "theme": "light",
                "compactView": False,
                "defaultPageSize": 50
            }
        }
        
        prefs = UserPreferences(
            user_id="test-user-123",
            preferences=initial_prefs
        )
        
        original_updated_at = prefs.updated_at
        
        # Update only transfers - should replace entire transfers object
        update_data = UserPreferencesUpdate(
            preferences={
                "transfers": {
                    "defaultDateRangeDays": 14,
                    "lastUsedDateRanges": [14, 7, 30],
                    "autoExpandSuggestion": False
                    # Note: completely different structure, missing some fields, added others
                }
            }
        )
        
        # Perform update
        result = prefs.update_preferences(update_data)
        
        # Verify update was successful
        assert result is True
        assert prefs.updated_at > original_updated_at
        
        # Verify transfers was completely replaced
        assert prefs.preferences["transfers"] == {
            "defaultDateRangeDays": 14,
            "lastUsedDateRanges": [14, 7, 30],
            "autoExpandSuggestion": False
        }
        
        # Verify UI preferences were completely preserved
        assert prefs.preferences["ui"] == {
            "theme": "light",
            "compactView": False,
            "defaultPageSize": 50
        }

    def test_update_preferences_adds_new_category(self):
        """Test that updating preferences can add new preference categories."""
        # Start with only transfers
        initial_prefs = {
            "transfers": {
                "defaultDateRangeDays": 7,
                "lastUsedDateRanges": [7, 14, 30]
            }
        }
        
        prefs = UserPreferences(
            user_id="test-user-123",
            preferences=initial_prefs
        )
        
        # Add UI preferences
        update_data = UserPreferencesUpdate(
            preferences={
                "ui": {
                    "theme": "dark",
                    "compactView": True
                }
            }
        )
        
        result = prefs.update_preferences(update_data)
        
        assert result is True
        
        # Verify both categories exist
        assert "transfers" in prefs.preferences
        assert "ui" in prefs.preferences
        
        # Verify transfers was preserved
        assert prefs.preferences["transfers"]["defaultDateRangeDays"] == 7
        
        # Verify UI was added
        assert prefs.preferences["ui"]["theme"] == "dark"

    def test_update_multiple_categories_at_once(self):
        """Test updating multiple preference categories in a single update."""
        initial_prefs = {
            "transfers": {
                "defaultDateRangeDays": 7
            },
            "ui": {
                "theme": "light"
            },
            "transactions": {
                "defaultSortBy": "date"
            }
        }
        
        prefs = UserPreferences(
            user_id="test-user-123",
            preferences=initial_prefs
        )
        
        # Update both transfers and UI, leave transactions alone
        update_data = UserPreferencesUpdate(
            preferences={
                "transfers": {
                    "defaultDateRangeDays": 30,
                    "lastUsedDateRanges": [30, 14, 7]
                },
                "ui": {
                    "theme": "dark",
                    "compactView": True,
                    "newFeature": "enabled"
                }
            }
        )
        
        result = prefs.update_preferences(update_data)
        
        assert result is True
        
        # Verify transfers was completely replaced
        assert prefs.preferences["transfers"] == {
            "defaultDateRangeDays": 30,
            "lastUsedDateRanges": [30, 14, 7]
        }
        
        # Verify UI was completely replaced
        assert prefs.preferences["ui"] == {
            "theme": "dark",
            "compactView": True,
            "newFeature": "enabled"
        }
        
        # Verify transactions was preserved
        assert prefs.preferences["transactions"] == {
            "defaultSortBy": "date"
        }

    def test_update_preferences_with_none_does_nothing(self):
        """Test that updating with None preferences does nothing."""
        initial_prefs = {
            "transfers": {
                "defaultDateRangeDays": 7
            }
        }
        
        prefs = UserPreferences(
            user_id="test-user-123",
            preferences=initial_prefs
        )
        
        original_updated_at = prefs.updated_at
        
        # Update with None
        update_data = UserPreferencesUpdate(preferences=None)
        result = prefs.update_preferences(update_data)
        
        assert result is False
        assert prefs.updated_at == original_updated_at
        assert prefs.preferences == initial_prefs

    def test_update_preferences_with_empty_dict(self):
        """Test that updating with empty dict still triggers update."""
        initial_prefs = {
            "transfers": {
                "defaultDateRangeDays": 7
            }
        }
        
        prefs = UserPreferences(
            user_id="test-user-123",
            preferences=initial_prefs
        )
        
        original_updated_at = prefs.updated_at
        
        # Update with empty dict
        update_data = UserPreferencesUpdate(preferences={})
        result = prefs.update_preferences(update_data)
        
        assert result is True
        assert prefs.updated_at > original_updated_at
        # Original preferences should be preserved since empty dict adds nothing
        assert prefs.preferences == initial_prefs

    def test_to_dynamodb_item(self):
        """Test serialization to DynamoDB format."""
        prefs = UserPreferences(
            user_id="test-user-123",
            preferences={
                "transfers": {
                    "defaultDateRangeDays": 14
                }
            }
        )
        
        item = prefs.to_dynamodb_item()
        
        assert item["userId"] == "test-user-123"
        assert item["preferences"]["transfers"]["defaultDateRangeDays"] == 14
        assert "createdAt" in item
        assert "updatedAt" in item

    def test_from_dynamodb_item(self):
        """Test deserialization from DynamoDB format."""
        item = {
            "userId": "test-user-123",
            "preferences": {
                "transfers": {
                    "defaultDateRangeDays": 14,
                    "lastUsedDateRanges": [14, 7, 30]
                }
            },
            "createdAt": 1704067200000,
            "updatedAt": 1704067300000
        }
        
        prefs = UserPreferences.from_dynamodb_item(item)
        
        assert prefs.user_id == "test-user-123"
        assert prefs.preferences["transfers"]["defaultDateRangeDays"] == 14
        assert prefs.created_at == 1704067200000
        assert prefs.updated_at == 1704067300000


class TestUserPreferencesCreate:
    """Test cases for UserPreferencesCreate DTO."""

    def test_create_with_minimal_data(self):
        """Test creating DTO with minimal required data."""
        create_dto = UserPreferencesCreate(user_id="test-user-123")
        
        assert create_dto.user_id == "test-user-123"
        assert create_dto.preferences == {}

    def test_create_with_preferences(self):
        """Test creating DTO with initial preferences."""
        prefs_data = {
            "transfers": {
                "defaultDateRangeDays": 14
            }
        }
        
        create_dto = UserPreferencesCreate(
            user_id="test-user-123",
            preferences=prefs_data
        )
        
        assert create_dto.user_id == "test-user-123"
        assert create_dto.preferences == prefs_data


class TestUserPreferencesUpdate:
    """Test cases for UserPreferencesUpdate DTO."""

    def test_update_with_none(self):
        """Test creating update DTO with None preferences."""
        update_dto = UserPreferencesUpdate()
        
        assert update_dto.preferences is None

    def test_update_with_preferences(self):
        """Test creating update DTO with preference data."""
        prefs_data = {
            "transfers": {
                "defaultDateRangeDays": 30
            }
        }
        
        update_dto = UserPreferencesUpdate(preferences=prefs_data)
        
        assert update_dto.preferences == prefs_data


class TestPreferenceTypeClasses:
    """Test cases for the preference type classes."""

    def test_transfer_preferences_defaults(self):
        """Test TransferPreferences with default values."""
        prefs = TransferPreferences()
        
        assert prefs.default_date_range_days == 7
        assert prefs.last_used_date_ranges == [7, 14, 30]
        assert prefs.auto_expand_suggestion is True

    def test_transfer_preferences_with_values(self):
        """Test TransferPreferences with custom values."""
        prefs = TransferPreferences(
            default_date_range_days=14,
            last_used_date_ranges=[14, 7, 30],
            auto_expand_suggestion=False
        )
        
        assert prefs.default_date_range_days == 14
        assert prefs.last_used_date_ranges == [14, 7, 30]
        assert prefs.auto_expand_suggestion is False

    def test_ui_preferences_defaults(self):
        """Test UIPreferences with default values."""
        prefs = UIPreferences()
        
        assert prefs.theme == "light"
        assert prefs.compact_view is False
        assert prefs.default_page_size == 50

    def test_transaction_preferences_defaults(self):
        """Test TransactionPreferences with default values."""
        prefs = TransactionPreferences()
        
        assert prefs.default_sort_by == "date"
        assert prefs.default_sort_order == "desc"
        assert prefs.default_page_size == 50


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_transfer_preferences_update_scenario(self):
        """Test the exact scenario used in the transfers page."""
        # User starts with default preferences
        prefs = UserPreferences(
            user_id="user-123",
            preferences={
                "transfers": {
                    "defaultDateRangeDays": 7,
                    "lastUsedDateRanges": [7, 14, 30],
                    "autoExpandSuggestion": True
                },
                "ui": {
                    "theme": "light"
                }
            }
        )
        
        # User changes date range to 14 days
        # Frontend sends complete transfer preferences object
        update_data = UserPreferencesUpdate(
            preferences={
                "transfers": {
                    "defaultDateRangeDays": 14,
                    "lastUsedDateRanges": [14, 7, 30],  # Reordered
                    "autoExpandSuggestion": True
                }
            }
        )
        
        prefs.update_preferences(update_data)
        
        # Verify transfers was updated
        assert prefs.preferences["transfers"]["defaultDateRangeDays"] == 14
        assert prefs.preferences["transfers"]["lastUsedDateRanges"] == [14, 7, 30]
        
        # Verify UI was preserved
        assert prefs.preferences["ui"]["theme"] == "light"

    def test_multiple_users_independent_preferences(self):
        """Test that different users have independent preferences."""
        user1_prefs = UserPreferences(
            user_id="user-1",
            preferences={
                "transfers": {"defaultDateRangeDays": 7}
            }
        )
        
        user2_prefs = UserPreferences(
            user_id="user-2", 
            preferences={
                "transfers": {"defaultDateRangeDays": 30}
            }
        )
        
        # Update user1's preferences
        user1_prefs.update_preferences(
            UserPreferencesUpdate(
                preferences={
                    "transfers": {"defaultDateRangeDays": 14}
                }
            )
        )
        
        # Verify user1 changed but user2 didn't
        assert user1_prefs.preferences["transfers"]["defaultDateRangeDays"] == 14
        assert user2_prefs.preferences["transfers"]["defaultDateRangeDays"] == 30

"""
User preferences service for managing user-specific settings and preferences.
"""
import os
import logging
from typing import Optional
from datetime import datetime, timezone

from ..models.user_preferences import UserPreferences, UserPreferencesCreate, UserPreferencesUpdate
from ..utils.db_utils import get_dynamodb_resource

# Configure logging
logger = logging.getLogger(__name__)


class UserPreferencesService:
    """Service for managing user preferences in DynamoDB."""
    
    def __init__(self):
        """Initialize the service with DynamoDB connection."""
        self.dynamodb = get_dynamodb_resource()
        table_name = os.environ.get('USER_PREFERENCES_TABLE')
        if not table_name:
            raise ValueError("USER_PREFERENCES_TABLE environment variable is not set")
        self.table = self.dynamodb.Table(table_name)
        logger.info(f"UserPreferencesService initialized with table: {table_name}")

    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """
        Get user preferences by user ID.
        
        Args:
            user_id: The user's ID
            
        Returns:
            UserPreferences object if found, None otherwise
            
        Raises:
            Exception: If there's an error accessing the database
        """
        try:
            logger.debug(f"Getting preferences for user: {user_id}")
            response = self.table.get_item(Key={'userId': user_id})
            
            if 'Item' in response:
                logger.debug(f"Found preferences for user: {user_id}")
                return UserPreferences.from_dynamodb_item(response['Item'])
            
            logger.debug(f"No preferences found for user: {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting user preferences for {user_id}: {str(e)}", exc_info=True)
            raise

    async def create_user_preferences(self, create_data: UserPreferencesCreate) -> UserPreferences:
        """
        Create new user preferences.
        
        Args:
            create_data: UserPreferencesCreate DTO with user preferences data
            
        Returns:
            Created UserPreferences object
            
        Raises:
            Exception: If there's an error creating the preferences
        """
        try:
            logger.debug(f"Creating preferences for user: {create_data.user_id}")
            
            # Check if preferences already exist
            existing = await self.get_user_preferences(create_data.user_id)
            if existing:
                logger.warning(f"Preferences already exist for user: {create_data.user_id}")
                raise ValueError(f"Preferences already exist for user: {create_data.user_id}")
            
            # Create new preferences
            preferences = UserPreferences(
                user_id=create_data.user_id,
                preferences=create_data.preferences
            )
            
            # Save to DynamoDB
            self.table.put_item(Item=preferences.to_dynamodb_item())
            
            logger.info(f"Created preferences for user: {create_data.user_id}")
            return preferences
            
        except Exception as e:
            logger.error(f"Error creating user preferences for {create_data.user_id}: {str(e)}", exc_info=True)
            raise

    async def update_user_preferences(self, user_id: str, update_data: UserPreferencesUpdate) -> UserPreferences:
        """
        Update or create user preferences.
        
        Args:
            user_id: The user's ID
            update_data: UserPreferencesUpdate DTO with preference updates
            
        Returns:
            Updated UserPreferences object
            
        Raises:
            Exception: If there's an error updating the preferences
        """
        try:
            logger.debug(f"Updating preferences for user: {user_id}")
            
            # Get existing preferences
            existing = await self.get_user_preferences(user_id)
            
            if existing:
                # Update existing preferences
                existing.update_preferences(update_data)
                preferences = existing
                logger.debug(f"Updated existing preferences for user: {user_id}")
            else:
                # Create new preferences if none exist
                preferences = UserPreferences(
                    user_id=user_id,
                    preferences=update_data.preferences or {}
                )
                logger.debug(f"Created new preferences for user: {user_id}")
            
            # Save to DynamoDB
            self.table.put_item(Item=preferences.to_dynamodb_item())
            
            logger.info(f"Saved preferences for user: {user_id}")
            return preferences
            
        except Exception as e:
            logger.error(f"Error updating user preferences for {user_id}: {str(e)}", exc_info=True)
            raise

    async def delete_user_preferences(self, user_id: str) -> bool:
        """
        Delete user preferences.
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if preferences were deleted, False if they didn't exist
            
        Raises:
            Exception: If there's an error deleting the preferences
        """
        try:
            logger.debug(f"Deleting preferences for user: {user_id}")
            
            # Check if preferences exist first
            existing = await self.get_user_preferences(user_id)
            if not existing:
                logger.debug(f"No preferences to delete for user: {user_id}")
                return False
            
            # Delete from DynamoDB
            self.table.delete_item(Key={'userId': user_id})
            
            logger.info(f"Deleted preferences for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user preferences for {user_id}: {str(e)}", exc_info=True)
            raise

    async def get_transfer_preferences(self, user_id: str) -> dict:
        """
        Get transfer-specific preferences for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dictionary with transfer preferences or defaults
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            
            if preferences and 'transfers' in preferences.preferences:
                return preferences.preferences['transfers']
            
            # Return default transfer preferences
            return {
                'defaultDateRangeDays': 7,
                'lastUsedDateRanges': [7, 14, 30],
                'autoExpandSuggestion': True
            }
            
        except Exception as e:
            logger.error(f"Error getting transfer preferences for {user_id}: {str(e)}", exc_info=True)
            # Return defaults on error
            return {
                'defaultDateRangeDays': 7,
                'lastUsedDateRanges': [7, 14, 30],
                'autoExpandSuggestion': True
            }

    async def update_transfer_preferences(self, user_id: str, transfer_prefs: dict) -> UserPreferences:
        """
        Update transfer-specific preferences for a user.
        
        Args:
            user_id: The user's ID
            transfer_prefs: Dictionary with transfer preference updates
            
        Returns:
            Updated UserPreferences object
        """
        update_data = UserPreferencesUpdate(
            preferences={'transfers': transfer_prefs}
        )
        return await self.update_user_preferences(user_id, update_data)

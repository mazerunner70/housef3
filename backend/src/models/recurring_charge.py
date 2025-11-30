"""
Recurring Charge Detection Models.

This module provides Pydantic models for ML-based recurring charge detection,
including pattern representation, predictions, and related enums.
"""

import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing_extensions import Self

logger = logging.getLogger(__name__)

# Constants
TIMESTAMP_ERROR_MESSAGE = "Timestamp must be a positive integer representing milliseconds since epoch"
DAY_OF_WEEK_ERROR_MESSAGE = "day_of_week must be between 0 (Monday) and 6 (Sunday)"
DAY_OF_MONTH_ERROR_MESSAGE = "day_of_month must be between 1 and 31"


class RecurrenceFrequency(str, Enum):
    """Frequency of recurring charges."""
    DAILY = "daily"                   # ~1 day intervals
    WEEKLY = "weekly"                 # ~7 day intervals
    BI_WEEKLY = "bi_weekly"           # ~14 day intervals
    SEMI_MONTHLY = "semi_monthly"     # ~15 day intervals (1st & 15th)
    MONTHLY = "monthly"               # ~30 day intervals
    BI_MONTHLY = "bi_monthly"         # ~60 day intervals
    QUARTERLY = "quarterly"           # ~90 day intervals
    SEMI_ANNUALLY = "semi_annually"   # ~182 day intervals
    ANNUALLY = "annually"             # ~365 day intervals
    IRREGULAR = "irregular"           # No clear pattern


class TemporalPatternType(str, Enum):
    """Type of temporal pattern detected in recurring charges."""
    DAY_OF_WEEK = "day_of_week"              # e.g., every Tuesday
    DAY_OF_MONTH = "day_of_month"            # e.g., 15th of each month
    FIRST_WORKING_DAY = "first_working_day"  # First business day
    LAST_WORKING_DAY = "last_working_day"    # Last business day
    FIRST_DAY_OF_MONTH = "first_day_of_month" # 1st of month
    LAST_DAY_OF_MONTH = "last_day_of_month"  # End of month
    WEEKEND = "weekend"                      # Saturday or Sunday
    WEEKDAY = "weekday"                      # Monday-Friday
    FLEXIBLE = "flexible"                    # No strict temporal pattern


class PatternStatus(str, Enum):
    """Lifecycle status of a recurring charge pattern."""
    DETECTED = "detected"      # ML detected, awaiting review
    CONFIRMED = "confirmed"    # User confirmed, criteria validated
    ACTIVE = "active"          # Actively categorizing transactions
    REJECTED = "rejected"      # User rejected pattern
    PAUSED = "paused"          # Temporarily disabled


class RecurringChargePattern(BaseModel):
    """
    Represents a detected recurring charge pattern.
    
    This model captures all aspects of a recurring pattern including:
    - Pattern identification (merchant, frequency, temporal constraints)
    - Amount patterns and tolerances
    - ML features and metadata
    - Category associations
    """
    pattern_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="patternId")
    user_id: str = Field(alias="userId")
    
    # Pattern identification
    merchant_pattern: str = Field(alias="merchantPattern")  # Regex or substring for matching
    frequency: RecurrenceFrequency
    temporal_pattern_type: TemporalPatternType = Field(alias="temporalPatternType")
    
    # Temporal constraints
    day_of_week: Optional[int] = Field(default=None, alias="dayOfWeek", ge=0, le=6)
    day_of_month: Optional[int] = Field(default=None, alias="dayOfMonth", ge=1, le=31)
    tolerance_days: int = Field(default=2, alias="toleranceDays", ge=0)
    
    # Amount constraints
    amount_mean: Decimal = Field(alias="amountMean")
    amount_std: Decimal = Field(alias="amountStd")
    amount_min: Decimal = Field(alias="amountMin")
    amount_max: Decimal = Field(alias="amountMax")
    amount_tolerance_pct: Decimal = Field(default=Decimal("10.0"), alias="amountTolerancePct", ge=0.0, le=100.0)
    
    # Pattern metadata
    confidence_score: Decimal = Field(alias="confidenceScore", ge=0.0, le=1.0)
    transaction_count: int = Field(alias="transactionCount", ge=0)
    first_occurrence: int = Field(alias="firstOccurrence")
    last_occurrence: int = Field(alias="lastOccurrence")
    
    # ML features
    feature_vector: Optional[List[Decimal]] = Field(default=None, alias="featureVector")
    cluster_id: Optional[int] = Field(default=None, alias="clusterId")
    
    # Associated category
    suggested_category_id: Optional[uuid.UUID] = Field(default=None, alias="suggestedCategoryId")
    auto_categorize: bool = Field(default=False, alias="autoCategorize")
    
    # Phase 1: Pattern Review - Store matched transaction IDs from DBSCAN cluster
    matched_transaction_ids: Optional[List[uuid.UUID]] = Field(
        default=None,
        alias="matchedTransactionIds",
        description="Transaction IDs used to create this pattern (from DBSCAN cluster)"
    )
    
    # Phase 1: Pattern lifecycle status
    status: PatternStatus = Field(
        default=PatternStatus.DETECTED,
        description="Current lifecycle status of the pattern"
    )
    
    # Phase 1: Validation metadata
    criteria_validated: bool = Field(
        default=False,
        alias="criteriaValidated",
        description="Whether criteria have been validated against original matches"
    )
    
    criteria_validation_errors: Optional[List[str]] = Field(
        default=None,
        alias="criteriaValidationErrors",
        description="Any validation warnings or errors"
    )
    
    # Phase 1: User review metadata
    reviewed_by: Optional[str] = Field(
        default=None,
        alias="reviewedBy",
        description="User ID who reviewed the pattern"
    )
    
    reviewed_at: Optional[int] = Field(
        default=None,
        alias="reviewedAt",
        description="Timestamp when pattern was reviewed"
    )
    
    # Status
    active: bool = Field(
        default=False,  # Changed: patterns start inactive until activated
        description="Whether to apply this pattern for auto-categorization"
    )
    created_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000),
        alias="createdAt"
    )
    updated_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000),
        alias="updatedAt"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            Decimal: str,
            uuid.UUID: str
        },
        use_enum_values=False  # Preserve enum objects (not strings) for type safety
    )

    @field_validator('first_occurrence', 'last_occurrence', 'created_at', 'updated_at', 'reviewed_at')
    @classmethod
    def check_positive_timestamp(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError(TIMESTAMP_ERROR_MESSAGE)
        return v

    @field_validator('day_of_week')
    @classmethod
    def validate_day_of_week(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 6):
            raise ValueError(DAY_OF_WEEK_ERROR_MESSAGE)
        return v

    @field_validator('day_of_month')
    @classmethod
    def validate_day_of_month(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 31):
            raise ValueError(DAY_OF_MONTH_ERROR_MESSAGE)
        return v

    def update_model_details(self, update_data: 'RecurringChargePatternUpdate') -> bool:
        """
        Updates the pattern with data from a RecurringChargePatternUpdate DTO.
        Returns True if any fields were changed, False otherwise.
        """
        updated_fields = False
        
        # Get only the fields that were actually set (not None)
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True, by_alias=False)
        
        # Handle each field individually to preserve object types
        for key, value in update_dict.items():
            if key not in ["pattern_id", "user_id", "created_at"] and hasattr(self, key):
                if getattr(self, key) != value:
                    setattr(self, key, value)
                    updated_fields = True
        
        if updated_fields:
            self.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        return updated_fields

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Ensure all UUID fields are converted to strings for DynamoDB
        for key, value in data.items():
            if isinstance(value, uuid.UUID):
                data[key] = str(value)
        
        # Convert list of UUIDs to list of strings
        if 'matchedTransactionIds' in data and data['matchedTransactionIds'] is not None:
            data['matchedTransactionIds'] = [str(tid) for tid in data['matchedTransactionIds']]
        
        # Convert boolean fields to 'true'/'false' strings for DynamoDB GSI compatibility
        # DynamoDB GSIs require string types for boolean attributes to enable indexing
        if 'active' in data:
            data['active'] = 'true' if data['active'] else 'false'
        if 'autoCategorize' in data:
            data['autoCategorize'] = 'true' if data['autoCategorize'] else 'false'
        if 'criteriaValidated' in data:
            data['criteriaValidated'] = 'true' if data['criteriaValidated'] else 'false'
        
        # No float-to-Decimal conversion needed - all numeric fields are already Decimal
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """Create from DynamoDB item data."""
        converted_data = data.copy()
        
        # Convert Decimal fields to appropriate types
        int_fields = ['dayOfWeek', 'dayOfMonth', 'toleranceDays', 'transactionCount', 
                      'firstOccurrence', 'lastOccurrence', 'createdAt', 'updatedAt', 
                      'reviewedAt', 'clusterId']
        for field in int_fields:
            if field in converted_data and converted_data[field] is not None and isinstance(converted_data[field], Decimal):
                converted_data[field] = int(converted_data[field])
        
        # Convert UUID string fields to UUID objects
        uuid_fields = ['patternId', 'suggestedCategoryId']
        for field in uuid_fields:
            if field in converted_data and isinstance(converted_data[field], str):
                try:
                    converted_data[field] = uuid.UUID(converted_data[field])
                except ValueError:
                    pass
        
        # Convert list of UUID strings to list of UUID objects
        if 'matchedTransactionIds' in converted_data and converted_data['matchedTransactionIds'] is not None:
            converted_ids = []
            for tid in converted_data['matchedTransactionIds']:
                if isinstance(tid, str):
                    try:
                        converted_ids.append(uuid.UUID(tid))
                    except ValueError:
                        pass
                elif isinstance(tid, uuid.UUID):
                    converted_ids.append(tid)
            converted_data['matchedTransactionIds'] = converted_ids if converted_ids else None
        
        # Convert enum string fields to enum objects
        if 'frequency' in converted_data and isinstance(converted_data['frequency'], str):
            try:
                converted_data['frequency'] = RecurrenceFrequency(converted_data['frequency'])
            except ValueError:
                logger.warning(f"Invalid RecurrenceFrequency value: {converted_data['frequency']}")
                converted_data['frequency'] = RecurrenceFrequency.IRREGULAR
        
        if 'temporalPatternType' in converted_data and isinstance(converted_data['temporalPatternType'], str):
            try:
                converted_data['temporalPatternType'] = TemporalPatternType(converted_data['temporalPatternType'])
            except ValueError:
                logger.warning(f"Invalid TemporalPatternType value: {converted_data['temporalPatternType']}")
                converted_data['temporalPatternType'] = TemporalPatternType.FLEXIBLE
        
        if 'status' in converted_data and isinstance(converted_data['status'], str):
            try:
                converted_data['status'] = PatternStatus(converted_data['status'])
            except ValueError:
                logger.warning(f"Invalid PatternStatus value: {converted_data['status']}")
                converted_data['status'] = PatternStatus.DETECTED
        
        # Convert boolean string fields to boolean objects
        if 'active' in converted_data and isinstance(converted_data['active'], str):
            converted_data['active'] = converted_data['active'].lower() == 'true'
        if 'autoCategorize' in converted_data and isinstance(converted_data['autoCategorize'], str):
            converted_data['autoCategorize'] = converted_data['autoCategorize'].lower() == 'true'
        if 'criteriaValidated' in converted_data and isinstance(converted_data['criteriaValidated'], str):
            converted_data['criteriaValidated'] = converted_data['criteriaValidated'].lower() == 'true'
        
        return cls.model_validate(converted_data)


class PatternCriteriaValidation(BaseModel):
    """Result of validating pattern criteria against original matched transactions."""
    
    pattern_id: uuid.UUID = Field(alias="patternId")
    is_valid: bool = Field(alias="isValid", description="All original transactions match criteria")
    
    # Statistics
    original_count: int = Field(alias="originalCount", description="Number of original matched transactions")
    criteria_match_count: int = Field(alias="criteriaMatchCount", description="Number of transactions matching criteria")
    
    # Matching analysis
    all_original_match_criteria: bool = Field(
        alias="allOriginalMatchCriteria",
        description="All original transactions match the pattern criteria"
    )
    
    no_false_positives: bool = Field(
        alias="noFalsePositives", 
        description="Criteria don't match extra transactions beyond original cluster"
    )
    
    perfect_match: bool = Field(
        alias="perfectMatch",
        description="Criteria exactly match original cluster, no more, no less"
    )
    
    # Transaction ID analysis
    missing_from_criteria: List[uuid.UUID] = Field(
        default_factory=list,
        alias="missingFromCriteria",
        description="Original transactions that don't match criteria (false negatives)"
    )
    
    extra_from_criteria: List[uuid.UUID] = Field(
        default_factory=list,
        alias="extraFromCriteria",
        description="Non-original transactions that match criteria (false positives)"
    )
    
    # Recommendations
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={uuid.UUID: str}
    )


class PatternReviewAction(BaseModel):
    """User action when reviewing a pattern."""
    
    pattern_id: uuid.UUID = Field(alias="patternId")
    user_id: str = Field(alias="userId")
    action: str = Field(description="confirm, reject, or edit")
    
    # Optional edits to pattern criteria
    edited_merchant_pattern: Optional[str] = Field(default=None, alias="editedMerchantPattern")
    edited_amount_tolerance_pct: Optional[Decimal] = Field(default=None, alias="editedAmountTolerancePct")
    edited_tolerance_days: Optional[int] = Field(default=None, alias="editedToleranceDays")
    edited_suggested_category_id: Optional[uuid.UUID] = Field(default=None, alias="editedSuggestedCategoryId")
    
    # User notes
    notes: Optional[str] = Field(default=None, description="User's review notes")
    
    # Whether to activate immediately after confirmation
    activate_immediately: bool = Field(default=False, alias="activateImmediately")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            Decimal: str,
            uuid.UUID: str
        }
    )

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid_actions = {'confirm', 'reject', 'edit'}
        if v not in valid_actions:
            raise ValueError(f"action must be one of {valid_actions}")
        return v


class RecurringChargePatternCreate(BaseModel):
    """
    Data Transfer Object for creating a new recurring charge pattern.
    
    This DTO contains all required fields for pattern creation except
    auto-generated fields (pattern_id, created_at, updated_at).
    """
    user_id: str = Field(alias="userId")
    
    # Pattern identification
    merchant_pattern: str = Field(alias="merchantPattern")  # Regex or substring for matching
    frequency: RecurrenceFrequency
    temporal_pattern_type: TemporalPatternType = Field(alias="temporalPatternType")
    
    # Temporal constraints
    day_of_week: Optional[int] = Field(default=None, alias="dayOfWeek", ge=0, le=6)
    day_of_month: Optional[int] = Field(default=None, alias="dayOfMonth", ge=1, le=31)
    tolerance_days: int = Field(default=2, alias="toleranceDays", ge=0)
    
    # Amount constraints
    amount_mean: Decimal = Field(alias="amountMean")
    amount_std: Decimal = Field(alias="amountStd")
    amount_min: Decimal = Field(alias="amountMin")
    amount_max: Decimal = Field(alias="amountMax")
    amount_tolerance_pct: Decimal = Field(default=Decimal("10.0"), alias="amountTolerancePct", ge=0.0, le=100.0)
    
    # Pattern metadata
    confidence_score: Decimal = Field(alias="confidenceScore", ge=0.0, le=1.0)
    transaction_count: int = Field(alias="transactionCount", ge=0)
    first_occurrence: int = Field(alias="firstOccurrence")
    last_occurrence: int = Field(alias="lastOccurrence")
    
    # ML features
    feature_vector: Optional[List[Decimal]] = Field(default=None, alias="featureVector")
    cluster_id: Optional[int] = Field(default=None, alias="clusterId")
    
    # Associated category
    suggested_category_id: Optional[uuid.UUID] = Field(default=None, alias="suggestedCategoryId")
    auto_categorize: bool = Field(default=False, alias="autoCategorize")
    
    # Phase 1: Pattern Review
    matched_transaction_ids: Optional[List[uuid.UUID]] = Field(
        default=None,
        alias="matchedTransactionIds",
        description="Transaction IDs used to create this pattern (from DBSCAN cluster)"
    )
    
    status: PatternStatus = Field(
        default=PatternStatus.DETECTED,
        description="Current lifecycle status of the pattern"
    )
    
    # Status
    active: bool = Field(default=False)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            Decimal: str,
            uuid.UUID: str
        },
        use_enum_values=False  # Preserve enum objects (not strings) for type safety
    )

    @field_validator('first_occurrence', 'last_occurrence')
    @classmethod
    def check_positive_timestamp(cls, v: int) -> int:
        if v < 0:
            raise ValueError(TIMESTAMP_ERROR_MESSAGE)
        return v

    @field_validator('day_of_week')
    @classmethod
    def validate_day_of_week(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 6):
            raise ValueError(DAY_OF_WEEK_ERROR_MESSAGE)
        return v

    @field_validator('day_of_month')
    @classmethod
    def validate_day_of_month(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 31):
            raise ValueError(DAY_OF_MONTH_ERROR_MESSAGE)
        return v


class RecurringChargePatternUpdate(BaseModel):
    """
    Data Transfer Object for updating a recurring charge pattern.
    
    All fields are optional to allow partial updates.
    """
    # Pattern identification
    merchant_pattern: Optional[str] = Field(default=None, alias="merchantPattern")
    frequency: Optional[RecurrenceFrequency] = None
    temporal_pattern_type: Optional[TemporalPatternType] = Field(default=None, alias="temporalPatternType")
    
    # Temporal constraints
    day_of_week: Optional[int] = Field(default=None, alias="dayOfWeek", ge=0, le=6)
    day_of_month: Optional[int] = Field(default=None, alias="dayOfMonth", ge=1, le=31)
    tolerance_days: Optional[int] = Field(default=None, alias="toleranceDays", ge=0)
    
    # Amount constraints
    amount_mean: Optional[Decimal] = Field(default=None, alias="amountMean")
    amount_std: Optional[Decimal] = Field(default=None, alias="amountStd")
    amount_min: Optional[Decimal] = Field(default=None, alias="amountMin")
    amount_max: Optional[Decimal] = Field(default=None, alias="amountMax")
    amount_tolerance_pct: Optional[Decimal] = Field(default=None, alias="amountTolerancePct", ge=0.0, le=100.0)
    
    # Pattern metadata
    confidence_score: Optional[Decimal] = Field(default=None, alias="confidenceScore", ge=0.0, le=1.0)
    transaction_count: Optional[int] = Field(default=None, alias="transactionCount", ge=0)
    first_occurrence: Optional[int] = Field(default=None, alias="firstOccurrence")
    last_occurrence: Optional[int] = Field(default=None, alias="lastOccurrence")
    
    # ML features
    feature_vector: Optional[List[Decimal]] = Field(default=None, alias="featureVector")
    cluster_id: Optional[int] = Field(default=None, alias="clusterId")
    
    # Associated category
    suggested_category_id: Optional[uuid.UUID] = Field(default=None, alias="suggestedCategoryId")
    auto_categorize: Optional[bool] = Field(default=None, alias="autoCategorize")
    
    # Status
    active: Optional[bool] = None

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            Decimal: str,
            uuid.UUID: str
        },
        use_enum_values=False  # Preserve enum objects (not strings) for type safety
    )

    @field_validator('first_occurrence', 'last_occurrence')
    @classmethod
    def check_positive_timestamp(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError(TIMESTAMP_ERROR_MESSAGE)
        return v

    @field_validator('day_of_week')
    @classmethod
    def validate_day_of_week(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 6):
            raise ValueError(DAY_OF_WEEK_ERROR_MESSAGE)
        return v

    @field_validator('day_of_month')
    @classmethod
    def validate_day_of_month(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 31):
            raise ValueError(DAY_OF_MONTH_ERROR_MESSAGE)
        return v


class RecurringChargePrediction(BaseModel):
    """
    Prediction for next occurrence of a recurring charge.
    
    Used to forecast when a recurring charge will next appear and
    what amount to expect.
    """
    pattern_id: uuid.UUID = Field(alias="patternId")
    next_expected_date: int = Field(alias="nextExpectedDate")  # Timestamp (ms)
    expected_amount: Decimal = Field(alias="expectedAmount")
    confidence: Decimal = Field(ge=0.0, le=1.0)  # 0.0-1.0
    days_until_due: int = Field(alias="daysUntilDue")
    amount_range: Dict[str, Decimal] = Field(alias="amountRange")  # {"min": X, "max": Y}

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            Decimal: str,
            uuid.UUID: str
        }
    )

    @field_validator('next_expected_date')
    @classmethod
    def check_positive_timestamp(cls, v: int) -> int:
        if v < 0:
            raise ValueError(TIMESTAMP_ERROR_MESSAGE)
        return v

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: Decimal) -> Decimal:
        if not (Decimal("0.0") <= v <= Decimal("1.0")):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Ensure UUID fields are converted to strings
        if isinstance(data.get('patternId'), uuid.UUID):
            data['patternId'] = str(data['patternId'])
        
        # No float-to-Decimal conversion needed - confidence is already Decimal
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """Create from DynamoDB item data."""
        converted_data = data.copy()
        
        # Convert Decimal to int for timestamp fields
        int_fields = ['nextExpectedDate', 'daysUntilDue']
        for field in int_fields:
            if field in converted_data and converted_data[field] is not None:
                if isinstance(converted_data[field], Decimal):
                    converted_data[field] = int(converted_data[field])
        
        # Note: confidence remains as Decimal - no conversion needed
        
        # Convert UUID string to UUID object
        if 'patternId' in converted_data and isinstance(converted_data['patternId'], str):
            try:
                converted_data['patternId'] = uuid.UUID(converted_data['patternId'])
            except ValueError:
                pass
        
        # amount_range and expected_amount remain as Decimal (DynamoDB native)
        
        return cls.model_validate(converted_data)


class RecurringChargePredictionCreate(BaseModel):
    """Data Transfer Object for creating a new recurring charge prediction."""
    pattern_id: uuid.UUID = Field(alias="patternId")
    next_expected_date: int = Field(alias="nextExpectedDate")  # Timestamp (ms)
    expected_amount: Decimal = Field(alias="expectedAmount")
    confidence: Decimal = Field(ge=0.0, le=1.0)  # 0.0-1.0
    days_until_due: int = Field(alias="daysUntilDue")
    amount_range: Dict[str, Decimal] = Field(alias="amountRange")  # {"min": X, "max": Y}

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            Decimal: str,
            uuid.UUID: str
        }
    )

    @field_validator('next_expected_date')
    @classmethod
    def check_positive_timestamp(cls, v: int) -> int:
        if v < 0:
            raise ValueError(TIMESTAMP_ERROR_MESSAGE)
        return v

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: Decimal) -> Decimal:
        if not (Decimal("0.0") <= v <= Decimal("1.0")):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class PatternFeedbackCreate(BaseModel):
    """
    Data Transfer Object for creating pattern feedback.
    
    Excludes auto-generated fields (feedback_id, timestamp).
    """
    pattern_id: uuid.UUID = Field(alias="patternId")
    user_id: str = Field(alias="userId")
    feedback_type: str = Field(alias="feedbackType")  # 'correct', 'incorrect', 'missed_transaction', 'false_positive'
    user_correction: Optional[Dict[str, Any]] = Field(default=None, alias="userCorrection")  # What the user changed
    transaction_id: Optional[uuid.UUID] = Field(default=None, alias="transactionId")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        }
    )

    @field_validator('feedback_type')
    @classmethod
    def validate_feedback_type(cls, v: str) -> str:
        valid_types = {'correct', 'incorrect', 'missed_transaction', 'false_positive'}
        if v not in valid_types:
            raise ValueError(f"feedback_type must be one of {valid_types}")
        return v


class PatternFeedback(BaseModel):
    """
    User feedback on pattern detection accuracy.
    
    Used to improve the ML algorithm through supervised learning.
    """
    feedback_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="feedbackId")
    pattern_id: uuid.UUID = Field(alias="patternId")
    user_id: str = Field(alias="userId")
    feedback_type: str = Field(alias="feedbackType")  # 'correct', 'incorrect', 'missed_transaction', 'false_positive'
    user_correction: Optional[Dict[str, Any]] = Field(default=None, alias="userCorrection")  # What the user changed
    transaction_id: Optional[uuid.UUID] = Field(default=None, alias="transactionId")
    timestamp: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000)
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        }
    )

    @field_validator('timestamp')
    @classmethod
    def check_positive_timestamp(cls, v: int) -> int:
        if v < 0:
            raise ValueError(TIMESTAMP_ERROR_MESSAGE)
        return v

    @field_validator('feedback_type')
    @classmethod
    def validate_feedback_type(cls, v: str) -> str:
        valid_types = {'correct', 'incorrect', 'missed_transaction', 'false_positive'}
        if v not in valid_types:
            raise ValueError(f"feedback_type must be one of {valid_types}")
        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Ensure UUID fields are converted to strings
        for key, value in data.items():
            if isinstance(value, uuid.UUID):
                data[key] = str(value)
        
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """Create from DynamoDB item data."""
        converted_data = data.copy()
        
        # Convert Decimal to int for timestamp
        if 'timestamp' in converted_data and isinstance(converted_data['timestamp'], Decimal):
            converted_data['timestamp'] = int(converted_data['timestamp'])
        
        # Convert UUID strings to UUID objects
        uuid_fields = ['feedbackId', 'patternId', 'transactionId']
        for field in uuid_fields:
            if field in converted_data and isinstance(converted_data[field], str):
                try:
                    converted_data[field] = uuid.UUID(converted_data[field])
                except ValueError:
                    pass
        
        return cls.model_validate(converted_data)

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
    amount_tolerance_pct: float = Field(default=10.0, alias="amountTolerancePct", ge=0.0, le=100.0)
    
    # Pattern metadata
    confidence_score: float = Field(alias="confidenceScore", ge=0.0, le=1.0)
    transaction_count: int = Field(alias="transactionCount", ge=0)
    first_occurrence: int = Field(alias="firstOccurrence")
    last_occurrence: int = Field(alias="lastOccurrence")
    
    # ML features
    feature_vector: Optional[List[float]] = Field(default=None, alias="featureVector")
    cluster_id: Optional[int] = Field(default=None, alias="clusterId")
    
    # Associated category
    suggested_category_id: Optional[uuid.UUID] = Field(default=None, alias="suggestedCategoryId")
    auto_categorize: bool = Field(default=False, alias="autoCategorize")
    
    # Status
    active: bool = Field(default=True)
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
        use_enum_values=True
    )

    @field_validator('first_occurrence', 'last_occurrence', 'created_at', 'updated_at')
    @classmethod
    def check_positive_timestamp(cls, v: int) -> int:
        if v < 0:
            raise ValueError(TIMESTAMP_ERROR_MESSAGE)
        return v

    @field_validator('day_of_week')
    @classmethod
    def validate_day_of_week(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 6):
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday)")
        return v

    @field_validator('day_of_month')
    @classmethod
    def validate_day_of_month(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 31):
            raise ValueError("day_of_month must be between 1 and 31")
        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Ensure all UUID fields are converted to strings for DynamoDB
        for key, value in data.items():
            if isinstance(value, uuid.UUID):
                data[key] = str(value)
        
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """Create from DynamoDB item data."""
        converted_data = data.copy()
        
        cls._convert_decimal_fields(converted_data)
        cls._convert_uuid_fields(converted_data)
        cls._convert_enum_fields(converted_data)
        
        return cls.model_construct(**converted_data)
    
    @staticmethod
    def _convert_decimal_fields(data: Dict[str, Any]) -> None:
        """Convert Decimal fields to appropriate types."""
        int_fields = ['dayOfWeek', 'dayOfMonth', 'toleranceDays', 'transactionCount', 
                      'firstOccurrence', 'lastOccurrence', 'createdAt', 'updatedAt', 'clusterId']
        for field in int_fields:
            if field in data and data[field] is not None and isinstance(data[field], Decimal):
                data[field] = int(data[field])
        
        float_fields = ['confidenceScore', 'amountTolerancePct']
        for field in float_fields:
            if field in data and data[field] is not None and isinstance(data[field], Decimal):
                data[field] = float(data[field])
        
        if 'featureVector' in data and data['featureVector'] is not None:
            if isinstance(data['featureVector'], list):
                data['featureVector'] = [
                    float(x) if isinstance(x, Decimal) else x for x in data['featureVector']
                ]
    
    @staticmethod
    def _convert_uuid_fields(data: Dict[str, Any]) -> None:
        """Convert UUID string fields to UUID objects."""
        uuid_fields = ['patternId', 'suggestedCategoryId']
        for field in uuid_fields:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = uuid.UUID(data[field])
                except ValueError:
                    pass
    
    @staticmethod
    def _convert_enum_fields(data: Dict[str, Any]) -> None:
        """Convert enum string fields to enum objects."""
        if 'frequency' in data and isinstance(data['frequency'], str):
            try:
                data['frequency'] = RecurrenceFrequency(data['frequency'])
            except ValueError:
                logger.warning(f"Invalid RecurrenceFrequency value: {data['frequency']}")
                data['frequency'] = RecurrenceFrequency.IRREGULAR
        
        if 'temporalPatternType' in data and isinstance(data['temporalPatternType'], str):
            try:
                data['temporalPatternType'] = TemporalPatternType(data['temporalPatternType'])
            except ValueError:
                logger.warning(f"Invalid TemporalPatternType value: {data['temporalPatternType']}")
                data['temporalPatternType'] = TemporalPatternType.FLEXIBLE


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
    amount_tolerance_pct: float = Field(default=10.0, alias="amountTolerancePct", ge=0.0, le=100.0)
    
    # Pattern metadata
    confidence_score: float = Field(alias="confidenceScore", ge=0.0, le=1.0)
    transaction_count: int = Field(alias="transactionCount", ge=0)
    first_occurrence: int = Field(alias="firstOccurrence")
    last_occurrence: int = Field(alias="lastOccurrence")
    
    # ML features
    feature_vector: Optional[List[float]] = Field(default=None, alias="featureVector")
    cluster_id: Optional[int] = Field(default=None, alias="clusterId")
    
    # Associated category
    suggested_category_id: Optional[uuid.UUID] = Field(default=None, alias="suggestedCategoryId")
    auto_categorize: bool = Field(default=False, alias="autoCategorize")
    
    # Status
    active: bool = Field(default=True)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            Decimal: str,
            uuid.UUID: str
        },
        use_enum_values=True
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
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday)")
        return v

    @field_validator('day_of_month')
    @classmethod
    def validate_day_of_month(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 31):
            raise ValueError("day_of_month must be between 1 and 31")
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
    amount_tolerance_pct: Optional[float] = Field(default=None, alias="amountTolerancePct", ge=0.0, le=100.0)
    
    # Pattern metadata
    confidence_score: Optional[float] = Field(default=None, alias="confidenceScore", ge=0.0, le=1.0)
    transaction_count: Optional[int] = Field(default=None, alias="transactionCount", ge=0)
    first_occurrence: Optional[int] = Field(default=None, alias="firstOccurrence")
    last_occurrence: Optional[int] = Field(default=None, alias="lastOccurrence")
    
    # ML features
    feature_vector: Optional[List[float]] = Field(default=None, alias="featureVector")
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
        use_enum_values=True
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
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday)")
        return v

    @field_validator('day_of_month')
    @classmethod
    def validate_day_of_month(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 31):
            raise ValueError("day_of_month must be between 1 and 31")
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
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0-1.0
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
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Ensure UUID fields are converted to strings
        if isinstance(data.get('patternId'), uuid.UUID):
            data['patternId'] = str(data['patternId'])
        
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
        
        # Convert Decimal to float for confidence
        if 'confidence' in converted_data and isinstance(converted_data['confidence'], Decimal):
            converted_data['confidence'] = float(converted_data['confidence'])
        
        # Convert UUID string to UUID object
        if 'patternId' in converted_data and isinstance(converted_data['patternId'], str):
            try:
                converted_data['patternId'] = uuid.UUID(converted_data['patternId'])
            except ValueError:
                pass
        
        # amount_range and expected_amount remain as Decimal (DynamoDB native)
        
        return cls.model_construct(**converted_data)


class RecurringChargePredictionCreate(BaseModel):
    """Data Transfer Object for creating a new recurring charge prediction."""
    pattern_id: uuid.UUID = Field(alias="patternId")
    next_expected_date: int = Field(alias="nextExpectedDate")  # Timestamp (ms)
    expected_amount: Decimal = Field(alias="expectedAmount")
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0-1.0
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
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
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
        
        return cls.model_construct(**converted_data)


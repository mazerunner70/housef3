"""
Analytics models for the financial analytics system.
"""
import enum
import logging
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any, List
from typing_extensions import Self

from pydantic import BaseModel, Field, ConfigDict

# Configure logging
logger = logging.getLogger(__name__)


class DataQuality(str, enum.Enum):
    """Enum for data quality assessment"""
    COMPLETE = "complete"
    PARTIAL = "partial"
    GAPS = "gaps"


class AnalyticType(str, enum.Enum):
    """Enum for different analytics types"""
    CASH_FLOW = "cash_flow"
    CATEGORY_TRENDS = "category_trends"
    BUDGET_PERFORMANCE = "budget_performance"
    FINANCIAL_HEALTH = "financial_health"
    CREDIT_UTILIZATION = "credit_utilization"
    PAYMENT_PATTERNS = "payment_patterns"
    ACCOUNT_EFFICIENCY = "account_efficiency"
    MERCHANT_ANALYSIS = "merchant_analysis"
    GOAL_PROGRESS = "goal_progress"
    RECOMMENDATIONS = "recommendations"


class ComputationStatus(str, enum.Enum):
    """Enum for computation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"


class AccountDataRange(BaseModel):
    """Represents the data range available for a specific account"""
    account_id: str
    earliest_transaction_date: Optional[date] = Field(alias="earliestTransactionDate")
    latest_transaction_date: Optional[date] = Field(alias="latestTransactionDate")
    last_statement_upload: Optional[datetime] = Field(alias="lastStatementUpload")
    data_quality: DataQuality = Field(alias="dataQuality")
    transaction_count: int = Field(default=0, alias="transactionCount")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class AnalyticDateRange(BaseModel):
    """Represents the computed analytic date range across all accounts"""
    start_date: Optional[date] = Field(alias="startDate")
    end_date: Optional[date] = Field(alias="endDate")
    gap_days: int = Field(default=0, alias="gapDays")
    can_precompute: bool = Field(default=False, alias="canPrecompute")
    next_computation_date: Optional[date] = Field(alias="nextComputationDate")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            date: lambda v: v.isoformat() if v else None
        }
    )


class AnalyticsProcessingStatus(BaseModel):
    """Represents the processing status for analytics computations"""
    user_id: str = Field(alias="userId")
    account_id: Optional[str] = Field(default=None, alias="accountId")
    analytic_type: AnalyticType = Field(alias="analyticType")
    last_computed_date: Optional[date] = Field(alias="lastComputedDate")
    data_available_through: Optional[date] = Field(alias="dataAvailableThrough")
    computation_needed: bool = Field(default=False, alias="computationNeeded")
    processing_priority: int = Field(default=3, alias="processingPriority")
    status: ComputationStatus = Field(default=ComputationStatus.PENDING)
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="lastUpdated"
    )
    error_message: Optional[str] = Field(default=None, alias="errorMessage")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }
    )

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Serialize to DynamoDB format"""
        item = self.model_dump(mode='python', by_alias=True, exclude_none=True)

        # Convert dates to ISO strings for DynamoDB
        if 'lastComputedDate' in item and item['lastComputedDate']:
            item['lastComputedDate'] = item['lastComputedDate'].isoformat()
        if 'dataAvailableThrough' in item and item['dataAvailableThrough']:
            item['dataAvailableThrough'] = item['dataAvailableThrough'].isoformat()
        if 'lastUpdated' in item and item['lastUpdated']:
            item['lastUpdated'] = item['lastUpdated'].isoformat()

        # Convert enums to string values
        if 'analyticType' in item:
            item['analyticType'] = (
                item['analyticType'].value
                if hasattr(item['analyticType'], 'value')
                else str(item['analyticType'])
            )
        if 'status' in item:
            item['status'] = (
                item['status'].value
                if hasattr(item['status'], 'value')
                else str(item['status'])
            )

        return item

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """Deserialize from DynamoDB format"""
        # Convert ISO strings back to dates/datetimes
        if 'lastComputedDate' in data and data['lastComputedDate']:
            data['lastComputedDate'] = date.fromisoformat(data['lastComputedDate'])
        if 'dataAvailableThrough' in data and data['dataAvailableThrough']:
            data['dataAvailableThrough'] = date.fromisoformat(data['dataAvailableThrough'])
        if 'lastUpdated' in data and data['lastUpdated']:
            data['lastUpdated'] = datetime.fromisoformat(data['lastUpdated'])

        # Convert string enums back to enum types
        if 'analyticType' in data and isinstance(data['analyticType'], str):
            data['analyticType'] = AnalyticType(data['analyticType'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ComputationStatus(data['status'])

        return cls.model_validate(data)


class AnalyticsData(BaseModel):
    """Represents computed analytics data"""
    user_id: str = Field(alias="userId")
    analytic_type: AnalyticType = Field(alias="analyticType")
    time_period: str = Field(alias="timePeriod")
    account_id: Optional[str] = Field(default=None, alias="accountId")
    data: Dict[str, Any] = Field(default_factory=dict)
    computed_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="computedDate"
    )
    data_through_date: Optional[date] = Field(alias="dataThroughDate")
    ttl: Optional[int] = None

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }
    )

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Serialize to DynamoDB format with partition key and sort key"""
        item = self.model_dump(mode='python', by_alias=True, exclude_none=True)

        # Create DynamoDB partition key: user_id#analytic_type
        item['pk'] = f"{self.user_id}#{self.analytic_type.value}"

        # Create DynamoDB sort key: time_period#account_id (or 'ALL' for cross-account)
        account_part = self.account_id or 'ALL'
        item['sk'] = f"{self.time_period}#{account_part}"

        # Convert dates to ISO strings for DynamoDB
        if 'computedDate' in item and item['computedDate']:
            item['computedDate'] = item['computedDate'].isoformat()
        if 'dataThroughDate' in item and item['dataThroughDate']:
            item['dataThroughDate'] = item['dataThroughDate'].isoformat()

        # Convert enum to string value
        if 'analyticType' in item:
            item['analyticType'] = (
                item['analyticType'].value
                if hasattr(item['analyticType'], 'value')
                else str(item['analyticType'])
            )

        return item

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """Deserialize from DynamoDB format"""
        # Extract user_id and analytic_type from partition key
        if 'pk' in data:
            pk_parts = data['pk'].split('#')
            if len(pk_parts) == 2:
                data['userId'] = pk_parts[0]
                data['analyticType'] = pk_parts[1]

        # Extract time_period and account_id from sort key
        if 'sk' in data:
            sk_parts = data['sk'].split('#')
            if len(sk_parts) == 2:
                data['timePeriod'] = sk_parts[0]
                if sk_parts[1] != 'ALL':
                    data['accountId'] = sk_parts[1]

        # Convert ISO strings back to dates/datetimes
        if 'computedDate' in data and data['computedDate']:
            data['computedDate'] = datetime.fromisoformat(data['computedDate'])
        if 'dataThroughDate' in data and data['dataThroughDate']:
            data['dataThroughDate'] = date.fromisoformat(data['dataThroughDate'])

        # Convert string enum back to enum type
        if 'analyticType' in data and isinstance(data['analyticType'], str):
            data['analyticType'] = AnalyticType(data['analyticType'])

        return cls.model_validate(data)


class DataGap(BaseModel):
    """Represents a gap in available data"""
    account_id: str = Field(alias="accountId")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    gap_type: str = Field(alias="gapType")
    impact_level: str = Field(alias="impactLevel")
    affected_analytics: List[AnalyticType] = Field(default_factory=list, alias="affectedAnalytics")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            date: lambda v: v.isoformat() if v else None
        }
    )


class DataDisclaimer(BaseModel):
    """Represents a disclaimer about data limitations"""
    message: str
    affected_tabs: List[str] = Field(alias="affectedTabs")
    suggested_action: Optional[str] = Field(alias="suggestedAction")
    severity: str = Field(default="info")

    model_config = ConfigDict(populate_by_name=True)
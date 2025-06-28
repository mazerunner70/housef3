"""
Data availability service for financial analytics.
"""
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from ..models.analytics import (
    AccountDataRange, AnalyticDateRange, DataGap, DataDisclaimer,
    AnalyticType, DataQuality
)
from ..utils.db_utils import (
    get_transactions_table, get_files_table, get_accounts_table
)

# Configure logging
logger = logging.getLogger(__name__)


class DataAvailabilityService:
    """Service to assess data availability and quality for analytics."""

    def __init__(self):
        self.transactions_table = get_transactions_table()
        self.files_table = get_files_table()
        self.accounts_table = get_accounts_table()

    def get_account_data_ranges(self, user_id: str) -> List[AccountDataRange]:
        """
        Get data ranges for all accounts belonging to a user.

        Args:
            user_id: The user ID to check data ranges for

        Returns:
            List of AccountDataRange objects, one per account
        """
        try:
            accounts_response = self.accounts_table.scan(
                FilterExpression='#userId = :user_id',
                ExpressionAttributeNames={'#userId': 'userId'},
                ExpressionAttributeValues={':user_id': user_id}
            )

            account_ranges = []
            for account in accounts_response.get('Items', []):
                account_id = account['accountId']

                # Query transactions for this account
                transactions_response = self.transactions_table.scan(
                    FilterExpression='#userId = :user_id AND #accountId = :account_id',
                    ExpressionAttributeNames={
                        '#userId': 'userId',
                        '#accountId': 'accountId'
                    },
                    ExpressionAttributeValues={
                        ':user_id': user_id,
                        ':account_id': account_id
                    }
                )

                transactions = transactions_response.get('Items', [])
                transaction_count = len(transactions)

                earliest_date = None
                latest_date = None

                if transactions:
                    # Convert date strings to date objects for comparison
                    dates = []
                    for txn in transactions:
                        try:
                            txn_date = date.fromisoformat(txn['transactionDate'])
                            dates.append(txn_date)
                        except (ValueError, KeyError):
                            logger.warning(f"Invalid date format in transaction: {txn}")
                            continue

                    if dates:
                        earliest_date = min(dates)
                        latest_date = max(dates)

                # Get the last statement upload for this account
                files_response = self.files_table.scan(
                    FilterExpression='#userId = :user_id AND #accountId = :account_id',
                    ExpressionAttributeNames={
                        '#userId': 'userId',
                        '#accountId': 'accountId'
                    },
                    ExpressionAttributeValues={
                        ':user_id': user_id,
                        ':account_id': account_id
                    }
                )

                last_upload = None
                files = files_response.get('Items', [])
                if files:
                    # Find the most recent upload
                    upload_dates = []
                    for file_item in files:
                        try:
                            upload_date = datetime.fromisoformat(file_item['uploadTimestamp'])
                            upload_dates.append(upload_date)
                        except (ValueError, KeyError):
                            continue

                    if upload_dates:
                        last_upload = max(upload_dates)

                # Assess data quality
                data_quality = self._assess_data_quality(
                    earliest_date, latest_date, transaction_count, last_upload
                )

                account_range = AccountDataRange(
                    account_id=account_id,
                    earliestTransactionDate=earliest_date,
                    latestTransactionDate=latest_date,
                    lastStatementUpload=last_upload,
                    dataQuality=data_quality,
                    transactionCount=transaction_count
                )
                account_ranges.append(account_range)

            return account_ranges

        except Exception as e:
            logger.error(f"Error getting account data ranges for user {user_id}: {str(e)}")
            return []

    def calculate_analytic_date_range(self, account_ranges: List[AccountDataRange],
                                      analytic_type: AnalyticType) -> AnalyticDateRange:
        """
        Calculate the overall date range for analytics computations.

        Args:
            account_ranges: List of account data ranges
            analytic_type: Type of analytic to compute

        Returns:
            AnalyticDateRange object with computed range
        """
        if not account_ranges:
            return AnalyticDateRange(
                startDate=None,
                endDate=None,
                nextComputationDate=None
            )

        # Filter out accounts with no data
        valid_ranges = [
            acc_range for acc_range in account_ranges
            if acc_range.earliest_transaction_date and acc_range.latest_transaction_date
        ]

        if not valid_ranges:
            return AnalyticDateRange(
                startDate=None,
                endDate=None,
                nextComputationDate=None
            )

        # For most analytics, we want the intersection of dates (latest start, earliest end)
        earliest_dates = [acc_range.earliest_transaction_date for acc_range in valid_ranges 
                          if acc_range.earliest_transaction_date is not None]
        latest_dates = [acc_range.latest_transaction_date for acc_range in valid_ranges 
                        if acc_range.latest_transaction_date is not None]
        
        if not earliest_dates or not latest_dates:
            return AnalyticDateRange(
                startDate=None,
                endDate=None,
                nextComputationDate=None
            )
            
        latest_start = max(earliest_dates)
        earliest_end = min(latest_dates)

        # For some analytics, we might want the union instead
        if analytic_type in [AnalyticType.ACCOUNT_EFFICIENCY, AnalyticType.PAYMENT_PATTERNS]:
            # Use union (earliest start, latest end) for account-specific analytics
            earliest_start = min(earliest_dates)
            latest_end = max(latest_dates)
            start_date = earliest_start
            end_date = latest_end
        else:
            # Use intersection for cross-account analytics
            start_date = latest_start
            end_date = earliest_end

        # Ensure start_date is not after end_date
        if start_date > end_date:
            start_date = end_date

        # Calculate gap days (days where we don't have complete data)
        gap_days = self._calculate_gap_days(valid_ranges, start_date, end_date)

        # Determine if we can precompute (if data is recent enough)
        can_precompute = self._can_precompute(valid_ranges)

        # Calculate next computation date
        next_computation_date = self._calculate_next_computation_date(
            valid_ranges, analytic_type
        )

        return AnalyticDateRange(
            startDate=start_date,
            endDate=end_date,
            gapDays=gap_days,
            canPrecompute=can_precompute,
            nextComputationDate=next_computation_date
        )

    def check_precomputation_opportunity(self, user_id: str,
                                         analytic_type: AnalyticType) -> bool:
        """
        Check if analytics can be precomputed based on recent statement uploads.

        Args:
            user_id: User ID to check
            analytic_type: Type of analytic to check

        Returns:
            True if precomputation is recommended
        """
        try:
            account_ranges = self.get_account_data_ranges(user_id)
            if not account_ranges:
                return False

            # Check if any account has recent data uploads
            recent_threshold = datetime.now() - timedelta(days=7)
            has_recent_uploads = any(
                acc_range.last_statement_upload and
                acc_range.last_statement_upload > recent_threshold
                for acc_range in account_ranges
            )

            # Check if data quality is sufficient
            has_sufficient_data = any(
                acc_range.data_quality in [DataQuality.COMPLETE, DataQuality.PARTIAL]
                for acc_range in account_ranges
            )

            return has_recent_uploads and has_sufficient_data

        except Exception as e:
            logger.error(f"Error checking precomputation opportunity: {str(e)}")
            return False

    def identify_data_gaps(self, account_ranges: List[AccountDataRange]) -> List[DataGap]:
        """
        Identify gaps in data that might affect analytics quality.

        Args:
            account_ranges: List of account data ranges to analyze

        Returns:
            List of DataGap objects
        """
        gaps = []

        for acc_range in account_ranges:
            if not acc_range.earliest_transaction_date or not acc_range.latest_transaction_date:
                continue

            # Check for large gaps in transaction data
            # This is a simplified implementation - in reality, you'd analyze the actual dates
            date_span = (acc_range.latest_transaction_date -
                         acc_range.earliest_transaction_date).days

            # If we have very few transactions for a large date span, there might be gaps
            if date_span > 90 and acc_range.transaction_count < 10:
                gap = DataGap(
                    accountId=acc_range.account_id,
                    startDate=acc_range.earliest_transaction_date,
                    endDate=acc_range.latest_transaction_date,
                    gapType="sparse_data",
                    impactLevel="medium",
                    affectedAnalytics=[
                        AnalyticType.CASH_FLOW,
                        AnalyticType.CATEGORY_TRENDS,
                        AnalyticType.FINANCIAL_HEALTH
                    ]
                )
                gaps.append(gap)

            # Check for outdated data
            if acc_range.latest_transaction_date < date.today() - timedelta(days=30):
                gap = DataGap(
                    accountId=acc_range.account_id,
                    startDate=acc_range.latest_transaction_date,
                    endDate=date.today(),
                    gapType="outdated_data",
                    impactLevel="high",
                    affectedAnalytics=[
                        AnalyticType.FINANCIAL_HEALTH,
                        AnalyticType.CREDIT_UTILIZATION,
                        AnalyticType.CASH_FLOW
                    ]
                )
                gaps.append(gap)

        return gaps

    def generate_data_disclaimers(self, gaps: List[DataGap],
                                  analytic_type: AnalyticType) -> List[DataDisclaimer]:
        """
        Generate user-friendly disclaimers about data limitations.

        Args:
            gaps: List of data gaps identified
            analytic_type: Type of analytic being computed

        Returns:
            List of DataDisclaimer objects
        """
        disclaimers = []

        # Group gaps by type
        gap_types = {}
        for gap in gaps:
            if analytic_type in gap.affected_analytics:
                if gap.gap_type not in gap_types:
                    gap_types[gap.gap_type] = []
                gap_types[gap.gap_type].append(gap)

        # Generate disclaimers for each gap type
        if 'sparse_data' in gap_types:
            disclaimers.append(DataDisclaimer(
                message="Some accounts have limited transaction history, which may affect the accuracy of analytics.",
                affectedTabs=["Overview", "Accounts"],
                suggestedAction="Upload more complete statement files for better insights.",
                severity="warning"
            ))

        if 'outdated_data' in gap_types:
            disclaimers.append(DataDisclaimer(
                message="Analytics are based on data that may be outdated. Upload recent statements for current insights.",
                affectedTabs=["Overview", "Categories", "Accounts"],
                suggestedAction="Upload your most recent account statements.",
                severity="info"
            ))

        return disclaimers

    def get_computation_scope_for_analytic_type(self, user_id: str,
                                                 analytic_type: AnalyticType) -> Dict[str, Any]:
        """
        Determine what can be computed for a specific analytic type.

        Args:
            user_id: User ID
            analytic_type: Type of analytic

        Returns:
            Dictionary with computation scope information
        """
        account_ranges = self.get_account_data_ranges(user_id)
        date_range = self.calculate_analytic_date_range(account_ranges, analytic_type)
        gaps = self.identify_data_gaps(account_ranges)
        disclaimers = self.generate_data_disclaimers(gaps, analytic_type)

        return {
            'can_compute': bool(date_range.start_date and date_range.end_date),
            'date_range': date_range,
            'account_ranges': account_ranges,
            'data_gaps': gaps,
            'disclaimers': disclaimers,
            'recommended_accounts': [
                acc_range.account_id for acc_range in account_ranges
                if acc_range.data_quality in [DataQuality.COMPLETE, DataQuality.PARTIAL]
            ]
        }

    def _assess_data_quality(self, earliest_date: Optional[date], latest_date: Optional[date],
                             transaction_count: int, last_upload: Optional[datetime]) -> DataQuality:
        """Assess the quality of data for an account."""
        if not earliest_date or not latest_date or transaction_count == 0:
            return DataQuality.GAPS

        # Check if data is recent
        days_since_last_data = (date.today() - latest_date).days
        if days_since_last_data > 60:
            return DataQuality.PARTIAL

        # Check transaction density
        date_span = (latest_date - earliest_date).days
        if date_span > 0:
            transactions_per_day = transaction_count / date_span
            if transactions_per_day < 0.1:  # Less than 1 transaction per 10 days
                return DataQuality.PARTIAL

        return DataQuality.COMPLETE

    def _calculate_gap_days(self, account_ranges: List[AccountDataRange],
                            start_date: date, end_date: date) -> int:
        """Calculate the number of days with potential data gaps."""
        # Simplified implementation
        total_days = (end_date - start_date).days
        if total_days <= 0:
            return 0

        # For now, estimate based on data quality
        low_quality_accounts = sum(
            1 for acc_range in account_ranges
            if acc_range.data_quality == DataQuality.GAPS
        )

        total_accounts = len(account_ranges)
        if total_accounts == 0:
            return total_days

        # Estimate gap percentage based on account quality
        gap_percentage = low_quality_accounts / total_accounts
        return int(total_days * gap_percentage)

    def _can_precompute(self, account_ranges: List[AccountDataRange]) -> bool:
        """Determine if data is recent enough for precomputation."""
        if not account_ranges:
            return False

        # Check if majority of accounts have recent data
        recent_accounts = sum(
            1 for acc_range in account_ranges
            if (acc_range.latest_transaction_date and
                (date.today() - acc_range.latest_transaction_date).days <= 30)
        )

        return recent_accounts >= len(account_ranges) * 0.7  # 70% threshold

    def _calculate_next_computation_date(self, account_ranges: List[AccountDataRange],
                                         analytic_type: AnalyticType) -> Optional[date]:
        """Calculate when the next computation should occur."""
        if not account_ranges:
            return None

        # For most analytics, suggest recomputation in 7 days
        base_days = 7

        # Adjust based on analytic type
        if analytic_type in [AnalyticType.FINANCIAL_HEALTH, AnalyticType.CREDIT_UTILIZATION]:
            base_days = 14  # Less frequent for slower-changing metrics

        return date.today() + timedelta(days=base_days) 
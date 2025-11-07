"""
Analytics computation engine for financial analytics.
"""
import logging
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from models.account import AccountType
from models.transaction import Transaction
from models.category import CategoryType
from utils.db_utils import list_user_accounts, list_user_transactions, list_categories_by_user_from_db

# Configure logging
logger = logging.getLogger(__name__)


class AnalyticsComputationEngine:
    """
    Core analytics computation engine.
    
    This service contains the algorithms for computing all analytics types.
    """

    def __init__(self):
        self._transfer_category_cache = {}
    
    def _get_transfer_category_ids(self, user_id: str) -> set:
        """Get the category IDs for transfer categories for this user."""
        if user_id in self._transfer_category_cache:
            return self._transfer_category_cache[user_id]
        
        try:
            categories = list_categories_by_user_from_db(user_id)
            transfer_category_ids = {
                str(cat.categoryId) for cat in categories 
                if type(cat.type).__name__ == "CategoryType" and cat.type.name == "TRANSFER"
            }
            self._transfer_category_cache[user_id] = transfer_category_ids
            return transfer_category_ids
        except Exception as e:
            logger.warning(f"Error getting transfer categories for user {user_id}: {str(e)}")
            return set()
    
    def _is_transfer_transaction(self, transaction: Transaction, user_id: str) -> bool:
        """Check if a transaction is categorized as a transfer."""
        if not transaction.categories:
            return False
        
        transfer_category_ids = self._get_transfer_category_ids(user_id)
        
        for assignment in transaction.categories:
            if str(assignment.category_id) in transfer_category_ids:
                return True
        
        return False
    
    def _filter_non_transfer_transactions(self, transactions: List[Transaction], user_id: str) -> List[Transaction]:
        """Filter out transfer transactions from the list."""
        return [tx for tx in transactions if not self._is_transfer_transaction(tx, user_id)]

    def compute_cash_flow_analytics(self, user_id: str, time_period: str,
                                    account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute cash flow analytics for the Overview tab.

        Args:
            user_id: The user ID
            time_period: Time period (e.g., '2024-12', '2024-Q4', '2024')
            account_id: Optional specific account ID

        Returns:
            Dictionary with cash flow analytics data
        """
        logger.info(f"Computing cash flow analytics for user {user_id}, period {time_period}, account {account_id}")
        
        try:
            # Parse time period to get date range
            start_date, end_date = self._parse_time_period(time_period)
            logger.info(f"Parsed time period: {start_date} to {end_date}")

            # Get transactions for the period
            account_ids = [uuid.UUID(account_id)] if account_id else None
            all_transactions = self._get_transactions_for_period(user_id, start_date, end_date, account_ids)
            logger.info(f"Found {len(all_transactions)} transactions in period")
            
            # Filter out transfer transactions
            transactions = self._filter_non_transfer_transactions(all_transactions, user_id)
            logger.info(f"After filtering transfers: {len(transactions)} transactions")

            # Separate income and expenses
            income_transactions = []
            expense_transactions = []

            for transaction in transactions:
                logger.debug(f"Processing transaction {transaction.transaction_id}: amount={transaction.amount}")
                if transaction.amount > 0:
                    income_transactions.append(transaction)
                else:
                    expense_transactions.append(transaction)

            logger.info(f"Split into {len(income_transactions)} income and {len(expense_transactions)} expense transactions")

            # Calculate totals
            total_income = sum(t.amount for t in income_transactions)
            total_expenses = abs(sum(t.amount for t in expense_transactions))
            net_cash_flow = total_income - total_expenses

            logger.info(f"Calculated totals - Income: {total_income}, Expenses: {total_expenses}, Net Cash Flow: {net_cash_flow}")

            # Calculate monthly averages if period is longer than a month
            months_in_period = self._calculate_months_in_period(start_date, end_date)
            avg_monthly_income = total_income / months_in_period if months_in_period > 0 else total_income
            avg_monthly_expenses = total_expenses / months_in_period if months_in_period > 0 else total_expenses

            # Calculate transaction frequency
            transaction_count = len(transactions)
            avg_transaction_amount = ((total_income + total_expenses) / transaction_count
                                      if transaction_count > 0 else 0)

            # Income stability analysis (variance in monthly income)
            income_stability_score = self._calculate_income_stability(
                income_transactions, start_date, end_date
            )

            # Calculate expense ratio
            expense_ratio = (total_expenses / total_income * 100) if total_income > 0 else 0

            return {
                "totalIncome": Decimal(str(total_income)),
                "totalExpenses": Decimal(str(total_expenses)),
                "netCashFlow": Decimal(str(net_cash_flow)),
                "avgMonthlyIncome": Decimal(str(avg_monthly_income)),
                "avgMonthlyExpenses": Decimal(str(avg_monthly_expenses)),
                "transactionCount": transaction_count,
                "avgTransactionAmount": Decimal(str(avg_transaction_amount)),
                "incomeStabilityScore": Decimal(str(income_stability_score)),
                "expenseRatio": Decimal(str(expense_ratio)),
                "cashFlowTrend": "positive" if net_cash_flow > 0 else "negative",
                "periodMonths": months_in_period,
                "periodStart": start_date.isoformat(),
                "periodEnd": end_date.isoformat()
            }

        except Exception as e:
            logger.error(f"Error computing cash flow analytics: {str(e)}")
            # Return safe defaults instead of crashing
            return {
                "totalIncome": Decimal('0.0'),
                "totalExpenses": Decimal('0.0'),
                "netCashFlow": Decimal('0.0'),
                "avgMonthlyIncome": Decimal('0.0'),
                "avgMonthlyExpenses": Decimal('0.0'),
                "transactionCount": 0,
                "avgTransactionAmount": Decimal('0.0'),
                "incomeStabilityScore": Decimal('50.0'),
                "expenseRatio": Decimal('0.0'),
                "cashFlowTrend": "neutral",
                "periodMonths": 1,
                "periodStart": date.today().isoformat(),
                "periodEnd": date.today().isoformat()
            }

    def compute_category_analytics(self, user_id: str, time_period: str,
                                   account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute category analytics for the Categories tab.

        Args:
            user_id: The user ID
            time_period: Time period
            account_id: Optional specific account ID

        Returns:
            Dictionary with category analytics data
        """
        try:
            start_date, end_date = self._parse_time_period(time_period)
            account_ids = [uuid.UUID(account_id)] if account_id else None
            all_transactions = self._get_transactions_for_period(user_id, start_date, end_date, account_ids)
            
            # Filter out transfer transactions
            transactions = self._filter_non_transfer_transactions(all_transactions, user_id)

            # Group transactions by category
            # Note: Transaction model doesn't have direct category field yet
            # For now, use transaction_type or a simple categorization
            category_spending = defaultdict(lambda: Decimal('0'))
            category_counts = defaultdict(int)

            for transaction in transactions:
                # Use transaction_type if available, otherwise categorize by amount
                if hasattr(transaction, 'transaction_type') and transaction.transaction_type:
                    category = transaction.transaction_type
                else:
                    # Simple categorization based on amount (positive = income, negative = expense)
                    category = 'Income' if transaction.amount > 0 else 'Expense'
                
                category_spending[category] += abs(transaction.amount)
                category_counts[category] += 1

            # Calculate category percentages
            total_spending = sum(category_spending.values())
            category_percentages = {}
            category_rankings = []

            for category, amount in category_spending.items():
                percentage = (amount / total_spending * 100) if total_spending > 0 else 0
                category_percentages[category] = percentage
                category_rankings.append({
                    "category": category,
                    "amount": Decimal(str(amount)),
                    "percentage": Decimal(str(percentage)),
                    "transactionCount": category_counts[category]
                })

            # Sort by spending amount
            category_rankings.sort(key=lambda x: x["amount"], reverse=True)

            # Calculate category trends (requires historical comparison)
            category_trends = self._calculate_category_trends(
                user_id, time_period, category_spending, account_ids
            )

            return {
                "categoryBreakdown": category_rankings,
                "categoryPercentages": category_percentages,
                "categoryTrends": category_trends,
                "totalSpending": Decimal(str(total_spending)),
                "topCategory": category_rankings[0]["category"] if category_rankings else None,
                "categoryCount": len(category_spending),
                "uncategorizedAmount": Decimal('0')  # No uncategorized since we're using simple categorization
            }

        except Exception as e:
            logger.error(f"Error computing category analytics: {str(e)}")
            # Return safe defaults instead of crashing
            return {
                "categoryBreakdown": [],
                "categoryPercentages": {},
                "categoryTrends": {},
                "totalSpending": Decimal('0.0'),
                "topCategory": None,
                "categoryCount": 0,
                "uncategorizedAmount": Decimal('0')
            }

    def compute_account_analytics(self, user_id: str, time_period: str) -> Dict[str, Any]:
        """
        Compute account analytics for the Accounts tab.

        Args:
            user_id: The user ID
            time_period: Time period

        Returns:
            Dictionary with account analytics data
        """
        try:
            accounts = list_user_accounts(user_id)
            start_date, end_date = self._parse_time_period(time_period)

            account_analytics = []
            total_balance = Decimal('0')

            for account in accounts:
                # Get transactions for this account
                account_transactions = self._get_transactions_for_period(
                    user_id, start_date, end_date, [account.account_id]
                )

                # Calculate account metrics
                account_income = sum(t.amount for t in account_transactions if t.amount > 0)
                account_expenses = abs(sum(t.amount for t in account_transactions if t.amount < 0))
                account_net_flow = account_income - account_expenses

                # Credit utilization for credit card accounts
                credit_utilization = None
                credit_utilization_estimated = None
                if type(account.account_type).__name__ == "AccountType" and account.account_type.name == "CREDIT_CARD" and account.balance:
                    # TODO: Use actual credit limit data when available
                    # For now, use a rough estimate (3x balance) but mark it as estimated
                    estimated_limit = abs(account.balance) * 3  # Rough estimate
                    if estimated_limit > 0:
                        credit_utilization = (abs(account.balance) / estimated_limit) * 100
                        credit_utilization_estimated = True  # Mark as estimated since we don't have real credit limit data

                # Account efficiency (transactions per balance)
                account_efficiency = len(account_transactions) / max(abs(account.balance or Decimal('1')), Decimal('1'))

                account_analytics.append({
                    "accountId": str(account.account_id),
                    "accountName": account.account_name,
                    "accountType": account.account_type.value,
                    "balance": Decimal(str(account.balance)) if account.balance else Decimal('0'),
                    "income": Decimal(str(account_income)),
                    "expenses": Decimal(str(account_expenses)),
                    "netFlow": Decimal(str(account_net_flow)),
                    "transactionCount": len(account_transactions),
                    "creditUtilization": Decimal(str(credit_utilization)) if credit_utilization is not None else None,
                    "creditUtilizationEstimated": credit_utilization_estimated,
                    "efficiencyScore": Decimal(str(account_efficiency))
                })

                if account.balance:
                    total_balance += account.balance

            # Calculate cross-account insights
            total_accounts = len(accounts)
            avg_balance = total_balance / total_accounts if total_accounts > 0 else Decimal('0')

            # Account performance ranking
            account_analytics.sort(key=lambda x: x["netFlow"], reverse=True)

            return {
                "accountDetails": account_analytics,
                "totalBalance": total_balance,
                "avgBalance": avg_balance,
                "accountCount": total_accounts,
                "bestPerformingAccount": account_analytics[0]["accountName"] if account_analytics else None,
                "highestUtilization": max((a["creditUtilization"] for a in account_analytics
                                           if a["creditUtilization"] is not None), default=Decimal('0'))
            }

        except Exception as e:
            logger.error(f"Error computing account analytics: {str(e)}")
            # Return safe defaults instead of crashing
            return {
                "accountDetails": [],
                "totalBalance": Decimal('0.0'),
                "avgBalance": Decimal('0.0'),
                "accountCount": 0,
                "bestPerformingAccount": None,
                "highestUtilization": Decimal('0')
            }

    def compute_financial_health_score(self, user_id: str, time_period: str) -> Dict[str, Any]:
        """
        Compute overall financial health score.

        Args:
            user_id: The user ID
            time_period: Time period

        Returns:
            Dictionary with financial health score and breakdown
        """
        try:
            # Get component analytics
            cash_flow_data = self.compute_cash_flow_analytics(user_id, time_period)
            account_data = self.compute_account_analytics(user_id, time_period)

            # Handle None cash_flow_data
            if cash_flow_data is None:
                cash_flow_data = {
                    "netCashFlow": 0,
                    "totalIncome": 0,
                    "incomeStabilityScore": 50,
                    "expenseRatio": 0
                }

            # Handle None account_data
            if account_data is None:
                account_data = {"highestUtilization": 0}

            # Component scores (0-100)
            cash_flow_score = min(100, max(0,
                                           (float(cash_flow_data["netCashFlow"]) / 
                                            max(float(cash_flow_data["totalIncome"]), 1) * 100) + 50))
            
            income_stability_score = float(cash_flow_data["incomeStabilityScore"])
            
            expense_management_score = min(100, max(0, 100 - float(cash_flow_data["expenseRatio"])))
            
            account_health_score = 100 - min(100, float(account_data.get("highestUtilization", 0)))

            # Weighted overall score
            overall_score = (
                cash_flow_score * 0.3 +
                income_stability_score * 0.25 +
                expense_management_score * 0.25 +
                account_health_score * 0.2
            )

            # Generate recommendations
            recommendations = self._generate_health_recommendations(
                overall_score, cash_flow_data, account_data
            )

            # Calculate additional health indicators
            emergency_fund_months = 0.0  # TODO: Calculate based on savings vs expenses
            debt_to_income_ratio = 0.0   # TODO: Calculate based on debt payments vs income
            savings_rate = 0.0           # TODO: Calculate savings rate
            expense_volatility = 0.0     # TODO: Calculate expense variance
            
            # Generate risk factors based on scores
            risk_factors = []
            if cash_flow_score < 50:
                risk_factors.append("Negative cash flow - expenses exceed income")
            if float(income_stability_score) < 60:
                risk_factors.append("Irregular income patterns detected")
            if expense_management_score < 50:
                risk_factors.append("High expense ratio relative to income")
            if account_health_score < 70:
                risk_factors.append("High credit utilization detected")

            return {
                "overallScore": Decimal(str(round(overall_score, 1))),
                "componentScores": {
                    "cashFlowScore": Decimal(str(round(cash_flow_score, 1))),
                    "expenseStabilityScore": Decimal(str(round(expense_management_score, 1))),
                    "emergencyFundScore": Decimal(str(round(account_health_score, 1))),  # Using account health as proxy
                    "debtManagementScore": Decimal(str(round(account_health_score, 1))), # Using account health as proxy
                    "savingsRateScore": Decimal(str(round(float(income_stability_score), 1)))  # Using income stability as proxy
                },
                "healthIndicators": {
                    "emergencyFundMonths": Decimal(str(emergency_fund_months)),
                    "debtToIncomeRatio": Decimal(str(debt_to_income_ratio)),
                    "savingsRate": Decimal(str(savings_rate)),
                    "expenseVolatility": Decimal(str(expense_volatility))
                },
                "scoreLevel": ("excellent" if overall_score >= 80 else
                               "good" if overall_score >= 60 else
                               "fair" if overall_score >= 40 else "poor"),
                "recommendations": recommendations,
                "riskFactors": risk_factors
            }

        except Exception as e:
            logger.error(f"Error computing financial health score: {str(e)}")
            raise

    def _parse_time_period(self, time_period: str) -> Tuple[date, date]:
        """
        Parse time period string into start and end dates.

        Args:
            time_period: Time period string (e.g., '2024-12', '2024-Q4', '2024', 'overall', '12months')

        Returns:
            Tuple of start_date and end_date
        """
        try:
            if time_period.lower() == 'overall':
                # Overall period: Use a very wide date range to capture all data
                # Start from 10 years ago to today
                end_date = date.today()
                start_date = date(end_date.year - 10, 1, 1)
                
            elif time_period.lower().endswith('months'):
                # Format: '12months', '3months', etc.
                try:
                    num_months = int(time_period[:-6])  # Remove 'months' suffix
                    end_date = date.today()
                    # Calculate start date by subtracting months
                    year = end_date.year
                    month = end_date.month - num_months
                    # Adjust year if we went back past January
                    while month <= 0:
                        year -= 1
                        month += 12
                    start_date = date(year, month, 1)
                    logger.info(f"Parsed '{time_period}' as {start_date} to {end_date}")
                except ValueError as e:
                    logger.error(f"Invalid months format in '{time_period}': {str(e)}")
                    raise
                
            elif '-Q' in time_period:
                # Quarterly format: 2024-Q4
                year, quarter = time_period.split('-Q')
                year = int(year)
                quarter = int(quarter)
                
                if quarter == 1:
                    start_date = date(year, 1, 1)
                    end_date = date(year, 3, 31)
                elif quarter == 2:
                    start_date = date(year, 4, 1)
                    end_date = date(year, 6, 30)
                elif quarter == 3:
                    start_date = date(year, 7, 1)
                    end_date = date(year, 9, 30)
                else:  # quarter == 4
                    start_date = date(year, 10, 1)
                    end_date = date(year, 12, 31)
                    
            elif '-' in time_period:
                # Monthly format: 2024-12
                year, month = time_period.split('-')
                year = int(year)
                month = int(month)
                start_date = date(year, month, 1)
                
                # Calculate last day of month
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)
                    
            else:
                # Yearly format: 2024
                year = int(time_period)
                start_date = date(year, 1, 1)
                end_date = date(year, 12, 31)

            return start_date, end_date

        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing time period '{time_period}': {str(e)}")
            # Default to current month
            today = date.today()
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
            return start_date, end_date

    def _get_transactions_for_period(self, user_id: str, start_date: date, end_date: date,
                                     account_ids: Optional[List[uuid.UUID]] = None) -> List[Transaction]:
        """Get transactions for a specific time period and optional account filter."""
        try:
            # Convert dates to milliseconds for the API
            start_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000)
            end_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp() * 1000)

            transactions, _, _ = list_user_transactions(
                user_id=user_id,
                account_ids=account_ids,
                start_date_ts=start_timestamp,
                end_date_ts=end_timestamp,
                limit=10000  # Get all transactions in period
            )

            return transactions

        except Exception as e:
            logger.error(f"Error getting transactions for period: {str(e)}")
            return []

    def _calculate_months_in_period(self, start_date: date, end_date: date) -> float:
        """Calculate the number of months in a date range."""
        return ((end_date.year - start_date.year) * 12 + end_date.month - start_date.month) + 1

    def _calculate_income_stability(self, income_transactions: List[Transaction],
                                    start_date: date, end_date: date) -> Decimal:
        """
        Calculate income stability score based on variance in monthly income.

        Args:
            income_transactions: List of income transactions
            start_date: Period start date
            end_date: Period end date

        Returns:
            Stability score from 0-100 (higher is more stable)
        """
        try:
            if not income_transactions:
                return Decimal('0.0')

            # Group income by month
            monthly_income = defaultdict(lambda: Decimal('0'))
            for transaction in income_transactions:
                # Convert timestamp to date
                transaction_date = datetime.fromtimestamp(transaction.date / 1000).date()
                month_key = f"{transaction_date.year}-{transaction_date.month:02d}"
                monthly_income[month_key] += transaction.amount

            if len(monthly_income) <= 1:
                return Decimal('100.0')  # Perfect stability if only one month

            incomes = list(monthly_income.values())
            avg_income = sum(incomes) / Decimal(str(len(incomes)))

            if avg_income == 0:
                return Decimal('0.0')

            # Calculate coefficient of variation using float for mathematical operations
            incomes_float = [float(income) for income in incomes]
            avg_income_float = float(avg_income)
            
            variance = sum((income - avg_income_float) ** 2 for income in incomes_float) / len(incomes_float)
            std_dev = variance ** 0.5
            cv = std_dev / avg_income_float

            # Convert to 0-100 score (lower CV = higher stability)
            stability_score = max(0, 100 - (cv * 100))
            return Decimal(str(min(100, stability_score)))

        except Exception as e:
            logger.error(f"Error calculating income stability: {str(e)}")
            return Decimal('50.0')  # Default neutral score

    def _calculate_category_trends(self, user_id: str, time_period: str,
                                   current_spending: Dict[str, Decimal],
                                   account_ids: Optional[List[uuid.UUID]] = None) -> Dict[str, Any]:
        """Calculate category spending trends compared to previous period."""
        try:
            # Get previous period for comparison
            current_start, current_end = self._parse_time_period(time_period)
            period_length = (current_end - current_start).days

            # Calculate previous period
            previous_end = current_start - timedelta(days=1)
            previous_start = previous_end - timedelta(days=period_length)

            # Get previous period transactions
            previous_transactions = self._get_transactions_for_period(
                user_id, previous_start, previous_end, account_ids
            )

            # Calculate previous period spending by category
            # Use same categorization logic as main analytics function
            previous_spending = defaultdict(lambda: Decimal('0'))
            for transaction in previous_transactions:
                # Use transaction_type if available, otherwise categorize by amount
                if hasattr(transaction, 'transaction_type') and transaction.transaction_type:
                    category = transaction.transaction_type
                else:
                    # Simple categorization based on amount (positive = income, negative = expense)
                    category = 'Income' if transaction.amount > 0 else 'Expense'
                    
                previous_spending[category] += abs(transaction.amount)

            # Calculate trends
            trends = {}
            for category, current_amount in current_spending.items():
                previous_amount = previous_spending.get(category, Decimal('0'))
                
                if previous_amount > 0:
                    change_percentage = ((current_amount - previous_amount) / previous_amount) * 100
                    trend = "increasing" if change_percentage > 5 else (
                        "decreasing" if change_percentage < -5 else "stable"
                    )
                else:
                    change_percentage = 100 if current_amount > 0 else 0
                    trend = "new" if current_amount > 0 else "stable"

                trends[category] = {
                    "trend": trend,
                    "change_percentage": Decimal(str(round(float(change_percentage), 1))),
                    "previous_amount": previous_amount,
                    "current_amount": current_amount
                }

            return trends

        except Exception as e:
            logger.error(f"Error calculating category trends: {str(e)}")
            return {}

    def _generate_health_recommendations(self, overall_score: float,
                                         cash_flow: Dict[str, Any],
                                         account_data: Dict[str, Any]) -> List[str]:
        """Generate personalized financial health recommendations."""
        recommendations = []

        # Handle None values with safe defaults
        if cash_flow is None:
            cash_flow = {
                "net_cash_flow": 0,
                "expense_ratio": 0,
                "income_stability_score": 50
            }
        
        if account_data is None:
            account_data = {"highest_utilization": 0}

        if cash_flow.get("net_cash_flow", 0) < 0:
            recommendations.append("Your expenses exceed income. Consider reviewing and reducing unnecessary spending.")

        if cash_flow.get("expense_ratio", 0) > 80:
            recommendations.append("Your expense ratio is high. Aim to keep expenses below 80% of income.")

        if cash_flow.get("income_stability_score", 50) < 60:
            recommendations.append("Your income shows high variability. Consider building an emergency fund.")

        if account_data.get("highest_utilization", 0) > 30:
            recommendations.append("High credit utilization detected. Try to keep credit usage below 30%.")

        if overall_score >= 80:
            recommendations.append("Great financial health! Consider investing surplus funds for long-term growth.")
        elif overall_score < 40:
            recommendations.append("Focus on basic financial stability: emergency fund and debt reduction.")

        return recommendations[:5]  # Limit to top 5 recommendations 
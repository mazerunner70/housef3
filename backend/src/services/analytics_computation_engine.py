"""
Analytics computation engine for financial analytics.
"""
import logging
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from ..models.account import AccountType
from ..models.transaction import Transaction
from ..utils.db_utils import list_user_accounts, list_user_transactions

# Configure logging
logger = logging.getLogger(__name__)


class AnalyticsComputationEngine:
    """
    Core analytics computation engine.
    
    This service contains the algorithms for computing all analytics types.
    """

    def __init__(self):
        self.logger = logger

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
        try:
            # Parse time period to get date range
            start_date, end_date = self._parse_time_period(time_period)

            # Get transactions for the period
            account_ids = [uuid.UUID(account_id)] if account_id else None
            transactions = self._get_transactions_for_period(user_id, start_date, end_date, account_ids)

            # Separate income and expenses
            income_transactions = []
            expense_transactions = []

            for transaction in transactions:
                if transaction.amount > 0:
                    income_transactions.append(transaction)
                else:
                    expense_transactions.append(transaction)

            # Calculate totals
            total_income = sum(t.amount for t in income_transactions)
            total_expenses = abs(sum(t.amount for t in expense_transactions))
            net_cash_flow = total_income - total_expenses

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
                "total_income": float(total_income),
                "total_expenses": float(total_expenses),
                "net_cash_flow": float(net_cash_flow),
                "avg_monthly_income": float(avg_monthly_income),
                "avg_monthly_expenses": float(avg_monthly_expenses),
                "transaction_count": transaction_count,
                "avg_transaction_amount": float(avg_transaction_amount),
                "income_stability_score": income_stability_score,
                "expense_ratio": float(expense_ratio),
                "cash_flow_trend": "positive" if net_cash_flow > 0 else "negative",
                "period_months": months_in_period,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error computing cash flow analytics: {str(e)}")
            # Return safe defaults instead of crashing
            return {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net_cash_flow": 0.0,
                "avg_monthly_income": 0.0,
                "avg_monthly_expenses": 0.0,
                "transaction_count": 0,
                "avg_transaction_amount": 0.0,
                "income_stability_score": 50.0,
                "expense_ratio": 0.0,
                "cash_flow_trend": "neutral",
                "period_months": 1,
                "period_start": date.today().isoformat(),
                "period_end": date.today().isoformat()
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
            transactions = self._get_transactions_for_period(user_id, start_date, end_date, account_ids)

            # Group transactions by category
            # Note: Transaction model doesn't have direct category field yet
            # For now, use transaction_type or a simple categorization
            category_spending = defaultdict(float)
            category_counts = defaultdict(int)

            for transaction in transactions:
                # Use transaction_type if available, otherwise categorize by amount
                if hasattr(transaction, 'transaction_type') and transaction.transaction_type:
                    category = transaction.transaction_type
                else:
                    # Simple categorization based on amount (positive = income, negative = expense)
                    category = 'Income' if transaction.amount > 0 else 'Expense'
                
                category_spending[category] += abs(float(transaction.amount))
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
                    "amount": amount,
                    "percentage": percentage,
                    "transaction_count": category_counts[category]
                })

            # Sort by spending amount
            category_rankings.sort(key=lambda x: x["amount"], reverse=True)

            # Calculate category trends (requires historical comparison)
            category_trends = self._calculate_category_trends(
                user_id, time_period, category_spending, account_ids
            )

            return {
                "category_breakdown": category_rankings,
                "category_percentages": category_percentages,
                "category_trends": category_trends,
                "total_spending": total_spending,
                "top_category": category_rankings[0]["category"] if category_rankings else None,
                "category_count": len(category_spending),
                "uncategorized_amount": 0  # No uncategorized since we're using simple categorization
            }

        except Exception as e:
            self.logger.error(f"Error computing category analytics: {str(e)}")
            # Return safe defaults instead of crashing
            return {
                "category_breakdown": [],
                "category_percentages": {},
                "category_trends": {},
                "total_spending": 0.0,
                "top_category": None,
                "category_count": 0,
                "uncategorized_amount": 0
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
                if account.account_type == AccountType.CREDIT_CARD and account.balance:
                    # This would need credit limit data - for now use a placeholder
                    estimated_limit = abs(float(account.balance)) * 3  # Rough estimate
                    if estimated_limit > 0:
                        credit_utilization = (abs(float(account.balance)) / estimated_limit) * 100

                # Account efficiency (transactions per balance)
                account_efficiency = len(account_transactions) / max(float(abs(account.balance or 1)), 1)

                account_analytics.append({
                    "account_id": str(account.account_id),
                    "account_name": account.account_name,
                    "account_type": account.account_type.value,
                    "balance": float(account.balance) if account.balance else 0,
                    "income": float(account_income),
                    "expenses": float(account_expenses),
                    "net_flow": float(account_net_flow),
                    "transaction_count": len(account_transactions),
                    "credit_utilization": credit_utilization,
                    "efficiency_score": account_efficiency
                })

                if account.balance:
                    total_balance += account.balance

            # Calculate cross-account insights
            total_accounts = len(accounts)
            avg_balance = float(total_balance) / total_accounts if total_accounts > 0 else 0

            # Account performance ranking
            account_analytics.sort(key=lambda x: x["net_flow"], reverse=True)

            return {
                "account_details": account_analytics,
                "total_balance": float(total_balance),
                "avg_balance": avg_balance,
                "account_count": total_accounts,
                "best_performing_account": account_analytics[0]["account_name"] if account_analytics else None,
                "highest_utilization": max((a["credit_utilization"] for a in account_analytics
                                           if a["credit_utilization"] is not None), default=0)
            }

        except Exception as e:
            self.logger.error(f"Error computing account analytics: {str(e)}")
            # Return safe defaults instead of crashing
            return {
                "account_details": [],
                "total_balance": 0.0,
                "avg_balance": 0.0,
                "account_count": 0,
                "best_performing_account": None,
                "highest_utilization": 0
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
                    "net_cash_flow": 0,
                    "total_income": 0,
                    "income_stability_score": 50,
                    "expense_ratio": 0
                }

            # Handle None account_data
            if account_data is None:
                account_data = {"highest_utilization": 0}

            # Component scores (0-100)
            cash_flow_score = min(100, max(0,
                                           (cash_flow_data["net_cash_flow"] / 
                                            max(cash_flow_data["total_income"], 1) * 100) + 50))
            
            income_stability_score = cash_flow_data["income_stability_score"]
            
            expense_management_score = min(100, max(0, 100 - cash_flow_data["expense_ratio"]))
            
            account_health_score = 100 - min(100, account_data.get("highest_utilization", 0))

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

            return {
                "overall_score": round(overall_score, 1),
                "score_breakdown": {
                    "cash_flow": round(cash_flow_score, 1),
                    "income_stability": round(income_stability_score, 1),
                    "expense_management": round(expense_management_score, 1),
                    "account_health": round(account_health_score, 1)
                },
                "score_level": ("excellent" if overall_score >= 80 else
                                "good" if overall_score >= 60 else
                                "fair" if overall_score >= 40 else "poor"),
                "recommendations": recommendations
            }

        except Exception as e:
            self.logger.error(f"Error computing financial health score: {str(e)}")
            raise

    def _parse_time_period(self, time_period: str) -> Tuple[date, date]:
        """
        Parse time period string into start and end dates.

        Args:
            time_period: Time period string (e.g., '2024-12', '2024-Q4', '2024')

        Returns:
            Tuple of start_date and end_date
        """
        try:
            if '-Q' in time_period:
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
            self.logger.error(f"Error parsing time period '{time_period}': {str(e)}")
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
            self.logger.error(f"Error getting transactions for period: {str(e)}")
            return []

    def _calculate_months_in_period(self, start_date: date, end_date: date) -> float:
        """Calculate the number of months in a date range."""
        return ((end_date.year - start_date.year) * 12 + end_date.month - start_date.month) + 1

    def _calculate_income_stability(self, income_transactions: List[Transaction],
                                    start_date: date, end_date: date) -> float:
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
                return 0.0

            # Group income by month
            monthly_income = defaultdict(float)
            for transaction in income_transactions:
                # Convert timestamp to date
                transaction_date = datetime.fromtimestamp(transaction.date / 1000).date()
                month_key = f"{transaction_date.year}-{transaction_date.month:02d}"
                monthly_income[month_key] += float(transaction.amount)

            if len(monthly_income) <= 1:
                return 100.0  # Perfect stability if only one month

            incomes = list(monthly_income.values())
            avg_income = sum(incomes) / len(incomes)

            if avg_income == 0:
                return 0.0

            # Calculate coefficient of variation
            variance = sum((income - avg_income) ** 2 for income in incomes) / len(incomes)
            std_dev = variance ** 0.5
            cv = std_dev / avg_income

            # Convert to 0-100 score (lower CV = higher stability)
            stability_score = max(0, 100 - (cv * 100))
            return min(100, stability_score)

        except Exception as e:
            self.logger.error(f"Error calculating income stability: {str(e)}")
            return 50.0  # Default neutral score

    def _calculate_category_trends(self, user_id: str, time_period: str,
                                   current_spending: Dict[str, float],
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
            previous_spending = defaultdict(float)
            for transaction in previous_transactions:
                # Use transaction_type if available, otherwise categorize by amount
                if hasattr(transaction, 'transaction_type') and transaction.transaction_type:
                    category = transaction.transaction_type
                else:
                    # Simple categorization based on amount (positive = income, negative = expense)
                    category = 'Income' if transaction.amount > 0 else 'Expense'
                    
                previous_spending[category] += abs(float(transaction.amount))

            # Calculate trends
            trends = {}
            for category, current_amount in current_spending.items():
                previous_amount = previous_spending.get(category, 0)
                
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
                    "change_percentage": round(change_percentage, 1),
                    "previous_amount": previous_amount,
                    "current_amount": current_amount
                }

            return trends

        except Exception as e:
            self.logger.error(f"Error calculating category trends: {str(e)}")
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
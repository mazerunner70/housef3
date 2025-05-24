from dataclasses import dataclass
from decimal import Decimal
import enum
from typing import Any, Dict, Optional



class Currency(str, enum.Enum):
    """Enum for currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    JPY = "JPY"
    AUD = "AUD"
    CHF = "CHF"
    CNY = "CNY"
    OTHER = "other"


"""
Money is a class that represents a monetary amount.
It is used to represent the amount of money in a given currency.
A None currency is used to represent a currency that is not yet known because the transactions have not been parsed yet
"""

@dataclass
class Money:
    amount: Decimal
    currency: Optional[Currency]
    
    def __post_init__(self):
        # Ensure amount is a Decimal
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        if self.currency and not isinstance(self.currency, Currency):
            raise ValueError("Currency is required")


    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add money with different currencies")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot subtract money with different currencies")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, other: Decimal) -> 'Money':
        return Money(self.amount * other, self.currency)
    
    def __truediv__(self, other: Decimal) -> 'Money':
        return Money(self.amount / other, self.currency)
            
    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount": str(self.amount),
            "currency": self.currency.value if self.currency else None
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Money':
        return cls(
            amount=Decimal(str(data["amount"])),
            currency=Currency(data["currency"]) if data["currency"] else None
        ) 
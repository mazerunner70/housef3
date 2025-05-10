from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict

from models.account import Currency




@dataclass
class Money:
    amount: Decimal
    currency: Currency
    
    def __post_init__(self):
        # Ensure amount is a Decimal
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        if not self.currency:
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
            "currency": self.currency.value
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Money':
        return cls(
            amount=Decimal(str(data["amount"])),
            currency=Currency(data["currency"])
        ) 
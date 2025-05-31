from decimal import Decimal
import enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


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


class Money(BaseModel):
    """
    Money is a class that represents a monetary amount using Pydantic.
    It is used to represent the amount of money in a given currency.
    A None currency is used to represent a currency that is not yet known 
    because the transactions have not been parsed yet.
    """
    amount: Decimal
    currency: Optional[Currency] = None

    model_config = ConfigDict(
        json_encoders={
            Decimal: str
        },
        use_enum_values=True,
        arbitrary_types_allowed=True
    )

    @field_validator('amount', mode='before')
    @classmethod
    def ensure_amount_is_decimal(cls, v: Any) -> Decimal:
        if not isinstance(v, Decimal):
            try:
                return Decimal(str(v))
            except Exception as e:
                raise ValueError(f"Invalid amount value: {v}. Could not convert to Decimal.") from e
        return v

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            if self.currency is not None and other.currency is not None:
                raise ValueError("Cannot add money with different currencies")
        
        resulting_currency = self.currency if self.currency is not None else other.currency
        return Money(amount=self.amount + other.amount, currency=resulting_currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            if self.currency is not None and other.currency is not None:
                raise ValueError("Cannot subtract money with different currencies")
        
        resulting_currency = self.currency if self.currency is not None else other.currency
        return Money(amount=self.amount - other.amount, currency=resulting_currency)
    
    def __mul__(self, other: Decimal) -> 'Money':
        if not isinstance(other, Decimal):
            other = Decimal(str(other))
        return Money(amount=self.amount * other, currency=self.currency)
    
    def __truediv__(self, other: Decimal) -> 'Money':
        if not isinstance(other, Decimal):
            other = Decimal(str(other))
        if other == Decimal(0):
            raise ValueError("Cannot divide by zero")
        return Money(amount=self.amount / other, currency=self.currency)
            
    

# End of Money class, no further methods after arithmetic operations. 
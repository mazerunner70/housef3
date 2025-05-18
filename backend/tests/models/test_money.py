import unittest
from decimal import Decimal
from typing import Any, Dict, Optional
from models.money import Money, Currency

class TestMoney(unittest.TestCase):
    def setUp(self):
        """Set up test cases"""
        self.amount = Decimal('100.50')
        self.currency = Currency.USD
        self.money = Money(self.amount, self.currency)

    def test_init(self):
        """Test Money initialization"""
        # Test normal initialization
        money = Money(Decimal('100.50'), Currency.USD)
        self.assertEqual(money.amount, Decimal('100.50'))
        self.assertEqual(money.currency, Currency.USD)

        # Test initialization with string amount (via Decimal conversion)
        money = Money(Decimal('100.50'), Currency.USD)
        self.assertEqual(money.amount, Decimal('100.50'))
        self.assertTrue(isinstance(money.amount, Decimal))

        # Test initialization with float amount (via Decimal conversion)
        money = Money(Decimal(str(100.50)), Currency.USD)
        self.assertEqual(money.amount, Decimal('100.50'))
        self.assertTrue(isinstance(money.amount, Decimal))

        # Test initialization with integer amount (via Decimal conversion)
        money = Money(Decimal('100'), Currency.USD)
        self.assertEqual(money.amount, Decimal('100'))
        self.assertTrue(isinstance(money.amount, Decimal))

    def test_init_validation(self):
        """Test Money initialization validation"""
        # Test invalid currency (using Any to test invalid types)
        invalid_currency: Any = None
        with self.assertRaises(ValueError):
            Money(Decimal('100.50'), invalid_currency)
        
        invalid_str: Any = 'USD'
        with self.assertRaises(ValueError):
            Money(Decimal('100.50'), invalid_str)

    def test_add(self):
        """Test Money addition"""
        # Test same currency addition
        money1 = Money(Decimal('100.50'), Currency.USD)
        money2 = Money(Decimal('50.25'), Currency.USD)
        result = money1 + money2
        self.assertEqual(result.amount, Decimal('150.75'))
        self.assertEqual(result.currency, Currency.USD)

        # Test different currency addition (should raise error)
        money3 = Money(Decimal('50.25'), Currency.EUR)
        with self.assertRaises(ValueError):
            money1 + money3

    def test_subtract(self):
        """Test Money subtraction"""
        # Test same currency subtraction
        money1 = Money(Decimal('100.50'), Currency.USD)
        money2 = Money(Decimal('50.25'), Currency.USD)
        result = money1 - money2
        self.assertEqual(result.amount, Decimal('50.25'))
        self.assertEqual(result.currency, Currency.USD)

        # Test different currency subtraction (should raise error)
        money3 = Money(Decimal('50.25'), Currency.EUR)
        with self.assertRaises(ValueError):
            money1 - money3

    def test_multiply(self):
        """Test Money multiplication"""
        money = Money(Decimal('100.50'), Currency.USD)
        result = money * Decimal('2')
        self.assertEqual(result.amount, Decimal('201.00'))
        self.assertEqual(result.currency, Currency.USD)

    def test_divide(self):
        """Test Money division"""
        money = Money(Decimal('100.50'), Currency.USD)
        result = money / Decimal('2')
        self.assertEqual(result.amount, Decimal('50.25'))
        self.assertEqual(result.currency, Currency.USD)

    def test_to_dict(self):
        """Test conversion to dictionary"""
        money = Money(Decimal('100.50'), Currency.USD)
        result = money.to_dict()
        expected = {
            'amount': '100.50',
            'currency': 'USD'
        }
        self.assertEqual(result, expected)

    def test_from_dict(self):
        """Test creation from dictionary"""
        data: Dict[str, Any] = {
            'amount': '100.50',
            'currency': 'USD'
        }
        money = Money.from_dict(data)
        self.assertEqual(money.amount, Decimal('100.50'))
        self.assertEqual(money.currency, Currency.USD)

        # Test with numeric amount
        data = {
            'amount': 100.50,
            'currency': 'USD'
        }
        money = Money.from_dict(data)
        self.assertEqual(money.amount, Decimal('100.50'))
        self.assertEqual(money.currency, Currency.USD)

    def test_currency_enum(self):
        """Test Currency enum values"""
        # Test all defined currencies
        self.assertEqual(Currency.USD.value, "USD")
        self.assertEqual(Currency.EUR.value, "EUR")
        self.assertEqual(Currency.GBP.value, "GBP")
        self.assertEqual(Currency.CAD.value, "CAD")
        self.assertEqual(Currency.JPY.value, "JPY")
        self.assertEqual(Currency.AUD.value, "AUD")
        self.assertEqual(Currency.CHF.value, "CHF")
        self.assertEqual(Currency.CNY.value, "CNY")
        self.assertEqual(Currency.OTHER.value, "other")

if __name__ == '__main__':
    unittest.main() 
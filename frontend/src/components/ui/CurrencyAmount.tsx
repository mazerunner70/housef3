import React from 'react';
import { Decimal } from 'decimal.js';

interface CurrencyAmountProps {
  amount: any; // Accept any type, validate internally
  currency?: string;
  className?: string;
}

const CurrencyAmount: React.FC<CurrencyAmountProps> = ({ 
  amount, 
  currency = 'USD', 
  className = '' 
}) => {
  // Check if amount is a valid Decimal instance
  const isValidDecimal = amount instanceof Decimal;
  
  if (!isValidDecimal) {
    return (
      <span className={`currency-broken ${className}`} title={`Invalid currency amount type: ${typeof amount}`}>
        ⚠️ Invalid
      </span>
    );
  }

  const displayAmount = amount.toFixed(2);
  const currencySymbol = currency === 'USD' ? '$' : currency;
  const amountClass = amount.greaterThanOrEqualTo(new Decimal(0)) ? 'amount-income' : 'amount-expense';

  return (
    <span className={`${amountClass} ${className}`}>
      {currencySymbol}{displayAmount}
    </span>
  );
};

export default CurrencyAmount; 
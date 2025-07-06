import React from 'react';
import { Decimal } from 'decimal.js';

interface CurrencyDisplayProps {
  amount: Decimal | number;
  currency?: string;
  className?: string;
  showSign?: boolean;
  precision?: number;
}

const CurrencyDisplay: React.FC<CurrencyDisplayProps> = ({
  amount,
  currency = 'USD',
  className = '',
  showSign = false,
  precision = 2,
}) => {
  const formatAmount = (value: Decimal | number): string => {
    const decimal = value instanceof Decimal ? value : new Decimal(value);
    return decimal.toFixed(precision);
  };

  const getAmountClass = (value: Decimal | number): string => {
    const decimal = value instanceof Decimal ? value : new Decimal(value);
    if (decimal.greaterThan(0)) return 'currency-positive';
    if (decimal.lessThan(0)) return 'currency-negative';
    return 'currency-zero';
  };

  const getCurrencySymbol = (curr: string): string => {
    const symbols: { [key: string]: string } = {
      USD: '$',
      EUR: '€',
      GBP: '£',
      JPY: '¥',
      CAD: 'C$',
      AUD: 'A$',
      CHF: 'Fr.',
      CNY: '¥',
    };
    return symbols[curr.toUpperCase()] || curr;
  };

  const formattedAmount = formatAmount(amount);
  const amountClass = getAmountClass(amount);
  const currencySymbol = getCurrencySymbol(currency);

  return (
    <span className={`currency-display ${amountClass} ${className}`}>
      {showSign && amount instanceof Decimal && amount.greaterThan(0) && '+'}
      {currencySymbol}{formattedAmount}
    </span>
  );
};

export default CurrencyDisplay; 
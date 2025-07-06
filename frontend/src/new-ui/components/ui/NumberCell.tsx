import React from 'react';

interface NumberCellProps {
  value?: number | string;
  fallback?: string;
  className?: string;
  format?: 'default' | 'currency' | 'percentage' | 'integer' | 'decimal';
  precision?: number;
  prefix?: string;
  suffix?: string;
  align?: 'left' | 'center' | 'right';
}

const NumberCell: React.FC<NumberCellProps> = ({ 
  value,
  fallback = 'N/A',
  className = '',
  format = 'default',
  precision = 0,
  prefix = '',
  suffix = '',
  align = 'center'
}) => {
  const formatNumber = (num: number, formatType: string, prec: number): string => {
    switch (formatType) {
      case 'currency':
        return new Intl.NumberFormat('en-US', { 
          style: 'currency', 
          currency: 'USD',
          minimumFractionDigits: prec,
          maximumFractionDigits: prec 
        }).format(num);
      case 'percentage':
        return new Intl.NumberFormat('en-US', { 
          style: 'percent',
          minimumFractionDigits: prec,
          maximumFractionDigits: prec 
        }).format(num / 100);
      case 'integer':
        return Math.round(num).toLocaleString();
      case 'decimal':
        return num.toFixed(prec);
      case 'default':
      default:
        return prec > 0 ? num.toFixed(prec) : num.toString();
    }
  };

  const getDisplayValue = (): string => {
    if (value === undefined || value === null || value === '') {
      return fallback;
    }

    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    
    if (isNaN(numValue)) {
      return fallback;
    }

    const formattedValue = formatNumber(numValue, format, precision);
    return `${prefix}${formattedValue}${suffix}`;
  };

  const displayValue = getDisplayValue();
  const isValid = displayValue !== fallback;
  const alignClass = `text-${align}`;

  return (
    <span 
      className={`number-cell ${alignClass} ${isValid ? 'number-valid' : 'number-invalid'} ${className}`}
      style={{ 
        fontFamily: format === 'currency' || format === 'decimal' ? 'monospace' : 'inherit',
        textAlign: align 
      }}
    >
      {displayValue}
    </span>
  );
};

export default NumberCell; 
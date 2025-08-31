import React from 'react';

interface DateCellProps {
  date: number | Date | string; // More flexible input types
  className?: string;
  format?: 'short' | 'long' | 'iso' | 'relative';
  showTime?: boolean;
  locale?: string; // Allow custom locale
}

const DateCell: React.FC<DateCellProps> = ({
  date,
  className = '',
  format = 'short',
  showTime = false,
  locale
}) => {
  const formatDate = (inputDate: number | Date | string, formatType: string, includeTime: boolean): string => {
    let dateObj: Date;

    if (typeof inputDate === 'number') {
      dateObj = new Date(inputDate);
    } else if (typeof inputDate === 'string') {
      dateObj = new Date(inputDate);
    } else {
      dateObj = inputDate;
    }

    // Handle invalid dates
    if (isNaN(dateObj.getTime())) {
      return 'Invalid Date';
    }

    // Determine locale: use prop, browser locale, or fallback to 'en-US'
    const userLocale = locale || navigator.language || 'en-US';

    const options: Intl.DateTimeFormatOptions = {};

    switch (formatType) {
      case 'long':
        options.year = 'numeric';
        options.month = 'long';
        options.day = 'numeric';
        break;
      case 'iso':
        return dateObj.toISOString().split('T')[0];
      case 'relative':
        return getRelativeTime(dateObj);
      case 'short':
      default:
        options.year = 'numeric';
        options.month = 'short';
        options.day = 'numeric';
        break;
    }

    if (includeTime) {
      options.hour = '2-digit';
      options.minute = '2-digit';
    }

    return dateObj.toLocaleDateString(userLocale, options);
  };

  const getRelativeTime = (date: Date): string => {
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInDays = diffInMs / (1000 * 60 * 60 * 24);

    if (diffInDays < 1) return 'Today';
    if (diffInDays < 2) return 'Yesterday';
    if (diffInDays < 7) return `${diffInDays.toFixed(1)} days ago`;
    if (diffInDays < 30) return `${(diffInDays / 7).toFixed(1)} weeks ago`;
    if (diffInDays < 365) return `${(diffInDays / 30).toFixed(1)} months ago`;
    return `${(diffInDays / 365).toFixed(1)} years ago`;
  };

  const userLocale = locale || navigator.language || 'en-US';

  return (
    <span className={`date-cell ${className}`} title={new Date(date).toLocaleString(userLocale)}>
      {formatDate(date, format, showTime)}
    </span>
  );
};

export default DateCell; 
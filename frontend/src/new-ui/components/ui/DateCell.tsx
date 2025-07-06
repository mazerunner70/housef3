import React from 'react';

interface DateCellProps {
  date: number | Date | string; // More flexible input types
  className?: string;
  format?: 'short' | 'long' | 'iso' | 'relative';
  showTime?: boolean;
}

const DateCell: React.FC<DateCellProps> = ({ 
  date, 
  className = '',
  format = 'short',
  showTime = false
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
    
    return dateObj.toLocaleDateString('en-US', options);
  };

  const getRelativeTime = (date: Date): string => {
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));
    
    if (diffInDays === 0) return 'Today';
    if (diffInDays === 1) return 'Yesterday';
    if (diffInDays < 7) return `${diffInDays} days ago`;
    if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
    if (diffInDays < 365) return `${Math.floor(diffInDays / 30)} months ago`;
    return `${Math.floor(diffInDays / 365)} years ago`;
  };

  return (
    <span className={`date-cell ${className}`} title={new Date(date).toLocaleString()}>
      {formatDate(date, format, showTime)}
    </span>
  );
};

export default DateCell; 
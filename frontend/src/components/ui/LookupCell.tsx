import React from 'react';

interface LookupCellProps {
  id?: string | number;
  lookupMap: Map<string, string> | Record<string, string>;
  fallback?: string;
  className?: string;
  showId?: boolean; // Show the ID if lookup fails
}

const LookupCell: React.FC<LookupCellProps> = ({ 
  id,
  lookupMap,
  fallback = 'N/A',
  className = '',
  showId = false
}) => {
  const getLookupValue = (): string => {
    if (!id) return fallback;
    
    const idString = String(id);
    
    // Handle Map
    if (lookupMap instanceof Map) {
      const value = lookupMap.get(idString);
      if (value) return value;
    } 
    // Handle Record/Object
    else {
      const value = lookupMap[idString];
      if (value) return value;
    }
    
    // Fallback options
    if (showId) {
      return `${fallback} (${idString})`;
    }
    
    return fallback;
  };

  const displayValue = getLookupValue();
  const isUnknown = displayValue === fallback || displayValue.includes(fallback);

  return (
    <span 
      className={`lookup-cell ${isUnknown ? 'lookup-unknown' : 'lookup-found'} ${className}`}
      title={id ? `ID: ${id}` : undefined}
    >
      {displayValue}
    </span>
  );
};

export default LookupCell; 
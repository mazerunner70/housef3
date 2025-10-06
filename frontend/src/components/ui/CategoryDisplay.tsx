import React from 'react';
import { CategoryInfo } from '../../services/TransactionService';

interface CategoryDisplayProps {
  category?: CategoryInfo;
  showIcon?: boolean;
  showParent?: boolean;
  className?: string;
  size?: 'small' | 'medium' | 'large';
  variant?: 'badge' | 'text' | 'chip';
}

const CategoryDisplay: React.FC<CategoryDisplayProps> = ({
  category,
  showIcon = true,
  showParent = false,
  className = '',
  size = 'medium',
  variant = 'badge',
}) => {
  if (!category) {
    return (
      <span className={`category-display category-empty ${size} ${variant} ${className}`}>
        Uncategorized
      </span>
    );
  }

  const getCategoryIcon = (categoryType: string): string => {
    const icons: { [key: string]: string } = {
      'INCOME': '💰',
      'EXPENSE': '💸',
      'TRANSFER': '🔄',
      'INVESTMENT': '📈',
      'BILLS': '📄',
      'FOOD': '🍽️',
      'TRANSPORT': '🚗',
      'SHOPPING': '🛍️',
      'ENTERTAINMENT': '🎬',
      'HEALTH': '🏥',
      'EDUCATION': '📚',
      'TRAVEL': '✈️',
      'OTHER': '📋',
    };
    return icons[categoryType?.toUpperCase()] || '📋';
  };

  const getCategoryColor = (categoryType: string): string => {
    const colors: { [key: string]: string } = {
      'INCOME': '#28a745',
      'EXPENSE': '#dc3545',
      'TRANSFER': '#6c757d',
      'INVESTMENT': '#17a2b8',
      'BILLS': '#ffc107',
      'FOOD': '#fd7e14',
      'TRANSPORT': '#20c997',
      'SHOPPING': '#e83e8c',
      'ENTERTAINMENT': '#6f42c1',
      'HEALTH': '#dc3545',
      'EDUCATION': '#007bff',
      'TRAVEL': '#17a2b8',
      'OTHER': '#6c757d',
    };
    return colors[categoryType?.toUpperCase()] || '#6c757d';
  };

  const displayName = showParent && category.parentName 
    ? `${category.parentName} > ${category.name}`
    : category.name;

  const icon = showIcon ? getCategoryIcon(category.type || 'OTHER') : '';
  const color = getCategoryColor(category.type || 'OTHER');

  const baseClass = `category-display category-${variant} category-${size}`;
  const typeClass = `category-type-${category.type?.toLowerCase() || 'other'}`;

  if (variant === 'badge') {
    return (
      <span 
        className={`${baseClass} ${typeClass} ${className}`}
        style={{ backgroundColor: `${color}20`, color: color, borderColor: color }}
      >
        {icon && <span className="category-icon">{icon}</span>}
        <span className="category-name">{displayName}</span>
      </span>
    );
  }

  if (variant === 'chip') {
    return (
      <span 
        className={`${baseClass} ${typeClass} ${className}`}
        style={{ backgroundColor: color, color: 'white' }}
      >
        {icon && <span className="category-icon">{icon}</span>}
        <span className="category-name">{displayName}</span>
      </span>
    );
  }

  // variant === 'text'
  return (
    <span className={`${baseClass} ${typeClass} ${className}`}>
      {icon && <span className="category-icon">{icon}</span>}
      <span className="category-name" style={{ color }}>{displayName}</span>
    </span>
  );
};

export default CategoryDisplay; 
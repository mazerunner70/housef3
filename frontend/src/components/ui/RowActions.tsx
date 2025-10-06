import React from 'react';

export interface ActionConfig {
  key: string;
  icon: string;
  label: string;
  onClick: (itemId: string) => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger' | 'success';
  showLabel?: boolean;
}

interface RowActionsProps {
  itemId: string;
  actions: ActionConfig[];
  className?: string;
  size?: 'small' | 'medium' | 'large';
  orientation?: 'horizontal' | 'vertical';
  showLabels?: boolean;
}

const RowActions: React.FC<RowActionsProps> = ({ 
  itemId,
  actions,
  className = '',
  size = 'medium',
  orientation = 'horizontal',
  showLabels = false
}) => {
  const getVariantClass = (variant: string = 'secondary'): string => {
    const variantMap = {
      primary: 'action-primary',
      secondary: 'action-secondary', 
      danger: 'action-danger',
      success: 'action-success'
    };
    return variantMap[variant as keyof typeof variantMap] || variantMap.secondary;
  };

  const orientationClass = `row-actions-${orientation}`;
  const sizeClass = `row-actions-${size}`;

  return (
    <div className={`row-actions ${orientationClass} ${sizeClass} ${className}`}>
      {actions.map((action) => (
        <button
          key={action.key}
          onClick={() => action.onClick(itemId)}
          className={`action-button ${getVariantClass(action.variant)}`}
          disabled={action.disabled}
          title={action.label}
          aria-label={action.label}
        >
          <span className="action-icon">{action.icon}</span>
          {(showLabels || action.showLabel) && (
            <span className="action-label">{action.label}</span>
          )}
        </button>
      ))}
    </div>
  );
};

export default RowActions; 
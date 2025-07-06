import React from 'react';

export type StatusVariant = 'processing' | 'success' | 'error' | 'warning' | 'pending' | 'unknown';

interface StatusBadgeProps {
  status: string;
  variant?: StatusVariant;
  className?: string;
  showIcon?: boolean;
  size?: 'small' | 'medium' | 'large';
  tooltip?: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  className = '',
  showIcon = true,
  size = 'medium',
  tooltip,
}) => {
  // Auto-determine variant from status if not provided
  const determineVariant = (statusText: string): StatusVariant => {
    const lowerStatus = statusText.toLowerCase();
    
    if (lowerStatus.includes('success') || lowerStatus.includes('completed') || lowerStatus.includes('processed')) {
      return 'success';
    }
    if (lowerStatus.includes('error') || lowerStatus.includes('failed') || lowerStatus.includes('rejected')) {
      return 'error';
    }
    if (lowerStatus.includes('warning') || lowerStatus.includes('partial')) {
      return 'warning';
    }
    if (lowerStatus.includes('processing') || lowerStatus.includes('uploading') || lowerStatus.includes('parsing')) {
      return 'processing';
    }
    if (lowerStatus.includes('pending') || lowerStatus.includes('queued') || lowerStatus.includes('waiting')) {
      return 'pending';
    }
    
    return 'unknown';
  };

  const getStatusIcon = (statusVariant: StatusVariant): string => {
    const icons = {
      processing: '🔄',
      success: '✅',
      error: '❌',
      warning: '⚠️',
      pending: '⏳',
      unknown: '❓'
    };
    return icons[statusVariant] || icons.unknown;
  };

  const getStatusColor = (statusVariant: StatusVariant): string => {
    const colors = {
      processing: '#17a2b8', // info blue
      success: '#28a745',    // success green
      error: '#dc3545',      // danger red
      warning: '#ffc107',    // warning yellow
      pending: '#6c757d',    // secondary gray
      unknown: '#6c757d'     // secondary gray
    };
    return colors[statusVariant] || colors.unknown;
  };

  const actualVariant = variant || determineVariant(status);
  const icon = getStatusIcon(actualVariant);
  const color = getStatusColor(actualVariant);

  const badgeClasses = [
    'status-badge',
    `status-badge-${actualVariant}`,
    `status-badge-${size}`,
    className
  ].filter(Boolean).join(' ');

  return (
    <span
      className={badgeClasses}
      style={{ color }}
      title={tooltip || status}
    >
      {showIcon && <span className="status-icon">{icon}</span>}
      <span className="status-text">{status}</span>
    </span>
  );
};

export default StatusBadge; 
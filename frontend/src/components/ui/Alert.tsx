import React from 'react';

export type AlertVariant = 'info' | 'success' | 'warning' | 'error';

interface AlertProps {
    variant: AlertVariant;
    title?: string;
    children: React.ReactNode;
    className?: string;
    onDismiss?: () => void;
    dismissible?: boolean;
}

const Alert: React.FC<AlertProps> = ({
    variant,
    title,
    children,
    className = '',
    onDismiss,
    dismissible = false
}) => {
    const alertClasses = `alert alert--${variant} ${className}`.trim();

    const getIcon = () => {
        switch (variant) {
            case 'success':
                return '✓';
            case 'warning':
                return '⚠';
            case 'error':
                return '✕';
            case 'info':
            default:
                return 'ℹ';
        }
    };

    return (
        <div className={alertClasses} role="alert">
            <div className="alert__icon">
                {getIcon()}
            </div>
            <div className="alert__content">
                {title && <div className="alert__title">{title}</div>}
                <div className="alert__message">{children}</div>
            </div>
            {dismissible && onDismiss && (
                <button
                    className="alert__dismiss"
                    onClick={onDismiss}
                    aria-label="Dismiss alert"
                >
                    ×
                </button>
            )}
        </div>
    );
};

export default Alert;

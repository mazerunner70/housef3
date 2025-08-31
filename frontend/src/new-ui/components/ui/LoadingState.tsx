import React from 'react';

interface LoadingStateProps {
    message?: string;
    size?: 'small' | 'medium' | 'large';
    variant?: 'spinner' | 'dots' | 'pulse';
    className?: string;
}

const LoadingState: React.FC<LoadingStateProps> = ({
    message = 'Loading...',
    size = 'medium',
    variant = 'spinner',
    className = ''
}) => {
    const containerClasses = `loading-state loading-state--${size} ${className}`.trim();
    const loaderClasses = `loading-state__loader loading-state__loader--${variant}`;

    return (
        <div className={containerClasses}>
            <div className={loaderClasses} aria-hidden="true">
                {variant === 'spinner' && <div className="loading-state__spinner" />}
                {variant === 'dots' && (
                    <div className="loading-state__dots">
                        <div className="loading-state__dot" />
                        <div className="loading-state__dot" />
                        <div className="loading-state__dot" />
                    </div>
                )}
                {variant === 'pulse' && <div className="loading-state__pulse" />}
            </div>
            {message && (
                <div className="loading-state__message" aria-live="polite">
                    {message}
                </div>
            )}
        </div>
    );
};

export default LoadingState;

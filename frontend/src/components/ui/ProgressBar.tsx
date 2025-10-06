import React from 'react';

interface ProgressBarProps {
    percentage: number;
    label?: string;
    showPercentage?: boolean;
    size?: 'small' | 'medium' | 'large';
    variant?: 'default' | 'success' | 'warning' | 'error';
    className?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
    percentage,
    label,
    showPercentage = true,
    size = 'medium',
    variant = 'default',
    className = ''
}) => {
    // Clamp percentage between 0 and 100
    const clampedPercentage = Math.max(0, Math.min(100, percentage));

    const progressClasses = `progress-bar progress-bar--${size} progress-bar--${variant} ${className}`.trim();
    const fillClasses = `progress-bar__fill progress-bar__fill--${variant}`;

    return (
        <div className={progressClasses}>
            {label && <div className="progress-bar__label">{label}</div>}
            <div className="progress-bar__track">
                <div
                    className={fillClasses}
                    style={{ width: `${clampedPercentage}%` }}
                    role="progressbar"
                    aria-valuenow={clampedPercentage}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={label || `${clampedPercentage}% complete`}
                />
            </div>
            {showPercentage && (
                <div className="progress-bar__percentage">
                    {Math.round(clampedPercentage)}% complete
                </div>
            )}
        </div>
    );
};

export default ProgressBar;

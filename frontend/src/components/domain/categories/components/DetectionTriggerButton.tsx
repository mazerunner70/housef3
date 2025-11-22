/**
 * DetectionTriggerButton Component
 * 
 * Button to trigger recurring charge detection with loading state.
 */

import React, { useState } from 'react';
import Button from '@/components/ui/Button';
import './DetectionTriggerButton.css';

export interface DetectionTriggerButtonProps {
    onTrigger: () => Promise<void>;
    disabled?: boolean;
    loading?: boolean;
    variant?: 'primary' | 'secondary' | 'tertiary' | 'danger';
    size?: 'standard' | 'compact';
    className?: string;
}

const DetectionTriggerButton: React.FC<DetectionTriggerButtonProps> = ({
    onTrigger,
    disabled = false,
    loading: externalLoading = false,
    variant = 'primary',
    size = 'standard',
    className = ''
}) => {
    const [internalLoading, setInternalLoading] = useState(false);

    const isLoading = externalLoading || internalLoading;

    const handleClick = async () => {
        if (isLoading || disabled) return;

        setInternalLoading(true);
        try {
            await onTrigger();
        } finally {
            setInternalLoading(false);
        }
    };

    const buttonClasses = [
        'detection-trigger-button',
        isLoading && 'detection-trigger-button--loading',
        className
    ].filter(Boolean).join(' ');

    return (
        <Button
            variant={variant}
            size={size}
            onClick={handleClick}
            disabled={disabled || isLoading}
            className={buttonClasses}
        >
            {isLoading ? (
                <>
                    <span className="detection-trigger-button__spinner" />
                    <span>Detecting Patterns...</span>
                </>
            ) : (
                <>
                    <span className="detection-trigger-button__icon">🔍</span>
                    <span>Detect Recurring Charges</span>
                </>
            )}
        </Button>
    );
};

export default DetectionTriggerButton;


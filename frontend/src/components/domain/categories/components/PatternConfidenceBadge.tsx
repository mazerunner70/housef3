/**
 * PatternConfidenceBadge Component
 * 
 * Displays a confidence score for recurring charge patterns with visual indicators.
 */

import React from 'react';
import { getConfidenceLevel, getConfidenceColor } from '@/types/RecurringCharge';
import './PatternConfidenceBadge.css';

export interface PatternConfidenceBadgeProps {
    confidence: number; // 0.0-1.0
    size?: 'small' | 'medium' | 'large';
    showLabel?: boolean;
    showPercentage?: boolean;
    className?: string;
}

const PatternConfidenceBadge: React.FC<PatternConfidenceBadgeProps> = ({
    confidence,
    size = 'medium',
    showLabel = true,
    showPercentage = true,
    className = ''
}) => {
    const level = getConfidenceLevel(confidence);
    const color = getConfidenceColor(confidence);
    const percentage = Math.round(confidence * 100);

    const getIcon = (): string => {
        if (level === 'high') return '✓';
        if (level === 'medium') return '~';
        return '!';
    };

    const getLabel = (): string => {
        if (level === 'high') return 'High Confidence';
        if (level === 'medium') return 'Medium Confidence';
        return 'Low Confidence';
    };

    const badgeClasses = [
        'pattern-confidence-badge',
        `pattern-confidence-badge--${level}`,
        `pattern-confidence-badge--${size}`,
        className
    ].filter(Boolean).join(' ');

    return (
        <span
            className={badgeClasses}
            style={{ borderColor: color, color }}
            title={`Confidence: ${percentage}%`}
        >
            <span className="pattern-confidence-badge__icon">{getIcon()}</span>
            {showLabel && (
                <span className="pattern-confidence-badge__label">{getLabel()}</span>
            )}
            {showPercentage && (
                <span className="pattern-confidence-badge__percentage">{percentage}%</span>
            )}
        </span>
    );
};

export default PatternConfidenceBadge;


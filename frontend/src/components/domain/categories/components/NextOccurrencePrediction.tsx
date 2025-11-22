/**
 * NextOccurrencePrediction Component
 * 
 * Displays prediction information for the next occurrence of a recurring charge.
 */

import React from 'react';
import {
    RecurringChargePrediction,
    RecurringChargePattern,
    formatAmount,
    formatDate,
    formatRelativeDate
} from '@/types/RecurringCharge';
import PatternConfidenceBadge from './PatternConfidenceBadge';
import './NextOccurrencePrediction.css';

export interface NextOccurrencePredictionProps {
    prediction: RecurringChargePrediction;
    pattern?: RecurringChargePattern;
    compact?: boolean;
    showConfidence?: boolean;
    className?: string;
}

const NextOccurrencePrediction: React.FC<NextOccurrencePredictionProps> = ({
    prediction,
    pattern,
    compact = false,
    showConfidence = true,
    className = ''
}) => {
    const isOverdue = prediction.daysUntilDue < 0;
    const isDueSoon = prediction.daysUntilDue >= 0 && prediction.daysUntilDue <= 7;

    const componentClasses = [
        'next-occurrence-prediction',
        compact && 'next-occurrence-prediction--compact',
        isOverdue && 'next-occurrence-prediction--overdue',
        isDueSoon && 'next-occurrence-prediction--due-soon',
        className
    ].filter(Boolean).join(' ');

    return (
        <div className={componentClasses}>
            <div className="next-occurrence-prediction__header">
                <div className="next-occurrence-prediction__date">
                    <span className="next-occurrence-prediction__date-label">
                        {isOverdue ? 'Expected' : 'Next Due'}:
                    </span>
                    <span className="next-occurrence-prediction__date-value">
                        {formatDate(prediction.nextExpectedDate)}
                    </span>
                    <span className="next-occurrence-prediction__date-relative">
                        ({formatRelativeDate(prediction.nextExpectedDate)})
                    </span>
                </div>
                {showConfidence && (
                    <PatternConfidenceBadge
                        confidence={prediction.confidence}
                        size={compact ? 'small' : 'medium'}
                        showLabel={!compact}
                    />
                )}
            </div>

            <div className="next-occurrence-prediction__amount">
                <span className="next-occurrence-prediction__amount-label">
                    Expected Amount:
                </span>
                <span className="next-occurrence-prediction__amount-value">
                    {formatAmount(prediction.expectedAmount)}
                </span>
                {!compact && prediction.amountRange && (
                    <span className="next-occurrence-prediction__amount-range">
                        (Range: {formatAmount(prediction.amountRange.min)} - {formatAmount(prediction.amountRange.max)})
                    </span>
                )}
            </div>

            {!compact && pattern && (
                <div className="next-occurrence-prediction__pattern-info">
                    <span className="next-occurrence-prediction__merchant">
                        {pattern.merchantPattern}
                    </span>
                </div>
            )}

            {isOverdue && (
                <div className="next-occurrence-prediction__warning">
                    ⚠️ This charge may be overdue or the pattern may have changed
                </div>
            )}
        </div>
    );
};

export default NextOccurrencePrediction;


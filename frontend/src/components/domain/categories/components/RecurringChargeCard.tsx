/**
 * RecurringChargeCard Component
 * 
 * Displays a single recurring charge pattern with actions.
 * Domain component specific to category management.
 */

import React, { useState } from 'react';
import {
    RecurringChargePattern,
    getFrequencyLabel,
    getTemporalPatternLabel,
    getDayOfWeekLabel,
    formatAmount,
    formatDate
} from '@/types/RecurringCharge';
import {
    PatternConfidenceBadge,
    Button
} from '@/components/ui';
import './RecurringChargeCard.css';

export interface RecurringChargeCardProps {
    pattern: RecurringChargePattern;
    categoryName?: string;
    onEdit?: (pattern: RecurringChargePattern) => void;
    onDelete?: (patternId: string) => void;
    onToggleActive?: (patternId: string, active: boolean) => void;
    onLinkToCategory?: (patternId: string) => void;
    onUnlinkFromCategory?: (patternId: string) => void;
    showActions?: boolean;
}

const RecurringChargeCard: React.FC<RecurringChargeCardProps> = ({
    pattern,
    categoryName,
    onEdit,
    onDelete,
    onToggleActive,
    onLinkToCategory,
    onUnlinkFromCategory,
    showActions = true
}) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    const handleToggleActive = async () => {
        if (onToggleActive) {
            await onToggleActive(pattern.patternId, !pattern.active);
        }
    };

    const handleDelete = async () => {
        if (!onDelete) return;

        if (confirm(`Are you sure you want to delete this pattern for "${pattern.merchantPattern}"?`)) {
            setIsDeleting(true);
            try {
                await onDelete(pattern.patternId);
            } finally {
                setIsDeleting(false);
            }
        }
    };

    const handleLinkToCategory = () => {
        if (onLinkToCategory) {
            onLinkToCategory(pattern.patternId);
        }
    };

    const handleUnlinkFromCategory = () => {
        if (onUnlinkFromCategory) {
            onUnlinkFromCategory(pattern.patternId);
        }
    };

    const cardClasses = [
        'recurring-charge-card',
        !pattern.active && 'recurring-charge-card--inactive',
        isDeleting && 'recurring-charge-card--deleting'
    ].filter(Boolean).join(' ');

    return (
        <div className={cardClasses}>
            <div className="recurring-charge-card__header">
                <div className="recurring-charge-card__title-section">
                    <div className="recurring-charge-card__merchant">
                        {pattern.merchantPattern}
                    </div>
                    <div className="recurring-charge-card__meta">
                        <span className="recurring-charge-card__frequency">
                            {getFrequencyLabel(pattern.frequency)}
                        </span>
                        <span className="recurring-charge-card__separator">•</span>
                        <span className="recurring-charge-card__count">
                            {pattern.transactionCount} transactions
                        </span>
                    </div>
                </div>

                <div className="recurring-charge-card__badges">
                    <PatternConfidenceBadge
                        confidence={pattern.confidenceScore}
                        size="small"
                        showLabel={false}
                    />
                    {!pattern.active && (
                        <span className="recurring-charge-card__inactive-badge">Inactive</span>
                    )}
                </div>
            </div>

            <div className="recurring-charge-card__body">
                <div className="recurring-charge-card__amount-section">
                    <div className="recurring-charge-card__amount-label">Expected Amount</div>
                    <div className="recurring-charge-card__amount-value">
                        {formatAmount(pattern.amountMean)}
                    </div>
                    <div className="recurring-charge-card__amount-range">
                        Range: {formatAmount(pattern.amountMin)} - {formatAmount(pattern.amountMax)}
                    </div>
                </div>

                {categoryName && (
                    <div className="recurring-charge-card__category-section">
                        <div className="recurring-charge-card__category-label">Linked Category</div>
                        <div className="recurring-charge-card__category-name">
                            {categoryName}
                            {pattern.autoCategorize && (
                                <span className="recurring-charge-card__auto-badge">Auto</span>
                            )}
                        </div>
                    </div>
                )}

                {isExpanded && (
                    <div className="recurring-charge-card__details">
                        <div className="recurring-charge-card__detail-row">
                            <span className="recurring-charge-card__detail-label">Temporal Pattern:</span>
                            <span className="recurring-charge-card__detail-value">
                                {getTemporalPatternLabel(pattern.temporalPatternType)}
                                {pattern.dayOfWeek !== undefined && ` (${getDayOfWeekLabel(pattern.dayOfWeek)})`}
                                {pattern.dayOfMonth !== undefined && ` (Day ${pattern.dayOfMonth})`}
                            </span>
                        </div>
                        <div className="recurring-charge-card__detail-row">
                            <span className="recurring-charge-card__detail-label">First Seen:</span>
                            <span className="recurring-charge-card__detail-value">
                                {formatDate(pattern.firstOccurrence)}
                            </span>
                        </div>
                        <div className="recurring-charge-card__detail-row">
                            <span className="recurring-charge-card__detail-label">Last Seen:</span>
                            <span className="recurring-charge-card__detail-value">
                                {formatDate(pattern.lastOccurrence)}
                            </span>
                        </div>
                        <div className="recurring-charge-card__detail-row">
                            <span className="recurring-charge-card__detail-label">Tolerance:</span>
                            <span className="recurring-charge-card__detail-value">
                                ±{pattern.toleranceDays} days, ±{pattern.amountTolerancePct}%
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {showActions && (
                <div className="recurring-charge-card__actions">
                    <button
                        className="recurring-charge-card__expand-btn"
                        onClick={() => setIsExpanded(!isExpanded)}
                    >
                        {isExpanded ? 'Show Less' : 'Show More'}
                    </button>

                    <div className="recurring-charge-card__action-buttons">
                        {pattern.suggestedCategoryId ? (
                            <Button
                                variant="secondary"
                                size="compact"
                                onClick={handleUnlinkFromCategory}
                                disabled={isDeleting}
                            >
                                Unlink Category
                            </Button>
                        ) : (
                            <Button
                                variant="secondary"
                                size="compact"
                                onClick={handleLinkToCategory}
                                disabled={isDeleting}
                            >
                                Link to Category
                            </Button>
                        )}

                        <Button
                            variant="secondary"
                            size="compact"
                            onClick={handleToggleActive}
                            disabled={isDeleting}
                        >
                            {pattern.active ? 'Deactivate' : 'Activate'}
                        </Button>

                        {onDelete && (
                            <Button
                                variant="danger"
                                size="compact"
                                onClick={handleDelete}
                                disabled={isDeleting}
                            >
                                {isDeleting ? 'Deleting...' : 'Delete'}
                            </Button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default RecurringChargeCard;


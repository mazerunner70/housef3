/**
 * RecurringChargesTab Component
 * 
 * Main tab component for managing recurring charge patterns within category management.
 * Displays patterns, allows detection, and provides pattern management actions.
 */

import React, { useEffect, useState } from 'react';
import { useRecurringCharges } from '@/stores/recurringChargeStore';
import { useCategories } from '@/hooks/useCategories';
import {
    DetectionTriggerButton,
    LoadingState,
    Alert,
    LinkToCategoryDialog
} from '@/components/ui';
import RecurringChargeCard from './RecurringChargeCard';
import { RecurringChargePattern } from '@/types/RecurringCharge';
import './RecurringChargesTab.css';

interface RecurringChargesTabProps {
    categoryId?: string; // If provided, filter patterns for this category
}

const RecurringChargesTab: React.FC<RecurringChargesTabProps> = ({ categoryId }) => {
    const {
        patterns,
        isLoading,
        error,
        fetchPatterns,
        deletePattern,
        toggleActive,
        linkToCategory,
        unlinkFromCategory,
        triggerDetection,
        clearError,
        setFilters
    } = useRecurringCharges();

    const { categories } = useCategories();

    const [linkDialogPattern, setLinkDialogPattern] = useState<RecurringChargePattern | null>(null);
    const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined);
    const [filterConfidence, setFilterConfidence] = useState<number>(0);

    // Load patterns on mount
    useEffect(() => {
        fetchPatterns();
    }, [fetchPatterns]);

    // Apply filters when they change
    useEffect(() => {
        setFilters({
            active: filterActive,
            minConfidence: filterConfidence > 0 ? filterConfidence / 100 : undefined,
            categoryId
        });
    }, [filterActive, filterConfidence, categoryId, setFilters]);

    const handleTriggerDetection = async () => {
        const operationId = await triggerDetection();
        if (operationId) {
            // Show success message
            alert('Detection started! Patterns will be updated shortly.');
            // Refresh patterns after a delay
            setTimeout(() => {
                fetchPatterns(true);
            }, 3000);
        }
    };

    const handleDeletePattern = async (patternId: string) => {
        const success = await deletePattern(patternId);
        if (success) {
            // Pattern deleted successfully
        }
    };

    const handleToggleActive = async (patternId: string, active: boolean) => {
        await toggleActive(patternId, active);
    };

    const handleLinkToCategory = (patternId: string) => {
        const pattern = patterns.find(p => p.patternId === patternId);
        if (pattern) {
            setLinkDialogPattern(pattern);
        }
    };

    const handleUnlinkFromCategory = async (patternId: string) => {
        await unlinkFromCategory(patternId);
    };

    const handleConfirmLink = async (categoryId: string, autoCategorize: boolean) => {
        if (linkDialogPattern) {
            await linkToCategory(linkDialogPattern.patternId, categoryId, autoCategorize);
            setLinkDialogPattern(null);
        }
    };

    const getCategoryName = (categoryId?: string): string | undefined => {
        if (!categoryId) return undefined;
        const category = categories.find(c => c.categoryId === categoryId);
        return category?.name;
    };

    // Filter patterns based on current filters
    const filteredPatterns = patterns.filter(pattern => {
        if (filterActive !== undefined && pattern.active !== filterActive) {
            return false;
        }
        if (filterConfidence > 0 && pattern.confidenceScore < filterConfidence / 100) {
            return false;
        }
        return true;
    });

    const activePatternCount = patterns.filter(p => p.active).length;
    const linkedPatternCount = patterns.filter(p => p.suggestedCategoryId).length;

    return (
        <div className="recurring-charges-tab">
            <div className="recurring-charges-tab__header">
                <div className="recurring-charges-tab__title-section">
                    <h2>Recurring Charge Patterns</h2>
                    <p className="recurring-charges-tab__description">
                        Automatically detected recurring charges based on transaction patterns.
                    </p>
                </div>

                <DetectionTriggerButton
                    onTrigger={handleTriggerDetection}
                    disabled={isLoading}
                />
            </div>

            {error && (
                <Alert
                    variant="error"
                    dismissible={true}
                    onDismiss={clearError}
                >
                    {error}
                </Alert>
            )}

            <div className="recurring-charges-tab__stats">
                <div className="recurring-charges-tab__stat">
                    <span className="recurring-charges-tab__stat-value">{patterns.length}</span>
                    <span className="recurring-charges-tab__stat-label">Total Patterns</span>
                </div>
                <div className="recurring-charges-tab__stat">
                    <span className="recurring-charges-tab__stat-value">{activePatternCount}</span>
                    <span className="recurring-charges-tab__stat-label">Active</span>
                </div>
                <div className="recurring-charges-tab__stat">
                    <span className="recurring-charges-tab__stat-value">{linkedPatternCount}</span>
                    <span className="recurring-charges-tab__stat-label">Linked to Categories</span>
                </div>
            </div>

            <div className="recurring-charges-tab__filters">
                <div className="recurring-charges-tab__filter">
                    <label htmlFor="filter-active">Status:</label>
                    <select
                        id="filter-active"
                        value={filterActive === undefined ? 'all' : filterActive ? 'active' : 'inactive'}
                        onChange={(e) => {
                            const value = e.target.value;
                            setFilterActive(value === 'all' ? undefined : value === 'active');
                        }}
                    >
                        <option value="all">All</option>
                        <option value="active">Active Only</option>
                        <option value="inactive">Inactive Only</option>
                    </select>
                </div>

                <div className="recurring-charges-tab__filter">
                    <label htmlFor="filter-confidence">Min Confidence:</label>
                    <select
                        id="filter-confidence"
                        value={filterConfidence}
                        onChange={(e) => setFilterConfidence(Number(e.target.value))}
                    >
                        <option value="0">Any</option>
                        <option value="60">60%+</option>
                        <option value="70">70%+</option>
                        <option value="80">80%+</option>
                        <option value="90">90%+</option>
                    </select>
                </div>
            </div>

            {isLoading && patterns.length === 0 ? (
                <LoadingState message="Loading recurring charge patterns..." />
            ) : filteredPatterns.length === 0 ? (
                <div className="recurring-charges-tab__empty">
                    <div className="recurring-charges-tab__empty-icon">🔍</div>
                    <h3>No Patterns Found</h3>
                    <p>
                        {patterns.length === 0
                            ? 'No recurring charge patterns have been detected yet. Click "Detect Recurring Charges" to analyze your transactions.'
                            : 'No patterns match the current filters. Try adjusting your filter criteria.'}
                    </p>
                </div>
            ) : (
                <div className="recurring-charges-tab__patterns">
                    {filteredPatterns.map(pattern => (
                        <RecurringChargeCard
                            key={pattern.patternId}
                            pattern={pattern}
                            categoryName={getCategoryName(pattern.suggestedCategoryId)}
                            onDelete={handleDeletePattern}
                            onToggleActive={handleToggleActive}
                            onLinkToCategory={handleLinkToCategory}
                            onUnlinkFromCategory={handleUnlinkFromCategory}
                        />
                    ))}
                </div>
            )}

            {linkDialogPattern && (
                <LinkToCategoryDialog
                    pattern={linkDialogPattern}
                    isOpen={true}
                    onClose={() => setLinkDialogPattern(null)}
                    onConfirm={handleConfirmLink}
                />
            )}
        </div>
    );
};

export default RecurringChargesTab;


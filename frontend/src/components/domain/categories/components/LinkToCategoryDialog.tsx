/**
 * LinkToCategoryDialog Component
 * 
 * Modal dialog for linking a recurring charge pattern to a category.
 */

import React, { useState, useEffect } from 'react';
import { RecurringChargePattern } from '@/types/RecurringCharge';
import { useCategories } from '@/hooks/useCategories';
import Button from '@/components/ui/Button';
import './LinkToCategoryDialog.css';

export interface LinkToCategoryDialogProps {
    pattern: RecurringChargePattern;
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (categoryId: string, autoCategorize: boolean) => Promise<void>;
}

const LinkToCategoryDialog: React.FC<LinkToCategoryDialogProps> = ({
    pattern,
    isOpen,
    onClose,
    onConfirm
}) => {
    const { categories, isLoading: categoriesLoading } = useCategories();
    const [selectedCategoryId, setSelectedCategoryId] = useState<string>(
        pattern.suggestedCategoryId || ''
    );
    const [autoCategorize, setAutoCategorize] = useState<boolean>(
        pattern.autoCategorize || false
    );
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Reset state when pattern changes
    useEffect(() => {
        setSelectedCategoryId(pattern.suggestedCategoryId || '');
        setAutoCategorize(pattern.autoCategorize || false);
        setError(null);
    }, [pattern]);

    if (!isOpen) return null;

    const handleOverlayClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget && !isSubmitting) {
            onClose();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Escape' && !isSubmitting) {
            onClose();
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!selectedCategoryId) {
            setError('Please select a category');
            return;
        }

        setIsSubmitting(true);
        setError(null);

        try {
            await onConfirm(selectedCategoryId, autoCategorize);
            onClose();
        } catch (err: any) {
            setError(err.message || 'Failed to link pattern to category');
        } finally {
            setIsSubmitting(false);
        }
    };

    // Filter categories to only show EXPENSE categories (most recurring charges are expenses)
    const expenseCategories = categories.filter(cat => cat.type === 'EXPENSE');

    return (
        <div
            className="link-category-dialog-overlay"
            onClick={handleOverlayClick}
            onKeyDown={handleKeyDown}
            tabIndex={0}
            role="dialog"
            aria-modal="true"
            aria-labelledby="link-category-dialog-title"
        >
            <div className="link-category-dialog">
                <div className="link-category-dialog__header">
                    <h3 id="link-category-dialog-title">Link to Category</h3>
                    <button
                        className="link-category-dialog__close"
                        onClick={onClose}
                        disabled={isSubmitting}
                        aria-label="Close dialog"
                    >
                        ×
                    </button>
                </div>

                <div className="link-category-dialog__body">
                    <div className="link-category-dialog__pattern-info">
                        <div className="link-category-dialog__pattern-merchant">
                            {pattern.merchantPattern}
                        </div>
                        <div className="link-category-dialog__pattern-details">
                            {pattern.frequency} • Confidence: {Math.round(pattern.confidenceScore * 100)}%
                        </div>
                    </div>

                    <form onSubmit={handleSubmit}>
                        <div className="link-category-dialog__field">
                            <label htmlFor="category-select">
                                Category <span className="required">*</span>
                            </label>
                            <select
                                id="category-select"
                                value={selectedCategoryId}
                                onChange={(e) => setSelectedCategoryId(e.target.value)}
                                disabled={isSubmitting || categoriesLoading}
                                required
                            >
                                <option value="">Select a category...</option>
                                {expenseCategories.map(category => (
                                    <option key={category.categoryId} value={category.categoryId}>
                                        {category.name}
                                    </option>
                                ))}
                            </select>
                            {categoriesLoading && (
                                <span className="link-category-dialog__loading">Loading categories...</span>
                            )}
                        </div>

                        <div className="link-category-dialog__field">
                            <label className="link-category-dialog__checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={autoCategorize}
                                    onChange={(e) => setAutoCategorize(e.target.checked)}
                                    disabled={isSubmitting}
                                />
                                <span>Automatically categorize future transactions</span>
                            </label>
                            <p className="link-category-dialog__help-text">
                                When enabled, future transactions matching this pattern will be automatically
                                assigned to this category.
                            </p>
                        </div>

                        {error && (
                            <div className="link-category-dialog__error">
                                ⚠️ {error}
                            </div>
                        )}

                        <div className="link-category-dialog__actions">
                            <Button
                                type="button"
                                variant="secondary"
                                onClick={onClose}
                                disabled={isSubmitting}
                            >
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                variant="primary"
                                disabled={isSubmitting || !selectedCategoryId}
                            >
                                {isSubmitting ? 'Linking...' : 'Link to Category'}
                            </Button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default LinkToCategoryDialog;


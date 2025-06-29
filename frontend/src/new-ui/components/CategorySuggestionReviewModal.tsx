import React, { useState, useEffect, useCallback } from 'react';
import { Transaction } from '../../services/TransactionService';
import { Category, TransactionCategoryAssignment, CategorySuggestionStrategy } from '../../types/Category';
import { useSuggestionReview } from '../hooks/useCategories';
import './CategorySuggestionReviewModal.css';

interface CategorySuggestionReviewModalProps {
  transaction: Transaction;
  categorySuggestions: TransactionCategoryAssignment[];
  availableCategories: Category[];
  onConfirmSuggestions: (confirmedCategoryIds: string[], primaryCategoryId: string) => Promise<void>;
  onRejectSuggestion: (categoryId: string) => Promise<void>;
  onClose: () => void;
  isOpen: boolean;
  strategy?: CategorySuggestionStrategy;
}

const CategorySuggestionReviewModal: React.FC<CategorySuggestionReviewModalProps> = ({
  transaction,
  categorySuggestions,
  availableCategories,
  onConfirmSuggestions,
  onRejectSuggestion,
  onClose,
  isOpen,
  strategy = 'all_matches'
}) => {
  const [confirmedCategories, setConfirmedCategories] = useState<Set<string>>(new Set());
  const [primaryCategory, setPrimaryCategory] = useState<string>('');
  const [rejectedCategories, setRejectedCategories] = useState<Set<string>>(new Set());
  const [isProcessing, setIsProcessing] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  // Initialize with highest confidence suggestion
  useEffect(() => {
    if (isOpen && categorySuggestions.length > 0) {
      // Sort suggestions by confidence (highest first)
      const sortedSuggestions = [...categorySuggestions].sort((a, b) => b.confidence - a.confidence);
      const highest = sortedSuggestions[0];
      
      setPrimaryCategory(highest.categoryId);
      setConfirmedCategories(new Set([highest.categoryId]));
      setRejectedCategories(new Set());
    }
  }, [isOpen, categorySuggestions]);

  const getCategoryName = useCallback((categoryId: string): string => {
    const category = availableCategories.find(c => c.categoryId === categoryId);
    return category?.name || 'Unknown Category';
  }, [availableCategories]);

  const getCategoryColor = useCallback((categoryId: string): string => {
    const category = availableCategories.find(c => c.categoryId === categoryId);
    return category?.color || '#667eea';
  }, [availableCategories]);

  const getConfidenceLevel = useCallback((confidence: number): 'high' | 'medium' | 'low' => {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.6) return 'medium';
    return 'low';
  }, []);

  const getConfidenceColor = useCallback((confidence: number): string => {
    const level = getConfidenceLevel(confidence);
    switch (level) {
      case 'high': return '#22c55e';
      case 'medium': return '#f59e0b';
      case 'low': return '#ef4444';
      default: return '#6b7280';
    }
  }, [getConfidenceLevel]);

  const handleCategoryToggle = useCallback((categoryId: string) => {
    if (rejectedCategories.has(categoryId)) return; // Can't select rejected categories

    const newConfirmed = new Set(confirmedCategories);
    if (newConfirmed.has(categoryId)) {
      newConfirmed.delete(categoryId);
      // If removing primary category, set new primary
      if (primaryCategory === categoryId) {
        const remaining = Array.from(newConfirmed);
        setPrimaryCategory(remaining.length > 0 ? remaining[0] : '');
      }
    } else {
      newConfirmed.add(categoryId);
      // If no primary set, make this the primary
      if (!primaryCategory || !newConfirmed.has(primaryCategory)) {
        setPrimaryCategory(categoryId);
      }
    }
    setConfirmedCategories(newConfirmed);
  }, [confirmedCategories, rejectedCategories, primaryCategory]);

  const handleRejectSuggestion = useCallback(async (categoryId: string) => {
    try {
      await onRejectSuggestion(categoryId);
      
      // Update local state
      setRejectedCategories(prev => new Set(prev).add(categoryId));
      setConfirmedCategories(prev => {
        const newSet = new Set(prev);
        newSet.delete(categoryId);
        return newSet;
      });
      
      if (primaryCategory === categoryId) {
        const remaining = Array.from(confirmedCategories).filter(id => id !== categoryId);
        setPrimaryCategory(remaining.length > 0 ? remaining[0] : '');
      }
    } catch (error) {
      console.error('Error rejecting suggestion:', error);
    }
  }, [onRejectSuggestion, primaryCategory, confirmedCategories]);

  const handleConfirmAll = useCallback(() => {
    const highConfidenceSuggestions = categorySuggestions.filter(s => s.confidence >= 0.8);
    const categoryIds = highConfidenceSuggestions.map(s => s.categoryId);
    
    setConfirmedCategories(new Set(categoryIds));
    if (categoryIds.length > 0 && !categoryIds.includes(primaryCategory)) {
      setPrimaryCategory(categoryIds[0]);
    }
  }, [categorySuggestions, primaryCategory]);

  const handleRejectAll = useCallback(async () => {
    setIsProcessing(true);
    try {
      for (const suggestion of categorySuggestions) {
        await handleRejectSuggestion(suggestion.categoryId);
      }
      onClose();
    } catch (error) {
      console.error('Error rejecting all suggestions:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [categorySuggestions, handleRejectSuggestion, onClose]);

  const handleConfirmSuggestions = useCallback(async () => {
    if (confirmedCategories.size === 0 || !primaryCategory) return;

    setIsProcessing(true);
    try {
      await onConfirmSuggestions(Array.from(confirmedCategories), primaryCategory);
      onClose();
    } catch (error) {
      console.error('Error confirming suggestions:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [confirmedCategories, primaryCategory, onConfirmSuggestions, onClose]);

  const formatAmount = useCallback((amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(Math.abs(amount));
  }, []);

  const formatDate = useCallback((date: number): string => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }, []);

  const visibleSuggestions = categorySuggestions.filter(s => !rejectedCategories.has(s.categoryId));

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="suggestion-review-modal">
        <div className="modal-header">
          <div className="header-content">
            <h3>🎯 Review Category Suggestions</h3>
            <p>
              Strategy: <span className="strategy-badge">{strategy.replace('_', ' ')}</span>
            </p>
          </div>
          <button className="close-btn" onClick={onClose} disabled={isProcessing}>
            ✕
          </button>
        </div>
        
        <div className="modal-content">
          {/* Transaction Summary */}
          <div className="transaction-summary">
            <div className="summary-header">
              <h4>💳 Transaction Details</h4>
              <button
                className="details-toggle"
                onClick={() => setShowDetails(!showDetails)}
              >
                {showDetails ? '👁️ Hide' : '👁️‍🗨️ Show'} Details
              </button>
            </div>
            
            <div className="transaction-info">
              <div className="info-row primary">
                <span className="info-label">Description:</span>
                <span className="info-value">{transaction.description}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Amount:</span>
                <span className={`info-value amount ${Number(transaction.amount) >= 0 ? 'positive' : 'negative'}`}>
                  {formatAmount(Number(transaction.amount))}
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Date:</span>
                <span className="info-value">{formatDate(transaction.date)}</span>
              </div>
              
              {showDetails && (
                <>
                  {transaction.payee && (
                    <div className="info-row">
                      <span className="info-label">Payee:</span>
                      <span className="info-value">{transaction.payee}</span>
                    </div>
                  )}
                  {transaction.memo && (
                    <div className="info-row">
                      <span className="info-label">Memo:</span>
                      <span className="info-value">{transaction.memo}</span>
                    </div>
                  )}
                  <div className="info-row">
                    <span className="info-label">Account:</span>
                    <span className="info-value">{transaction.accountId || 'Unknown'}</span>
                  </div>
                </>
              )}
            </div>
          </div>
          
          {/* Quick Actions */}
          <div className="quick-actions">
            <button
              className="quick-action-btn confirm-all"
              onClick={handleConfirmAll}
              disabled={isProcessing}
            >
              ✅ Confirm High Confidence
            </button>
            <button
              className="quick-action-btn reject-all"
              onClick={handleRejectAll}
              disabled={isProcessing}
            >
              ❌ Reject All
            </button>
          </div>

          {/* Suggestion Options */}
          <div className="suggestion-options">
            <div className="options-header">
              <h4>📋 Suggested Categories ({visibleSuggestions.length})</h4>
              <p className="instruction-text">
                Select categories to confirm. Multiple categories can be assigned to one transaction.
              </p>
            </div>
            
            {visibleSuggestions.length === 0 ? (
              <div className="no-suggestions">
                <span className="no-suggestions-icon">🚫</span>
                <p>All suggestions have been rejected.</p>
              </div>
            ) : (
              <div className="suggestions-list">
                {visibleSuggestions.map((suggestion) => {
                  const categoryName = getCategoryName(suggestion.categoryId);
                  const categoryColor = getCategoryColor(suggestion.categoryId);
                  const confidenceLevel = getConfidenceLevel(suggestion.confidence);
                  const confidenceColor = getConfidenceColor(suggestion.confidence);
                  const isConfirmed = confirmedCategories.has(suggestion.categoryId);
                  const isPrimary = primaryCategory === suggestion.categoryId;
                  
                  return (
                    <div 
                      key={suggestion.categoryId} 
                      className={`suggestion-option ${isConfirmed ? 'confirmed' : ''} ${isPrimary ? 'primary' : ''}`}
                    >
                      <div className="option-main">
                        <label className="category-option">
                          <input
                            type="checkbox"
                            checked={isConfirmed}
                            onChange={() => handleCategoryToggle(suggestion.categoryId)}
                            disabled={isProcessing}
                          />
                          
                          <div className="category-details">
                            <div className="category-header">
                              <span 
                                className="category-name"
                                style={{ borderLeftColor: categoryColor }}
                              >
                                {categoryName}
                              </span>
                              <div className="confidence-indicator">
                                <span 
                                  className={`confidence-badge ${confidenceLevel}`}
                                  style={{ backgroundColor: confidenceColor }}
                                >
                                  {Math.round(suggestion.confidence * 100)}%
                                </span>
                                <span className="confidence-level">{confidenceLevel}</span>
                              </div>
                            </div>
                            
                            <div className="suggestion-metadata">
                              <span className="suggestion-status">
                                Status: {suggestion.status}
                              </span>
                              {suggestion.ruleId && (
                                <span className="matching-rule">
                                  Rule: {suggestion.ruleId}
                                </span>
                              )}
                              {suggestion.isManual && (
                                <span className="manual-indicator">Manual</span>
                              )}
                            </div>
                            
                            {suggestion.assignedAt && (
                              <div className="suggestion-timing">
                                Suggested: {formatDate(suggestion.assignedAt)}
                              </div>
                            )}
                          </div>
                        </label>
                        
                        <div className="option-actions">
                          {isConfirmed && (
                            <label className="primary-radio">
                              <input
                                type="radio"
                                name="primaryCategory"
                                checked={isPrimary}
                                onChange={() => setPrimaryCategory(suggestion.categoryId)}
                                disabled={isProcessing}
                              />
                              <span className="radio-label">Primary</span>
                            </label>
                          )}
                          
                          <button
                            className="reject-suggestion-btn"
                            onClick={() => handleRejectSuggestion(suggestion.categoryId)}
                            disabled={isProcessing}
                            title="Reject this suggestion"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Selected Summary */}
          {confirmedCategories.size > 0 && (
            <div className="selection-summary">
              <h4>📝 Selection Summary</h4>
              <div className="summary-content">
                <div className="summary-item">
                  <span className="summary-label">Categories Selected:</span>
                  <span className="summary-value">{confirmedCategories.size}</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Primary Category:</span>
                  <span className="summary-value primary-category">
                    {primaryCategory ? getCategoryName(primaryCategory) : 'None'}
                  </span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Assignment Type:</span>
                  <span className="summary-value">Confirmed Suggestion</span>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* Modal Actions */}
        <div className="modal-actions">
          <button 
            className="cancel-btn" 
            onClick={onClose}
            disabled={isProcessing}
          >
            Cancel
          </button>
          
          <button 
            className="confirm-btn" 
            onClick={handleConfirmSuggestions}
            disabled={isProcessing || confirmedCategories.size === 0 || !primaryCategory}
          >
            {isProcessing ? (
              <>
                <span className="loading-spinner">🔄</span>
                Processing...
              </>
            ) : (
              <>
                ✅ Confirm {confirmedCategories.size} Categories
              </>
            )}
          </button>
        </div>

        {/* Processing Overlay */}
        {isProcessing && (
          <div className="processing-overlay">
            <div className="processing-content">
              <div className="processing-spinner">🔄</div>
              <p>Processing suggestions...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CategorySuggestionReviewModal; 
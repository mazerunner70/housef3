import React, { useState, useRef, useEffect } from 'react';
import { CategoryService } from '@/services/CategoryService';
import { Category, MatchCondition } from '@/types/Category';
import './CategoryQuickSelector.css';

interface CategoryQuickSelectorProps {
  transactionId: string;
  transactionDescription: string;
  transactionAmount?: string;
  availableCategories: Category[];
  currentCategoryId?: string;
  onCategorySelect: (transactionId: string, categoryId: string) => void;
  onCreateNewCategory: (transactionData: {
    description: string;
    amount?: string;
    suggestedCategory?: {
      name: string;
      type: 'INCOME' | 'EXPENSE';
      confidence: number;
    };
    suggestedPatterns?: Array<{
      pattern: string;
      confidence: number;
      explanation: string;
    }>;
  }) => void;
  disabled?: boolean;
}

interface QuickSuggestion {
  suggestedCategory: {
    name: string;
    type: 'INCOME' | 'EXPENSE';
    confidence: number;
    merchantName?: string;
  };
  suggestedPatterns: Array<{
    pattern: string;
    confidence: number;
    explanation: string;
    matchCount: number;
  }>;
}

const CategoryQuickSelector: React.FC<CategoryQuickSelectorProps> = ({
  transactionId,
  transactionDescription,
  transactionAmount,
  availableCategories,
  currentCategoryId,
  onCategorySelect,
  onCreateNewCategory,
  disabled = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showRuleCreation, setShowRuleCreation] = useState(false);
  const [selectedCategoryForRule, setSelectedCategoryForRule] = useState<string>('');
  const [suggestedPattern, setSuggestedPattern] = useState('');
  const [patternMatchCount, setPatternMatchCount] = useState(0);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [quickSuggestion, setQuickSuggestion] = useState<QuickSuggestion | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Get current category name for display
  const currentCategory = availableCategories.find(cat => cat.categoryId === currentCategoryId);
  const displayText = currentCategory?.name || 'Uncategorized';

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setShowRuleCreation(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Load quick suggestions when dropdown opens
  useEffect(() => {
    if (isOpen && !currentCategoryId && !quickSuggestion) {
      loadQuickSuggestions();
    }
  }, [isOpen, currentCategoryId, quickSuggestion]);

  const loadQuickSuggestions = async () => {
    if (!transactionDescription) return;

    setIsLoadingSuggestions(true);
    try {
      const suggestions = await CategoryService.getQuickCategorySuggestions(transactionDescription);
      setQuickSuggestion(suggestions);
    } catch (error) {
      console.error('Error loading quick suggestions:', error);
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  const handleCategoryClick = (categoryId: string) => {
    if (categoryId === 'create-new') {
      handleCreateNewCategory();
      return;
    }

    const category = availableCategories.find(cat => cat.categoryId === categoryId);
    if (!category) return;

    setSelectedCategoryForRule(categoryId);

    // Check if we should offer rule creation
    if (!category.rules || category.rules.length === 0) {
      // Suggest creating a rule for this category
      setShowRuleCreation(true);
      generateSuggestedPattern();
    } else {
      // Category already has rules, just assign it
      onCategorySelect(transactionId, categoryId);
      setIsOpen(false);
    }
  };

  const handleCreateNewCategory = () => {
    onCreateNewCategory({
      description: transactionDescription,
      amount: transactionAmount,
      suggestedCategory: quickSuggestion?.suggestedCategory,
      suggestedPatterns: quickSuggestion?.suggestedPatterns
    });
    setIsOpen(false);
  };

  const generateSuggestedPattern = async () => {
    try {
      const suggestions = await CategoryService.getQuickCategorySuggestions(transactionDescription);
      if (suggestions.suggestedPatterns.length > 0) {
        const bestPattern = suggestions.suggestedPatterns[0];
        setSuggestedPattern(bestPattern.pattern);

        // Get match count preview
        const matchPreview = await CategoryService.previewPatternMatches(bestPattern.pattern, 'description');
        setPatternMatchCount(matchPreview.matchCount);
      }
    } catch (error) {
      console.error('Error generating pattern suggestions:', error);
      // Fallback to simple pattern extraction
      const words = transactionDescription.toUpperCase().split(/\s+/);
      const meaningfulWords = words.filter(word => word.length >= 3 && !['THE', 'AND', 'OR', 'AT', 'TO', 'FROM'].includes(word));
      if (meaningfulWords.length > 0) {
        setSuggestedPattern(meaningfulWords[0]);
        setPatternMatchCount(0);
      }
    }
  };

  const handleCreateWithRule = async () => {
    const category = availableCategories.find(cat => cat.categoryId === selectedCategoryForRule);
    if (!category || !suggestedPattern) return;

    try {
      // First assign the category
      onCategorySelect(transactionId, selectedCategoryForRule);

      // Then create the rule
      await CategoryService.addRuleToCategory(selectedCategoryForRule, {
        fieldToMatch: 'description',
        condition: 'contains' as MatchCondition,
        value: suggestedPattern,
        caseSensitive: false,
        priority: 0,
        enabled: true,
        confidence: 80,
        allowMultipleMatches: true,
        autoSuggest: true
      });

      setIsOpen(false);
      setShowRuleCreation(false);
    } catch (error) {
      console.error('Error creating rule:', error);
      // Still assign the category even if rule creation fails
      onCategorySelect(transactionId, selectedCategoryForRule);
      setIsOpen(false);
      setShowRuleCreation(false);
    }
  };

  const handleJustAssign = () => {
    onCategorySelect(transactionId, selectedCategoryForRule);
    setIsOpen(false);
    setShowRuleCreation(false);
  };

  if (disabled) {
    return <span className="category-quick-selector disabled">{displayText}</span>;
  }

  return (
    <div className="category-quick-selector" ref={dropdownRef}>
      <button
        className={`category-display ${isOpen ? 'open' : ''} ${!currentCategoryId ? 'uncategorized' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Click to change category"
      >
        <span className="category-name">{displayText}</span>
        <span className="dropdown-arrow">▼</span>
      </button>

      {isOpen && (
        <div className="category-dropdown">
          {showRuleCreation ? (
            <div className="rule-creation-panel">
              <div className="rule-creation-header">
                <h4>Create Rule for Category</h4>
                <button
                  className="close-button"
                  onClick={() => setShowRuleCreation(false)}
                >
                  ✕
                </button>
              </div>

              <div className="suggested-rule">
                <p><strong>Suggested Pattern:</strong> "{suggestedPattern}"</p>
                <p className="match-count">
                  This pattern will match {patternMatchCount} existing transactions
                </p>
              </div>

              <div className="rule-actions">
                <button
                  className="create-rule-button"
                  onClick={handleCreateWithRule}
                >
                  Assign & Create Rule
                </button>
                <button
                  className="just-assign-button"
                  onClick={handleJustAssign}
                >
                  Just Assign Category
                </button>
              </div>
            </div>
          ) : (
            <div className="category-options">
              {isLoadingSuggestions && (
                <div className="loading-suggestions">
                  <span className="loading-spinner">⏳</span> Loading suggestions...
                </div>
              )}

              {quickSuggestion && !currentCategoryId && (
                <div className="quick-suggestion">
                  <div className="suggestion-header">
                    <span className="suggestion-icon">💡</span>
                    <strong>Suggested: {quickSuggestion.suggestedCategory.name}</strong>
                    <span className="confidence-badge">
                      {quickSuggestion.suggestedCategory.confidence}%
                    </span>
                  </div>
                  <button
                    className="suggestion-button"
                    onClick={() => {
                      // Find or create category
                      const existingCategory = availableCategories.find(
                        cat => cat.name.toLowerCase() === quickSuggestion.suggestedCategory.name.toLowerCase()
                      );

                      if (existingCategory) {
                        handleCategoryClick(existingCategory.categoryId);
                      } else {
                        handleCreateNewCategory();
                      }
                    }}
                  >
                    Use Suggestion
                  </button>
                </div>
              )}

              <div className="category-list">
                {availableCategories.length === 0 ? (
                  <div className="no-categories-message">
                    <span className="no-categories-icon">📂</span>
                    <p>No categories yet</p>
                    <p className="no-categories-hint">Create your first category below</p>
                  </div>
                ) : (
                  availableCategories.map(category => (
                    <button
                      key={category.categoryId}
                      className="category-option"
                      onClick={() => handleCategoryClick(category.categoryId)}
                    >
                      <span className="category-icon">{category.icon || '📁'}</span>
                      <span className="category-name">{category.name}</span>
                      {category.rules && category.rules.length > 0 && (
                        <span className="has-rules" title="Has rules">⚙️</span>
                      )}
                    </button>
                  ))
                )}
              </div>

              <div className="create-new-section">
                <button
                  className="create-new-button"
                  onClick={handleCreateNewCategory}
                >
                  <span className="plus-icon">+</span>
                  Create New Category
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CategoryQuickSelector; 
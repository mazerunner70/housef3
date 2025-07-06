import React, { useState, useEffect } from 'react';
import { Category, CategoryRule, MatchCondition } from '../../types/Category';
import { usePatternSuggestions, PatternSuggestionItem } from '../hooks/usePatternSuggestions';
import CategorySelector from './CategorySelector';
import PatternList from './PatternList';
import './PatternSuggestionModal.css';

interface PatternSuggestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  transactionDescription: string;
  selectedCategory: Category;
  onConfirmPattern: (pattern: string, rule: Partial<CategoryRule>) => void;
  onCreateCategory: (categoryName: string, categoryType: 'INCOME' | 'EXPENSE', pattern: string, fieldToMatch: string, condition: string) => void;
}

const PatternSuggestionModal: React.FC<PatternSuggestionModalProps> = ({
  isOpen,
  onClose,
  transactionDescription,
  selectedCategory,
  onConfirmPattern,
  onCreateCategory
}) => {
  // Load pattern suggestions using custom hook
  const { suggestedPatterns, categorySuggestion, existingCategories, isLoading } = 
    usePatternSuggestions(transactionDescription, isOpen);

  // Pattern selection state
  const [selectedPattern, setSelectedPattern] = useState<PatternSuggestionItem | null>(null);

  // Category selection state
  const [selectedExistingCategory, setSelectedExistingCategory] = useState('');
  const [isCreatingNewCategory, setIsCreatingNewCategory] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryType, setNewCategoryType] = useState<'INCOME' | 'EXPENSE'>('EXPENSE');

  // Auto-select best pattern when suggestions load
  useEffect(() => {
    if (suggestedPatterns.length > 0) {
      const bestPattern = suggestedPatterns[0];
      setSelectedPattern(bestPattern);
    }
  }, [suggestedPatterns]);

  // Pre-populate new category form with suggestion
  useEffect(() => {
    if (categorySuggestion && !newCategoryName) {
      setNewCategoryName(categorySuggestion.categoryName);
      setNewCategoryType(categorySuggestion.categoryType);
    }
  }, [categorySuggestion, newCategoryName]);

  const handlePatternSelect = (pattern: PatternSuggestionItem) => {
    setSelectedPattern(pattern);
  };

  const createRule = (): Partial<CategoryRule> => ({
    fieldToMatch: selectedPattern?.field || 'description',
    condition: (selectedPattern?.condition || 'contains') as MatchCondition,
    value: selectedPattern?.pattern || '',
    caseSensitive: false,
    priority: 0,
    enabled: true,
    confidence: 80,
    allowMultipleMatches: true,
    autoSuggest: true
  });

  const handleConfirm = () => {
    if (!selectedPattern) return;

    if (selectedCategory) {
      onConfirmPattern(selectedPattern.pattern, createRule());
    } else if (selectedExistingCategory) {
      onConfirmPattern(selectedPattern.pattern, createRule());
    } else if (isCreatingNewCategory && newCategoryName) {
      onCreateCategory(newCategoryName, newCategoryType, selectedPattern.pattern, selectedPattern.field, selectedPattern.condition);
    }
    onClose();
  };

  const getModalTitle = () => {
    if (selectedCategory) return 'Add Rule to Category';
    if (selectedExistingCategory) return 'Add Pattern to Category';
    return 'Pattern Suggestions';
  };

  const getConfirmButtonText = () => {
    if (selectedCategory) return 'Add Rule to Category';
    if (selectedExistingCategory) return 'Add Pattern to Category';
    if (isCreatingNewCategory) return 'Create Category with Rule';
    return 'Select Category or Create New';
  };

  const isConfirmDisabled = () => {
    return !selectedPattern || (!selectedCategory && !selectedExistingCategory && !isCreatingNewCategory);
  };

  if (!isOpen) return null;

  return (
    <div className="pattern-suggestion-modal-overlay">
      <div className="pattern-suggestion-modal">
        <div className="modal-header">
          <h3>{getModalTitle()}</h3>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>
        
        <div className="modal-content">
          <div className="transaction-info">
            <h4>Transaction Details</h4>
            <div className="transaction-description">
              <strong>Description:</strong> {transactionDescription}
            </div>
          </div>

          {isLoading ? (
            <div className="loading-container">
              <div className="loading-spinner">⏳</div>
              <p>Analyzing transaction and generating patterns...</p>
            </div>
          ) : (
            <>
              <CategorySelector
                existingCategories={existingCategories}
                selectedExistingCategory={selectedExistingCategory}
                onSelectExistingCategory={setSelectedExistingCategory}
                isCreatingNewCategory={isCreatingNewCategory}
                onStartCreatingNew={() => setIsCreatingNewCategory(true)}
                onCancelCreatingNew={() => {
                  setIsCreatingNewCategory(false);
                  setNewCategoryName('');
                  setNewCategoryType('EXPENSE');
                }}
                newCategoryName={newCategoryName}
                onNewCategoryNameChange={setNewCategoryName}
                newCategoryType={newCategoryType}
                onNewCategoryTypeChange={setNewCategoryType}
                categorySuggestion={categorySuggestion}
              />

              <PatternList
                patterns={suggestedPatterns}
                selectedPattern={selectedPattern}
                onPatternSelect={handlePatternSelect}
              />
            </>
          )}
        </div>
        
        <div className="modal-actions">
          <button className="cancel-button" onClick={onClose}>
            Cancel
          </button>
          <button 
            className="confirm-button"
            onClick={handleConfirm}
            disabled={isConfirmDisabled()}
          >
            {getConfirmButtonText()}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PatternSuggestionModal; 
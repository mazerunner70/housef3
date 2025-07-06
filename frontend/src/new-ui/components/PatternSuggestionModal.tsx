import React, { useState, useEffect } from 'react';
import { CategoryService } from '../../services/CategoryService';
import { Category, CategoryRule, MatchCondition } from '../../types/Category';
import './PatternSuggestionModal.css';

interface PatternSuggestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  transactionDescription: string;
  selectedCategory: Category;
  onConfirmPattern: (pattern: string, rule: Partial<CategoryRule>) => void;
  onCreateCategory: (categoryName: string, categoryType: 'INCOME' | 'EXPENSE', pattern: string, fieldToMatch: string, condition: string) => void;
}

interface PatternSuggestionItem {
  pattern: string;
  confidence: number;
  matchCount: number;
  field: string;
  condition: string;
  explanation: string;
  sampleMatches: Array<{
    transactionId: string;
    description: string;
    amount: string;
    date: string;
    matchedText: string;
  }>;
}

interface CategorySuggestion {
  categoryName: string;
  categoryType: 'INCOME' | 'EXPENSE';
  confidence: number;
  icon: string;
  suggestedPatterns: Array<{
    pattern: string;
    confidence: number;
    field: string;
    condition: string;
    explanation: string;
  }>;
}

const PatternSuggestionModal: React.FC<PatternSuggestionModalProps> = ({
  isOpen,
  onClose,
  transactionDescription,
  selectedCategory,
  onConfirmPattern,
  onCreateCategory
}) => {
  const [suggestedPatterns, setSuggestedPatterns] = useState<PatternSuggestionItem[]>([]);
  const [categorySuggestion, setCategorySuggestion] = useState<CategorySuggestion | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPattern, setSelectedPattern] = useState<string>('');
  const [selectedField, setSelectedField] = useState<string>('description');
  const [selectedCondition, setSelectedCondition] = useState<string>('contains');
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryType, setNewCategoryType] = useState<'INCOME' | 'EXPENSE'>('EXPENSE');
  const [expandedMatches, setExpandedMatches] = useState<Set<number>>(new Set());
  const [existingCategories, setExistingCategories] = useState<Category[]>([]);
  const [selectedExistingCategory, setSelectedExistingCategory] = useState<string>('');
  const [isCreatingNewCategory, setIsCreatingNewCategory] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadSuggestions();
    }
  }, [isOpen, transactionDescription]);

  const loadSuggestions = async () => {
    if (!transactionDescription) return;
    
    setIsLoading(true);
    try {
      // Get category suggestions and patterns from suggestFromTransaction
      const categoryResponse = await CategoryService.suggestFromTransaction({
        description: transactionDescription
      });

      // Get existing categories
      console.log('About to call CategoryService.getCategories()');
      const categoriesResponse = await CategoryService.getCategories();
      console.log('CategoryService.getCategories() returned:', categoriesResponse);
      console.log('Type of categoriesResponse:', typeof categoriesResponse);
      console.log('Is array?', Array.isArray(categoriesResponse));
      console.log('categoriesResponse keys:', Object.keys(categoriesResponse || {}));
      
      const sortedCategories = categoriesResponse.sort((a: Category, b: Category) => a.name.localeCompare(b.name));
      setExistingCategories(sortedCategories);

      // Use patterns from suggestFromTransaction response
      const patterns = categoryResponse?.suggestedPatterns || [];

      // Enhance pattern suggestions with match counts and samples
      const enhancedPatterns = await Promise.all(
        patterns.map(async (pattern) => {
          try {
            const matchPreview = await CategoryService.previewPatternMatches(
              pattern.pattern, 
              pattern.field,
              pattern.condition
            );
            
            return {
              ...pattern,
              matchCount: matchPreview.matchCount,
              sampleMatches: matchPreview.sampleMatches
            };
          } catch (error) {
            console.error('Error previewing pattern matches for pattern:', pattern, error);
            return {
              ...pattern,
              matchCount: 0,
              sampleMatches: []
            };
          }
        })
      );

      // Sort patterns by confidence (highest first) for display
      const sortedPatterns = [...enhancedPatterns].sort((a, b) => b.confidence - a.confidence);

      setSuggestedPatterns(sortedPatterns);
      setCategorySuggestion(categoryResponse);
      
      // Pre-select the best pattern (highest confidence)
      if (sortedPatterns.length > 0) {
        const bestPattern = sortedPatterns[0];
        setSelectedPattern(bestPattern.pattern);
        setSelectedField(bestPattern.field);
        setSelectedCondition(bestPattern.condition);
      }

      // Pre-populate new category form if category doesn't exist
      if (categoryResponse) {
        setNewCategoryName(categoryResponse.categoryName);
        setNewCategoryType(categoryResponse.categoryType);
      }
      
    } catch (error) {
      console.error('Error loading pattern suggestions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmPattern = () => {
    if (!selectedPattern) return;

    const rule: Partial<CategoryRule> = {
      fieldToMatch: selectedField,
      condition: selectedCondition as MatchCondition,
      value: selectedPattern,
      caseSensitive: false,
      priority: 0,
      enabled: true,
      confidence: 80,
      allowMultipleMatches: true,
      autoSuggest: true
    };

    onConfirmPattern(selectedPattern, rule);
    onClose();
  };

  const handleCreateNewCategory = () => {
    if (!newCategoryName || !selectedPattern) return;
    
    onCreateCategory(newCategoryName, newCategoryType, selectedPattern, selectedField, selectedCondition);
    onClose();
  };

  const handleAddToExistingCategory = () => {
    if (!selectedExistingCategory || !selectedPattern) return;
    
    const existingCategory = existingCategories.find(cat => cat.categoryId === selectedExistingCategory);
    if (existingCategory) {
      const rule: Partial<CategoryRule> = {
        fieldToMatch: selectedField,
        condition: selectedCondition as MatchCondition,
        value: selectedPattern,
        caseSensitive: false,
        priority: 0,
        enabled: true,
        confidence: 80,
        allowMultipleMatches: true,
        autoSuggest: true
      };
      
      onConfirmPattern(selectedPattern, rule);
    }
    onClose();
  };

  const handleStartCreatingNewCategory = () => {
    setIsCreatingNewCategory(true);
    // Pre-populate with suggested name if available
    if (categorySuggestion && !newCategoryName) {
      setNewCategoryName(categorySuggestion.categoryName);
      setNewCategoryType(categorySuggestion.categoryType);
    }
  };

  const handleCancelNewCategory = () => {
    setIsCreatingNewCategory(false);
    setNewCategoryName('');
    setNewCategoryType('EXPENSE');
  };

  const handleConfirmNewCategory = () => {
    if (!newCategoryName || !selectedPattern) return;
    
    onCreateCategory(newCategoryName, newCategoryType, selectedPattern, selectedField, selectedCondition);
    onClose();
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'high-confidence';
    if (confidence >= 60) return 'medium-confidence';
    return 'low-confidence';
  };

  const getMatchCountColor = (matchCount: number) => {
    if (matchCount >= 10) return 'high-matches';
    if (matchCount >= 5) return 'medium-matches';
    if (matchCount >= 1) return 'low-matches';
    return 'no-matches';
  };

  const toggleMatchesExpanded = (patternIndex: number) => {
    setExpandedMatches(prev => {
      const newSet = new Set(prev);
      if (newSet.has(patternIndex)) {
        newSet.delete(patternIndex);
      } else {
        newSet.add(patternIndex);
      }
      return newSet;
    });
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return dateString;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="pattern-suggestion-modal-overlay">
      <div className="pattern-suggestion-modal">
        <div className="modal-header">
          <h3>
            {selectedCategory ? 'Add Rule to Category' : 
             selectedExistingCategory ? 'Add Pattern to Category' : 
             'Pattern Suggestions'}
          </h3>
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
              <div className="category-selection-section">
                <h4>Select Category</h4>
                <div className="category-selector">
                  {!isCreatingNewCategory ? (
                    <div className="category-dropdown-container">
                      <select
                        value={selectedExistingCategory}
                        onChange={(e) => setSelectedExistingCategory(e.target.value)}
                        className="category-dropdown"
                      >
                        <option value="">Select a category...</option>
                        {existingCategories.map(category => (
                          <option key={category.categoryId} value={category.categoryId}>
                            {category.name}
                          </option>
                        ))}
                      </select>
                      <button
                        className="add-category-button"
                        onClick={handleStartCreatingNewCategory}
                        title="Create new category"
                      >
                        +
                      </button>
                    </div>
                  ) : (
                    <div className="new-category-input-container">
                      <input
                        type="text"
                        value={newCategoryName}
                        onChange={(e) => setNewCategoryName(e.target.value)}
                        placeholder="Enter category name"
                        className="new-category-input"
                      />
                      <div className="new-category-type-selector">
                        <select
                          value={newCategoryType}
                          onChange={(e) => setNewCategoryType(e.target.value as 'INCOME' | 'EXPENSE')}
                          className="category-type-dropdown"
                        >
                          <option value="EXPENSE">Expense</option>
                          <option value="INCOME">Income</option>
                        </select>
                      </div>
                      <button
                        className="confirm-category-button"
                        onClick={handleConfirmNewCategory}
                        disabled={!newCategoryName}
                        title="Create category"
                      >
                        ✓
                      </button>
                      <button
                        className="cancel-category-button"
                        onClick={handleCancelNewCategory}
                        title="Cancel"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="pattern-suggestions-section">
                <h4>Suggested Patterns</h4>
                <p className="section-description">
                  Select a pattern that will automatically categorize similar transactions.
                </p>
                
                {suggestedPatterns.length === 0 ? (
                  <div className="no-patterns">
                    <p>No patterns could be generated for this transaction.</p>
                    <p>You can still create a category manually.</p>
                  </div>
                ) : (
                  <div className="pattern-list">
                    {suggestedPatterns.map((pattern, index) => (
                      <div 
                        key={index}
                        className={`pattern-item ${selectedPattern === pattern.pattern ? 'selected' : ''}`}
                        onClick={() => {
                          setSelectedPattern(pattern.pattern);
                          setSelectedField(pattern.field);
                          setSelectedCondition(pattern.condition);
                        }}
                      >
                        <div className="pattern-header">
                          <div className="pattern-radio">
                            <input
                              type="radio"
                              name="selectedPattern"
                              checked={selectedPattern === pattern.pattern}
                              onChange={() => {
                                setSelectedPattern(pattern.pattern);
                                setSelectedField(pattern.field);
                                setSelectedCondition(pattern.condition);
                              }}
                            />
                          </div>
                          <div className="pattern-info">
                            <div className="pattern-text">
                              <strong>Pattern:</strong> "{pattern.pattern}"
                            </div>
                            <div className="pattern-rule">
                              <strong>Rule:</strong> {pattern.field} {pattern.condition} "{pattern.pattern}"
                            </div>
                            <div className="pattern-explanation">
                              {pattern.explanation}
                            </div>
                          </div>
                          <div className="pattern-stats">
                            <div className={`confidence-badge ${getConfidenceColor(pattern.confidence)}`}>
                              {pattern.confidence}%
                            </div>
                            <button 
                              className={`match-count-button ${getMatchCountColor(pattern.matchCount)}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleMatchesExpanded(index);
                              }}
                              disabled={pattern.matchCount === 0}
                              title={pattern.matchCount > 0 ? "Click to see matching transactions" : "No matching transactions"}
                            >
                              {pattern.matchCount} match{pattern.matchCount !== 1 ? 'es' : ''}
                              {pattern.matchCount > 0 && (
                                <span className="expand-icon">
                                  {expandedMatches.has(index) ? '▼' : '▶'}
                                </span>
                              )}
                            </button>
                          </div>
                        </div>
                        
                        {pattern.sampleMatches && pattern.sampleMatches.length > 0 && expandedMatches.has(index) && (
                          <div className="sample-matches">
                            <h5>Matching Transactions:</h5>
                            <div className="sample-transactions">
                              {pattern.sampleMatches.map((match, sampleIndex) => (
                                <div key={sampleIndex} className="sample-transaction expanded">
                                  <div className="transaction-main">
                                    <div className="sample-description">
                                      {match.description}
                                    </div>
                                    <div className="sample-amount">
                                      {match.amount}
                                    </div>
                                  </div>
                                  <div className="transaction-meta">
                                    <div className="sample-date">
                                      {formatDate(match.date)}
                                    </div>
                                    {match.matchedText && (
                                      <div className="matched-text">
                                        Matched: "{match.matchedText}"
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              
            </>
          )}
        </div>
        
        <div className="modal-actions">
          <button className="cancel-button" onClick={onClose}>
            Cancel
          </button>
          
          {selectedCategory ? (
            <button 
              className="confirm-button"
              onClick={handleConfirmPattern}
              disabled={!selectedPattern}
            >
              Add Rule to Category
            </button>
          ) : selectedExistingCategory ? (
            <button 
              className="confirm-button"
              onClick={handleAddToExistingCategory}
              disabled={!selectedPattern}
            >
              Add Pattern to Category
            </button>
          ) : (
            <button 
              className="confirm-button"
              onClick={handleCreateNewCategory}
              disabled={!selectedPattern || (!isCreatingNewCategory && !selectedExistingCategory)}
            >
              {isCreatingNewCategory ? 'Create Category with Rule' : 'Select Category or Create New'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default PatternSuggestionModal; 
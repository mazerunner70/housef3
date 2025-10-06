import React from 'react';
import { Category } from '../../types/Category';
import { CategorySuggestion } from '../hooks/usePatternSuggestions';
import './CategorySelector.css';

interface CategorySelectorProps {
  existingCategories: Category[];
  selectedExistingCategory: string;
  onSelectExistingCategory: (categoryId: string) => void;
  isCreatingNewCategory: boolean;
  onStartCreatingNew: () => void;
  onCancelCreatingNew: () => void;
  newCategoryName: string;
  onNewCategoryNameChange: (name: string) => void;
  newCategoryType: 'INCOME' | 'EXPENSE';
  onNewCategoryTypeChange: (type: 'INCOME' | 'EXPENSE') => void;
  categorySuggestion: CategorySuggestion | null;
}

const CategorySelector: React.FC<CategorySelectorProps> = ({
  existingCategories,
  selectedExistingCategory,
  onSelectExistingCategory,
  isCreatingNewCategory,
  onStartCreatingNew,
  onCancelCreatingNew,
  newCategoryName,
  onNewCategoryNameChange,
  newCategoryType,
  onNewCategoryTypeChange,
  categorySuggestion
}) => {
  const handleStartCreatingNew = () => {
    onStartCreatingNew();
    // Pre-populate with suggested name if available
    if (categorySuggestion && !newCategoryName) {
      onNewCategoryNameChange(categorySuggestion.categoryName);
      onNewCategoryTypeChange(categorySuggestion.categoryType);
    }
  };

  // Sort categories alphabetically
  const sortedCategories = [...existingCategories].sort((a, b) => 
    a.name.localeCompare(b.name)
  );

  return (
    <div className="category-selection-section">
      <h4>Select Category</h4>
      <div className="category-selector">
        {!isCreatingNewCategory ? (
          <div className="category-selector-dropdown-container">
            <select
              id="category-selector"
              name="category-selector"
              value={selectedExistingCategory}
              onChange={(e) => onSelectExistingCategory(e.target.value)}
              className="category-selector-dropdown"
            >
              <option value="">Select a category...</option>
              {sortedCategories.map(category => (
                <option key={category.categoryId} value={category.categoryId}>
                  {category.name}
                </option>
              ))}
            </select>
            <button
              className="add-category-button"
              onClick={handleStartCreatingNew}
              title="Create new category for this rule"
            >
              +
            </button>
          </div>
        ) : (
          <div className="new-category-input-container">
            <input
              type="text"
              value={newCategoryName}
              onChange={(e) => onNewCategoryNameChange(e.target.value)}
              placeholder="Enter category name"
              className="new-category-input"
            />
            <div className="new-category-type-selector">
              <select
                value={newCategoryType}
                onChange={(e) => onNewCategoryTypeChange(e.target.value as 'INCOME' | 'EXPENSE')}
                className="category-selector-type-dropdown"
              >
                <option value="EXPENSE">Expense</option>
                <option value="INCOME">Income</option>
              </select>
            </div>
            <button
              className="cancel-category-button"
              onClick={onCancelCreatingNew}
              title="Cancel"
            >
              ✕
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CategorySelector; 
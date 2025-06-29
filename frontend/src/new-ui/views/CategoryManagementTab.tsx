import React, { useState, useCallback } from 'react';
import { Category, CategorySuggestionStrategy } from '../../types/Category';
import { useCategories } from '../hooks/useCategories';
import { useRealTimeRuleTesting } from '../hooks/useRealTimeRuleTesting';
import CategoryHierarchyTree from '../components/CategoryHierarchyTree';
import './CategoryManagementTab.css';

const CategoryManagementTab: React.FC = () => {
  const {
    categories,
    hierarchy,
    selectedCategory,
    isLoading,
    error,
    selectCategory,
    createCategory,
    updateCategory,
    deleteCategory,
    clearError
  } = useCategories();

  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionStrategy, setSuggestionStrategy] = useState<CategorySuggestionStrategy>(CategorySuggestionStrategy.ALL_MATCHES);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createParentId, setCreateParentId] = useState<string | undefined>();

  // Real-time rule testing for selected category
  const {
    isTestingRule,
    testResults,
    error: testError
  } = useRealTimeRuleTesting();

  const handleSelectCategory = useCallback((category: Category) => {
    selectCategory(category);
  }, [selectCategory]);

  const handleCreateCategory = useCallback((parentId?: string) => {
    setCreateParentId(parentId);
    setShowCreateModal(true);
  }, []);

  const handleMoveCategory = useCallback(async (categoryId: string, newParentId: string | null) => {
    try {
      // For now, we'll need to implement category moving through a separate service call
      // The CategoryUpdate interface doesn't support parentCategoryId
      console.log(`Moving category ${categoryId} to parent ${newParentId || 'root'} - feature not yet implemented`);
    } catch (error) {
      console.error('Error moving category:', error);
    }
  }, []);

  if (error) {
    return (
      <div className="category-management-error">
        <div className="error-content">
          <h3>❌ Error Loading Categories</h3>
          <p>{error}</p>
          <button onClick={clearError} className="retry-btn">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="category-management-container">
      <div className="category-management-header">
        <div className="header-content">
          <h2>Category Management</h2>
          <p>Organize transactions with intelligent category rules and hierarchies.</p>
        </div>
        
        <div className="category-management-controls">
          <div className="control-group">
            <label htmlFor="suggestion-strategy">Suggestion Strategy:</label>
            <select 
              id="suggestion-strategy"
              value={suggestionStrategy}
              onChange={(e) => setSuggestionStrategy(e.target.value as CategorySuggestionStrategy)}
              className="suggestion-strategy-selector"
            >
              <option value="all_matches">All Matches</option>
              <option value="top_n_matches">Top N Matches</option>
              <option value="confidence_threshold">Confidence Threshold</option>
              <option value="priority_filtered">Priority Filtered</option>
            </select>
          </div>
          
          <button 
            className={`suggestion-toggle ${showSuggestions ? 'active' : ''}`}
            onClick={() => setShowSuggestions(!showSuggestions)}
          >
            {showSuggestions ? '👁️ Hide' : '👁️‍🗨️ Show'} Suggestions
          </button>
        </div>
      </div>
      
      <div className="category-main-content">
        <div className="category-list-section">
          <CategoryHierarchyTree 
            hierarchy={hierarchy}
            selectedCategory={selectedCategory}
            onSelectCategory={handleSelectCategory}
            showSuggestions={showSuggestions}
            onCreateCategory={handleCreateCategory}
            onMoveCategory={handleMoveCategory}
            isLoading={isLoading}
          />
        </div>
        
        <div className="category-details-section">
          {selectedCategory ? (
            <CategoryEditor 
              category={selectedCategory}
              hierarchy={hierarchy}
              suggestionStrategy={suggestionStrategy}
              isTestingRule={isTestingRule}
              testResults={testResults}
              testError={testError}
              onUpdateCategory={updateCategory}
              onDeleteCategory={deleteCategory}
            />
          ) : (
            <EmptyStateMessage />
          )}
        </div>
      </div>

      {/* Create Category Modal - TODO: Implement */}
      {showCreateModal && (
        <CreateCategoryModal
          parentCategoryId={createParentId}
          availableCategories={categories}
          onCreate={async (categoryData) => {
            const newCategory = await createCategory(categoryData);
            if (newCategory) {
              setShowCreateModal(false);
              setCreateParentId(undefined);
              selectCategory(newCategory);
            }
          }}
          onCancel={() => {
            setShowCreateModal(false);
            setCreateParentId(undefined);
          }}
        />
      )}
    </div>
  );
};

// Placeholder components - TODO: Implement these in next tasks
interface CategoryEditorProps {
  category: Category;
  hierarchy: any[];
  suggestionStrategy: CategorySuggestionStrategy;
  isTestingRule: boolean;
  testResults: any;
  testError: string | null;
  onUpdateCategory: (id: string, data: any) => Promise<any>;
  onDeleteCategory: (id: string) => Promise<boolean>;
}

const CategoryEditor: React.FC<CategoryEditorProps> = ({ 
  category, 
  isTestingRule, 
  testResults,
  testError
}) => (
  <div className="category-editor">
    <div className="editor-header">
      <h3>📝 Editing: {category.name}</h3>
      <span className="category-type">{category.type}</span>
    </div>
    
    <div className="editor-content">
      <div className="category-info">
        <p><strong>Category ID:</strong> {category.categoryId}</p>
        <p><strong>Rules:</strong> {category.rules.length}</p>
        <p><strong>Parent:</strong> {category.parentCategoryId || 'None (Root)'}</p>
        <p><strong>Inheritance:</strong> {category.inheritParentRules ? 'Enabled' : 'Disabled'}</p>
      </div>

      {isTestingRule && (
        <div className="test-results">
          <h4>🧪 Testing Results</h4>
          {testError ? (
            <div className="test-error">❌ {testError}</div>
          ) : testResults ? (
            <p>Found {testResults.transactions?.length || 0} matching transactions</p>
          ) : (
            <p>Testing...</p>
          )}
        </div>
      )}

      <div className="editor-placeholder">
        <p>🚧 Category rule editor coming in next task...</p>
        <p>Will include:</p>
        <ul>
          <li>Visual rule builder</li>
          <li>Real-time pattern testing</li>
          <li>Rule inheritance management</li>
          <li>Smart pattern generation</li>
        </ul>
      </div>
    </div>
  </div>
);

const EmptyStateMessage: React.FC = () => (
  <div className="empty-state-message">
    <div className="empty-state-icon">📂</div>
    <h3>Select a Category</h3>
    <p>Choose a category from the tree to view and edit its rules.</p>
    <div className="empty-state-features">
      <div className="feature-item">
        <span className="feature-icon">⚡</span>
        <span>Real-time rule testing</span>
      </div>
      <div className="feature-item">
        <span className="feature-icon">🎯</span>
        <span>Smart pattern matching</span>
      </div>
      <div className="feature-item">
        <span className="feature-icon">🌳</span>
        <span>Hierarchical inheritance</span>
      </div>
    </div>
  </div>
);

interface CreateCategoryModalProps {
  parentCategoryId?: string;
  availableCategories: Category[];
  onCreate: (data: any) => Promise<void>;
  onCancel: () => void;
}

const CreateCategoryModal: React.FC<CreateCategoryModalProps> = ({
  parentCategoryId,
  availableCategories,
  onCreate,
  onCancel
}) => {
  const [formData, setFormData] = useState({
    name: '',
    type: 'EXPENSE' as const,
    icon: '',
    color: '#667eea',
    inheritParentRules: true,
    ruleInheritanceMode: 'additive' as const
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      setError('Category name is required');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onCreate({
        ...formData,
        parentCategoryId: parentCategoryId || undefined
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create category');
    } finally {
      setIsSubmitting(false);
    }
  };

  const parentCategory = parentCategoryId 
    ? availableCategories.find(cat => cat.categoryId === parentCategoryId)
    : null;

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="create-category-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create New Category</h3>
          <button className="close-btn" onClick={onCancel}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-content">
            {parentCategory && (
              <div className="parent-info">
                <strong>Parent Category:</strong> {parentCategory.name}
              </div>
            )}

            {error && (
              <div className="error-message">
                ❌ {error}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="category-name">Category Name *</label>
              <input
                id="category-name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter category name..."
                autoFocus
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="category-type">Type</label>
              <select
                id="category-type"
                value={formData.type}
                onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value as any }))}
              >
                <option value="EXPENSE">💸 Expense</option>
                <option value="INCOME">💰 Income</option>
              </select>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="category-icon">Icon</label>
                <input
                  id="category-icon"
                  type="text"
                  value={formData.icon}
                  onChange={(e) => setFormData(prev => ({ ...prev, icon: e.target.value }))}
                  placeholder="🏪"
                  maxLength={2}
                />
              </div>

              <div className="form-group">
                <label htmlFor="category-color">Color</label>
                <input
                  id="category-color"
                  type="color"
                  value={formData.color}
                  onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
                />
              </div>
            </div>

            {parentCategory && (
              <>
                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={formData.inheritParentRules}
                      onChange={(e) => setFormData(prev => ({ ...prev, inheritParentRules: e.target.checked }))}
                    />
                    Inherit rules from parent category
                  </label>
                </div>

                {formData.inheritParentRules && (
                  <div className="form-group">
                    <label htmlFor="inheritance-mode">Rule Inheritance Mode</label>
                    <select
                      id="inheritance-mode"
                      value={formData.ruleInheritanceMode}
                      onChange={(e) => setFormData(prev => ({ ...prev, ruleInheritanceMode: e.target.value as any }))}
                    >
                      <option value="additive">Additive (parent + own rules)</option>
                      <option value="override">Override (own rules only)</option>
                      <option value="disabled">Disabled</option>
                    </select>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onCancel} className="cancel-btn" disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="create-btn" disabled={isSubmitting || !formData.name.trim()}>
              {isSubmitting ? 'Creating...' : 'Create Category'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CategoryManagementTab; 
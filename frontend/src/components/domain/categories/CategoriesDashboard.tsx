import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Category, CategorySuggestionStrategy, CategoryRule, MatchCondition, CategoryHierarchy, RuleTestResponse, CategoryCreate, CategoryType } from '@/types/Category';
import { useCategories, useCategoryRules } from '@/hooks/useCategories';
import { useRealTimeRuleTesting } from '@/hooks/useRealTimeRuleTesting';
import { CategoryService } from '@/services/CategoryService';
import CategoryHierarchyTree from './CategoryHierarchyTree';
import RuleBuilder from './RuleBuilder';
import ConfirmationModal from '@/components/ui/ConfirmationModal';
import RecurringChargesTab from './components/RecurringChargesTab';
import './CategoriesDashboard.css';

interface CategoriesDashboardProps {
  // Deep-linking support for pre-populated category creation
  initialCategoryData?: {
    suggestedName?: string;
    suggestedType?: CategoryType;
    suggestedPattern?: string;
    transactionDescription?: string;
    autoOpenCreateModal?: boolean;
  };
  onCategoryCreated?: (category: Category) => void;
}

const CategoriesDashboard: React.FC<CategoriesDashboardProps> = ({
  initialCategoryData,
  onCategoryCreated
}) => {
  const navigate = useNavigate();
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

  const [activeTab, setActiveTab] = useState<'categories' | 'recurring'>('categories');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionStrategy, setSuggestionStrategy] = useState<CategorySuggestionStrategy>(CategorySuggestionStrategy.ALL_MATCHES);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createParentId, setCreateParentId] = useState<string | undefined>();

  // Deep-linking state
  const [prePopulatedData, setPrePopulatedData] = useState<{
    categoryName?: string;
    categoryType?: CategoryType;
    suggestedPatterns?: Array<{
      pattern: string;
      confidence: number;
      explanation: string;
    }>;
    transactionDescription?: string;
  } | null>(null);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  // Real-time rule testing for selected category
  const {
    isTestingRule,
    testResults,
    error: testError
  } = useRealTimeRuleTesting();

  // Reset categories state
  const [showResetModal, setShowResetModal] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [resetResults, setResetResults] = useState<any>(null);

  // Handle initial category data from deep-linking
  useEffect(() => {
    if (initialCategoryData) {
      handleInitialCategoryData(initialCategoryData);
    }
  }, [initialCategoryData]);

  const handleInitialCategoryData = useCallback(async (data: typeof initialCategoryData) => {
    if (!data) return;

    // Load suggestions if we have a transaction description
    if (data.transactionDescription) {
      setIsLoadingSuggestions(true);
      try {
        const suggestions = await CategoryService.getQuickCategorySuggestions(data.transactionDescription);

        setPrePopulatedData({
          categoryName: data.suggestedName || suggestions.suggestedCategory.name,
          categoryType: data.suggestedType || (suggestions.suggestedCategory.type === 'INCOME' ? CategoryType.INCOME : CategoryType.EXPENSE),
          suggestedPatterns: suggestions.suggestedPatterns,
          transactionDescription: data.transactionDescription
        });
      } catch (error) {
        console.error('Error loading category suggestions:', error);
        // Fallback to provided data
        setPrePopulatedData({
          categoryName: data.suggestedName || 'New Category',
          categoryType: data.suggestedType || CategoryType.EXPENSE,
          suggestedPatterns: data.suggestedPattern ? [{
            pattern: data.suggestedPattern,
            confidence: 80,
            explanation: 'Manual pattern suggestion'
          }] : [],
          transactionDescription: data.transactionDescription
        });
      } finally {
        setIsLoadingSuggestions(false);
      }
    } else {
      // Use provided data directly
      setPrePopulatedData({
        categoryName: data.suggestedName || 'New Category',
        categoryType: data.suggestedType || CategoryType.EXPENSE,
        suggestedPatterns: data.suggestedPattern ? [{
          pattern: data.suggestedPattern,
          confidence: 80,
          explanation: 'Manual pattern suggestion'
        }] : [],
        transactionDescription: data.transactionDescription
      });
    }

    // Auto-open create modal if requested
    if (data.autoOpenCreateModal !== false) {
      setShowCreateModal(true);
    }
  }, []);

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

  const handleResetAndReapplyCategories = useCallback(async () => {
    setIsResetting(true);
    try {
      const results = await CategoryService.resetAndReapplyCategories();
      setResetResults(results);
      setShowResetModal(false);

      // Show success message and reload categories
      alert(`Categories reset successfully! ${results.results.totalApplicationsApplied} category assignments were applied to ${results.results.totalTransactionsProcessed} transactions.`);

      // Refresh the categories list
      navigate(0);
    } catch (error) {
      console.error('Error resetting categories:', error);
      alert('Failed to reset categories. Please try again.');
    } finally {
      setIsResetting(false);
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
          {activeTab === 'categories' && (
            <>
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

              <button
                className="reset-categories-btn"
                onClick={() => setShowResetModal(true)}
                disabled={isResetting}
                title="Reset all category assignments and re-apply rules"
              >
                {isResetting ? '🔄 Resetting...' : '🔄 Reset All Categories'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="category-tabs">
        <button
          className={`category-tab ${activeTab === 'categories' ? 'active' : ''}`}
          onClick={() => setActiveTab('categories')}
        >
          📂 Categories & Rules
        </button>
        <button
          className={`category-tab ${activeTab === 'recurring' ? 'active' : ''}`}
          onClick={() => setActiveTab('recurring')}
        >
          🔄 Recurring Charges
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'categories' ? (
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
      ) : (
        <div className="category-tab-content">
          <RecurringChargesTab />
        </div>
      )}

      {/* Create Category Modal */}
      {showCreateModal && (
        <CreateCategoryModal
          parentCategoryId={createParentId}
          availableCategories={categories}
          prePopulatedData={prePopulatedData}
          isLoadingSuggestions={isLoadingSuggestions}
          onCreate={async (categoryData) => {
            const newCategory = await createCategory(categoryData);
            if (newCategory) {
              setShowCreateModal(false);
              setCreateParentId(undefined);
              setPrePopulatedData(null);
              selectCategory(newCategory);

              // Call callback if provided
              if (onCategoryCreated) {
                onCategoryCreated(newCategory);
              }
            }
          }}
          onCancel={() => {
            setShowCreateModal(false);
            setCreateParentId(undefined);
            setPrePopulatedData(null);
          }}
        />
      )}

      {/* Reset Categories Confirmation Modal */}
      <ConfirmationModal
        isOpen={showResetModal}
        title="Reset All Category Assignments"
        message="⚠️ This will permanently remove ALL category assignments from your transactions and re-apply category rules from scratch. This action cannot be undone. Are you sure you want to continue?"
        confirmButtonText="Reset Categories"
        cancelButtonText="Cancel"
        type="danger"
        onConfirm={handleResetAndReapplyCategories}
        onCancel={() => setShowResetModal(false)}
        isLoading={isResetting}
      />
    </div>
  );
};

// Real category editor implementation
interface CategoryEditorProps {
  category: Category;
  hierarchy: CategoryHierarchy[];
  suggestionStrategy: CategorySuggestionStrategy;
  isTestingRule: boolean;
  testResults: RuleTestResponse | null;
  testError: string | null;
  onUpdateCategory: (id: string, data: any) => Promise<any>;
  onDeleteCategory: (id: string) => Promise<boolean>;
}

const CategoryEditor: React.FC<CategoryEditorProps> = ({
  category,
  onUpdateCategory,
  onDeleteCategory
}) => {
  const [isEditingBasicInfo, setIsEditingBasicInfo] = useState(false);
  const [editingRule, setEditingRule] = useState<CategoryRule | null>(null);
  const [isCreatingRule, setIsCreatingRule] = useState(false);
  const [basicInfo, setBasicInfo] = useState({
    name: category.name,
    icon: category.icon || '',
    color: category.color || '#667eea',
    inheritParentRules: category.inheritParentRules,
    ruleInheritanceMode: category.ruleInheritanceMode
  });

  // Use category rules hook
  const {
    rules,
    isLoading: rulesLoading,
    error: rulesError,
    addRule,
    updateRule,
    deleteRule,
    toggleRuleEnabled
  } = useCategoryRules(category.categoryId);

  // Debug logging for rules returned by hook
  console.log(`CategoryEditor - useCategoryRules hook for category ${category.name}:`);
  console.log(`CategoryEditor - category.rules directly:`, category.rules);
  console.log(`CategoryEditor - category.rules length:`, category.rules?.length);
  console.log(`CategoryEditor - rules from hook:`, rules);
  console.log(`CategoryEditor - rules from hook length:`, rules.length);
  console.log(`CategoryEditor - rules from hook type:`, typeof rules);
  console.log(`CategoryEditor - rules from hook is array:`, Array.isArray(rules));
  console.log(`CategoryEditor - isLoading:`, rulesLoading);
  console.log(`CategoryEditor - error:`, rulesError);

  // Create new rule template
  const createNewRule = useCallback((): CategoryRule => ({
    ruleId: '', // Will be generated by backend
    fieldToMatch: 'description',
    condition: MatchCondition.CONTAINS,
    value: '',
    caseSensitive: false,
    priority: 1,
    enabled: true,
    confidence: 1.0,
    allowMultipleMatches: true,
    autoSuggest: true
  }), []);

  // Handle basic info save
  const handleSaveBasicInfo = useCallback(async () => {
    try {
      await onUpdateCategory(category.categoryId, basicInfo);
      setIsEditingBasicInfo(false);
    } catch (error) {
      console.error('Failed to update category:', error);
    }
  }, [category.categoryId, basicInfo, onUpdateCategory]);

  // Handle rule operations
  const handleSaveRule = useCallback(async (rule: CategoryRule) => {
    try {
      if (isCreatingRule) {
        const success = await addRule(rule);
        if (success) {
          setIsCreatingRule(false);
          setEditingRule(null);
        }
      } else if (editingRule) {
        const success = await updateRule(editingRule.ruleId, rule);
        if (success) {
          setEditingRule(null);
        }
      }
    } catch (error) {
      console.error('Failed to save rule:', error);
    }
  }, [isCreatingRule, editingRule, addRule, updateRule]);

  const handleDeleteRule = useCallback(async (ruleId: string) => {
    if (window.confirm('Are you sure you want to delete this rule?')) {
      try {
        await deleteRule(ruleId);
      } catch (error) {
        console.error('Failed to delete rule:', error);
      }
    }
  }, [deleteRule]);

  const handleCancelRule = useCallback(() => {
    setEditingRule(null);
    setIsCreatingRule(false);
  }, []);

  return (
    <div className="category-editor">
      <div className="editor-header">
        <h3>📝 Editing: {category.name}</h3>
        <span className={`category-type ${category.type.toLowerCase()}`}>
          {category.type}
        </span>
      </div>

      <div className="editor-content">
        {/* Basic Category Information */}
        <div className="category-basic-info">
          <div className="section-header">
            <h4>📋 Basic Information</h4>
            <button
              className="edit-btn"
              onClick={() => setIsEditingBasicInfo(!isEditingBasicInfo)}
            >
              {isEditingBasicInfo ? 'Cancel' : 'Edit'}
            </button>
          </div>

          {isEditingBasicInfo ? (
            <div className="basic-info-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Category Name</label>
                  <input
                    type="text"
                    value={basicInfo.name}
                    onChange={(e) => setBasicInfo(prev => ({ ...prev, name: e.target.value }))}
                  />
                </div>
                <div className="form-group">
                  <label>Icon</label>
                  <input
                    type="text"
                    value={basicInfo.icon}
                    onChange={(e) => setBasicInfo(prev => ({ ...prev, icon: e.target.value }))}
                    placeholder="📝"
                    maxLength={2}
                  />
                </div>
                <div className="form-group">
                  <label>Color</label>
                  <input
                    type="color"
                    value={basicInfo.color}
                    onChange={(e) => setBasicInfo(prev => ({ ...prev, color: e.target.value }))}
                  />
                </div>
              </div>

              <div className="form-actions">
                <button className="save-btn" onClick={handleSaveBasicInfo}>
                  Save Changes
                </button>
                <button
                  className="cancel-btn"
                  onClick={() => setIsEditingBasicInfo(false)}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="category-info">
              <p><strong>Category ID:</strong> {category.categoryId}</p>
              <p><strong>Rules:</strong> {rules.length}</p>
              <p><strong>Parent:</strong> {category.parentCategoryId || 'None (Root)'}</p>
              <p><strong>Inheritance:</strong> {category.inheritParentRules ? 'Enabled' : 'Disabled'}</p>
            </div>
          )}
        </div>

        {/* Rules Management */}
        <div className="category-rules-section">
          <div className="section-header">
            <h4>⚡ Automation Rules ({rules.length})</h4>
            <button
              className="add-rule-btn"
              onClick={() => {
                setIsCreatingRule(true);
                setEditingRule(createNewRule());
              }}
              disabled={isCreatingRule || editingRule !== null}
            >
              + Add Rule
            </button>
          </div>

          {rulesError && (
            <div className="error-message">
              ❌ {rulesError}
            </div>
          )}

          {/* Existing Rules List */}
          {rules.length > 0 && (
            <div className="rules-list">
              {rules.map((rule) => (
                <div key={rule.ruleId} className="rule-item">
                  <div className="rule-summary">
                    <div className="rule-info">
                      <span className="rule-condition">
                        {rule.fieldToMatch} {rule.condition} "{rule.value}"
                      </span>
                      <div className="rule-meta">
                        <span className={`rule-status ${rule.enabled ? 'enabled' : 'disabled'}`}>
                          {rule.enabled ? '✅ Enabled' : '⏸️ Disabled'}
                        </span>
                        <span className="rule-confidence">
                          {rule.confidence}% confidence
                        </span>
                        <span className="rule-priority">
                          Priority: {rule.priority}
                        </span>
                      </div>
                    </div>
                    <div className="rule-actions">
                      <button
                        className="toggle-btn"
                        onClick={() => toggleRuleEnabled(rule.ruleId, !rule.enabled)}
                        title={rule.enabled ? 'Disable rule' : 'Enable rule'}
                      >
                        {rule.enabled ? '⏸️' : '▶️'}
                      </button>
                      <button
                        className="edit-btn"
                        onClick={() => setEditingRule(rule)}
                        disabled={editingRule !== null || isCreatingRule}
                      >
                        ✏️
                      </button>
                      <button
                        className="delete-btn"
                        onClick={() => handleDeleteRule(rule.ruleId)}
                        disabled={editingRule !== null || isCreatingRule}
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Rule Builder */}
          {(editingRule || isCreatingRule) && editingRule && (
            <div className="rule-builder-container">
              <RuleBuilder
                rule={editingRule}
                onRuleChange={setEditingRule}
                onSave={handleSaveRule}
                onCancel={handleCancelRule}
                isNew={isCreatingRule}
                categoryName={category.name}
              />
            </div>
          )}

          {/* Empty state for rules */}
          {rules.length === 0 && !isCreatingRule && (
            <div className="rules-empty-state">
              <div className="empty-icon">⚡</div>
              <h4>No automation rules yet</h4>
              <p>Create rules to automatically categorize your transactions based on patterns.</p>
              <button
                className="create-first-rule-btn"
                onClick={() => {
                  setIsCreatingRule(true);
                  setEditingRule(createNewRule());
                }}
              >
                Create Your First Rule
              </button>
            </div>
          )}
        </div>

        {/* Category Actions */}
        <div className="category-actions-section">
          <div className="section-header">
            <h4>🛠️ Category Actions</h4>
          </div>
          <div className="action-buttons">
            <button
              className="danger-btn"
              onClick={() => {
                if (window.confirm(`Are you sure you want to delete the category "${category.name}"? This action cannot be undone.`)) {
                  onDeleteCategory(category.categoryId);
                }
              }}
            >
              🗑️ Delete Category
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

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
  prePopulatedData?: {
    categoryName?: string;
    categoryType?: CategoryType;
    suggestedPatterns?: Array<{
      pattern: string;
      confidence: number;
      explanation: string;
      field?: string;
      condition?: string;
    }>;
    transactionDescription?: string;
  } | null;
  isLoadingSuggestions?: boolean;
  onCreate: (data: CategoryCreate) => Promise<void>;
  onCancel: () => void;
}

const CreateCategoryModal: React.FC<CreateCategoryModalProps> = ({
  parentCategoryId,
  availableCategories,
  prePopulatedData,
  isLoadingSuggestions,
  onCreate,
  onCancel
}) => {
  const [formData, setFormData] = useState({
    name: prePopulatedData?.categoryName || '',
    type: prePopulatedData?.categoryType === 'INCOME' ? CategoryType.INCOME : CategoryType.EXPENSE,
    icon: '',
    color: '#667eea',
    inheritParentRules: true,
    ruleInheritanceMode: 'additive' as 'additive' | 'override' | 'disabled'
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Rule creation state for pre-populated patterns
  const [showRuleCreation, setShowRuleCreation] = useState(!!prePopulatedData?.suggestedPatterns?.length);
  const [selectedPattern, setSelectedPattern] = useState(
    prePopulatedData?.suggestedPatterns?.[0]?.pattern || ''
  );

  // Update form when pre-populated data changes
  useEffect(() => {
    if (prePopulatedData) {
      setFormData(prev => ({
        ...prev,
        name: prePopulatedData.categoryName || prev.name,
        type: prePopulatedData.categoryType === 'INCOME' ? CategoryType.INCOME : CategoryType.EXPENSE
      }));

      if (prePopulatedData.suggestedPatterns?.length) {
        setShowRuleCreation(true);
        setSelectedPattern(prePopulatedData.suggestedPatterns[0].pattern);
      }
    }
  }, [prePopulatedData]);

  // Handle escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onCancel]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      setError('Category name is required');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // If we have a selected pattern and rule creation is enabled, use the createWithRule API
      if (showRuleCreation && selectedPattern) {
        // Find the selected pattern data to get field and condition
        const selectedPatternData = prePopulatedData?.suggestedPatterns?.find(
          p => p.pattern === selectedPattern
        );

        const response = await CategoryService.createWithRule(
          formData.name,
          formData.type as 'INCOME' | 'EXPENSE',
          selectedPattern,
          selectedPatternData?.field || 'description', // Default to 'description' field
          selectedPatternData?.condition || 'contains' // Default to 'contains' condition
        );

        // Call the onCreate callback with the created category
        await onCreate({
          ...response.category,
          parentCategoryId: parentCategoryId || undefined
        });
      } else {
        // Standard category creation
        await onCreate({
          ...formData,
          parentCategoryId: parentCategoryId || undefined
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create category');
    } finally {
      setIsSubmitting(false);
    }
  };

  const parentCategory = parentCategoryId
    ? availableCategories.find(cat => cat.categoryId === parentCategoryId)
    : null;

  const handleOverlayKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onCancel();
    }
  };

  const handleModalKeyDown = (e: React.KeyboardEvent) => {
    // Prevent keyboard events from bubbling to overlay
    e.stopPropagation();
  };

  return (
    <div
      className="modal-overlay"
      onClick={onCancel}
      onKeyDown={handleOverlayKeyDown}
      tabIndex={0}
      role="button"
      aria-label="Close modal"
    >
      <div
        className="create-category-modal"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleModalKeyDown}
      >
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

            {/* Deep-linking context */}
            {prePopulatedData?.transactionDescription && (
              <div className="deep-link-context">
                <div className="context-header">
                  <h4>💡 Creating category for transaction:</h4>
                </div>
                <div className="transaction-description">
                  "{prePopulatedData.transactionDescription}"
                </div>

                {isLoadingSuggestions && (
                  <div className="loading-suggestions">
                    <span className="loading-spinner">⏳</span> Analyzing transaction...
                  </div>
                )}

                {prePopulatedData.suggestedPatterns && prePopulatedData.suggestedPatterns.length > 0 && (
                  <div className="suggested-patterns">
                    <h5>Suggested patterns for auto-categorization:</h5>
                    {prePopulatedData.suggestedPatterns.map((pattern, index) => (
                      <div
                        key={index}
                        className={`pattern-suggestion ${selectedPattern === pattern.pattern ? 'selected' : ''}`}
                        onClick={() => setSelectedPattern(pattern.pattern)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setSelectedPattern(pattern.pattern);
                          }
                        }}
                        role="button"
                        tabIndex={0}
                        aria-label={`Select pattern: ${pattern.pattern}, confidence: ${pattern.confidence}%. ${pattern.explanation}`}
                        aria-pressed={selectedPattern === pattern.pattern}
                      >
                        <div className="pattern-header">
                          <input
                            type="radio"
                            name="suggestedPattern"
                            checked={selectedPattern === pattern.pattern}
                            onChange={() => setSelectedPattern(pattern.pattern)}
                            tabIndex={-1}
                            aria-hidden="true"
                          />
                          <span className="pattern-text">"{pattern.pattern}"</span>
                          <span className="pattern-confidence">{pattern.confidence}%</span>
                        </div>
                        <div className="pattern-explanation">{pattern.explanation}</div>
                      </div>
                    ))}

                    <div className="rule-creation-toggle">
                      <label>
                        <input
                          type="checkbox"
                          checked={showRuleCreation}
                          onChange={(e) => setShowRuleCreation(e.target.checked)}
                        />
                        Create rule with selected pattern (recommended)
                      </label>
                    </div>
                  </div>
                )}
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
                onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value as CategoryType }))}
              >
                <option value={CategoryType.EXPENSE}>💸 Expense</option>
                <option value={CategoryType.INCOME}>💰 Income</option>
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

export default CategoriesDashboard; 
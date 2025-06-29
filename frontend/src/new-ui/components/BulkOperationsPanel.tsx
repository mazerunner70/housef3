import React, { useState, useCallback, useEffect } from 'react';
import { Transaction } from '../../services/TransactionService';
import { Category, CategoryRule, CategorySuggestionStrategy } from '../../types/Category';
import { useBulkOperations } from '../hooks/useCategories';
import './BulkOperationsPanel.css';

interface BulkOperationsPanelProps {
  selectedTransactions: Transaction[];
  availableCategories: Category[];
  availableRules: CategoryRule[];
  onTransactionUpdate: () => void;
  onClearSelection: () => void;
  isOpen: boolean;
  onClose: () => void;
}

type BulkOperation = 'categorize' | 'apply_rules' | 'generate_suggestions' | 'confirm_suggestions' | 'export_data';

interface BulkOperationProgress {
  operation: BulkOperation;
  total: number;
  completed: number;
  errors: string[];
  isRunning: boolean;
  startTime: number;
}

const BulkOperationsPanel: React.FC<BulkOperationsPanelProps> = ({
  selectedTransactions,
  availableCategories,
  availableRules,
  onTransactionUpdate,
  onClearSelection,
  isOpen,
  onClose
}) => {
  const [selectedOperation, setSelectedOperation] = useState<BulkOperation>('categorize');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedRules, setSelectedRules] = useState<Set<string>>(new Set());
  const [suggestionStrategy, setSuggestionStrategy] = useState<CategorySuggestionStrategy>(CategorySuggestionStrategy.ALL_MATCHES);
  const [progress, setProgress] = useState<BulkOperationProgress | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [previewResults, setPreviewResults] = useState<any[]>([]);

  const {
    bulkCategorize,
    applyCategoryRules,
    bulkConfirmSuggestions,
    isProcessing,
    progress: hookProgress
  } = useBulkOperations();

  // Reset form when panel opens/closes
  useEffect(() => {
    if (isOpen) {
      setSelectedOperation('categorize');
      setSelectedCategory('');
      setSelectedRules(new Set());
      setSuggestionStrategy(CategorySuggestionStrategy.ALL_MATCHES);
      setProgress(null);
      setShowPreview(false);
      setPreviewResults([]);
    }
  }, [isOpen]);

  // Update progress from hook
  useEffect(() => {
    if (hookProgress) {
      setProgress({
        operation: selectedOperation,
        total: 100,
        completed: hookProgress,
        errors: [],
        isRunning: isProcessing,
        startTime: Date.now()
      });
    }
  }, [hookProgress, selectedOperation, isProcessing]);

  const formatTransactionCount = useCallback((count: number): string => {
    return `${count} transaction${count !== 1 ? 's' : ''}`;
  }, []);

  const formatDuration = useCallback((startTime: number): string => {
    const duration = Math.floor((Date.now() - startTime) / 1000);
    if (duration < 60) return `${duration}s`;
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    return `${minutes}m ${seconds}s`;
  }, []);

  const getOperationDescription = useCallback((operation: BulkOperation): string => {
    switch (operation) {
      case 'categorize':
        return 'Assign selected category to all transactions';
      case 'apply_rules':
        return 'Run category rules against selected transactions';
      case 'generate_suggestions':
        return 'Generate category suggestions for uncategorized transactions';
      case 'confirm_suggestions':
        return 'Confirm pending category suggestions';
      case 'export_data':
        return 'Export transaction and category data';
      default:
        return 'Select an operation';
    }
  }, []);

  const handlePreview = useCallback(async () => {
    setShowPreview(true);
    setPreviewResults([]);

    try {
      let results: any[] = [];
      
      switch (selectedOperation) {
        case 'categorize':
          if (selectedCategory) {
            const category = availableCategories.find(c => c.categoryId === selectedCategory);
            results = selectedTransactions.map(t => ({
              transactionId: t.transactionId,
              description: t.description,
              currentCategory: 'None',
              newCategory: category?.name || 'Unknown',
              confidence: 1.0
            }));
          }
          break;

        case 'apply_rules':
          results = selectedTransactions.map(t => {
            const matchingRules = Array.from(selectedRules).filter(ruleId => {
              const rule = availableRules.find(r => r.ruleId === ruleId);
              if (!rule || !rule.enabled) return false;
              // Simplified rule matching for preview
              const fieldValue = getFieldValue(t, rule.fieldToMatch);
              return testRuleMatch(fieldValue, rule);
            });
            
            return {
              transactionId: t.transactionId,
              description: t.description,
              matchingRules: matchingRules.length,
              rules: matchingRules.map(ruleId => {
                const rule = availableRules.find(r => r.ruleId === ruleId);
                return rule?.fieldToMatch + ' ' + rule?.condition;
              })
            };
          });
          break;

        case 'generate_suggestions':
          results = selectedTransactions
            .filter(t => !t.category) // Only uncategorized
            .map((t, index) => ({
              transactionId: t.transactionId,
              description: t.description,
              strategy: suggestionStrategy,
              // Deterministic estimate based on description length and index
              estimatedSuggestions: Math.min(((t.description?.length || 10) % 3) + 1, 3)
            }));
          break;

        case 'confirm_suggestions':
          results = selectedTransactions
            .filter(t => t.category && t.category.includes('pending')) // Mock pending check
            .map((t, index) => ({
              transactionId: t.transactionId,
              description: t.description,
              // Deterministic estimate based on transaction amount and index
              pendingSuggestions: Math.min(((Number(t.amount) || 0) % 2) + 1, 2)
            }));
          break;

        case 'export_data':
          results = [{
            operation: 'export',
            transactionCount: selectedTransactions.length,
            categoryCount: availableCategories.length,
            ruleCount: availableRules.length,
            estimatedFileSize: `${Math.ceil(selectedTransactions.length / 100)}MB`
          }];
          break;
      }

      setPreviewResults(results);
    } catch (error) {
      console.error('Error generating preview:', error);
    }
  }, [selectedOperation, selectedCategory, selectedRules, suggestionStrategy, selectedTransactions, availableCategories, availableRules]);

  const handleExecute = useCallback(async () => {
    if (selectedTransactions.length === 0) return;

    try {
      switch (selectedOperation) {
        case 'categorize':
          if (selectedCategory) {
            await bulkCategorize(
              selectedTransactions.map(t => t.transactionId),
              selectedCategory
            );
          }
          break;

        case 'apply_rules':
          // Apply rules for each selected rule
          for (const ruleId of Array.from(selectedRules)) {
            await applyCategoryRules(ruleId, true, suggestionStrategy);
          }
          break;

        case 'generate_suggestions':
          // This would need a different implementation since the hook doesn't have this method
          console.log('Generate suggestions not yet implemented');
          break;

        case 'confirm_suggestions':
          await bulkConfirmSuggestions(
            selectedTransactions.map(t => t.transactionId)
          );
          break;

        case 'export_data':
          // Export functionality not available in current hook
          console.log('Export functionality not yet implemented');
          break;
      }

      // Refresh data and clear selection
      onTransactionUpdate();
      onClearSelection();
      
      // Close panel on success
      setTimeout(() => {
        onClose();
      }, 2000);

    } catch (error) {
      console.error('Error executing bulk operation:', error);
    }
  }, [selectedOperation, selectedCategory, selectedRules, suggestionStrategy, selectedTransactions, bulkCategorize, applyCategoryRules, bulkConfirmSuggestions, onTransactionUpdate, onClearSelection, onClose]);

  const getFieldValue = useCallback((transaction: Transaction, field: string): string => {
    switch (field) {
      case 'description':
        return transaction.description || '';
      case 'payee':
        return transaction.payee || '';
      case 'memo':
        return transaction.memo || '';
      case 'amount':
        return transaction.amount?.toString() || '';
      default:
        return '';
    }
  }, []);

  const testRuleMatch = useCallback((value: string, rule: CategoryRule): boolean => {
    // Simplified rule testing for preview
    const testValue = rule.caseSensitive ? value : value.toLowerCase();
    const pattern = rule.caseSensitive ? rule.value : rule.value.toLowerCase();

    switch (rule.condition) {
      case 'contains':
        return testValue.includes(pattern);
      case 'starts_with':
        return testValue.startsWith(pattern);
      case 'ends_with':
        return testValue.endsWith(pattern);
      case 'equals':
        return testValue === pattern;
      default:
        return false;
    }
  }, []);

  const canExecute = useCallback((): boolean => {
    if (selectedTransactions.length === 0 || isProcessing) return false;

    switch (selectedOperation) {
      case 'categorize':
        return !!selectedCategory;
      case 'apply_rules':
        return selectedRules.size > 0;
      case 'generate_suggestions':
      case 'confirm_suggestions':
      case 'export_data':
        return true;
      default:
        return false;
    }
  }, [selectedOperation, selectedCategory, selectedRules, selectedTransactions.length, isProcessing]);

  if (!isOpen) return null;

  return (
    <div className="bulk-operations-panel">
      <div className="panel-header">
        <div className="header-content">
          <h3>⚡ Bulk Operations</h3>
          <p>{formatTransactionCount(selectedTransactions.length)} selected</p>
        </div>
        <button className="close-panel-btn" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="panel-content">
        {/* Operation Selection */}
        <div className="operation-selection">
          <h4>🎯 Select Operation</h4>
          <div className="operation-grid">
            {([
              { id: 'categorize', icon: '🏷️', title: 'Categorize', desc: 'Assign category to transactions' },
              { id: 'apply_rules', icon: '🔧', title: 'Apply Rules', desc: 'Run category rules' },
              { id: 'generate_suggestions', icon: '💡', title: 'Generate Suggestions', desc: 'Create category suggestions' },
              { id: 'confirm_suggestions', icon: '✅', title: 'Confirm Suggestions', desc: 'Confirm pending suggestions' },
              { id: 'export_data', icon: '📤', title: 'Export Data', desc: 'Export transaction data' }
            ] as const).map(op => (
              <button
                key={op.id}
                className={`operation-card ${selectedOperation === op.id ? 'selected' : ''}`}
                onClick={() => setSelectedOperation(op.id)}
                disabled={isProcessing}
              >
                <span className="operation-icon">{op.icon}</span>
                <div className="operation-info">
                  <h5>{op.title}</h5>
                  <p>{op.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Operation Configuration */}
        <div className="operation-config">
          <h4>⚙️ Configuration</h4>
          <p className="config-description">
            {getOperationDescription(selectedOperation)}
          </p>

          {selectedOperation === 'categorize' && (
            <div className="config-section">
              <label htmlFor="category-select">Target Category</label>
              <select
                id="category-select"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="config-select"
                disabled={isProcessing}
              >
                <option value="">Select a category...</option>
                {availableCategories.map(category => (
                  <option key={category.categoryId} value={category.categoryId}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {selectedOperation === 'apply_rules' && (
            <div className="config-section">
              <label>Rules to Apply</label>
              <div className="rules-selection">
                {availableRules.filter(rule => rule.enabled).map(rule => (
                  <label key={rule.ruleId} className="rule-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedRules.has(rule.ruleId)}
                      onChange={(e) => {
                        const newRules = new Set(selectedRules);
                        if (e.target.checked) {
                          newRules.add(rule.ruleId);
                        } else {
                          newRules.delete(rule.ruleId);
                        }
                        setSelectedRules(newRules);
                      }}
                      disabled={isProcessing}
                    />
                    <span className="rule-info">
                      <strong>{rule.fieldToMatch}</strong> {rule.condition} "{rule.value}"
                    </span>
                  </label>
                ))}
                {availableRules.filter(rule => rule.enabled).length === 0 && (
                  <p className="no-rules">No enabled rules available</p>
                )}
              </div>
            </div>
          )}

          {selectedOperation === 'generate_suggestions' && (
            <div className="config-section">
              <label htmlFor="strategy-select">Suggestion Strategy</label>
              <select
                id="strategy-select"
                value={suggestionStrategy}
                onChange={(e) => setSuggestionStrategy(e.target.value as CategorySuggestionStrategy)}
                className="config-select"
                disabled={isProcessing}
              >
                <option value="all_matches">All Matches</option>
                <option value="highest_confidence">Highest Confidence</option>
                <option value="manual_review">Manual Review</option>
              </select>
            </div>
          )}
        </div>

        {/* Preview Section */}
        <div className="preview-section">
          <div className="preview-header">
            <h4>👁️ Preview</h4>
            <button
              className="preview-btn"
              onClick={handlePreview}
              disabled={!canExecute() || isProcessing}
            >
              🔍 Generate Preview
            </button>
          </div>

          {showPreview && (
            <div className="preview-content">
              {previewResults.length > 0 ? (
                <div className="preview-results">
                  <div className="results-header">
                    <span>Estimated Results ({previewResults.length} items)</span>
                  </div>
                  <div className="results-list">
                    {previewResults.slice(0, 5).map((result, index) => (
                      <div key={index} className="result-item">
                        {selectedOperation === 'categorize' && (
                          <>
                            <span className="transaction-desc">{result.description}</span>
                            <span className="category-change">
                              → <strong>{result.newCategory}</strong>
                            </span>
                          </>
                        )}
                        {selectedOperation === 'apply_rules' && (
                          <>
                            <span className="transaction-desc">{result.description}</span>
                            <span className="rules-match">
                              {result.matchingRules} rule{result.matchingRules !== 1 ? 's' : ''} match
                            </span>
                          </>
                        )}
                        {selectedOperation === 'generate_suggestions' && (
                          <>
                            <span className="transaction-desc">{result.description}</span>
                            <span className="suggestions-est">
                              ~{result.estimatedSuggestions} suggestions
                            </span>
                          </>
                        )}
                        {selectedOperation === 'export_data' && (
                          <>
                            <span className="export-summary">
                              {result.transactionCount} transactions, {result.categoryCount} categories
                            </span>
                            <span className="file-size">~{result.estimatedFileSize}</span>
                          </>
                        )}
                      </div>
                    ))}
                    {previewResults.length > 5 && (
                      <div className="more-results">
                        +{previewResults.length - 5} more items...
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="no-preview">
                  <span className="no-preview-icon">📝</span>
                  <p>No results to preview with current configuration</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Progress Section */}
        {progress && (
          <div className="progress-section">
            <div className="progress-header">
              <h4>⏳ Operation Progress</h4>
              {progress.isRunning && (
                <span className="progress-time">
                  {formatDuration(progress.startTime)}
                </span>
              )}
            </div>
            
            <div className="progress-bar-container">
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${(progress.completed / progress.total) * 100}%` }}
                />
              </div>
              <span className="progress-text">
                {progress.completed} / {progress.total} ({Math.round((progress.completed / progress.total) * 100)}%)
              </span>
            </div>

            {progress.errors.length > 0 && (
              <div className="progress-errors">
                <summary>❌ {progress.errors.length} Error{progress.errors.length !== 1 ? 's' : ''}</summary>
                <div className="error-list">
                  {progress.errors.slice(0, 3).map((error, index) => (
                    <div key={index} className="error-item">{error}</div>
                  ))}
                  {progress.errors.length > 3 && (
                    <div className="more-errors">+{progress.errors.length - 3} more errors</div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="panel-actions">
        <button
          className="cancel-btn"
          onClick={onClose}
          disabled={isProcessing}
        >
          Cancel
        </button>
        
        <button
          className="execute-btn"
          onClick={handleExecute}
          disabled={!canExecute()}
        >
          {isProcessing ? (
            <>
              <span className="loading-spinner">🔄</span>
              Processing...
            </>
          ) : (
            <>
              ⚡ Execute Operation
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default BulkOperationsPanel; 
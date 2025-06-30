import React, { useState, useCallback, useEffect } from 'react';
import { CategoryRule, MatchCondition } from '../../types/Category';
import { useRealTimeRuleTesting } from '../hooks/useRealTimeRuleTesting';
import { Transaction } from '../../services/TransactionService';
import './RuleBuilder.css';

interface RuleBuilderProps {
  rule: CategoryRule;
  onRuleChange: (rule: CategoryRule) => void;
  onSave: (rule: CategoryRule) => Promise<void>;
  onCancel: () => void;
  isNew?: boolean;
  categoryName?: string;
}

const RuleBuilder: React.FC<RuleBuilderProps> = ({
  rule,
  onRuleChange,
  onSave,
  onCancel,
  isNew = false,
  categoryName = 'Unknown Category'
}) => {
  const [localRule, setLocalRule] = useState<CategoryRule>(rule);
  const [isSaving, setIsSaving] = useState(false);
  const [showTestResults, setShowTestResults] = useState(false);

  const {
    isTestingRule,
    testResults,
    error: testError,
    testRuleImmediate
  } = useRealTimeRuleTesting();

  // Update parent when local rule changes
  useEffect(() => {
    onRuleChange(localRule);
  }, [localRule, onRuleChange]);

  const handleFieldChange = useCallback((field: keyof CategoryRule, value: any) => {
    setLocalRule(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      await onSave(localRule);
    } catch (error) {
      console.error('Error saving rule:', error);
    } finally {
      setIsSaving(false);
    }
  }, [localRule, onSave]);

  const handleTestRule = useCallback(() => {
    testRuleImmediate(localRule);
    setShowTestResults(true);
  }, [localRule, testRuleImmediate]);

  const isAmountCondition = localRule.condition === 'amount_greater' || 
                           localRule.condition === 'amount_less' || 
                           localRule.condition === 'amount_between';

  const conditionOptions = [
    { value: 'contains', label: 'Contains', description: 'Text contains the specified value' },
    { value: 'starts_with', label: 'Starts With', description: 'Text starts with the specified value' },
    { value: 'ends_with', label: 'Ends With', description: 'Text ends with the specified value' },
    { value: 'equals', label: 'Equals', description: 'Text exactly matches the specified value' },
    { value: 'regex', label: 'Regular Expression', description: 'Advanced pattern matching' },
    { value: 'amount_greater', label: 'Amount Greater Than', description: 'Transaction amount is greater than value' },
    { value: 'amount_less', label: 'Amount Less Than', description: 'Transaction amount is less than value' },
    { value: 'amount_between', label: 'Amount Between', description: 'Transaction amount is between two values' }
  ];

  const fieldOptions = [
    { value: 'description', label: 'Description', description: 'Transaction description/memo' },
    { value: 'payee', label: 'Payee', description: 'Transaction payee/merchant' },
    { value: 'memo', label: 'Memo', description: 'Additional transaction notes' },
    { value: 'amount', label: 'Amount', description: 'Transaction amount (for amount-based conditions)' }
  ];

  const isValidRuleForTesting = (rule: CategoryRule): boolean => {
    if (rule.condition === 'amount_between') {
      return rule.amountMin !== undefined && rule.amountMax !== undefined;
    } else if (isAmountCondition) {
      return Boolean(rule.value && rule.value.trim() !== '');
    } else {
      return Boolean(rule.value && rule.value.trim() !== '');
    }
  };

  return (
    <div className="rule-builder">
      <div className="rule-builder-header">
        <div className="header-content">
          <h3>{isNew ? '🆕 Create New Rule' : '✏️ Edit Rule'}</h3>
          <p>Define matching criteria for <strong>{categoryName}</strong></p>
        </div>
      </div>

      <div className="rule-builder-content">
        <div className="rule-form">
          {/* Rule Configuration */}
          <div className="form-section">
            <h4>📋 Rule Configuration</h4>
            
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="rule-field">Field to Match</label>
                <select
                  id="rule-field"
                  value={localRule.fieldToMatch}
                  onChange={(e) => handleFieldChange('fieldToMatch', e.target.value)}
                  className="form-select"
                >
                  {fieldOptions.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <small className="form-help">
                  {fieldOptions.find(opt => opt.value === localRule.fieldToMatch)?.description}
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="rule-condition">Condition</label>
                <select
                  id="rule-condition"
                  value={localRule.condition}
                  onChange={(e) => handleFieldChange('condition', e.target.value as MatchCondition)}
                  className="form-select"
                >
                  {conditionOptions.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <small className="form-help">
                  {conditionOptions.find(opt => opt.value === localRule.condition)?.description}
                </small>
              </div>
            </div>

            {/* Value Input - varies based on condition type */}
            <div className="form-group">
              <label htmlFor="rule-value">
                {isAmountCondition ? 'Amount Value' : 'Pattern Value'}
              </label>
              
              {localRule.condition === 'amount_between' ? (
                <div className="amount-range-inputs">
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Min amount"
                    value={localRule.amountMin?.toString() || ''}
                    onChange={(e) => handleFieldChange('amountMin', parseFloat(e.target.value) || undefined)}
                    className="form-input"
                  />
                  <span className="range-separator">to</span>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Max amount"
                    value={localRule.amountMax?.toString() || ''}
                    onChange={(e) => handleFieldChange('amountMax', parseFloat(e.target.value) || undefined)}
                    className="form-input"
                  />
                </div>
              ) : (
                <input
                  id="rule-value"
                  type={isAmountCondition ? 'number' : 'text'}
                  step={isAmountCondition ? '0.01' : undefined}
                  value={localRule.value}
                  onChange={(e) => handleFieldChange('value', e.target.value)}
                  className="form-input"
                  placeholder={
                    isAmountCondition ? 'Enter amount...' :
                    localRule.condition === 'regex' ? 'Enter regex pattern...' :
                    'Enter text to match...'
                  }
                />
              )}
            </div>

            {/* Test Button */}
            <div className="test-section">
              <button
                type="button"
                className="test-rule-btn"
                onClick={handleTestRule}
                disabled={isTestingRule || !isValidRuleForTesting(localRule)}
              >
                {isTestingRule ? '🔄 Testing...' : '🧪 Test'}
              </button>
              <small className="form-help">
                {!isValidRuleForTesting(localRule) 
                  ? 'Enter a value or amount to test the rule'
                  : 'Test this rule against existing transactions'
                }
              </small>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="rule-builder-actions">
        <button
          type="button"
          className="cancel-btn"
          onClick={onCancel}
          disabled={isSaving}
        >
          Cancel
        </button>
        
        <button
          type="button"
          className="save-btn"
          onClick={handleSave}
          disabled={isSaving || !isValidRuleForTesting(localRule)}
        >
          {isSaving ? '💾 Saving...' : isNew ? '✅ Create Rule' : '💾 Save Changes'}
        </button>
      </div>

      {/* Test Results Dialog */}
      {showTestResults && (
        <TestResultsDialog
          isOpen={showTestResults}
          results={testResults}
          rule={localRule}
          error={testError}
          isLoading={isTestingRule}
          onClose={() => setShowTestResults(false)}
        />
      )}
    </div>
  );
};

// Test Results Dialog Component
interface TestResultsDialogProps {
  isOpen: boolean;
  results: any;
  rule: CategoryRule;
  error: string | null;
  isLoading: boolean;
  onClose: () => void;
}

const TestResultsDialog: React.FC<TestResultsDialogProps> = ({
  isOpen,
  results,
  rule,
  error,
  isLoading,
  onClose
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const transactions = results?.matchingTransactions || [];

  return (
    <div className="test-results-overlay" onClick={onClose}>
      <div className="test-results-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h3>🧪 Test Results</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="dialog-content">
          {isLoading ? (
            <div className="loading-state">
              <div className="loading-spinner">🔄</div>
              <p>Testing rule against transactions...</p>
            </div>
          ) : error ? (
            <div className="error-state">
              <div className="error-icon">❌</div>
              <p>Error testing rule: {error}</p>
            </div>
          ) : (
            <div className="results-content">
              <div className="results-summary">
                <strong>{transactions.length} matching transactions found</strong>
                {results?.totalMatches !== undefined && (
                  <div style={{fontSize: '0.9rem', marginTop: '8px', color: '#666'}}>
                    API reported total matches: {results.totalMatches}
                  </div>
                )}
                {results?.averageConfidence !== undefined && (
                  <div style={{fontSize: '0.9rem', marginTop: '4px', color: '#666'}}>
                    Average confidence: {Math.round(results.averageConfidence * 100)}%
                  </div>
                )}
                {/* Debug info showing what rule was actually tested */}
                <div style={{
                  marginTop: '12px', 
                  padding: '8px', 
                  backgroundColor: '#f0f0f0', 
                  borderRadius: '4px',
                  fontSize: '0.8rem',
                  color: '#333'
                }}>
                  <strong>Rule tested:</strong> {rule.fieldToMatch} {rule.condition} "{rule.value || '(empty)'}"
                  {rule.caseSensitive && ' (case sensitive)'}
                  {rule.condition === 'amount_between' && rule.amountMin && rule.amountMax && 
                    ` (between ${rule.amountMin} and ${rule.amountMax})`}
                  {!rule.value && rule.condition !== 'amount_between' && 
                    ' ⚠️ Note: Empty value matches all transactions!'}
                </div>
              </div>
              
              {transactions.length > 0 ? (
                <div className="transactions-list">
                  {transactions.slice(0, 50).map((transaction: Transaction, index: number) => (
                    <div key={index} className="transaction-item">
                      <div className="transaction-main">
                        <span className="transaction-description">
                          {transaction.description || 'No description'}
                        </span>
                        <span className="transaction-amount">
                          ${Math.abs(Number(transaction.amount) || 0).toFixed(2)}
                        </span>
                      </div>
                      {transaction.date && (
                        <div className="transaction-date">
                          {new Date(transaction.date).toLocaleDateString()}
                        </div>
                      )}
                      {transaction.payee && (
                        <div className="transaction-payee">
                          Payee: {transaction.payee}
                        </div>
                      )}
                    </div>
                  ))}
                  {transactions.length > 50 && (
                    <div className="more-results">
                      And {transactions.length - 50} more transactions...
                    </div>
                  )}
                </div>
              ) : (
                <div className="no-matches">
                  <p>No transactions match this rule.</p>
                  <small>Try adjusting your matching criteria.</small>
                </div>
              )}
            </div>
          )}
        </div>
        
        <div className="dialog-actions">
          <button className="close-dialog-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default RuleBuilder; 
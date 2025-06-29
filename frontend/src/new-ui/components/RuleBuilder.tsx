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
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showPatternBuilder, setShowPatternBuilder] = useState(false);

  const {
    isTestingRule,
    testResults,
    error: testError,
    isLivePreviewEnabled,
    toggleLivePreview,
    testRuleImmediate,
    generateSmartSuggestions,
    validatePattern
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
  }, [localRule, testRuleImmediate]);

  const handleGeneratePattern = useCallback(async (sampleDescriptions: string[]) => {
    try {
      const generatedPattern = await generateSmartSuggestions(sampleDescriptions);
      if (generatedPattern) {
        setLocalRule(prev => ({
          ...prev,
          value: generatedPattern.pattern,
          condition: 'regex' as MatchCondition
        }));
      }
    } catch (error) {
      console.error('Error generating pattern:', error);
    }
  }, [generateSmartSuggestions]);

  const isAmountCondition = localRule.condition === 'amount_greater' || 
                           localRule.condition === 'amount_less' || 
                           localRule.condition === 'amount_between';

  const isRegexCondition = localRule.condition === 'regex';

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

  return (
    <div className="rule-builder">
      <div className="rule-builder-header">
        <div className="header-content">
          <h3>{isNew ? '🆕 Create New Rule' : '✏️ Edit Rule'}</h3>
          <p>Define matching criteria for <strong>{categoryName}</strong></p>
        </div>
        
        <div className="header-actions">
          <button
            className={`live-preview-toggle ${isLivePreviewEnabled ? 'active' : ''}`}
            onClick={() => toggleLivePreview(!isLivePreviewEnabled)}
            title="Toggle live preview"
          >
            {isLivePreviewEnabled ? '👁️ Live' : '👁️‍🗨️ Manual'}
          </button>
        </div>
      </div>

      <div className="rule-builder-content">
        <div className="rule-form">
          {/* Basic Rule Configuration */}
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
                <div className="value-input-group">
                  <input
                    id="rule-value"
                    type={isAmountCondition ? 'number' : 'text'}
                    step={isAmountCondition ? '0.01' : undefined}
                    value={localRule.value}
                    onChange={(e) => handleFieldChange('value', e.target.value)}
                    className="form-input"
                    placeholder={
                      isAmountCondition ? 'Enter amount...' :
                      isRegexCondition ? 'Enter regex pattern...' :
                      'Enter text to match...'
                    }
                  />
                  
                  {!isAmountCondition && (
                    <button
                      type="button"
                      className="pattern-builder-btn"
                      onClick={() => setShowPatternBuilder(true)}
                      title="Smart pattern builder"
                    >
                      🧠 Smart
                    </button>
                  )}
                </div>
              )}

              {isRegexCondition && (
                <RegexValidator
                  pattern={localRule.value}
                  onValidate={async (pattern) => {
                    const result = await validatePattern(pattern, localRule.condition);
                    return result || { isValid: false, error: 'Validation failed' };
                  }}
                />
              )}
            </div>
          </div>

          {/* Advanced Settings */}
          <div className="form-section">
            <div className="section-header">
              <h4>⚙️ Advanced Settings</h4>
              <button
                type="button"
                className="toggle-advanced"
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                {showAdvanced ? '▼ Hide' : '▶ Show'}
              </button>
            </div>

            {showAdvanced && (
              <div className="advanced-settings">
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="rule-priority">Priority</label>
                    <input
                      id="rule-priority"
                      type="number"
                      min="0"
                      max="100"
                      value={localRule.priority}
                      onChange={(e) => handleFieldChange('priority', parseInt(e.target.value) || 0)}
                      className="form-input"
                    />
                    <small className="form-help">Higher priority rules are evaluated first</small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="rule-confidence">Confidence</label>
                    <input
                      id="rule-confidence"
                      type="number"
                      min="0"
                      max="1"
                      step="0.1"
                      value={localRule.confidence}
                      onChange={(e) => handleFieldChange('confidence', parseFloat(e.target.value) || 1.0)}
                      className="form-input"
                    />
                    <small className="form-help">How confident we are in this rule (0.0 - 1.0)</small>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group checkbox-group">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={localRule.caseSensitive}
                        onChange={(e) => handleFieldChange('caseSensitive', e.target.checked)}
                      />
                      <span className="checkbox-text">Case Sensitive</span>
                    </label>
                    <small className="form-help">Make text matching case-sensitive</small>
                  </div>

                  <div className="form-group checkbox-group">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={localRule.enabled}
                        onChange={(e) => handleFieldChange('enabled', e.target.checked)}
                      />
                      <span className="checkbox-text">Enabled</span>
                    </label>
                    <small className="form-help">Enable or disable this rule</small>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Test Section */}
          <div className="form-section">
            <div className="section-header">
              <h4>🧪 Test Rule</h4>
              <button
                type="button"
                className="test-rule-btn"
                onClick={handleTestRule}
                disabled={isTestingRule || !localRule.value}
              >
                {isTestingRule ? '🔄 Testing...' : '🎯 Test Rule'}
              </button>
            </div>

            {testError && (
              <div className="test-error">
                <span className="error-icon">❌</span>
                <span>{testError}</span>
              </div>
            )}

            {testResults && testResults.transactions && testResults.transactions.length > 0 && (
              <TestResults
                results={testResults.transactions}
                rule={localRule}
                highlightMatches={true}
              />
            )}

            {isLivePreviewEnabled && (
              <div className="live-preview-indicator">
                <span className="live-indicator">🔴 Live Preview Active</span>
                <small>Results update automatically as you type</small>
              </div>
            )}
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
          disabled={isSaving || !localRule.value}
        >
          {isSaving ? '💾 Saving...' : isNew ? '✅ Create Rule' : '💾 Save Changes'}
        </button>
      </div>

      {/* Smart Pattern Builder Modal */}
      {showPatternBuilder && (
        <SmartPatternBuilder
          onPatternGenerated={handleGeneratePattern}
          onClose={() => setShowPatternBuilder(false)}
          currentField={localRule.fieldToMatch}
        />
      )}
    </div>
  );
};

// Supporting Components

interface RegexValidatorProps {
  pattern: string;
  onValidate: (pattern: string) => Promise<{ isValid: boolean; error?: string; suggestion?: string }>;
}

const RegexValidator: React.FC<RegexValidatorProps> = ({ pattern, onValidate }) => {
  const [validation, setValidation] = useState<{ isValid: boolean; error?: string; suggestion?: string } | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  useEffect(() => {
    if (pattern) {
      setIsValidating(true);
      const timer = setTimeout(async () => {
        try {
          const result = await onValidate(pattern);
          setValidation(result);
        } catch (error) {
          setValidation({ isValid: false, error: 'Validation failed' });
        } finally {
          setIsValidating(false);
        }
      }, 300);

      return () => clearTimeout(timer);
    } else {
      setValidation(null);
    }
  }, [pattern, onValidate]);

  if (!pattern) return null;

  return (
    <div className="regex-validator">
      {isValidating ? (
        <div className="validation-loading">🔄 Validating...</div>
      ) : validation ? (
        <div className={`validation-result ${validation.isValid ? 'valid' : 'invalid'}`}>
          <span className="validation-icon">
            {validation.isValid ? '✅' : '❌'}
          </span>
          <span className="validation-message">
            {validation.isValid ? 'Valid regex pattern' : validation.error}
          </span>
          {validation.suggestion && (
            <div className="validation-suggestion">
              💡 Suggestion: {validation.suggestion}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};

interface TestResultsProps {
  results: Transaction[];
  rule: CategoryRule;
  highlightMatches: boolean;
}

const TestResults: React.FC<TestResultsProps> = ({ results, rule, highlightMatches }) => {
  const highlightText = useCallback((text: string, pattern: string, condition: MatchCondition): string => {
    if (!highlightMatches || !pattern || rule.fieldToMatch === 'amount') return text;

    try {
      let regex: RegExp;
      
      switch (condition) {
        case 'contains':
          regex = new RegExp(`(${pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, rule.caseSensitive ? 'g' : 'gi');
          break;
        case 'starts_with':
          regex = new RegExp(`^(${pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, rule.caseSensitive ? 'g' : 'gi');
          break;
        case 'ends_with':
          regex = new RegExp(`(${pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})$`, rule.caseSensitive ? 'g' : 'gi');
          break;
        case 'equals':
          regex = new RegExp(`^(${pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})$`, rule.caseSensitive ? 'g' : 'gi');
          break;
        case 'regex':
          regex = new RegExp(`(${pattern})`, rule.caseSensitive ? 'g' : 'gi');
          break;
        default:
          return text;
      }

      return text.replace(regex, '<mark>$1</mark>');
    } catch (error) {
      return text;
    }
  }, [rule.caseSensitive, rule.fieldToMatch]);

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

  return (
    <div className="test-results">
      <div className="test-results-header">
        <h5>🎯 Match Results ({results.length} transactions)</h5>
        {results.length > 10 && (
          <small>Showing first 10 results</small>
        )}
      </div>

      <div className="test-results-list">
        {results.slice(0, 10).map((transaction, index) => {
          const fieldValue = getFieldValue(transaction, rule.fieldToMatch);
          const highlightedValue = highlightText(fieldValue, rule.value, rule.condition);
          
          return (
            <div key={transaction.transactionId || index} className="test-result-item">
              <div className="result-field">
                <strong>{rule.fieldToMatch}:</strong>
                <span 
                  className="field-value"
                  dangerouslySetInnerHTML={{ __html: highlightedValue }}
                />
              </div>
              <div className="result-details">
                <span className="transaction-date">
                  {new Date(transaction.date).toLocaleDateString()}
                </span>
                <span className="transaction-amount">
                  ${Math.abs(Number(transaction.amount) || 0).toFixed(2)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface SmartPatternBuilderProps {
  onPatternGenerated: (descriptions: string[]) => void;
  onClose: () => void;
  currentField: string;
}

const SmartPatternBuilder: React.FC<SmartPatternBuilderProps> = ({
  onPatternGenerated,
  onClose,
  currentField
}) => {
  const [sampleText, setSampleText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = useCallback(async () => {
    const descriptions = sampleText.split('\n').filter(line => line.trim());
    if (descriptions.length === 0) return;

    setIsGenerating(true);
    try {
      await onPatternGenerated(descriptions);
      onClose();
    } catch (error) {
      console.error('Error generating pattern:', error);
    } finally {
      setIsGenerating(false);
    }
  }, [sampleText, onPatternGenerated, onClose]);

  return (
    <div className="modal-overlay">
      <div className="smart-pattern-builder">
        <div className="builder-header">
          <h3>🧠 Smart Pattern Builder</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        
        <div className="builder-content">
          <p>
            Paste sample {currentField} values to auto-generate a matching pattern:
          </p>
          
          <textarea
            value={sampleText}
            onChange={(e) => setSampleText(e.target.value)}
            placeholder={`Example ${currentField} values:\nAMAZON.COM PURCHASE\nAMAZON PRIME MEMBERSHIP\nAMAZON MARKETPLACE\n\nEach line should be a separate example`}
            rows={8}
            className="sample-textarea"
          />
          
          <div className="builder-actions">
            <button
              className="cancel-btn"
              onClick={onClose}
              disabled={isGenerating}
            >
              Cancel
            </button>
            <button
              className="generate-btn"
              onClick={handleGenerate}
              disabled={isGenerating || !sampleText.trim()}
            >
              {isGenerating ? '🔄 Generating...' : '✨ Generate Pattern'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RuleBuilder; 
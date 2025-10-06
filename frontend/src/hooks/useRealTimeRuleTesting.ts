// Real-time Rule Testing Hook (Phase 3.1)
// Provides debounced live preview, pattern validation, and smart suggestions

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  CategoryRule,
  RuleTestResponse,
  PatternGenerationResponse,
  RegexValidationResponse,
  MatchCondition
} from '../../types/Category';
import { CategoryService } from '../../services/CategoryService';

export interface RealTimeTestingState {
  // Rule being tested
  currentRule: Partial<CategoryRule> | null;
  
  // Test results
  testResults: RuleTestResponse | null;
  isTestingRule: boolean;
  lastTestTime: number | null;
  
  // Live preview settings
  isLivePreviewEnabled: boolean;
  debounceDelay: number;
  
  // Pattern validation
  validationResult: RegexValidationResponse | null;
  isValidatingPattern: boolean;
  
  // Smart suggestions
  smartSuggestions: PatternGenerationResponse | null;
  isGeneratingSuggestions: boolean;
  
  // Error handling
  error: string | null;
}

export interface UseRealTimeRuleTestingOptions {
  debounceDelay?: number;
  enableLivePreview?: boolean;
  validatePatterns?: boolean;
  maxPreviewResults?: number;
}

export const useRealTimeRuleTesting = (options: UseRealTimeRuleTestingOptions = {}) => {
  const {
    debounceDelay = 500,
    enableLivePreview = true,
    validatePatterns = true,
    maxPreviewResults = 50
  } = options;

  const [state, setState] = useState<RealTimeTestingState>({
    currentRule: null,
    testResults: null,
    isTestingRule: false,
    lastTestTime: null,
    isLivePreviewEnabled: enableLivePreview,
    debounceDelay,
    validationResult: null,
    isValidatingPattern: false,
    smartSuggestions: null,
    isGeneratingSuggestions: false,
    error: null
  });

  // Refs for debouncing
  const testDebounceRef = useRef<number | null>(null);
  const validationDebounceRef = useRef<number | null>(null);
  const debouncedTestFnRef = useRef<ReturnType<typeof CategoryService.createDebouncedRuleTest> | null>(null);

  // Initialize debounced test function
  useEffect(() => {
    debouncedTestFnRef.current = CategoryService.createDebouncedRuleTest(debounceDelay);
    
    return () => {
      if (testDebounceRef.current) {
        clearTimeout(testDebounceRef.current);
      }
      if (validationDebounceRef.current) {
        clearTimeout(validationDebounceRef.current);
      }
    };
  }, [debounceDelay]);

  // ===== Core Testing Functions =====

  const testRuleImmediate = useCallback(async (rule: CategoryRule): Promise<RuleTestResponse | null> => {
    setState(prev => ({ ...prev, isTestingRule: true, error: null }));
    
    try {
      const results = await CategoryService.testRule(rule, maxPreviewResults);
      
      setState(prev => ({
        ...prev,
        testResults: results,
        isTestingRule: false,
        lastTestTime: Date.now()
      }));
      
      return results;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to test rule';
      setState(prev => ({
        ...prev,
        isTestingRule: false,
        error: errorMessage,
        testResults: null
      }));
      return null;
    }
  }, [maxPreviewResults]);

  const testRuleDebounced = useCallback((rule: Partial<CategoryRule>) => {
    if (!debouncedTestFnRef.current || !isValidCategoryRule(rule)) {
      return;
    }

    setState(prev => ({ 
      ...prev, 
      currentRule: rule,
      isTestingRule: true,
      error: null 
    }));

    // Clear existing timeout
    if (testDebounceRef.current) {
      clearTimeout(testDebounceRef.current);
    }

    // Set new debounced test
    testDebounceRef.current = window.setTimeout(() => {
      if (debouncedTestFnRef.current) {
        debouncedTestFnRef.current(rule as CategoryRule, (results: RuleTestResponse) => {
          setState(prev => ({
            ...prev,
            testResults: results,
            isTestingRule: false,
            lastTestTime: Date.now()
          }));
        });
      }
    }, debounceDelay);
  }, [debounceDelay]);

  // ===== Pattern Validation =====

  const validatePattern = useCallback(async (pattern: string, condition: MatchCondition): Promise<RegexValidationResponse | null> => {
    if (!validatePatterns || condition !== MatchCondition.REGEX) {
      return null;
    }

    setState(prev => ({ ...prev, isValidatingPattern: true }));

    try {
      const validation = await CategoryService.validateRegexPattern(pattern);
      
      setState(prev => ({
        ...prev,
        validationResult: validation,
        isValidatingPattern: false
      }));
      
      return validation;
    } catch (error) {
      setState(prev => ({
        ...prev,
        isValidatingPattern: false,
        validationResult: {
          isValid: false,
          error: error instanceof Error ? error.message : 'Validation failed'
        }
      }));
      return null;
    }
  }, [validatePatterns]);

  const validatePatternDebounced = useCallback((pattern: string, condition: MatchCondition) => {
    if (!validatePatterns || condition !== MatchCondition.REGEX || !pattern.trim()) {
      return;
    }

    // Clear existing timeout
    if (validationDebounceRef.current) {
      clearTimeout(validationDebounceRef.current);
    }

    setState(prev => ({ ...prev, isValidatingPattern: true }));

    // Set new debounced validation
    validationDebounceRef.current = window.setTimeout(() => {
      validatePattern(pattern, condition);
    }, 300); // Faster validation than testing
  }, [validatePattern, validatePatterns]);

  // ===== Smart Pattern Generation =====

  const generateSmartSuggestions = useCallback(async (
    descriptions: string[], 
    patternType: 'simple' | 'regex' = 'simple'
  ): Promise<PatternGenerationResponse | null> => {
    if (!descriptions.length) return null;

    setState(prev => ({ ...prev, isGeneratingSuggestions: true }));

    try {
      const suggestions = await CategoryService.generatePattern(descriptions, patternType);
      
      setState(prev => ({
        ...prev,
        smartSuggestions: suggestions,
        isGeneratingSuggestions: false
      }));
      
      return suggestions;
    } catch (error) {
      setState(prev => ({
        ...prev,
        isGeneratingSuggestions: false,
        error: error instanceof Error ? error.message : 'Failed to generate suggestions'
      }));
      return null;
    }
  }, []);

  // ===== Rule Update Handlers =====

  const updateRuleField = useCallback((field: keyof CategoryRule, value: any) => {
    const updatedRule = {
      ...state.currentRule,
      [field]: value
    } as Partial<CategoryRule>;

    setState(prev => ({ ...prev, currentRule: updatedRule }));

    // Trigger live preview if enabled and rule is valid
    if (state.isLivePreviewEnabled && isValidCategoryRule(updatedRule)) {
      testRuleDebounced(updatedRule);
    }

    // Trigger pattern validation for regex patterns
    if (field === 'value' || field === 'condition') {
      const condition = field === 'condition' ? value : updatedRule.condition;
      const pattern = field === 'value' ? value : updatedRule.value;
      
      if (condition && pattern) {
        validatePatternDebounced(pattern, condition);
      }
    }
  }, [state.currentRule, state.isLivePreviewEnabled, testRuleDebounced, validatePatternDebounced]);

  const setRule = useCallback((rule: Partial<CategoryRule>) => {
    setState(prev => ({ ...prev, currentRule: rule }));

    if (state.isLivePreviewEnabled && isValidCategoryRule(rule)) {
      testRuleDebounced(rule);
    }

    // Validate regex patterns
    if (rule.condition === MatchCondition.REGEX && rule.value) {
      validatePatternDebounced(rule.value, rule.condition);
    }
  }, [state.isLivePreviewEnabled, testRuleDebounced, validatePatternDebounced]);

  // ===== Control Functions =====

  const toggleLivePreview = useCallback((enabled: boolean) => {
    setState(prev => ({ ...prev, isLivePreviewEnabled: enabled }));
    
    // If enabling and we have a valid rule, test it
    if (enabled && state.currentRule && isValidCategoryRule(state.currentRule)) {
      testRuleDebounced(state.currentRule);
    }
  }, [state.currentRule, testRuleDebounced]);

  const clearResults = useCallback(() => {
    setState(prev => ({
      ...prev,
      testResults: null,
      validationResult: null,
      smartSuggestions: null,
      error: null,
      lastTestTime: null
    }));
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // ===== Utility Functions =====

  const getMatchCount = useCallback((): number => {
    return state.testResults?.matchCount || 0;
  }, [state.testResults]);

  const getConfidenceLevel = useCallback((): 'high' | 'medium' | 'low' | null => {
    if (!state.testResults) return null;
    
    const confidence = state.testResults.confidence;
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.6) return 'medium';
    return 'low';
  }, [state.testResults]);

  const isPatternValid = useCallback((): boolean => {
    if (!state.validationResult) return true; // Assume valid if not validated
    return state.validationResult.isValid;
  }, [state.validationResult]);

  const getValidationMessage = useCallback((): string | null => {
    if (!state.validationResult) return null;
    return state.validationResult.error || null;
  }, [state.validationResult]);

  const getSuggestionText = useCallback((): string | null => {
    return state.smartSuggestions?.pattern || null;
  }, [state.smartSuggestions]);

  const getSuggestionConfidence = useCallback((): number => {
    return state.smartSuggestions?.confidence || 0;
  }, [state.smartSuggestions]);

  // ===== Rule Building Helpers =====

  const createDefaultRule = useCallback((
    fieldToMatch: string = 'description',
    condition: MatchCondition = MatchCondition.CONTAINS
  ): Partial<CategoryRule> => {
    return CategoryService.createDefaultRule(fieldToMatch, condition, '');
  }, []);

  const buildRuleFromSuggestion = useCallback((suggestion: PatternGenerationResponse): Partial<CategoryRule> => {
    return {
      ...createDefaultRule(),
      condition: MatchCondition.CONTAINS,
      value: suggestion.pattern,
      confidence: suggestion.confidence
    };
  }, [createDefaultRule]);

  // ===== Performance Monitoring =====

  const getPerformanceMetrics = useCallback(() => {
    return {
      lastTestDuration: state.lastTestTime ? Date.now() - state.lastTestTime : null,
      isRealTimeEnabled: state.isLivePreviewEnabled,
      debounceDelay: state.debounceDelay,
      matchCount: getMatchCount(),
      confidenceLevel: getConfidenceLevel()
    };
  }, [state.lastTestTime, state.isLivePreviewEnabled, state.debounceDelay, getMatchCount, getConfidenceLevel]);

  return {
    // State
    ...state,
    
    // Core testing
    testRuleImmediate,
    testRuleDebounced,
    
    // Pattern validation
    validatePattern,
    validatePatternDebounced,
    isPatternValid,
    getValidationMessage,
    
    // Smart suggestions
    generateSmartSuggestions,
    getSuggestionText,
    getSuggestionConfidence,
    
    // Rule management
    updateRuleField,
    setRule,
    createDefaultRule,
    buildRuleFromSuggestion,
    
    // Controls
    toggleLivePreview,
    clearResults,
    clearError,
    
    // Utility
    getMatchCount,
    getConfidenceLevel,
    getPerformanceMetrics
  };
};

// ===== Utility Functions =====

function isValidCategoryRule(rule: Partial<CategoryRule>): rule is CategoryRule {
  return !!(
    rule.fieldToMatch &&
    rule.condition &&
    rule.value &&
    typeof rule.caseSensitive === 'boolean' &&
    typeof rule.priority === 'number' &&
    typeof rule.enabled === 'boolean' &&
    typeof rule.confidence === 'number' &&
    typeof rule.allowMultipleMatches === 'boolean' &&
    typeof rule.autoSuggest === 'boolean'
  );
}

// ===== Custom Hook for Rule Form Integration =====

export const useRuleFormWithRealTimeTesting = (initialRule?: Partial<CategoryRule>) => {
  const realTimeTesting = useRealTimeRuleTesting({
    enableLivePreview: true,
    validatePatterns: true,
    debounceDelay: 500,
    maxPreviewResults: 50
  });

  // Initialize with provided rule
  useEffect(() => {
    if (initialRule) {
      realTimeTesting.setRule(initialRule);
    }
  }, [initialRule, realTimeTesting.setRule]);

  const updateField = useCallback((field: keyof CategoryRule, value: any) => {
    realTimeTesting.updateRuleField(field, value);
  }, [realTimeTesting.updateRuleField]);

  const validateAndTest = useCallback(async () => {
    if (realTimeTesting.currentRule && isValidCategoryRule(realTimeTesting.currentRule)) {
      return await realTimeTesting.testRuleImmediate(realTimeTesting.currentRule);
    }
    return null;
  }, [realTimeTesting.currentRule, realTimeTesting.testRuleImmediate]);

  const canTestRule = useCallback((): boolean => {
    return !!(realTimeTesting.currentRule && isValidCategoryRule(realTimeTesting.currentRule));
  }, [realTimeTesting.currentRule]);

  const getFormValidation = useCallback(() => {
    const rule = realTimeTesting.currentRule;
    if (!rule) return { isValid: false, errors: ['No rule specified'] };
    
    return CategoryService.validateRule(rule);
  }, [realTimeTesting.currentRule]);

  return {
    ...realTimeTesting,
    updateField,
    validateAndTest,
    canTestRule,
    getFormValidation
  };
};

export default useRealTimeRuleTesting; 
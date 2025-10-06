// React Hooks for Category Management (Phase 3.1)
// Comprehensive hooks for all category management functionality

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Category,
  CategoryCreate,
  CategoryUpdate,
  CategoryRule,
  CategoryHierarchy,
  TransactionCategoryAssignment,
  CategorySuggestionStrategy,
  RuleTestResponse,
  CategoryPreviewResponse,
  PatternGenerationResponse,
  RegexValidationResponse,
  CategoryManagementState,
  RuleTestingState,
  SuggestionReviewState,
  MatchCondition
} from '../../types/Category';
import { CategoryService } from '../../services/CategoryService';

// ===== Core Category Management Hook =====

export const useCategories = () => {
  const [state, setState] = useState<CategoryManagementState>({
    categories: [],
    hierarchy: [],
    selectedCategory: null,
    isLoading: false,
    error: null,
    lastUpdated: null
  });

  const loadCategories = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const [categories, hierarchy] = await Promise.all([
        CategoryService.getCategories(),
        CategoryService.getCategoryHierarchy()
      ]);

      setState(prev => ({
        ...prev,
        categories,
        hierarchy,
        isLoading: false,
        lastUpdated: Date.now()
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load categories'
      }));
    }
  }, []);

  const createCategory = useCallback(async (categoryData: CategoryCreate): Promise<Category | null> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const newCategory = await CategoryService.createCategory(categoryData);
      
      // Refresh categories and hierarchy
      await loadCategories();
      
      return newCategory;
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to create category'
      }));
      return null;
    }
  }, [loadCategories]);

  const updateCategory = useCallback(async (categoryId: string, categoryData: CategoryUpdate): Promise<Category | null> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const updatedCategory = await CategoryService.updateCategory(categoryId, categoryData);
      
      // Update local state
      setState(prev => ({
        ...prev,
        categories: prev.categories.map(cat => 
          cat.categoryId === categoryId ? updatedCategory : cat
        ),
        selectedCategory: prev.selectedCategory?.categoryId === categoryId ? updatedCategory : prev.selectedCategory,
        isLoading: false
      }));
      
      return updatedCategory;
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to update category'
      }));
      return null;
    }
  }, []);

  const deleteCategory = useCallback(async (categoryId: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      await CategoryService.deleteCategory(categoryId);
      
      // Remove from local state
      setState(prev => ({
        ...prev,
        categories: prev.categories.filter(cat => cat.categoryId !== categoryId),
        selectedCategory: prev.selectedCategory?.categoryId === categoryId ? null : prev.selectedCategory,
        isLoading: false
      }));
      
      // Refresh hierarchy
      await loadCategories();
      
      return true;
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to delete category'
      }));
      return false;
    }
  }, [loadCategories]);

  const selectCategory = useCallback((category: Category | null) => {
    setState(prev => ({ ...prev, selectedCategory: category }));
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // Load categories on mount
  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  return {
    ...state,
    loadCategories,
    createCategory,
    updateCategory,
    deleteCategory,
    selectCategory,
    clearError,
    refresh: loadCategories
  };
};

// ===== Rule Testing Hook =====

export const useRuleTesting = () => {
  const [state, setState] = useState<RuleTestingState>({
    currentRule: null,
    testResults: null,
    isTestingRule: false,
    isLivePreview: false,
    debounceTimer: null
  });

  const debouncedTestRef = useRef<ReturnType<typeof CategoryService.createDebouncedRuleTest> | null>(null);

  useEffect(() => {
    debouncedTestRef.current = CategoryService.createDebouncedRuleTest(500);
    
    return () => {
      if (state.debounceTimer) {
        clearTimeout(state.debounceTimer);
      }
    };
  }, [state.debounceTimer]);

  const testRule = useCallback(async (rule: CategoryRule): Promise<RuleTestResponse | null> => {
    setState(prev => ({ ...prev, isTestingRule: true, currentRule: rule }));
    
    try {
      const results = await CategoryService.testRule(rule);
      setState(prev => ({
        ...prev,
        testResults: results,
        isTestingRule: false
      }));
      return results;
    } catch (error) {
      console.error('Error testing rule:', error);
      setState(prev => ({
        ...prev,
        testResults: null,
        isTestingRule: false
      }));
      return null;
    }
  }, []);

  const testRuleDebounced = useCallback((rule: CategoryRule) => {
    if (!debouncedTestRef.current) return;
    
    setState(prev => ({ ...prev, currentRule: rule }));
    
    debouncedTestRef.current(rule, (results: RuleTestResponse) => {
      setState(prev => ({
        ...prev,
        testResults: results,
        isTestingRule: false
      }));
    });
  }, []);

  const setLivePreview = useCallback((enabled: boolean) => {
    setState(prev => ({ ...prev, isLivePreview: enabled }));
  }, []);

  const clearResults = useCallback(() => {
    setState(prev => ({
      ...prev,
      testResults: null,
      currentRule: null
    }));
  }, []);

  return {
    ...state,
    testRule,
    testRuleDebounced,
    setLivePreview,
    clearResults
  };
};

// ===== Category Preview Hook =====

export const useCategoryPreview = () => {
  const [previewData, setPreviewData] = useState<CategoryPreviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const previewCategoryMatches = useCallback(async (categoryId: string, includeInherited: boolean = true) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const results = await CategoryService.previewCategoryMatches(categoryId, includeInherited);
      setPreviewData(results);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to preview category matches');
      setPreviewData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearPreview = useCallback(() => {
    setPreviewData(null);
    setError(null);
  }, []);

  return {
    previewData,
    isLoading,
    error,
    previewCategoryMatches,
    clearPreview
  };
};

// ===== Pattern Generation Hook =====

export const usePatternGeneration = () => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [lastGenerated, setLastGenerated] = useState<PatternGenerationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const generatePattern = useCallback(async (
    descriptions: string[], 
    patternType: 'simple' | 'regex' = 'simple'
  ): Promise<PatternGenerationResponse | null> => {
    setIsGenerating(true);
    setError(null);
    
    try {
      const result = await CategoryService.generatePattern(descriptions, patternType);
      setLastGenerated(result);
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate pattern';
      setError(errorMessage);
      return null;
    } finally {
      setIsGenerating(false);
    }
  }, []);

  const validateRegex = useCallback(async (pattern: string): Promise<RegexValidationResponse | null> => {
    try {
      return await CategoryService.validateRegexPattern(pattern);
    } catch (error) {
      console.error('Error validating regex:', error);
      return {
        isValid: false,
        error: error instanceof Error ? error.message : 'Validation failed'
      };
    }
  }, []);

  const clearGenerated = useCallback(() => {
    setLastGenerated(null);
    setError(null);
  }, []);

  return {
    isGenerating,
    lastGenerated,
    error,
    generatePattern,
    validateRegex,
    clearGenerated
  };
};

// ===== Suggestion Review Hook =====

export const useSuggestionReview = () => {
  const [state, setState] = useState<SuggestionReviewState>({
    pendingSuggestions: new Map(),
    isReviewModalOpen: false,
    currentTransactionId: null,
    reviewStrategy: CategorySuggestionStrategy.ALL_MATCHES
  });

  const loadSuggestions = useCallback(async (transactionId: string) => {
    try {
      const suggestions = await CategoryService.getTransactionCategorySuggestions(transactionId);
      
      setState(prev => ({
        ...prev,
        pendingSuggestions: new Map(prev.pendingSuggestions.set(transactionId, suggestions))
      }));
      
      return suggestions;
    } catch (error) {
      console.error('Error loading suggestions:', error);
      return [];
    }
  }, []);

  const confirmSuggestions = useCallback(async (
    transactionId: string,
    confirmedCategoryIds: string[],
    primaryCategoryId: string
  ): Promise<boolean> => {
    try {
      await CategoryService.confirmCategorySuggestions(transactionId, confirmedCategoryIds, primaryCategoryId);
      
      // Remove from pending suggestions
      setState(prev => {
        const newPendingSuggestions = new Map(prev.pendingSuggestions);
        newPendingSuggestions.delete(transactionId);
        
        return {
          ...prev,
          pendingSuggestions: newPendingSuggestions,
          isReviewModalOpen: false,
          currentTransactionId: null
        };
      });
      
      return true;
    } catch (error) {
      console.error('Error confirming suggestions:', error);
      return false;
    }
  }, []);

  const rejectSuggestion = useCallback(async (transactionId: string, categoryId: string): Promise<boolean> => {
    try {
      await CategoryService.rejectCategorySuggestion(transactionId, categoryId);
      
      // Update local suggestions
      setState(prev => {
        const suggestions = prev.pendingSuggestions.get(transactionId) || [];
        const updatedSuggestions = suggestions.filter(s => s.categoryId !== categoryId);
        
        const newPendingSuggestions = new Map(prev.pendingSuggestions);
        if (updatedSuggestions.length > 0) {
          newPendingSuggestions.set(transactionId, updatedSuggestions);
        } else {
          newPendingSuggestions.delete(transactionId);
        }
        
        return {
          ...prev,
          pendingSuggestions: newPendingSuggestions
        };
      });
      
      return true;
    } catch (error) {
      console.error('Error rejecting suggestion:', error);
      return false;
    }
  }, []);

  const openReviewModal = useCallback((transactionId: string) => {
    setState(prev => ({
      ...prev,
      isReviewModalOpen: true,
      currentTransactionId: transactionId
    }));
  }, []);

  const closeReviewModal = useCallback(() => {
    setState(prev => ({
      ...prev,
      isReviewModalOpen: false,
      currentTransactionId: null
    }));
  }, []);

  const setReviewStrategy = useCallback((strategy: CategorySuggestionStrategy) => {
    setState(prev => ({ ...prev, reviewStrategy: strategy }));
  }, []);

  const getPendingSuggestionCount = useCallback((transactionId?: string): number => {
    if (transactionId) {
      return state.pendingSuggestions.get(transactionId)?.length || 0;
    }
    
    return Array.from(state.pendingSuggestions.values()).reduce((total, suggestions) => total + suggestions.length, 0);
  }, [state.pendingSuggestions]);

  const getCurrentSuggestions = useCallback((): TransactionCategoryAssignment[] => {
    if (!state.currentTransactionId) return [];
    return state.pendingSuggestions.get(state.currentTransactionId) || [];
  }, [state.currentTransactionId, state.pendingSuggestions]);

  return {
    ...state,
    loadSuggestions,
    confirmSuggestions,
    rejectSuggestion,
    openReviewModal,
    closeReviewModal,
    setReviewStrategy,
    getPendingSuggestionCount,
    getCurrentSuggestions
  };
};

// ===== Category Rule Management Hook =====

export const useCategoryRules = (categoryId: string | null) => {
  const [rules, setRules] = useState<CategoryRule[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCategoryRules = useCallback(async () => {
    console.log(`useCategoryRules.loadCategoryRules - categoryId: ${categoryId}`);
    if (!categoryId) {
      console.log(`useCategoryRules.loadCategoryRules - No categoryId, setting rules to empty array`);
      setRules([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      console.log(`useCategoryRules.loadCategoryRules - Calling CategoryService.getCategoryById(${categoryId})`);
      const category = await CategoryService.getCategoryById(categoryId);
      console.log(`useCategoryRules.loadCategoryRules - Got category:`, category);
      console.log(`useCategoryRules.loadCategoryRules - Category rules:`, category.rules);
      console.log(`useCategoryRules.loadCategoryRules - Setting rules to:`, category.rules || []);
      setRules(category.rules || []);
    } catch (error) {
      console.error(`useCategoryRules.loadCategoryRules - Error:`, error);
      setError(error instanceof Error ? error.message : 'Failed to load category rules');
      setRules([]);
    } finally {
      setIsLoading(false);
    }
  }, [categoryId]);

  const addRule = useCallback(async (rule: Omit<CategoryRule, 'ruleId'>): Promise<boolean> => {
    if (!categoryId) return false;

    setIsLoading(true);
    setError(null);

    try {
      const updatedCategory = await CategoryService.addRuleToCategory(categoryId, rule);
      setRules(updatedCategory.rules || []);
      return true;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to add rule');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [categoryId]);

  const updateRule = useCallback(async (ruleId: string, rule: Partial<CategoryRule>): Promise<boolean> => {
    if (!categoryId) return false;

    setIsLoading(true);
    setError(null);

    try {
      const updatedCategory = await CategoryService.updateCategoryRule(categoryId, ruleId, rule);
      setRules(updatedCategory.rules || []);
      return true;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to update rule');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [categoryId]);

  const deleteRule = useCallback(async (ruleId: string): Promise<boolean> => {
    if (!categoryId) return false;

    setIsLoading(true);
    setError(null);

    try {
      const updatedCategory = await CategoryService.deleteCategoryRule(categoryId, ruleId);
      setRules(updatedCategory.rules || []);
      return true;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to delete rule');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [categoryId]);

  const toggleRuleEnabled = useCallback(async (ruleId: string, enabled: boolean): Promise<boolean> => {
    if (!categoryId) return false;

    try {
      const updatedCategory = await CategoryService.toggleRuleEnabled(categoryId, ruleId, enabled);
      setRules(updatedCategory.rules || []);
      return true;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to toggle rule');
      return false;
    }
  }, [categoryId]);

  // Load rules when categoryId changes
  useEffect(() => {
    loadCategoryRules();
  }, [loadCategoryRules]);

  return {
    rules,
    isLoading,
    error,
    addRule,
    updateRule,
    deleteRule,
    toggleRuleEnabled,
    refresh: loadCategoryRules
  };
};

// ===== Bulk Operations Hook =====

export const useBulkOperations = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const bulkCategorize = useCallback(async (
    transactionIds: string[],
    categoryId: string,
    replaceExisting: boolean = false
  ): Promise<boolean> => {
    setIsProcessing(true);
    setError(null);
    setProgress(0);

    try {
      const result = await CategoryService.bulkCategorizeTransactions(transactionIds, categoryId, replaceExisting);
      setProgress(100);
      return result.applied > 0;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Bulk categorization failed');
      return false;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const applyCategoryRules = useCallback(async (
    categoryId: string,
    createSuggestions: boolean = true,
    strategy: CategorySuggestionStrategy = CategorySuggestionStrategy.ALL_MATCHES
  ): Promise<boolean> => {
    setIsProcessing(true);
    setError(null);
    setProgress(0);

    try {
      const result = await CategoryService.applyCategoryRules(categoryId, createSuggestions, strategy);
      setProgress(100);
      return result.applied > 0;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Rule application failed');
      return false;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const bulkConfirmSuggestions = useCallback(async (transactionIds: string[]): Promise<boolean> => {
    setIsProcessing(true);
    setError(null);
    setProgress(0);

    try {
      const result = await CategoryService.bulkConfirmSuggestions(transactionIds);
      setProgress(100);
      return result.applied > 0;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Bulk confirmation failed');
      return false;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isProcessing,
    progress,
    error,
    bulkCategorize,
    applyCategoryRules,
    bulkConfirmSuggestions,
    clearError
  };
}; 
// Comprehensive Category Service for Phase 2.1 Enhanced Category Management
// Integrates with all enhanced backend APIs and provides full TypeScript support

import {
  Category,
  CategoryCreate,
  CategoryUpdate,
  CategoryRule,
  CategoryHierarchy,
  TransactionCategoryAssignment,
  CategorySuggestionStrategy,
  RuleTestRequest,
  RuleTestResponse,
  CategoryPreviewResponse,
  PatternGenerationRequest,
  PatternGenerationResponse,
  RegexValidationRequest,
  RegexValidationResponse,
  CategoryConfirmationRequest,
  BulkCategorizeRequest,
  BulkRuleApplicationRequest,
  BulkOperationResponse,
  CategoryUsageStats,
  CategoryEffectivenessReport,
  CategoryApiResponse,
  MatchCondition
} from '../types/Category';

// Import authentication helper
import { getCurrentUser } from './AuthService';

// API Configuration
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || 'https://api.housef3.com';

// Authenticated request helper
async function authenticatedRequest(endpoint: string, options: RequestInit = {}): Promise<any> {
  const user = getCurrentUser();
  if (!user) {
    throw new Error('User not authenticated');
  }

  // The AuthService returns an AuthUser object with token property, not a Cognito user object
  const token = user.token;
  
  const response = await fetch(`${API_ENDPOINT}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(errorData.message || `Request failed: ${response.status}`);
  }

  return response.json();
}

// Enhanced CategoryService with comprehensive Phase 2.1 functionality
export class CategoryService {
  // ===== Core Category CRUD Operations =====
  
  static async getCategories(): Promise<Category[]> {
    console.log('CategoryService.getCategories() - Making request to /api/categories');
    const response = await authenticatedRequest('/api/categories');
    console.log('CategoryService.getCategories() - Backend response:', response);
    console.log('CategoryService.getCategories() - Response type:', typeof response);
    console.log('CategoryService.getCategories() - Is array?', Array.isArray(response));
    if (response && typeof response === 'object') {
      console.log('CategoryService.getCategories() - Response keys:', Object.keys(response));
    }
    
    // Extract the categories array from the response
    const categories = response.categories || [];
    console.log('CategoryService.getCategories() - Extracted categories:', categories);
    console.log('CategoryService.getCategories() - Categories is array?', Array.isArray(categories));
    
    // Debug individual categories and their rules
    if (Array.isArray(categories)) {
      categories.forEach((category: any, index: number) => {
        console.log(`CategoryService.getCategories() - Category ${index}:`, category);
        console.log(`CategoryService.getCategories() - Category ${index} name:`, category.name);
        console.log(`CategoryService.getCategories() - Category ${index} rules:`, category.rules);
        console.log(`CategoryService.getCategories() - Category ${index} rules type:`, typeof category.rules);
        console.log(`CategoryService.getCategories() - Category ${index} rules is array:`, Array.isArray(category.rules));
        if (category.rules && Array.isArray(category.rules)) {
          console.log(`CategoryService.getCategories() - Category ${index} rules length:`, category.rules.length);
          category.rules.forEach((rule: any, ruleIndex: number) => {
            console.log(`CategoryService.getCategories() - Category ${index} rule ${ruleIndex}:`, rule);
          });
        }
      });
    }
    
    return categories;
  }

  static async getCategoryById(categoryId: string): Promise<Category> {
    console.log(`CategoryService.getCategoryById(${categoryId}) - Making request`);
    const response = await authenticatedRequest(`/api/categories/${categoryId}`);
    console.log(`CategoryService.getCategoryById(${categoryId}) - Response:`, response);
    console.log(`CategoryService.getCategoryById(${categoryId}) - Response.category:`, response.category);
    console.log(`CategoryService.getCategoryById(${categoryId}) - Response.category.rules:`, response.category?.rules);
    console.log(`CategoryService.getCategoryById(${categoryId}) - Response.category.rules length:`, response.category?.rules?.length);
    return response.category;
  }

  static async createCategory(categoryData: CategoryCreate): Promise<Category> {
    const response = await authenticatedRequest('/api/categories', {
      method: 'POST',
      body: JSON.stringify(categoryData)
    });
    return response;
  }

  static async updateCategory(categoryId: string, categoryData: CategoryUpdate): Promise<Category> {
    const response = await authenticatedRequest(`/api/categories/${categoryId}`, {
      method: 'PUT',
      body: JSON.stringify(categoryData)
    });
    return response;
  }

  static async deleteCategory(categoryId: string): Promise<void> {
    await authenticatedRequest(`/api/categories/${categoryId}`, {
      method: 'DELETE'
    });
  }

  // ===== Hierarchical Category Management =====
  
  static async getCategoryHierarchy(): Promise<CategoryHierarchy[]> {
    console.log('CategoryService.getCategoryHierarchy() - Making request to /api/categories/hierarchy');
    const response = await authenticatedRequest('/api/categories/hierarchy');
    console.log('CategoryService.getCategoryHierarchy() - Backend response:', response);
    console.log('CategoryService.getCategoryHierarchy() - Response type:', typeof response);
    console.log('CategoryService.getCategoryHierarchy() - Is array?', Array.isArray(response));
    
    // Debug individual hierarchy nodes and their categories
    if (Array.isArray(response)) {
      response.forEach((node: any, index: number) => {
        console.log(`CategoryService.getCategoryHierarchy() - Node ${index}:`, node);
        console.log(`CategoryService.getCategoryHierarchy() - Node ${index} category:`, node.category);
        console.log(`CategoryService.getCategoryHierarchy() - Node ${index} category name:`, node.category?.name);
        console.log(`CategoryService.getCategoryHierarchy() - Node ${index} category rules:`, node.category?.rules);
        console.log(`CategoryService.getCategoryHierarchy() - Node ${index} category rules length:`, node.category?.rules?.length);
        console.log(`CategoryService.getCategoryHierarchy() - Node ${index} inheritedRules:`, node.inheritedRules);
        console.log(`CategoryService.getCategoryHierarchy() - Node ${index} inheritedRules length:`, node.inheritedRules?.length);
      });
    }
    
    return response;
  }

  static async createSubCategory(parentCategoryId: string, categoryData: CategoryCreate): Promise<Category> {
    const response = await authenticatedRequest('/api/categories', {
      method: 'POST',
      body: JSON.stringify({ ...categoryData, parentCategoryId })
    });
    return response;
  }

  static async moveCategoryToParent(categoryId: string, newParentId: string | null): Promise<Category> {
    const response = await authenticatedRequest(`/api/categories/${categoryId}`, {
      method: 'PUT',
      body: JSON.stringify({ parentCategoryId: newParentId })
    });
    return response;
  }

  // ===== Enhanced Rule Testing & Validation (Phase 2.1) =====
  
  static async testRule(rule: CategoryRule, limit: number = 100): Promise<RuleTestResponse> {
    const request: RuleTestRequest = { rule, limit };
    const response = await authenticatedRequest('/api/categories/test-rule', {
      method: 'POST',
      body: JSON.stringify(request)
    });
    return response;
  }

  static async previewCategoryMatches(categoryId: string, includeInherited: boolean = true): Promise<CategoryPreviewResponse> {
    const response = await authenticatedRequest(`/api/categories/${categoryId}/preview-matches?includeInherited=${includeInherited}`);
    return response;
  }

  static async validateRegexPattern(pattern: string): Promise<RegexValidationResponse> {
    const request: RegexValidationRequest = { pattern };
    const response = await authenticatedRequest('/api/categories/validate-regex', {
      method: 'POST',
      body: JSON.stringify(request)
    });
    return response;
  }

  static async generatePattern(descriptions: string[], patternType: 'simple' | 'regex' = 'simple'): Promise<PatternGenerationResponse> {
    const request: PatternGenerationRequest = { descriptions, patternType };
    const response = await authenticatedRequest('/api/categories/generate-pattern', {
      method: 'POST',
      body: JSON.stringify(request)
    });
    return response;
  }

  // ===== Pattern Extraction & Smart Category Creation (Phase 4.2) =====
  
  static async suggestFromTransaction(transactionData: {
    description: string;
    amount?: string;
    payee?: string;
    memo?: string;
  }): Promise<{
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
  }> {
    const response = await authenticatedRequest('/api/categories/suggest-from-transaction', {
      method: 'POST',
      body: JSON.stringify(transactionData)
    });
    return response;
  }

  static async extractPatterns(descriptions: string[]): Promise<{
    patterns: Array<{
      pattern: string;
      confidence: number;
      matchCount: number;
      field: string;
      condition: string;
      explanation: string;
    }>;
    totalDescriptions: number;
    totalPatterns: number;
  }> {
    const response = await authenticatedRequest('/api/categories/extract-patterns', {
      method: 'POST',
      body: JSON.stringify({ descriptions })
    });
    return response;
  }

  static async createWithRule(
    categoryName: string,
    categoryType: 'INCOME' | 'EXPENSE',
    pattern: string,
    fieldToMatch: string,
    condition: string
  ): Promise<{
    message: string;
    category: Category;
    rule: CategoryRule;
  }> {
    const response = await authenticatedRequest('/api/categories/create-with-rule', {
      method: 'POST',
      body: JSON.stringify({
        categoryName,
        categoryType,
        pattern,
        fieldToMatch,
        condition
      })
    });
    
    // No need to manually apply rules - the backend automatically applies rules to uncategorized transactions
    return response;
  }

  // ===== Smart Category Suggestions (Phase 4.2) =====
  
  // Simple fallback for API failures - backend now handles intelligent name derivation
  private static getSimpleFallbackName(description: string): string {
    if (!description || description.trim().length === 0) {
      return 'General';
    }
    
    // Extract first meaningful word and capitalize it
    const words = description.trim().split(/\s+/);
    const meaningfulWords = words.filter(word => 
      word.length >= 3 && 
      !/^\d+$/.test(word) && // Skip pure numbers
      !['THE', 'AND', 'OR', 'AT', 'TO', 'FROM', 'FOR', 'WITH'].includes(word.toUpperCase())
    );
    
    if (meaningfulWords.length > 0) {
      const firstWord = meaningfulWords[0];
      return firstWord.charAt(0).toUpperCase() + firstWord.slice(1).toLowerCase();
    }
    
    return 'General';
  }
  
  static async getQuickCategorySuggestions(transactionDescription: string): Promise<{
    suggestedCategory: {
      name: string;
      type: 'INCOME' | 'EXPENSE';
      confidence: number;
      merchantName?: string;
    };
    suggestedPatterns: Array<{
      pattern: string;
      confidence: number;
      explanation: string;
      matchCount: number;
    }>;
  }> {
    try {
      const suggestionResponse = await this.suggestFromTransaction({
        description: transactionDescription
      });
      
      return {
        suggestedCategory: {
          name: suggestionResponse.categoryName,
          type: suggestionResponse.categoryType,
          confidence: suggestionResponse.confidence,
          merchantName: suggestionResponse.suggestedPatterns.find(p => p.explanation.includes('merchant'))?.pattern
        },
        suggestedPatterns: suggestionResponse.suggestedPatterns.map(p => ({
          pattern: p.pattern,
          confidence: p.confidence,
          explanation: p.explanation,
          matchCount: 0 // Will be populated by additional API call if needed
        }))
      };
    } catch (error) {
      console.error('Error getting quick category suggestions:', error);
      // Use simple fallback for API failures
      const fallbackName = this.getSimpleFallbackName(transactionDescription);
      return {
        suggestedCategory: {
          name: fallbackName,
          type: 'EXPENSE',
          confidence: 50
        },
        suggestedPatterns: []
      };
    }
  }

  static async previewPatternMatches(pattern: string, field: string, condition: string): Promise<{
    matchCount: number;
    sampleMatches: Array<{
      transactionId: string;
      description: string;
      amount: string;
      date: string;
      matchedText: string;
    }>;
  }> {
    try {
      // Create a temporary rule to test the pattern
      const testRule: CategoryRule = {
        ruleId: 'temp',
        fieldToMatch: field,
        condition: condition as MatchCondition,
        value: pattern,
        caseSensitive: false,
        priority: 0,
        enabled: true,
        confidence: 100,
        allowMultipleMatches: true,
        autoSuggest: true
      };

      const testResponse = await this.testRule(testRule, 10);
      
      return {
        matchCount: testResponse.totalMatches || 0,
        sampleMatches: testResponse.matchingTransactions?.slice(0, 5).map(t => ({
          transactionId: t.transactionId,
          description: t.description,
          amount: t.amount,
          date: t.date,
          matchedText: pattern // Simplified - in real implementation would highlight exact match
        })) || []
      };
    } catch (error) {
      console.error('Error previewing pattern matches:', error);
      return {
        matchCount: 0,
        sampleMatches: []
      };
    }
  }

  // ===== Category Rule Management =====
  
  static async addRuleToCategory(categoryId: string, rule: Omit<CategoryRule, 'ruleId'>): Promise<Category> {
    const response = await authenticatedRequest(`/api/categories/${categoryId}/rules`, {
      method: 'POST',
      body: JSON.stringify(rule)
    });
    
    // No need to manually apply rules - if the backend supports auto-application, it will handle it
    return response;
  }

  static async updateCategoryRule(categoryId: string, ruleId: string, rule: Partial<CategoryRule>): Promise<Category> {
    const response = await authenticatedRequest(`/api/categories/${categoryId}/rules/${ruleId}`, {
      method: 'PUT',
      body: JSON.stringify(rule)
    });
    return response;
  }

  static async deleteCategoryRule(categoryId: string, ruleId: string): Promise<Category> {
    const response = await authenticatedRequest(`/api/categories/${categoryId}/rules/${ruleId}`, {
      method: 'DELETE'
    });
    return response;
  }

  static async toggleRuleEnabled(categoryId: string, ruleId: string, enabled: boolean): Promise<Category> {
    const response = await authenticatedRequest(`/api/categories/${categoryId}/rules/${ruleId}`, {
      method: 'PUT',
      body: JSON.stringify({ enabled })
    });
    return response;
  }

  // ===== Transaction Category Assignment Management =====
  
  static async addCategoryToTransaction(transactionId: string, categoryId: string, isPrimary: boolean = false): Promise<void> {
    await authenticatedRequest(`/api/transactions/${transactionId}/categories`, {
      method: 'POST',
      body: JSON.stringify({ categoryId, isPrimary })
    });
  }

  static async removeCategoryFromTransaction(transactionId: string, categoryId: string): Promise<void> {
    await authenticatedRequest(`/api/transactions/${transactionId}/categories/${categoryId}`, {
      method: 'DELETE'
    });
  }

  static async setPrimaryCategory(transactionId: string, categoryId: string): Promise<void> {
    await authenticatedRequest(`/api/transactions/${transactionId}/primary-category`, {
      method: 'PUT',
      body: JSON.stringify({ categoryId })
    });
  }

  // ===== Category Suggestion & Confirmation Workflow =====
  
  static async getTransactionCategorySuggestions(transactionId: string): Promise<TransactionCategoryAssignment[]> {
    const response = await authenticatedRequest(`/api/transactions/${transactionId}/category-suggestions`);
    return response;
  }

  static async confirmCategorySuggestions(
    transactionId: string, 
    confirmedCategoryIds: string[], 
    primaryCategoryId: string
  ): Promise<void> {
    const request: CategoryConfirmationRequest = {
      transactionId,
      confirmedCategoryIds,
      primaryCategoryId
    };
    await authenticatedRequest(`/api/transactions/${transactionId}/confirm-suggestions`, {
      method: 'POST',
      body: JSON.stringify(request)
    });
  }

  static async rejectCategorySuggestion(transactionId: string, categoryId: string): Promise<void> {
    await authenticatedRequest(`/api/transactions/${transactionId}/suggestions/${categoryId}`, {
      method: 'DELETE'
    });
  }

  static async generateCategorySuggestions(transactionId: string, strategy: CategorySuggestionStrategy = CategorySuggestionStrategy.ALL_MATCHES): Promise<TransactionCategoryAssignment[]> {
    const response = await authenticatedRequest(`/api/transactions/${transactionId}/category-suggestions`, {
      method: 'POST',
      body: JSON.stringify({ strategy })
    });
    return response;
  }

  // ===== Bulk Operations =====
  
  static async bulkCategorizeTransactions(
    transactionIds: string[], 
    categoryId: string, 
    replaceExisting: boolean = false
  ): Promise<BulkOperationResponse> {
    const request: BulkCategorizeRequest = { transactionIds, categoryId, replaceExisting };
    const response = await authenticatedRequest('/api/transactions/bulk-categorize', {
      method: 'POST',
      body: JSON.stringify(request)
    });
    return response;
  }

  static async applyCategoryRules(
    categoryId: string, 
    createSuggestions: boolean = true,
    strategy: CategorySuggestionStrategy = CategorySuggestionStrategy.ALL_MATCHES
  ): Promise<BulkOperationResponse> {
    const request: BulkRuleApplicationRequest = { 
      categoryId, 
      createSuggestions, 
      strategy 
    };
    const response = await authenticatedRequest('/api/categories/apply-rules-bulk', {
      method: 'POST',
      body: JSON.stringify(request)
    });
    return response;
  }

  static async applyCategoryRulesToAllTransactions(
    categoryId: string,
    createSuggestions: boolean = true
  ): Promise<BulkOperationResponse> {
    console.log(`Applying all rules for category ${categoryId} to existing transactions...`);
    try {
      const result = await this.applyCategoryRules(categoryId, createSuggestions, CategorySuggestionStrategy.ALL_MATCHES);
      console.log(`Successfully applied category rules to existing transactions:`, result);
      return result;
    } catch (error) {
      console.error(`Failed to apply category rules to existing transactions:`, error);
      throw error;
    }
  }

  static async bulkConfirmSuggestions(transactionIds: string[]): Promise<BulkOperationResponse> {
    const response = await authenticatedRequest('/api/transactions/bulk-confirm-suggestions', {
      method: 'POST',
      body: JSON.stringify({ transactionIds })
    });
    return response;
  }

  // ===== Review and Analytics =====
  
  static async getTransactionsNeedingReview(categoryId?: string): Promise<any[]> {
    const endpoint = categoryId 
      ? `/api/categories/${categoryId}/needs-review`
      : '/api/transactions/needs-review';
    const response = await authenticatedRequest(endpoint);
    return response;
  }

  static async getCategoryUsageStats(categoryId?: string): Promise<CategoryUsageStats[]> {
    const endpoint = categoryId 
      ? `/api/categories/${categoryId}/usage-stats`
      : '/api/categories/usage-stats';
    const response = await authenticatedRequest(endpoint);
    return response;
  }

  static async getCategoryEffectivenessReport(categoryId: string): Promise<CategoryEffectivenessReport> {
    const response = await authenticatedRequest(`/api/categories/${categoryId}/effectiveness`);
    return response;
  }

  // ===== Configuration & Import/Export =====
  
  static async exportCategoryConfiguration(): Promise<{ categories: Category[]; rules: CategoryRule[] }> {
    const response = await authenticatedRequest('/api/categories/export');
    return response;
  }

  static async importCategoryConfiguration(
    configuration: { categories: Category[]; rules: CategoryRule[] }
  ): Promise<{ imported: number; errors: string[] }> {
    const response = await authenticatedRequest('/api/categories/import', {
      method: 'POST',
      body: JSON.stringify(configuration)
    });
    return response;
  }

  // ===== Utility Methods =====
  
  static async searchCategories(query: string, type?: 'INCOME' | 'EXPENSE'): Promise<Category[]> {
    const params = new URLSearchParams({ q: query });
    if (type) params.append('type', type);
    
    const response = await authenticatedRequest(`/api/categories/search?${params.toString()}`);
    return response;
  }

  static createDefaultRule(
    fieldToMatch: string, 
    condition: MatchCondition, 
    value: string
  ): Omit<CategoryRule, 'ruleId'> {
    return {
      fieldToMatch,
      condition,
      value,
      caseSensitive: false,
      priority: 0,
      enabled: true,
      confidence: 1.0,
      allowMultipleMatches: true,
      autoSuggest: true
    };
  }

  static validateRule(rule: Partial<CategoryRule>): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!rule.fieldToMatch) errors.push('Field to match is required');
    if (!rule.condition) errors.push('Condition is required');
    if (!rule.value) errors.push('Value is required');
    if (rule.confidence !== undefined && (rule.confidence < 0 || rule.confidence > 1)) {
      errors.push('Confidence must be between 0 and 1');
    }
    if (rule.priority !== undefined && rule.priority < 0) {
      errors.push('Priority must be non-negative');
    }

    // Amount-based rule validations
    if (rule.condition === MatchCondition.AMOUNT_BETWEEN) {
      if (!rule.amountMin || !rule.amountMax) {
        errors.push('Amount range is required for amount_between condition');
      } else if (rule.amountMin >= rule.amountMax) {
        errors.push('Amount minimum must be less than maximum');
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  // ===== Real-time Testing Utilities =====
  
  static debounce<T extends (...args: any[]) => any>(
    func: T,
    delay: number
  ): (...args: Parameters<T>) => void {
    let timeoutId: number;
    return (...args: Parameters<T>) => {
      clearTimeout(timeoutId);
      timeoutId = window.setTimeout(() => func(...args), delay);
    };
  }

  static createDebouncedRuleTest(delay: number = 500) {
    return this.debounce(async (rule: CategoryRule, callback: (results: RuleTestResponse) => void) => {
      try {
        const results = await this.testRule(rule);
        callback(results);
      } catch (error) {
        console.error('Error testing rule:', error);
        callback({
          matchingTransactions: [],
          totalMatches: 0,
          rule: rule,
          limit: 100,
          averageConfidence: 0
        });
      }
    }, delay);
  }

  // ===== Error Handling Utilities =====
  
  static handleApiError(error: any): CategoryApiResponse {
    console.error('CategoryService API Error:', error);
    
    return {
      success: false,
      error: {
        code: error.code || 'UNKNOWN_ERROR',
        message: error.message || 'An unexpected error occurred',
        details: error
      }
    };
  }

  static isValidCategoryId(categoryId: string): boolean {
    return /^[a-zA-Z0-9_-]+$/.test(categoryId) && categoryId.length > 0;
  }

  static isValidRuleId(ruleId: string): boolean {
    return /^rule_[a-zA-Z0-9]{8}$/.test(ruleId);
  }

  // ===== Category Reset and Reapply =====
  
  static async resetAndReapplyCategories(): Promise<{
    message: string;
    results: {
      totalTransactionsProcessed: number;
      transactionsClearedFromCategories: number;
      totalCategoriesProcessed: number;
      totalApplicationsApplied: number;
      categoryResults: Array<{
        categoryId: string;
        categoryName: string;
        appliedCount: number;
        processed: number;
        errors: number;
      }>;
    };
  }> {
    const response = await authenticatedRequest('/api/categories/reset-and-reapply', {
      method: 'POST',
      body: JSON.stringify({ confirmReset: true })
    });
    return response;
  }
}

// Export default for backward compatibility
export default CategoryService; 
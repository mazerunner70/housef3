// Category Management TypeScript Interfaces
// Phase 2.1 Enhanced Models

import { Decimal } from 'decimal.js';

export enum CategoryType {
  INCOME = 'INCOME',
  EXPENSE = 'EXPENSE'
}

export enum MatchCondition {
  CONTAINS = 'contains',
  STARTS_WITH = 'starts_with',
  ENDS_WITH = 'ends_with',
  EQUALS = 'equals',
  REGEX = 'regex',
  AMOUNT_GREATER = 'amount_greater',
  AMOUNT_LESS = 'amount_less',
  AMOUNT_BETWEEN = 'amount_between'
}

export enum CategorySuggestionStrategy {
  ALL_MATCHES = 'all_matches',
  TOP_N_MATCHES = 'top_n_matches',
  CONFIDENCE_THRESHOLD = 'confidence_threshold',
  PRIORITY_FILTERED = 'priority_filtered'
}

export enum CategoryAssignmentStatus {
  SUGGESTED = 'suggested',
  CONFIRMED = 'confirmed',
  REJECTED = 'rejected'
}

// Enhanced Category Rule Model (Phase 2.1)
export interface CategoryRule {
  ruleId: string;
  fieldToMatch: string; // description, payee, memo, amount
  condition: MatchCondition;
  value: string; // The pattern/value to match
  caseSensitive: boolean;
  priority: number; // Higher priority rules checked first
  enabled: boolean;
  confidence: number; // 0.0-1.0 confidence score
  
  // For amount-based rules
  amountMin?: Decimal;
  amountMax?: Decimal;
  
  // Suggestion behavior
  allowMultipleMatches: boolean;
  autoSuggest: boolean; // If false, rule won't create automatic suggestions
}

// Enhanced Category Model (Phase 2.1)
export interface Category {
  userId: string;
  name: string;
  type: CategoryType;
  categoryId: string;
  parentCategoryId?: string;
  icon?: string;
  color?: string;
  rules: CategoryRule[];
  createdAt: number;
  updatedAt: number;
  
  // Enhanced hierarchical support
  inheritParentRules: boolean;
  ruleInheritanceMode: 'additive' | 'override' | 'disabled';
  
  // Computed properties
  isRootCategory?: boolean;
}

// Category Creation/Update Models
export interface CategoryCreate {
  name: string;
  type: CategoryType;
  parentCategoryId?: string;
  icon?: string;
  color?: string;
  inheritParentRules?: boolean;
  ruleInheritanceMode?: 'additive' | 'override' | 'disabled';
}

export interface CategoryUpdate {
  name?: string;
  icon?: string;
  color?: string;
  inheritParentRules?: boolean;
  ruleInheritanceMode?: 'additive' | 'override' | 'disabled';
}

// Transaction Category Assignment Model (Phase 1)
export interface TransactionCategoryAssignment {
  categoryId: string;
  confidence: number; // 0.0 to 1.0 confidence score
  status: CategoryAssignmentStatus; // "suggested" or "confirmed"
  isManual: boolean; // Manually assigned vs auto-assigned
  assignedAt: number;
  confirmedAt?: number; // When user confirmed this assignment
  ruleId?: string; // Which rule triggered this assignment
}

// Category Hierarchy Model (Phase 2.1)
export interface CategoryHierarchy {
  category: Category;
  children: CategoryHierarchy[];
  depth: number;
  fullPath: string;
  inheritedRules: CategoryRule[];
}

// Rule Testing & Preview Models
export interface RuleTestRequest {
  rule: CategoryRule;
  limit?: number;
}

export interface RuleTestResponse {
  transactions: any[]; // Will reference Transaction type from main types
  matchCount: number;
  confidence: number;
}

export interface CategoryPreviewResponse {
  transactions: any[];
  effectiveRules: CategoryRule[];
  matchCount: number;
}

export interface PatternGenerationRequest {
  descriptions: string[];
  patternType?: 'simple' | 'regex';
}

export interface PatternGenerationResponse {
  pattern: string;
  regex: string;
  confidence: number;
}

// Rule Validation Models
export interface RegexValidationRequest {
  pattern: string;
}

export interface RegexValidationResponse {
  isValid: boolean;
  error?: string;
  suggestions?: string[];
}

// Suggestion Management Models
export interface CategorySuggestionRequest {
  transactionId: string;
  strategy?: CategorySuggestionStrategy;
}

export interface CategoryConfirmationRequest {
  transactionId: string;
  confirmedCategoryIds: string[];
  primaryCategoryId: string;
}

// Bulk Operations Models
export interface BulkCategorizeRequest {
  transactionIds: string[];
  categoryId: string;
  replaceExisting?: boolean;
}

export interface BulkRuleApplicationRequest {
  categoryId: string;
  createSuggestions?: boolean;
  strategy?: CategorySuggestionStrategy;
}

export interface BulkOperationResponse {
  applied: number;
  errors?: string[];
}

// Analytics Models for Categories
export interface CategoryUsageStats {
  categoryId: string;
  name: string;
  ruleCount: number;
  assignmentCount: number;
  suggestionCount: number;
  confirmationRate: number; // % of suggestions that were confirmed
  averageConfidence: number;
  lastUsed?: number;
}

export interface CategoryEffectivenessReport {
  categoryId: string;
  name: string;
  rules: Array<{
    ruleId: string;
    matchCount: number;
    confirmationRate: number;
    averageConfidence: number;
    effectivenessScore: number;
  }>;
  overallEffectiveness: number;
  recommendations: string[];
}

// Error Types
export interface CategoryError {
  code: string;
  message: string;
  field?: string;
  details?: any;
}

// API Response Types
export interface CategoryApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: CategoryError;
  message?: string;
}

// Utility Types for Form State Management
export interface CategoryFormState {
  category: Partial<Category>;
  isEditing: boolean;
  isDirty: boolean;
  isValid: boolean;
  errors: Record<string, string>;
}

export interface RuleFormState {
  rule: Partial<CategoryRule>;
  isEditing: boolean;
  isDirty: boolean;
  isValid: boolean;
  errors: Record<string, string>;
  testResults?: RuleTestResponse;
  isTestingRule: boolean;
}

// Hook State Types
export interface CategoryManagementState {
  categories: Category[];
  hierarchy: CategoryHierarchy[];
  selectedCategory: Category | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: number | null;
}

export interface RuleTestingState {
  currentRule: CategoryRule | null;
  testResults: RuleTestResponse | null;
  isTestingRule: boolean;
  isLivePreview: boolean;
  debounceTimer: number | null;
}

export interface SuggestionReviewState {
  pendingSuggestions: Map<string, TransactionCategoryAssignment[]>; // transactionId -> suggestions
  isReviewModalOpen: boolean;
  currentTransactionId: string | null;
  reviewStrategy: CategorySuggestionStrategy;
} 
import { useState, useEffect } from 'react';
import { CategoryService } from '../services/CategoryService';
import { Category } from '../types/Category';

export interface PatternSuggestionItem {
  pattern: string;
  confidence: number;
  matchCount: number;
  field: string;
  condition: string;
  explanation: string;
  sampleMatches: Array<{
    transactionId: string;
    description: string;
    amount: string;
    date: string;
    matchedText: string;
  }>;
}

export interface CategorySuggestion {
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
}

export interface PatternSuggestionState {
  suggestedPatterns: PatternSuggestionItem[];
  categorySuggestion: CategorySuggestion | null;
  existingCategories: Category[];
  isLoading: boolean;
  error: string | null;
}

export const usePatternSuggestions = (transactionDescription: string, isOpen: boolean) => {
  const [state, setState] = useState<PatternSuggestionState>({
    suggestedPatterns: [],
    categorySuggestion: null,
    existingCategories: [],
    isLoading: false,
    error: null
  });

  const loadSuggestions = async () => {
    if (!transactionDescription) return;

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // Load both suggestions and categories in parallel
      const [categoryResponse, categoriesResponse] = await Promise.all([
        CategoryService.suggestFromTransaction({ description: transactionDescription }),
        CategoryService.getCategories()
      ]);

      const sortedCategories = categoriesResponse.sort((a: Category, b: Category) =>
        a.name.localeCompare(b.name)
      );

      // Enhance patterns with match counts
      const patterns = categoryResponse?.suggestedPatterns || [];
      const enhancedPatterns = await Promise.all(
        patterns.map(async (pattern) => {
          try {
            const matchPreview = await CategoryService.previewPatternMatches(
              pattern.pattern,
              pattern.field,
              pattern.condition
            );
            return { ...pattern, matchCount: matchPreview.matchCount, sampleMatches: matchPreview.sampleMatches };
          } catch (error) {
            console.error('Error previewing pattern matches:', error);
            return { ...pattern, matchCount: 0, sampleMatches: [] };
          }
        })
      );

      // Sort by confidence (highest first)
      const sortedPatterns = enhancedPatterns.sort((a, b) => b.confidence - a.confidence);

      setState(prev => ({
        ...prev,
        suggestedPatterns: sortedPatterns,
        categorySuggestion: categoryResponse,
        existingCategories: sortedCategories,
        isLoading: false
      }));

    } catch (error) {
      console.error('Error loading pattern suggestions:', error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }));
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadSuggestions();
    }
  }, [isOpen, transactionDescription]);

  return { ...state, reload: loadSuggestions };
}; 
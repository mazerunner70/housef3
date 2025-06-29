import React, { useState, useCallback } from 'react';
import { Category, CategoryHierarchy } from '../../types/Category';
import './CategoryHierarchyTree.css';

interface CategoryHierarchyTreeProps {
  hierarchy: CategoryHierarchy[];
  selectedCategory: Category | null;
  onSelectCategory: (category: Category) => void;
  showSuggestions: boolean;
  onCreateCategory?: (parentId?: string) => void;
  onMoveCategory?: (categoryId: string, newParentId: string | null) => void;
  isLoading?: boolean;
}

const CategoryHierarchyTree: React.FC<CategoryHierarchyTreeProps> = ({
  hierarchy,
  selectedCategory,
  onSelectCategory,
  showSuggestions,
  onCreateCategory,
  onMoveCategory,
  isLoading = false
}) => {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [draggedCategory, setDraggedCategory] = useState<string | null>(null);

  const toggleNodeExpansion = useCallback((categoryId: string) => {
    setExpandedNodes(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(categoryId)) {
        newExpanded.delete(categoryId);
      } else {
        newExpanded.add(categoryId);
      }
      return newExpanded;
    });
  }, []);

  const handleDragStart = useCallback((e: React.DragEvent, categoryId: string) => {
    setDraggedCategory(categoryId);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', categoryId);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, targetCategoryId: string | null) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (draggedCategory && draggedCategory !== targetCategoryId && onMoveCategory) {
      onMoveCategory(draggedCategory, targetCategoryId);
    }
    
    setDraggedCategory(null);
  }, [draggedCategory, onMoveCategory]);

  const handleDragEnd = useCallback(() => {
    setDraggedCategory(null);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent, category: Category) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelectCategory(category);
    }
  }, [onSelectCategory]);

  const renderCategoryNode = (node: CategoryHierarchy, depth: number = 0): React.ReactNode => {
    const { category } = node;
    const isExpanded = expandedNodes.has(category.categoryId);
    const hasChildren = node.children.length > 0;
    const isSelected = selectedCategory?.categoryId === category.categoryId;
    const isDragging = draggedCategory === category.categoryId;

    const totalRules = category.rules.length + node.inheritedRules.length;
    const ownRulesCount = category.rules.length;
    const inheritedRulesCount = node.inheritedRules.length;

    // Mock suggestion count - in real implementation this would come from the backend
    // Deterministic count based on category name length to avoid security-sensitive random number usage
    const suggestionCount: number = (category.name.length % 3); // TODO: Get from backend API

    return (
      <div
        key={category.categoryId}
        className={`category-tree-node ${isDragging ? 'dragging' : ''}`}
      >
        <div
          className={`category-node-content depth-${depth} ${isSelected ? 'selected' : ''}`}
          onClick={() => onSelectCategory(category)}
          onKeyDown={(e) => handleKeyDown(e, category)}
          tabIndex={0}
          role="button"
          aria-label={`Select category ${category.name}`}
          draggable={!!onMoveCategory}
          onDragStart={(e) => handleDragStart(e, category.categoryId)}
          onDragOver={handleDragOver}
          onDrop={(e) => handleDrop(e, category.categoryId)}
          onDragEnd={handleDragEnd}
        >
          <div className="category-node-header">
            {/* Expansion Toggle */}
            {hasChildren && (
              <button
                className={`expand-toggle ${isExpanded ? 'expanded' : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleNodeExpansion(category.categoryId);
                }}
                aria-label={isExpanded ? 'Collapse' : 'Expand'}
              >
                <span className="expand-icon">▶</span>
              </button>
            )}
            
            {/* Category Icon */}
            <span className="category-icon">
              {category.icon || (category.type === 'INCOME' ? '💰' : '💸')}
            </span>
            
            {/* Category Name */}
            <span className="category-name">
              {category.name}
            </span>

            {/* Category Type Badge */}
            <span className={`category-type-badge ${category.type.toLowerCase()}`}>
              {category.type}
            </span>
            
            {/* Rule Count */}
            <div className="category-stats">
              <span 
                className="rule-count"
                title={`${ownRulesCount} own rules${inheritedRulesCount > 0 ? ` + ${inheritedRulesCount} inherited` : ''}`}
              >
                {totalRules} rule{totalRules !== 1 ? 's' : ''}
              </span>

              {inheritedRulesCount > 0 && (
                <span className="inherited-indicator" title="Has inherited rules">
                  ⬇️
                </span>
              )}
            </div>
            
            {/* Suggestion Indicator */}
            {showSuggestions && suggestionCount > 0 && (
              <span 
                className="suggestion-indicator" 
                title={`${suggestionCount} unconfirmed suggestion${suggestionCount !== 1 ? 's' : ''}`}
              >
                📋 {suggestionCount}
              </span>
            )}

            {/* Actions */}
            <div className="category-actions">
              {onCreateCategory && (
                <button
                  className="add-subcategory-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCreateCategory(category.categoryId);
                  }}
                  title="Add subcategory"
                >
                  +
                </button>
              )}
            </div>
          </div>
          
          {/* Category Path */}
          <div className="category-path">
            {node.fullPath}
          </div>

          {/* Depth indicator line */}
          {depth > 0 && (
            <div 
              className="depth-indicator" 
              style={{ left: `${(depth - 1) * 20}px` }}
            />
          )}
        </div>
        
        {/* Children */}
        {hasChildren && isExpanded && (
          <div className="category-children">
            {node.children.map(child => renderCategoryNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const handleCreateRootCategory = () => {
    if (onCreateCategory) {
      onCreateCategory();
    }
  };

  // Handle drop on empty space (move to root level)
  const handleDropOnEmptySpace = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (draggedCategory && onMoveCategory) {
      onMoveCategory(draggedCategory, null);
    }
    setDraggedCategory(null);
  }, [draggedCategory, onMoveCategory]);

  if (isLoading) {
    return (
      <div className="category-hierarchy-tree loading">
        <div className="tree-header">
          <h3>Categories</h3>
        </div>
        <div className="loading-placeholder">
          <div className="loading-spinner">🔄</div>
          <p>Loading categories...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="category-hierarchy-tree">
      <div className="tree-header">
        <h3>Categories</h3>
        {onCreateCategory && (
          <button 
            className="add-category-btn primary"
            onClick={handleCreateRootCategory}
          >
            + Add Category
          </button>
        )}
      </div>
      
      <div 
        className="tree-content"
        onDragOver={handleDragOver}
        onDrop={handleDropOnEmptySpace}
      >
        {hierarchy.length > 0 ? (
          hierarchy.map(node => renderCategoryNode(node))
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">📁</div>
            <h4>No Categories Yet</h4>
            <p>Create your first category to start organizing transactions.</p>
            {onCreateCategory && (
              <button 
                className="add-category-btn secondary"
                onClick={handleCreateRootCategory}
              >
                Create First Category
              </button>
            )}
          </div>
        )}
      </div>

      {/* Drop zone indicator */}
      {draggedCategory && (
        <div className="drop-zone-indicator">
          Drop here to move to root level
        </div>
      )}
    </div>
  );
};

export default CategoryHierarchyTree; 
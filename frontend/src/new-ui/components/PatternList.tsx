import React, { useState } from 'react';
import { PatternSuggestionItem } from '../hooks/usePatternSuggestions';
import PatternItem from './PatternItem';

interface PatternListProps {
  patterns: PatternSuggestionItem[];
  selectedPattern: PatternSuggestionItem | null;
  onPatternSelect: (pattern: PatternSuggestionItem) => void;
}

const PatternList: React.FC<PatternListProps> = ({
  patterns,
  selectedPattern,
  onPatternSelect
}) => {
  const [expandedMatches, setExpandedMatches] = useState<Set<number>>(new Set());

  const toggleMatchesExpanded = (patternIndex: number) => {
    setExpandedMatches(prev => {
      const newSet = new Set(prev);
      if (newSet.has(patternIndex)) {
        newSet.delete(patternIndex);
      } else {
        newSet.add(patternIndex);
      }
      return newSet;
    });
  }; 

  if (patterns.length === 0) {
    return (
      <div className="pattern-suggestions-section">
        <h4>Suggested Patterns</h4>
        <p className="section-description">
          Select a pattern that will automatically categorize similar transactions.
        </p>
        <div className="no-patterns">
          <p>No patterns could be generated for this transaction.</p>
          <p>You can still create a category manually.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pattern-suggestions-section">
      <h4>Suggested Patterns</h4>
      <p className="section-description">
        Select a pattern that will automatically categorize similar transactions.
      </p>
      <div className="pattern-list">
        {patterns.map((pattern, index) => (
          <PatternItem
            key={`${pattern.pattern}-${pattern.field}-${pattern.condition}`}
            pattern={pattern}
            index={index}
            isSelected={selectedPattern === pattern}
            isExpanded={expandedMatches.has(index)}
            onSelect={() => onPatternSelect(pattern)}
            onToggleExpanded={() => toggleMatchesExpanded(index)}
          />
        ))}
      </div>
    </div>
  );
};

export default PatternList; 
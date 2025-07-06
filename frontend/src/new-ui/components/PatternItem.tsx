import React from 'react';
import { PatternSuggestionItem } from '../hooks/usePatternSuggestions';

interface PatternItemProps {
  pattern: PatternSuggestionItem;
  index: number;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpanded: () => void;
}

const PatternItem: React.FC<PatternItemProps> = ({
  pattern,
  index,
  isSelected,
  isExpanded,
  onSelect,
  onToggleExpanded
}) => {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'high-confidence';
    if (confidence >= 60) return 'medium-confidence';
    return 'low-confidence';
  };

  const getMatchCountColor = (matchCount: number) => {
    if (matchCount >= 10) return 'high-matches';
    if (matchCount >= 5) return 'medium-matches';
    if (matchCount >= 1) return 'low-matches';
    return 'no-matches';
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return dateString;
    }
  };

  return (
    <div className={`pattern-item ${isSelected ? 'selected' : ''}`}>
      <div className="pattern-header">
        <div className="pattern-radio">
          <input
            type="radio"
            name="selectedPattern"
            checked={isSelected}
            onChange={onSelect}
          />
        </div>
        <div className="pattern-info" onClick={onSelect}>
          <div className="pattern-text">
            <strong>Pattern:</strong> "{pattern.pattern}"
          </div>
          <div className="pattern-rule">
            <strong>Rule:</strong> {pattern.field} {pattern.condition} "{pattern.pattern}"
          </div>
          <div className="pattern-explanation">
            {pattern.explanation}
          </div>
        </div>
        <div className="pattern-stats">
          <div className={`confidence-badge ${getConfidenceColor(pattern.confidence)}`}>
            {pattern.confidence}%
          </div>
          <button 
            className={`match-count-button ${getMatchCountColor(pattern.matchCount)}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpanded();
            }}
            disabled={pattern.matchCount === 0}
            title={pattern.matchCount > 0 ? "Click to see matching transactions" : "No matching transactions"}
          >
            {pattern.matchCount} match{pattern.matchCount !== 1 ? 'es' : ''}
            {pattern.matchCount > 0 && (
              <span className="expand-icon">
                {isExpanded ? '▼' : '▶'}
              </span>
            )}
          </button>
        </div>
      </div>
      
      {pattern.sampleMatches && pattern.sampleMatches.length > 0 && isExpanded && (
        <div className="sample-matches">
          <h5>Matching Transactions:</h5>
          <div className="sample-transactions">
            {pattern.sampleMatches.map((match, sampleIndex) => (
              <div key={sampleIndex} className="sample-transaction expanded">
                <div className="transaction-main">
                  <div className="sample-description">
                    {match.description}
                  </div>
                  <div className="sample-amount">
                    {match.amount}
                  </div>
                </div>
                <div className="transaction-meta">
                  <div className="sample-date">
                    {formatDate(match.date)}
                  </div>
                  {match.matchedText && (
                    <div className="matched-text">
                      Matched: "{match.matchedText}"
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PatternItem; 
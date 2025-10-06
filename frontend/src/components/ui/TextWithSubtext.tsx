import React from 'react';

interface TextWithSubtextProps {
  primaryText: string;
  secondaryText?: string;
  className?: string;
  showSecondary?: boolean;
  variant?: 'default' | 'description' | 'title';
  subtextPrefix?: string; // e.g., "(" for payee, "by " for author
  subtextSuffix?: string; // e.g., ")" for payee
}

const TextWithSubtext: React.FC<TextWithSubtextProps> = ({ 
  primaryText, 
  secondaryText,
  className = '',
  showSecondary = true,
  variant = 'default',
  subtextPrefix = '(',
  subtextSuffix = ')'
}) => {
  const variantClass = `text-with-subtext-${variant}`;

  return (
    <div className={`text-with-subtext ${variantClass} ${className}`}>
      <span className="primary-text">{primaryText}</span>
      {showSecondary && secondaryText && (
        <span className="secondary-text">
          {' '}{subtextPrefix}{secondaryText}{subtextSuffix}
        </span>
      )}
    </div>
  );
};

export default TextWithSubtext; 
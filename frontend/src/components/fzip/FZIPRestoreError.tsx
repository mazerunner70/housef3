import React from 'react';
import './FZIPRestoreError.css';

interface Props {
  error: string;
  onRetry: () => void;
  onAbort: () => void;
  isRetrying?: boolean;
}

export const FZIPRestoreError: React.FC<Props> = ({ 
  error, 
  onRetry, 
  onAbort, 
  isRetrying = false 
}) => {
  return (
    <div className="fzip-restore-error">
      <div className="error-header">
        <h3>❌ Restore Failed</h3>
        <p>The restore process encountered an error and could not complete:</p>
      </div>

      <div className="error-message">
        <div className="error-label">Error Details:</div>
        <code className="error-code">{error}</code>
      </div>

      <div className="error-help">
        <h4>💡 What you can do:</h4>
        <ul>
          <li><strong>Retry:</strong> Sometimes temporary issues resolve on retry</li>
          <li><strong>Check your FZIP file:</strong> Ensure it's not corrupted and was created properly</li>
          <li><strong>Contact support:</strong> If the problem persists, include the error details above</li>
        </ul>
      </div>

      <div className="error-actions">
        <button 
          className="btn-secondary" 
          onClick={onAbort}
          disabled={isRetrying}
        >
          Abort Restore
        </button>
        <button 
          className="btn-primary" 
          onClick={onRetry}
          disabled={isRetrying}
        >
          {isRetrying ? (
            <>
              <span className="retry-spinner">⟳</span>
              Retrying...
            </>
          ) : (
            'Retry Restore'
          )}
        </button>
      </div>
    </div>
  );
};

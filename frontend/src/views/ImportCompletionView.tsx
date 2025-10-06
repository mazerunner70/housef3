import React from 'react';
import './ImportCompletionView.css';

interface ImportCompletionProps {
  success: boolean;
  message?: string; // General message from FileProcessorResponse
  transactionCount?: number;
  fileName?: string;
  accountName?: string;
  errorDetails?: string; // For more detailed errors
  onViewTransactions: () => void;
  onImportAnother: () => void;
  onGoToStatements: () => void;
}

const ImportCompletionView: React.FC<ImportCompletionProps> = ({
  success,
  message,
  transactionCount,
  fileName,
  accountName,
  errorDetails,
  onViewTransactions,
  onImportAnother,
  onGoToStatements,
}) => {
  return (
    <div className="import-completion-view">
      <div className="import-completion-card">
        {success ? (
          <>
            <div className="icon success-icon">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2>Import Successful!</h2>
            {transactionCount !== undefined && fileName && accountName && (
              <p>
                <strong>{transactionCount}</strong> transaction{transactionCount === 1 ? '' : 's'} from <strong>'{fileName}'</strong>{' '}
                {accountName !== 'Unassigned' && accountName !== '' ? <>have been added to <strong>'{accountName}'</strong>.</> : <>have been imported.</>}
              </p>
            )}
            {message && <p className="additional-message">{message}</p>}
          </>
        ) : (
          <>
            <div className="icon error-icon">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" >
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
            </div>
            <h2>Import Failed</h2>
            <p>{message || 'An error occurred during the import process.'}</p>
            {errorDetails && <p className="error-details">Details: {errorDetails}</p>}
          </>
        )}

        <div className="actions">
          {success && (
            <button onClick={onViewTransactions} className="action-button primary">
              View Imported Transactions
            </button>
          )}
          <button onClick={onImportAnother} className="action-button secondary">
            Import Another File
          </button>
          <button onClick={onGoToStatements} className="action-button secondary">
            Go to Statements
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImportCompletionView; 
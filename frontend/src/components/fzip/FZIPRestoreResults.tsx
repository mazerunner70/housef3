import React from 'react';
import { FZIPRestoreResults as ResultsData } from '../../../services/FZIPService';
import './FZIPRestoreResults.css';

interface Props {
  results: ResultsData;
  onClose: () => void;
}

export const FZIPRestoreResults: React.FC<Props> = ({ results, onClose }) => {
  return (
    <div className="fzip-restore-results">
      <div className="results-header">
        <h3>✅ Restore Completed Successfully!</h3>
        <p>Your data has been restored. Here's what was created:</p>
      </div>

      <div className="results-grid">
        <div className="result-item">
          <span className="result-count">{results.accounts.created.toLocaleString()}</span>
          <span className="result-label">Accounts</span>
          <span className="result-icon">📊</span>
        </div>
        <div className="result-item">
          <span className="result-count">{results.categories.created.toLocaleString()}</span>
          <span className="result-label">Categories</span>
          <span className="result-icon">🏷️</span>
        </div>
        <div className="result-item">
          <span className="result-count">{results.file_maps.created.toLocaleString()}</span>
          <span className="result-label">File Maps</span>
          <span className="result-icon">🗂️</span>
        </div>
        <div className="result-item">
          <span className="result-count">{results.transaction_files.created.toLocaleString()}</span>
          <span className="result-label">Transaction Files</span>
          <span className="result-icon">📄</span>
        </div>
        <div className="result-item">
          <span className="result-count">{results.transactions.created.toLocaleString()}</span>
          <span className="result-label">Transactions</span>
          <span className="result-icon">💰</span>
        </div>
      </div>

      {results.total_processing_time && (
        <div className="processing-time">
          <p>
            <span className="time-icon">⏱️</span>
            Processing completed in <strong>{results.total_processing_time}</strong>
          </p>
        </div>
      )}

      {results.warnings && results.warnings.length > 0 && (
        <div className="warnings-section">
          <h4>⚠️ Warnings</h4>
          <p className="warnings-description">
            The following non-critical issues were encountered during the restore:
          </p>
          <ul className="warnings-list">
            {results.warnings.map((warning, index) => (
              <li key={index} className="warning-item">
                {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="success-message">
        <p>
          🎉 Your FZIP restore is complete! You can now navigate to the appropriate sections 
          to view your restored data.
        </p>
      </div>

      <div className="results-actions">
        <button className="btn-primary" onClick={onClose}>
          Continue to Application
        </button>
      </div>
    </div>
  );
};

import React from 'react';
import { FZIPRestoreSummary as SummaryData } from '../../../services/FZIPService';
import './FZIPRestoreSummary.css';

interface Props {
  summary: SummaryData;
  onConfirm: () => void;
  onCancel: () => void;
  isConfirming?: boolean;
}

export const FZIPRestoreSummary: React.FC<Props> = ({ 
  summary, 
  onConfirm, 
  onCancel, 
  isConfirming = false 
}) => {
  return (
    <div className="fzip-restore-summary">
      <div className="summary-header">
        <h3>📋 Restore Preview</h3>
        <p>Review what will be restored from your FZIP file:</p>
      </div>

      <div className="summary-grid">
        <div className="summary-section">
          <div className="section-header">
            <h4>📊 Accounts ({summary.accounts.count})</h4>
          </div>
          <div className="section-content">
            {summary.accounts.items.length > 0 ? (
              <ul className="item-list">
                {summary.accounts.items.slice(0, 5).map((account, index) => (
                  <li key={index}>
                    <span className="item-name">{account.name}</span>
                    <span className="item-type">{account.type}</span>
                  </li>
                ))}
                {summary.accounts.items.length > 5 && (
                  <li className="more-items">
                    +{summary.accounts.items.length - 5} more...
                  </li>
                )}
              </ul>
            ) : (
              <span className="no-items">No accounts found</span>
            )}
          </div>
        </div>

        <div className="summary-section">
          <div className="section-header">
            <h4>🏷️ Categories ({summary.categories.count})</h4>
            <span className="depth-indicator">
              {summary.categories.hierarchyDepth} levels deep
            </span>
          </div>
          <div className="section-content">
            {summary.categories.items.length > 0 ? (
              <ul className="item-list">
                {summary.categories.items.slice(0, 5).map((category, index) => (
                  <li key={index}>
                    <span className="item-name" style={{marginLeft: `${category.level * 12}px`}}>
                      {category.name}
                    </span>
                    {category.children > 0 && (
                      <span className="children-count">
                        {category.children} children
                      </span>
                    )}
                  </li>
                ))}
                {summary.categories.items.length > 5 && (
                  <li className="more-items">
                    +{summary.categories.items.length - 5} more...
                  </li>
                )}
              </ul>
            ) : (
              <span className="no-items">No categories found</span>
            )}
          </div>
        </div>

        <div className="summary-section">
          <div className="section-header">
            <h4>🗂️ File Maps ({summary.file_maps.count})</h4>
            <span className="size-indicator">{summary.file_maps.totalSize}</span>
          </div>
        </div>

        <div className="summary-section">
          <div className="section-header">
            <h4>📄 Transaction Files ({summary.transaction_files.count})</h4>
            <span className="size-indicator">{summary.transaction_files.totalSize}</span>
          </div>
          <div className="section-content">
            {summary.transaction_files.fileTypes.length > 0 && (
              <div className="file-types">
                <span className="label">File types:</span>
                <span className="types">
                  {summary.transaction_files.fileTypes.join(', ')}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="summary-section">
          <div className="section-header">
            <h4>💰 Transactions ({summary.transactions.count.toLocaleString()})</h4>
          </div>
          <div className="section-content">
            {summary.transactions.dateRange && (
              <div className="date-range">
                <span className="range-label">Date range:</span>
                <span className="range-dates">
                  {new Date(summary.transactions.dateRange.earliest).toLocaleDateString()} - {' '}
                  {new Date(summary.transactions.dateRange.latest).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="summary-warning">
        <p>⚠️ <strong>Important:</strong> This restore operation will add data to your account. 
        Existing data will not be modified or deleted.</p>
      </div>

      <div className="summary-actions">
        <button 
          className="btn-secondary" 
          onClick={onCancel}
          disabled={isConfirming}
        >
          Cancel
        </button>
        <button 
          className="btn-primary" 
          onClick={onConfirm}
          disabled={isConfirming}
        >
          {isConfirming ? 'Confirming...' : 'Confirm Restore'}
        </button>
      </div>
    </div>
  );
};

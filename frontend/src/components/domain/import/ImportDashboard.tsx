import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ImportViewLayout from './components/ImportViewLayout';
import ImportHeader from './components/ImportHeader';
import CompactAccountsList from './components/CompactAccountsList';
import useAccountsData from '@/components/domain/accounts/hooks/useAccountsData';
import useImportState from '@/hooks/useImportState';
import './ImportDashboard.css';

/**
 * ImportDashboard - Main dashboard component for transaction import workflow
 * 
 * Stage 1 Implementation Complete:
 * - Enhanced compact list design with rich metadata and import prioritization
 * - Improved state management with comprehensive import workflow tracking
 * - Better error handling with retry mechanisms and user feedback
 * - Enhanced accessibility and responsive design with keyboard navigation
 * - Visual polish with hover states, animations, and loading indicators
 * - Contextual sidebar integration with import-specific navigation
 * - Account statistics and last updated information
 * - Progressive enhancement approach leveraging existing infrastructure
 * 
 * Future Stages:
 * - Stage 2: Account file upload page with dedicated upload interface
 * - Stage 3: Advanced UX features and production polish
 */
const ImportDashboard: React.FC = () => {
  // === 1. STATE MANAGEMENT SECTION ===
  const navigate = useNavigate();
  const accountsData = useAccountsData();
  const importState = useImportState();

  // === 2. EVENT HANDLERS SECTION ===
  const handleImportClick = useCallback((accountId: string) => {
    // Stage 2: Navigate to dedicated account file upload page
    console.log('Navigating to account upload page for account:', accountId);
    navigate(`/import/account/${accountId}`);
  }, [navigate]);

  const handleAccountClick = useCallback((accountId: string) => {
    // Navigate to account detail view
    const account = accountsData.accounts.find(acc => acc.accountId === accountId);
    const accountName = account?.accountName || 'Unknown Account';

    console.log('Account clicked:', accountId, accountName);
    console.log('🏦 This will navigate to account detail page');

    // Navigate to account detail page
    navigate(`/accounts/${accountId}`);
  }, [accountsData.accounts, navigate]);

  const handleUploadClick = useCallback(() => {
    // Stage 1: Enhanced placeholder with context
    console.log('Upload new file clicked');
    console.log('📤 This will open the general file upload dialog in Stage 2');

    if (accountsData.activeAccountCount === 0) {
      alert('No Active Accounts\n\nYou need at least one active account to upload transaction files.\n\nPlease activate an account or create a new one first.');
      return;
    }

    alert(`Upload New File\n\nActive Accounts: ${accountsData.activeAccountCount}\nTotal Accounts: ${accountsData.accountCount}\n\nGeneral file upload functionality coming in Stage 2!`);
  }, [accountsData.activeAccountCount, accountsData.accountCount]);

  const handleHistoryClick = useCallback(() => {
    // Stage 1: Enhanced placeholder with import context
    console.log('View import history clicked');
    console.log('📊 This will navigate to import history page');

    const recentImportsCount = importState.importStatus.recentImports?.length || 0;

    alert(`Import History\n\nRecent Imports: ${recentImportsCount}\nTotal Accounts: ${accountsData.accountCount}\n\nImport history page coming in Stage 2!`);
  }, [importState.importStatus.recentImports, accountsData.accountCount]);

  // === 3. LAYOUT COMPOSITION SECTION ===
  return (
    <ImportViewLayout>
      <ImportHeader
        onUploadClick={handleUploadClick}
        onHistoryClick={handleHistoryClick}
        importStatus={importState.importStatus}
        accountCount={accountsData.accountCount}
        activeAccountCount={accountsData.activeAccountCount}
        lastUpdated={accountsData.lastUpdated}
      />

      <div className="import-main-content">
        {/* Enhanced Error State */}
        {accountsData.error && (
          <div className="import-error-container">
            <div className="error-content">
              <div className="error-icon">⚠️</div>
              <div className="error-details">
                <h4>Unable to Load Accounts</h4>
                <p className="error-message">{accountsData.error}</p>
                <p className="error-suggestion">
                  Please check your internet connection and try again.
                  If the problem persists, contact support.
                </p>
              </div>
            </div>
            <div className="error-actions">
              <button
                onClick={accountsData.refetch}
                className="retry-button primary"
                disabled={accountsData.isLoading}
              >
                {accountsData.isLoading ? (
                  <>
                    <span className="loading-spinner">🔄</span>
                    <span>Retrying...</span>
                  </>
                ) : (
                  <>
                    <span>🔄</span>
                    <span>Try Again</span>
                  </>
                )}
              </button>
              <button
                onClick={() => navigate(0)}
                className="retry-button secondary"
              >
                <span>↻</span>
                <span>Refresh Page</span>
              </button>
            </div>
          </div>
        )}

        {/* Success/Info Messages */}
        {importState.successAlert && (
          <div className="import-success-container">
            <div className="success-content">
              <div className="success-icon">✅</div>
              <div className="success-details">
                <h4>Import Successful!</h4>
                <p className="success-message">{importState.successAlert.message}</p>
                {importState.successAlert.transactionCount && (
                  <p className="success-stats">
                    Imported {importState.successAlert.transactionCount} transactions
                    {importState.successAlert.accountName && ` for ${importState.successAlert.accountName}`}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={importState.clearSuccess}
              className="close-button"
              aria-label="Close success message"
            >
              ×
            </button>
          </div>
        )}

        {/* Main Content: Accounts List */}
        {!accountsData.error && (
          <CompactAccountsList
            accounts={accountsData.accounts}
            onImportClick={handleImportClick}
            onAccountClick={handleAccountClick}
            isLoading={accountsData.isLoading}
          />
        )}
      </div>
    </ImportViewLayout>
  );
};

export default ImportDashboard;
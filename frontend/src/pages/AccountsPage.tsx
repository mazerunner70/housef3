import React from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useSessionRouting } from '@/hooks/useSessionRouting';
import { useNavigationStore } from '@/stores/navigationStore';
import AccountListView from '@/components/navigation/views/AccountListView';
import AccountDetailView from '@/components/navigation/views/AccountDetailView';
import FileTransactionsView from '@/components/navigation/views/FileTransactionsView';
import TransactionDetailView from '@/components/navigation/views/TransactionDetailView';
import useAccountsWithStore from '@/components/domain/accounts/stores/useAccountsStore';
import './AccountsPage.css';

/**
 * AccountsPage - Route-level page component for the accounts feature
 * 
 * This is a thin container that follows the frontend conventions:
 * - Pages are route-level containers referenced by React Router
 * - Pages should primarily compose business components/views
 * - Direct routing based on URL params, no central navigation controller
 * 
 * Updated to use the route-aware contextual sidebar navigation pattern.
 * The sidebar automatically shows account-specific content when on /accounts routes.
 * Route patterns:
 * - /accounts -> AccountListView
 * - /accounts/:accountId -> AccountDetailView
 * - /accounts/:accountId/files/:fileId -> FileTransactionsView
 * - /accounts/:accountId/transactions/:transactionId -> TransactionDetailView
 */
const AccountsPage: React.FC = () => {
    const params = useParams();
    const [searchParams] = useSearchParams();
    const { accounts } = useAccountsWithStore();
    const { selectedAccount, selectedFile, selectedTransaction, urlContext, goToAccountList } = useNavigationStore();

    // Sync React Router with navigation store using session URL compression
    useSessionRouting();

    // Set up correct breadcrumb when on accounts page
    React.useEffect(() => {
        const { accountId } = params;
        const fileId = urlContext.fileId;
        const transactionId = urlContext.transactionId;

        // If we're on the base accounts page (no specific account selected)
        if (!accountId && !fileId && !transactionId) {
            goToAccountList();
        }
    }, [params, urlContext, goToAccountList]);

    // Determine which view to render based on URL params
    const renderContent = () => {
        const { accountId } = params;
        const fileId = searchParams.get('fileId');
        const transactionId = searchParams.get('transactionId');

        // Transaction detail view
        if (transactionId && selectedTransaction) {
            return (
                <TransactionDetailView
                    transaction={selectedTransaction}
                    account={selectedAccount}
                    file={selectedFile}
                />
            );
        }

        // File transactions view
        if (accountId && fileId && selectedAccount && selectedFile) {
            return <FileTransactionsView account={selectedAccount} file={selectedFile} />;
        }

        // Account detail view
        if (accountId) {
            const account = selectedAccount || accounts.find(acc => acc.accountId === accountId);
            if (!account) {
                return <div className="error-state">Account not found</div>;
            }
            return <AccountDetailView account={account} />;
        }

        // Default: Account list view
        return <AccountListView />;
    };

    return (
        <div className="accounts-page">
            <main className="main-content">
                <div className="main-content-inner">
                    {renderContent()}
                </div>
            </main>
        </div>
    );
};

export default AccountsPage;

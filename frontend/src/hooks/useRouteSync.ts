import { useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useNavigationStore } from '@/stores/navigationStore';
import useAccountsWithStore from '@/stores/useAccountsStore';

/**
 * Hook to synchronize React Router with the navigation store
 * 
 * This creates a bidirectional sync:
 * 1. When navigation store changes → update URL
 * 2. When URL changes (direct navigation/back/forward) → update navigation store
 */
export const useRouteSync = () => {
    const navigate = useNavigate();
    const params = useParams();
    const location = useLocation();

    const {
        currentView,
        selectedAccount,
        selectedFile,
        selectedTransaction,
        selectAccount,
        selectFile,
        selectTransaction,
        goToAccountList
    } = useNavigationStore();

    const { accounts } = useAccountsWithStore();

    // Sync navigation store changes to URL
    useEffect(() => {
        let newPath = '/accounts';

        switch (currentView) {
            case 'account-list':
                newPath = '/accounts';
                break;

            case 'account-detail':
                if (selectedAccount) {
                    newPath = `/accounts/${selectedAccount.accountId}`;
                }
                break;

            case 'file-transactions':
                if (selectedAccount && selectedFile) {
                    newPath = `/accounts/${selectedAccount.accountId}/files/${selectedFile.fileId}`;
                }
                break;

            case 'transaction-detail':
                if (selectedAccount && selectedTransaction) {
                    if (selectedFile) {
                        newPath = `/accounts/${selectedAccount.accountId}/files/${selectedFile.fileId}/transactions/${selectedTransaction.transactionId}`;
                    } else {
                        newPath = `/accounts/${selectedAccount.accountId}/transactions/${selectedTransaction.transactionId}`;
                    }
                }
                break;
        }

        // Only navigate if the path has actually changed
        if (location.pathname !== newPath) {
            navigate(newPath, { replace: true });
        }
    }, [currentView, selectedAccount, selectedFile, selectedTransaction, navigate, location.pathname]);

    // Sync URL changes to navigation store
    useEffect(() => {
        const { accountId, fileId, transactionId } = params;
        const pathSegments = location.pathname.split('/').filter(Boolean);

        // Determine the current view from the URL structure
        if (pathSegments.length === 1 && pathSegments[0] === 'accounts') {
            // /accounts
            if (currentView !== 'account-list') {
                goToAccountList();
            }
        } else if (pathSegments.length === 2 && pathSegments[0] === 'accounts' && accountId) {
            // /accounts/:accountId
            const account = accounts.find(acc => acc.accountId === accountId);
            if (account && (currentView !== 'account-detail' || selectedAccount?.accountId !== accountId)) {
                selectAccount(account);
            }
        } else if (pathSegments.length === 4 && pathSegments[0] === 'accounts' && pathSegments[2] === 'files' && accountId && fileId) {
            // /accounts/:accountId/files/:fileId
            const account = accounts.find(acc => acc.accountId === accountId);
            if (account) {
                // For now, we'll need to create a mock file object since we don't have file data yet
                // This will be replaced when file management is implemented
                const mockFile = {
                    fileId: fileId,
                    fileName: `File ${fileId}`,
                    uploadDate: Date.now(),
                    startDate: Date.now(),
                    endDate: Date.now(),
                    transactionCount: 0
                };

                if (currentView !== 'file-transactions' || selectedFile?.fileId !== fileId) {
                    // First select the account if not already selected
                    if (selectedAccount?.accountId !== accountId) {
                        selectAccount(account);
                    }
                    selectFile(mockFile);
                }
            }
        } else if (pathSegments.includes('transactions') && accountId && transactionId) {
            // /accounts/:accountId/transactions/:transactionId or
            // /accounts/:accountId/files/:fileId/transactions/:transactionId
            const account = accounts.find(acc => acc.accountId === accountId);
            if (account) {
                // Mock transaction object - will be replaced when transaction management is implemented
                const mockTransaction = {
                    transactionId: transactionId,
                    amount: 0,
                    description: `Transaction ${transactionId}`,
                    date: Date.now()
                };

                if (currentView !== 'transaction-detail' || selectedTransaction?.transactionId !== transactionId) {
                    // First select the account if not already selected
                    if (selectedAccount?.accountId !== accountId) {
                        selectAccount(account);
                    }

                    // If there's a fileId in the path, select the file first
                    if (fileId) {
                        const mockFile = {
                            fileId: fileId,
                            fileName: `File ${fileId}`,
                            uploadDate: Date.now(),
                            startDate: Date.now(),
                            endDate: Date.now(),
                            transactionCount: 0
                        };
                        if (selectedFile?.fileId !== fileId) {
                            selectFile(mockFile);
                        }
                    }

                    selectTransaction(mockTransaction);
                }
            }
        }
    }, [params, location.pathname, accounts, currentView, selectedAccount, selectedFile, selectedTransaction,
        selectAccount, selectFile, selectTransaction, goToAccountList]);
};

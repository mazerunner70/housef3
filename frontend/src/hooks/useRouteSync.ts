import { useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useNavigationStore } from '@/stores/navigationStore';
import useAccountsWithStore from '@/components/domain/accounts/stores/useAccountsStore';
import { Account } from '@/schemas/Account';

// Helper function to find account by ID
const findAccountById = (accounts: Account[], accountId: string): Account | undefined => {
    return accounts.find(acc => acc.accountId === accountId);
};

// Helper function to create mock file object
const createMockFile = (fileId: string) => ({
    fileId,
    fileName: `File ${fileId}`,
    uploadDate: Date.now(),
    startDate: Date.now(),
    endDate: Date.now(),
    transactionCount: 0
});

// Helper function to create mock transaction object
const createMockTransaction = (transactionId: string) => ({
    transactionId,
    amount: 0,
    description: `Transaction ${transactionId}`,
    date: Date.now()
});

// Helper function to parse URL path segments
const parsePathSegments = (pathname: string): string[] => {
    return pathname.split('/').filter(Boolean);
};

// Helper function to generate path based on current navigation state
const generateNavigationPath = (
    currentView: string,
    selectedAccount: Account | undefined,
    selectedFile: any,
    selectedTransaction: any
): string => {
    switch (currentView) {
        case 'account-list':
            return '/accounts';

        case 'account-detail':
            return selectedAccount ? `/accounts/${selectedAccount.accountId}` : '/accounts';

        case 'file-transactions':
            if (selectedAccount && selectedFile) {
                return `/accounts/${selectedAccount.accountId}/files/${selectedFile.fileId}`;
            }
            return '/accounts';

        case 'transaction-detail':
            if (selectedAccount && selectedTransaction) {
                if (selectedFile) {
                    return `/accounts/${selectedAccount.accountId}/files/${selectedFile.fileId}/transactions/${selectedTransaction.transactionId}`;
                }
                return `/accounts/${selectedAccount.accountId}/transactions/${selectedTransaction.transactionId}`;
            }
            return '/accounts';

        default:
            return '/accounts';
    }
};

// Helper function to handle account list URL
const handleAccountListUrl = (currentView: string, goToAccountList: () => void): void => {
    if (currentView !== 'account-list') {
        goToAccountList();
    }
};

// Helper function to handle account detail URL
const handleAccountDetailUrl = (
    pathSegments: string[],
    accountId: string | undefined,
    context: NavigationContext
): void => {
    if (pathSegments.length !== 2 || pathSegments[0] !== 'accounts' || !accountId) {
        return;
    }

    const account = findAccountById(context.accounts, accountId);
    if (!account) {
        return;
    }

    const needsUpdate = context.currentView !== 'account-detail' || context.selectedAccount?.accountId !== accountId;
    if (needsUpdate) {
        context.selectAccount(account);
    }
};

interface NavigationContext {
    accounts: Account[];
    currentView: string;
    selectedAccount: Account | undefined;
    selectedFile: any;
    selectedTransaction: any;
    selectAccount: (account: Account) => void;
    selectFile: (file: any) => void;
    selectTransaction: (transaction: any) => void;
}

// Helper function to handle file transactions URL
const handleFileTransactionsUrl = (
    pathSegments: string[],
    accountId: string | undefined,
    fileId: string | undefined,
    context: NavigationContext
): void => {
    if (pathSegments.length !== 4 || pathSegments[0] !== 'accounts' || pathSegments[2] !== 'files' || !accountId || !fileId) {
        return;
    }

    const account = findAccountById(context.accounts, accountId);
    if (!account) {
        return;
    }

    const needsUpdate = context.currentView !== 'file-transactions' || context.selectedFile?.fileId !== fileId;
    if (!needsUpdate) {
        return;
    }

    if (context.selectedAccount?.accountId !== accountId) {
        context.selectAccount(account);
    }

    context.selectFile(createMockFile(fileId));
};

// Helper function to handle transaction detail URL
const handleTransactionDetailUrl = (
    pathSegments: string[],
    accountId: string | undefined,
    fileId: string | undefined,
    transactionId: string | undefined,
    context: NavigationContext
): void => {
    if (!pathSegments.includes('transactions') || !accountId || !transactionId) {
        return;
    }

    const account = findAccountById(context.accounts, accountId);
    if (!account) {
        return;
    }

    const needsUpdate = context.currentView !== 'transaction-detail' || context.selectedTransaction?.transactionId !== transactionId;
    if (!needsUpdate) {
        return;
    }

    if (context.selectedAccount?.accountId !== accountId) {
        context.selectAccount(account);
    }

    if (fileId && context.selectedFile?.fileId !== fileId) {
        context.selectFile(createMockFile(fileId));
    }

    context.selectTransaction(createMockTransaction(transactionId));
};

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
        const newPath = generateNavigationPath(currentView, selectedAccount, selectedFile, selectedTransaction);

        // Only navigate if the path has actually changed
        if (location.pathname !== newPath) {
            navigate(newPath, { replace: true });
        }
    }, [currentView, selectedAccount, selectedFile, selectedTransaction, navigate, location.pathname]);

    // Sync URL changes to navigation store
    useEffect(() => {
        const { accountId, fileId, transactionId } = params;
        const pathSegments = parsePathSegments(location.pathname);

        const navigationContext: NavigationContext = {
            accounts,
            currentView,
            selectedAccount,
            selectedFile,
            selectedTransaction,
            selectAccount,
            selectFile,
            selectTransaction
        };

        // Route to appropriate handler based on URL pattern
        if (pathSegments.length === 1 && pathSegments[0] === 'accounts') {
            handleAccountListUrl(currentView, goToAccountList);
        } else if (pathSegments.length === 2 && pathSegments[0] === 'accounts' && accountId) {
            handleAccountDetailUrl(pathSegments, accountId, navigationContext);
        } else if (pathSegments.length === 4 && pathSegments[0] === 'accounts' && pathSegments[2] === 'files' && accountId && fileId) {
            handleFileTransactionsUrl(pathSegments, accountId, fileId, navigationContext);
        } else if (pathSegments.includes('transactions') && accountId && transactionId) {
            handleTransactionDetailUrl(pathSegments, accountId, fileId, transactionId, navigationContext);
        }
    }, [params, location.pathname, accounts, currentView, selectedAccount, selectedFile, selectedTransaction,
        selectAccount, selectFile, selectTransaction, goToAccountList]);
};

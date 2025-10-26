import { useEffect, useCallback } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useNavigationStore } from '@/stores/navigationStore';
import { useSessionUrlStore, NavigationSessionState } from '@/stores/sessionUrlStore';
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

// Helper function to handle account selection with delay
const handleAccountSelection = async (
    accountId: string,
    accounts: Account[],
    selectedAccount: Account | undefined,
    selectAccount: (account: Account) => void
): Promise<boolean> => {
    const account = findAccountById(accounts, accountId);
    if (account && (!selectedAccount || selectedAccount.accountId !== accountId)) {
        selectAccount(account);
        await new Promise(resolve => setTimeout(resolve, 50));
        return true;
    }
    return false;
};

// Helper function to handle file selection
const handleFileSelection = async (
    fileId: string,
    selectedFile: any,
    selectFile: (file: any) => void
): Promise<void> => {
    if (!selectedFile || selectedFile.fileId !== fileId) {
        selectFile(createMockFile(fileId));
        await new Promise(resolve => setTimeout(resolve, 50));
    }
};

// Helper function to handle transaction selection
const handleTransactionSelection = (
    transactionId: string,
    selectedTransaction: any,
    selectTransaction: (transaction: any) => void
): void => {
    if (!selectedTransaction || selectedTransaction.transactionId !== transactionId) {
        selectTransaction(createMockTransaction(transactionId));
    }
};

interface NavigationHandlers {
    accounts: Account[];
    currentView: string;
    selectedAccount: Account | undefined;
    selectedFile: any;
    selectedTransaction: any;
    selectAccount: (account: Account) => void;
    selectFile: (file: any) => void;
    selectTransaction: (transaction: any) => void;
    goToAccountList: () => void;
}

// Helper functions for specific URL patterns
const handleAccountListPattern = (currentView: string, goToAccountList: () => void): void => {
    if (currentView !== 'account-list') {
        goToAccountList();
    }
};

const handleAccountDetailPattern = (
    accountId: string | undefined,
    handlers: NavigationHandlers
): void => {
    if (!accountId) return;

    const { accounts, currentView, selectedAccount, selectAccount } = handlers;
    const account = findAccountById(accounts, accountId);
    if (!account) return;

    if (currentView !== 'account-detail' || selectedAccount?.accountId !== accountId) {
        selectAccount(account);
    }
};

const handleFilePattern = (
    accountId: string | undefined,
    fileId: string | undefined,
    handlers: NavigationHandlers
): void => {
    if (!accountId || !fileId) return;

    const { accounts, selectedAccount, selectedFile, selectAccount, selectFile } = handlers;
    const account = findAccountById(accounts, accountId);
    if (!account) return;

    if (selectedAccount?.accountId !== accountId) {
        selectAccount(account);
    }

    if (!selectedFile || selectedFile.fileId !== fileId) {
        selectFile(createMockFile(fileId));
    }
};

const handleTransactionPattern = (
    accountId: string | undefined,
    fileId: string | undefined,
    transactionId: string | undefined,
    handlers: NavigationHandlers
): void => {
    if (!accountId || !transactionId) return;

    const { accounts, selectedAccount, selectedFile, selectedTransaction, selectAccount, selectFile, selectTransaction } = handlers;
    const account = findAccountById(accounts, accountId);
    if (!account) return;

    if (selectedAccount?.accountId !== accountId) {
        selectAccount(account);
    }

    if (fileId && (!selectedFile || selectedFile.fileId !== fileId)) {
        selectFile(createMockFile(fileId));
    }

    if (!selectedTransaction || selectedTransaction.transactionId !== transactionId) {
        selectTransaction(createMockTransaction(transactionId));
    }
};

// Helper function to handle traditional URL patterns
const handleTraditionalUrl = (
    pathSegments: string[],
    accountId: string | undefined,
    fileId: string | undefined,
    transactionId: string | undefined,
    handlers: NavigationHandlers
): void => {
    if (pathSegments.length === 1 && pathSegments[0] === 'accounts') {
        handleAccountListPattern(handlers.currentView, handlers.goToAccountList);
    } else if (pathSegments.length === 2 && pathSegments[0] === 'accounts') {
        handleAccountDetailPattern(accountId, handlers);
    } else if (pathSegments.includes('files')) {
        handleFilePattern(accountId, fileId, handlers);
    } else if (pathSegments.includes('transactions')) {
        handleTransactionPattern(accountId, fileId, transactionId, handlers);
    }
};

/**
 * Enhanced routing hook that uses session URL compression for complex navigation states
 * 
 * Features:
 * - Automatic URL compression when URLs get too long
 * - LRU caching of navigation states
 * - Seamless fallback between traditional and session URLs
 * - Bidirectional sync between URL and navigation store
 */
export const useSessionRouting = () => {
    const navigate = useNavigate();
    const params = useParams();
    const location = useLocation();

    const {
        currentView,
        selectedAccount,
        selectedFile,
        selectedTransaction,
        breadcrumb,
        selectAccount,
        selectFile,
        selectTransaction,
        goToAccountList
    } = useNavigationStore();

    const {
        generateSessionUrl,
        resolveSessionUrl,
        isSessionUrl,
        cleanupOldSessions
    } = useSessionUrlStore();

    const { accounts } = useAccountsWithStore();

    // Convert navigation store state to session state
    const getCurrentNavigationState = useCallback((): NavigationSessionState => {
        return {
            currentView,
            selectedAccountId: selectedAccount?.accountId,
            selectedFileId: selectedFile?.fileId,
            selectedTransactionId: selectedTransaction?.transactionId,
            context: {
                // Extract context from URL search params
                filter: new URLSearchParams(location.search).get('filter') || undefined,
                sort: new URLSearchParams(location.search).get('sort') || undefined,
                page: new URLSearchParams(location.search).get('page') || undefined,
                dateRange: new URLSearchParams(location.search).get('dateRange') || undefined,
                categoryId: new URLSearchParams(location.search).get('categoryId') || undefined,
                tagId: new URLSearchParams(location.search).get('tagId') || undefined,
                searchQuery: new URLSearchParams(location.search).get('search') || undefined,
                viewMode: new URLSearchParams(location.search).get('viewMode') || undefined,
                groupBy: new URLSearchParams(location.search).get('groupBy') || undefined
            },
            breadcrumb: breadcrumb.map(item => ({
                label: item.label,
                level: item.level,
                accountId: selectedAccount?.accountId,
                fileId: selectedFile?.fileId,
                transactionId: selectedTransaction?.transactionId
            }))
        };
    }, [currentView, selectedAccount, selectedFile, selectedTransaction, breadcrumb, location.search]);

    // Apply navigation state to the navigation store
    const applyNavigationState = useCallback(async (state: NavigationSessionState) => {
        // Handle account selection
        if (state.selectedAccountId) {
            await handleAccountSelection(state.selectedAccountId, accounts, selectedAccount, selectAccount);
        }

        // Handle file selection (requires account to be selected first)
        if (state.selectedFileId) {
            await handleFileSelection(state.selectedFileId, selectedFile, selectFile);
        }

        // Handle transaction selection (requires account to be selected first)
        if (state.selectedTransactionId) {
            handleTransactionSelection(state.selectedTransactionId, selectedTransaction, selectTransaction);
        }

        // Handle view-only states (no specific selections)
        if (!state.selectedAccountId && state.currentView === 'account-list') {
            if (currentView !== 'account-list') {
                goToAccountList();
            }
        }
    }, [accounts, selectedAccount, selectedFile, selectedTransaction, currentView,
        selectAccount, selectFile, selectTransaction, goToAccountList]);

    // Sync navigation store changes to URL (with session compression)
    useEffect(() => {
        const navigationState = getCurrentNavigationState();
        const newUrl = generateSessionUrl(navigationState);
        const currentUrl = location.pathname + location.search;

        if (currentUrl !== newUrl) {
            navigate(newUrl, { replace: true });
        }
    }, [getCurrentNavigationState, generateSessionUrl, navigate, location.pathname, location.search]);

    // Sync URL changes to navigation store (handle both traditional and session URLs)
    useEffect(() => {
        const currentUrl = location.pathname + location.search;

        // Check if this is a session URL
        if (isSessionUrl(currentUrl)) {
            const sessionState = resolveSessionUrl(currentUrl);
            if (sessionState) {
                applyNavigationState(sessionState);
                return;
            }
        }

        // Handle traditional URL parsing
        const { accountId, fileId, transactionId } = params;
        const pathSegments = parsePathSegments(location.pathname);

        // Parse traditional URL structure using helper function
        const handlers: NavigationHandlers = {
            accounts,
            currentView,
            selectedAccount,
            selectedFile,
            selectedTransaction,
            selectAccount,
            selectFile,
            selectTransaction,
            goToAccountList
        };

        handleTraditionalUrl(pathSegments, accountId, fileId, transactionId, handlers);
    }, [params, location.pathname, location.search, accounts, currentView, selectedAccount, selectedFile, selectedTransaction,
        selectAccount, selectFile, selectTransaction, goToAccountList, isSessionUrl, resolveSessionUrl, applyNavigationState]);

    // Cleanup old sessions periodically
    useEffect(() => {
        const cleanup = () => {
            cleanupOldSessions();
        };

        // Cleanup on mount and every 10 minutes
        cleanup();
        const interval = setInterval(cleanup, 10 * 60 * 1000);

        return () => clearInterval(interval);
    }, [cleanupOldSessions]);

    // Return utilities for components
    return {
        isSessionUrl: isSessionUrl(location.pathname + location.search),

        // Force generate a session URL for current state
        createSessionUrl: () => {
            const state = getCurrentNavigationState();
            return generateSessionUrl(state);
        },

        // Get current navigation state
        getCurrentState: getCurrentNavigationState,

        // Apply a specific navigation state
        applyState: applyNavigationState
    };
};

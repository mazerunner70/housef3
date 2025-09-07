import { useEffect, useCallback } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useNavigationStore } from '@/stores/navigationStore';
import { useSessionUrlStore, NavigationSessionState } from '@/stores/sessionUrlStore';
import useAccountsWithStore from '@/stores/useAccountsStore';

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
        // First, ensure we have the account if specified
        if (state.selectedAccountId) {
            const account = accounts.find(acc => acc.accountId === state.selectedAccountId);
            if (account && (!selectedAccount || selectedAccount.accountId !== state.selectedAccountId)) {
                selectAccount(account);
                // Wait a bit for the account selection to propagate
                await new Promise(resolve => setTimeout(resolve, 50));
            }
        }

        // Then handle file selection
        if (state.selectedFileId && selectedAccount) {
            const mockFile = {
                fileId: state.selectedFileId,
                fileName: `File ${state.selectedFileId}`,
                uploadDate: Date.now(),
                startDate: Date.now(),
                endDate: Date.now(),
                transactionCount: 0
            };

            if (!selectedFile || selectedFile.fileId !== state.selectedFileId) {
                selectFile(mockFile);
                await new Promise(resolve => setTimeout(resolve, 50));
            }
        }

        // Finally handle transaction selection
        if (state.selectedTransactionId && selectedAccount) {
            const mockTransaction = {
                transactionId: state.selectedTransactionId,
                amount: 0,
                description: `Transaction ${state.selectedTransactionId}`,
                date: Date.now()
            };

            if (!selectedTransaction || selectedTransaction.transactionId !== state.selectedTransactionId) {
                selectTransaction(mockTransaction);
            }
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
        const pathSegments = location.pathname.split('/').filter(Boolean);
        const searchParams = new URLSearchParams(location.search);

        // Parse traditional URL structure
        if (pathSegments.length === 1 && pathSegments[0] === 'accounts') {
            if (currentView !== 'account-list') {
                goToAccountList();
            }
        } else if (pathSegments.length === 2 && pathSegments[0] === 'accounts' && accountId) {
            const account = accounts.find(acc => acc.accountId === accountId);
            if (account && (currentView !== 'account-detail' || selectedAccount?.accountId !== accountId)) {
                selectAccount(account);
            }
        } else if (pathSegments.includes('files') && accountId && fileId) {
            const account = accounts.find(acc => acc.accountId === accountId);
            if (account) {
                const mockFile = {
                    fileId: fileId,
                    fileName: `File ${fileId}`,
                    uploadDate: Date.now(),
                    startDate: Date.now(),
                    endDate: Date.now(),
                    transactionCount: 0
                };

                if (selectedAccount?.accountId !== accountId) {
                    selectAccount(account);
                }
                if (!selectedFile || selectedFile.fileId !== fileId) {
                    selectFile(mockFile);
                }
            }
        } else if (pathSegments.includes('transactions') && accountId && transactionId) {
            const account = accounts.find(acc => acc.accountId === accountId);
            if (account) {
                const mockTransaction = {
                    transactionId: transactionId,
                    amount: 0,
                    description: `Transaction ${transactionId}`,
                    date: Date.now()
                };

                if (selectedAccount?.accountId !== accountId) {
                    selectAccount(account);
                }

                // Handle file context if present
                if (fileId) {
                    const mockFile = {
                        fileId: fileId,
                        fileName: `File ${fileId}`,
                        uploadDate: Date.now(),
                        startDate: Date.now(),
                        endDate: Date.now(),
                        transactionCount: 0
                    };
                    if (!selectedFile || selectedFile.fileId !== fileId) {
                        selectFile(mockFile);
                    }
                }

                if (!selectedTransaction || selectedTransaction.transactionId !== transactionId) {
                    selectTransaction(mockTransaction);
                }
            }
        }
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

import { useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useParams, useLocation, useSearchParams } from 'react-router-dom';
import { useNavigationStore, NavigationContext } from '@/stores/navigationStore';
import useAccountsWithStore from '@/stores/useAccountsStore';

/**
 * Smart routing strategy that handles URL depth growth gracefully
 * 
 * Strategy:
 * 1. Keep primary navigation in path segments (SEO friendly)
 * 2. Move secondary/contextual info to query parameters
 * 3. Use URL shortening for very deep navigation
 * 4. Implement breadcrumb-based navigation fallbacks
 */

// Maximum recommended path depth before using query params
const MAX_PATH_DEPTH = 3;


export const useSmartRouting = () => {
    const navigate = useNavigate();
    const params = useParams();
    const location = useLocation();
    const [searchParams, setSearchParams] = useSearchParams();

    const {
        currentView,
        selectedAccount,
        selectedFile,
        selectedTransaction,
        selectAccount,
        selectFile,
        selectTransaction,
        goToAccountList,
        setUrlContext
    } = useNavigationStore();

    const { accounts } = useAccountsWithStore();

    // Parse current navigation context from URL
    const navigationContext = useMemo((): NavigationContext => {
        return {
            view: searchParams.get('view') || undefined,
            fileId: searchParams.get('fileId') || params.fileId,
            transactionId: searchParams.get('transactionId') || params.transactionId,
            filter: searchParams.get('filter') || undefined,
            sort: searchParams.get('sort') || undefined,
            page: searchParams.get('page') || undefined,
            categoryId: searchParams.get('categoryId') || undefined,
            tagId: searchParams.get('tagId') || undefined,
            dateRange: searchParams.get('dateRange') || undefined
        };
    }, [searchParams, params]);

    // Calculate current URL depth
    const urlDepth = useMemo(() => {
        const pathSegments = location.pathname.split('/').filter(Boolean);
        return pathSegments.length;
    }, [location.pathname]);

    // Determine if we should use shallow or deep routing
    const useDeepRouting = useMemo(() => {
        return urlDepth > MAX_PATH_DEPTH ||
            Object.keys(navigationContext).filter(key => navigationContext[key as keyof NavigationContext]).length > 2;
    }, [urlDepth, navigationContext]);

    // Update navigation store with URL context
    useEffect(() => {
        setUrlContext(navigationContext);
    }, [navigationContext, setUrlContext]);

    // Helper functions for URL generation
    const generateShallowUrl = useCallback(() => {
        const { accountId } = params;

        switch (currentView) {
            case 'account-list':
                return '/accounts';

            case 'account-detail':
                return selectedAccount ? `/accounts/${selectedAccount.accountId}` : '/accounts';

            case 'file-transactions':
                return selectedAccount && selectedFile
                    ? `/accounts/${selectedAccount.accountId}/files/${selectedFile.fileId}`
                    : `/accounts/${selectedAccount?.accountId || accountId || ''}`;

            case 'transaction-detail':
                return generateTransactionDetailUrl();

            default:
                return '/accounts';
        }
    }, [currentView, selectedAccount, selectedFile, params]);

    const generateTransactionDetailUrl = useCallback(() => {
        if (selectedAccount && selectedTransaction) {
            if (selectedFile) {
                // This would exceed depth, use query params
                const url = new URL(`/accounts/${selectedAccount.accountId}`, window.location.origin);
                url.searchParams.set('view', 'transaction');
                url.searchParams.set('fileId', selectedFile.fileId);
                url.searchParams.set('transactionId', selectedTransaction.transactionId);
                return url.pathname + url.search;
            } else {
                return `/accounts/${selectedAccount.accountId}/transactions/${selectedTransaction.transactionId}`;
            }
        }
        return '/accounts';
    }, [selectedAccount, selectedTransaction, selectedFile]);

    const generateDeepUrl = useCallback(() => {
        const baseUrl = selectedAccount ? `/accounts/${selectedAccount.accountId}` : '/accounts';
        const url = new URL(baseUrl, window.location.origin);

        // Add context via query parameters
        if (currentView !== 'account-list' && currentView !== 'account-detail') {
            url.searchParams.set('view', currentView);
        }

        if (selectedFile) {
            url.searchParams.set('fileId', selectedFile.fileId);
        }

        if (selectedTransaction) {
            url.searchParams.set('transactionId', selectedTransaction.transactionId);
        }

        // Preserve other context
        Object.entries(navigationContext).forEach(([key, value]) => {
            if (value && !['view', 'fileId', 'transactionId'].includes(key)) {
                url.searchParams.set(key, value);
            }
        });

        return url.pathname + url.search;
    }, [currentView, selectedAccount, selectedFile, selectedTransaction, navigationContext]);

    // Generate URL based on current navigation state
    const generateUrl = useMemo(() => {
        return useDeepRouting ? generateDeepUrl() : generateShallowUrl();
    }, [useDeepRouting, generateDeepUrl, generateShallowUrl]);

    // Sync navigation store changes to URL
    useEffect(() => {
        const newUrl = generateUrl;
        const currentUrl = location.pathname + location.search;

        if (currentUrl !== newUrl) {
            navigate(newUrl, { replace: true });
        }
    }, [generateUrl, navigate, location.pathname, location.search]);

    // Helper functions for URL sync
    const handleAccountSelection = useCallback(() => {
        const { accountId } = params;
        if (accountId && (!selectedAccount || selectedAccount.accountId !== accountId)) {
            const account = accounts.find(acc => acc.accountId === accountId);
            if (account) {
                selectAccount(account);
                return true; // Handled
            }
        }
        return false;
    }, [params, selectedAccount, accounts, selectAccount]);

    const handleFileNavigation = useCallback((pathSegments: string[]) => {
        const view = navigationContext.view;
        const fileId = navigationContext.fileId;

        if (view === 'file-transactions' || (pathSegments.includes('files') && fileId)) {
            if (selectedAccount && fileId && (!selectedFile || selectedFile.fileId !== fileId)) {
                const mockFile = {
                    fileId: fileId,
                    fileName: `File ${fileId}`,
                    uploadDate: Date.now(),
                    startDate: Date.now(),
                    endDate: Date.now(),
                    transactionCount: 0
                };
                selectFile(mockFile);
            }
        }
    }, [navigationContext, selectedAccount, selectedFile, selectFile]);

    const handleTransactionNavigation = useCallback((pathSegments: string[]) => {
        const view = navigationContext.view;
        const transactionId = navigationContext.transactionId;

        if (view === 'transaction-detail' || view === 'transaction' ||
            (pathSegments.includes('transactions') && transactionId)) {
            if (selectedAccount && transactionId && (!selectedTransaction || selectedTransaction.transactionId !== transactionId)) {
                const mockTransaction = {
                    transactionId: transactionId,
                    amount: 0,
                    description: `Transaction ${transactionId}`,
                    date: Date.now()
                };
                selectTransaction(mockTransaction);
            }
        }
    }, [navigationContext, selectedAccount, selectedTransaction, selectTransaction]);

    const handleAccountListNavigation = useCallback((pathSegments: string[]) => {
        const view = navigationContext.view;
        if (pathSegments.length === 1 && pathSegments[0] === 'accounts' && !view) {
            if (currentView !== 'account-list') {
                goToAccountList();
            }
        }
    }, [navigationContext, currentView, goToAccountList]);

    // Sync URL changes to navigation store
    useEffect(() => {
        const pathSegments = location.pathname.split('/').filter(Boolean);

        // Handle account selection first
        if (handleAccountSelection()) {
            return; // Let the account selection trigger the next navigation
        }

        // Handle other navigation types
        handleFileNavigation(pathSegments);
        handleTransactionNavigation(pathSegments);
        handleAccountListNavigation(pathSegments);
    }, [params, location.pathname, location.search, navigationContext,
        handleAccountSelection, handleFileNavigation, handleTransactionNavigation, handleAccountListNavigation]);

    // Return utility functions for components to use
    return {
        navigationContext,
        urlDepth,
        useDeepRouting,
        isUrlTooLong: location.pathname.length + location.search.length > 1500, // Warning threshold

        // Helper to add context without full navigation
        addContext: (context: Partial<NavigationContext>) => {
            const newSearchParams = new URLSearchParams(searchParams);
            Object.entries(context).forEach(([key, value]) => {
                if (value) {
                    newSearchParams.set(key, value);
                } else {
                    newSearchParams.delete(key);
                }
            });
            setSearchParams(newSearchParams);
        },

        // Helper to clear context
        clearContext: (keys?: string[]) => {
            const newSearchParams = new URLSearchParams(searchParams);
            if (keys) {
                keys.forEach(key => newSearchParams.delete(key));
            } else {
                // Clear all context except core navigation
                ['filter', 'sort', 'page', 'categoryId', 'tagId', 'dateRange'].forEach(key => {
                    newSearchParams.delete(key);
                });
            }
            setSearchParams(newSearchParams);
        }
    };
};

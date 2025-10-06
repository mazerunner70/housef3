import { create } from 'zustand';
import { Account } from '../schemas/Account';

// Navigation view types
export type ViewType = 'account-list' | 'account-detail' | 'file-transactions' | 'transaction-detail';

// Breadcrumb item interface
export interface BreadcrumbItem {
    label: string;
    action: () => void;
    level: number;
}

// Transaction file interface (simplified for now)
export interface TransactionFile {
    fileId: string;
    fileName: string;
    uploadDate: number;
    startDate: number;
    endDate: number;
    transactionCount: number;
    processingStatus?: string;
}

// Transaction interface (simplified for now)
export interface Transaction {
    transactionId: string;
    amount: number;
    description: string;
    date: number;
    category?: string;
}

// Navigation context from URL parameters
export interface NavigationContext {
    // Core navigation context
    view?: string;
    fileId?: string;
    transactionId?: string;

    // UI state context
    filter?: string;
    sort?: string;
    page?: string;

    // Extended context
    categoryId?: string;
    tagId?: string;
    dateRange?: string;

    // Generic context for any additional parameters
    [key: string]: string | undefined;
}

// Navigation state interface
export interface NavigationState {
    currentView: ViewType;
    selectedAccount?: Account;
    selectedFile?: TransactionFile;
    selectedTransaction?: Transaction;
    sidebarCollapsed: boolean;
    breadcrumb: BreadcrumbItem[];

    // URL-derived context available to components
    urlContext: NavigationContext;
}

// Navigation actions interface
export interface NavigationActions {
    selectAccount: (account: Account) => void;
    selectFile: (file: TransactionFile) => void;
    selectTransaction: (transaction: Transaction) => void;
    goBack: () => void;
    goToAccountList: () => void;
    goToHome: () => void;
    goToTransfers: () => void;
    setBreadcrumb: (breadcrumb: BreadcrumbItem[]) => void;
    toggleSidebar: () => void;
    setSidebarCollapsed: (collapsed: boolean) => void;

    // URL context management
    setUrlContext: (context: NavigationContext) => void;
    updateUrlContext: (updates: Partial<NavigationContext>) => void;
    getContextValue: (key: string) => string | undefined;
    clearContext: (keys?: string[]) => void;
}

// Combined store interface
export interface NavigationStore extends NavigationState, NavigationActions { }

// Create the navigation store
export const useNavigationStore = create<NavigationStore>((set, get) => ({
    // Initial state - start with just Home, let pages set their own breadcrumb
    currentView: 'account-list',
    sidebarCollapsed: false,
    urlContext: {},
    breadcrumb: [
        { label: 'Home', action: () => get().goToHome(), level: 0 }
    ],

    // Actions
    selectAccount: (account: Account) => {
        set({
            currentView: 'account-detail',
            selectedAccount: account,
            selectedFile: undefined,
            selectedTransaction: undefined,
            breadcrumb: [
                { label: 'Home', action: () => get().goToHome(), level: 0 },
                { label: 'Accounts', action: () => get().goToAccountList(), level: 1 },
                { label: account.accountName, action: () => get().selectAccount(account), level: 2 }
            ]
        });
    },

    selectFile: (file: TransactionFile) => {
        const { selectedAccount } = get();
        if (!selectedAccount) return;

        set({
            currentView: 'file-transactions',
            selectedFile: file,
            selectedTransaction: undefined,
            breadcrumb: [
                { label: 'Home', action: () => get().goToHome(), level: 0 },
                { label: 'Accounts', action: () => get().goToAccountList(), level: 1 },
                { label: selectedAccount.accountName, action: () => get().selectAccount(selectedAccount), level: 2 },
                { label: file.fileName, action: () => get().selectFile(file), level: 3 }
            ]
        });
    },

    selectTransaction: (transaction: Transaction) => {
        const { selectedAccount, selectedFile } = get();
        if (!selectedAccount) return;

        const breadcrumb: BreadcrumbItem[] = [
            { label: 'Home', action: () => get().goToHome(), level: 0 },
            { label: 'Accounts', action: () => get().goToAccountList(), level: 1 },
            { label: selectedAccount.accountName, action: () => get().selectAccount(selectedAccount), level: 2 }
        ];

        if (selectedFile) {
            breadcrumb.push({ label: selectedFile.fileName, action: () => get().selectFile(selectedFile), level: 3 });
        }

        breadcrumb.push({
            label: `Transaction ${transaction.transactionId.slice(-6)}`,
            action: () => get().selectTransaction(transaction),
            level: selectedFile ? 4 : 3
        });

        set({
            currentView: 'transaction-detail',
            selectedTransaction: transaction,
            breadcrumb
        });
    },

    goBack: () => {
        const { currentView, selectedAccount, selectedFile } = get();

        switch (currentView) {
            case 'transaction-detail':
                if (selectedFile) {
                    get().selectFile(selectedFile);
                } else if (selectedAccount) {
                    get().selectAccount(selectedAccount);
                } else {
                    get().goToAccountList();
                }
                break;
            case 'file-transactions':
                if (selectedAccount) {
                    get().selectAccount(selectedAccount);
                } else {
                    get().goToAccountList();
                }
                break;
            case 'account-detail':
                get().goToAccountList();
                break;
            default:
                // Already at account list, do nothing
                break;
        }
    },

    goToAccountList: () => {
        const newBreadcrumb = [
            { label: 'Home', action: () => get().goToHome(), level: 0 },
            { label: 'Accounts', action: () => get().goToAccountList(), level: 1 }
        ];
        set({
            currentView: 'account-list',
            selectedAccount: undefined,
            selectedFile: undefined,
            selectedTransaction: undefined,
            breadcrumb: newBreadcrumb
        });
    },

    goToHome: () => {
        set({
            currentView: 'account-list', // This doesn't really matter for home
            selectedAccount: undefined,
            selectedFile: undefined,
            selectedTransaction: undefined,
            breadcrumb: [{ label: 'Home', action: () => get().goToHome(), level: 0 }]
        });
    },

    goToTransfers: () => {
        set({
            currentView: 'account-list', // This doesn't really matter for transfers
            selectedAccount: undefined,
            selectedFile: undefined,
            selectedTransaction: undefined,
            breadcrumb: [
                { label: 'Home', action: () => get().goToHome(), level: 0 },
                { label: 'Transfers', action: () => get().goToTransfers(), level: 1 }
            ]
        });
    },

    setBreadcrumb: (breadcrumb: BreadcrumbItem[]) => {
        set({ breadcrumb });
    },

    toggleSidebar: () => {
        set(state => ({ sidebarCollapsed: !state.sidebarCollapsed }));
    },

    setSidebarCollapsed: (collapsed: boolean) => {
        set({ sidebarCollapsed: collapsed });
    },

    // URL context management
    setUrlContext: (context: NavigationContext) => {
        set({ urlContext: { ...context } });
    },

    updateUrlContext: (updates: Partial<NavigationContext>) => {
        set(state => ({
            urlContext: { ...state.urlContext, ...updates }
        }));
    },

    getContextValue: (key: string) => {
        return get().urlContext[key];
    },

    clearContext: (keys?: string[]) => {
        const { urlContext } = get();
        if (keys) {
            // Clear specific keys
            const newContext = { ...urlContext };
            keys.forEach(key => delete newContext[key]);
            set({ urlContext: newContext });
        } else {
            // Clear all context except core navigation
            const coreKeys = ['view', 'fileId', 'transactionId'];
            const newContext: NavigationContext = {};
            coreKeys.forEach(key => {
                if (urlContext[key]) {
                    newContext[key] = urlContext[key];
                }
            });
            set({ urlContext: newContext });
        }
    }
}));

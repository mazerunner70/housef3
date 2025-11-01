import { create } from 'zustand';
import { Account } from '../schemas/Account';

/**
 * Navigation Store
 * 
 * Manages navigation state for the application including:
 * - Selected entities (account, file, transaction)
 * - View state
 * - Sidebar state
 * - URL context
 * 
 * Note: Breadcrumbs are now managed by React Router's useMatches() hook
 */

// Navigation view types
export type ViewType = 'account-list' | 'account-detail' | 'file-transactions' | 'transaction-detail';

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

    // URL-derived context available to components
    urlContext: NavigationContext;
}

// Navigation actions interface
export interface NavigationActions {
    selectAccount: (account: Account) => void;
    selectFile: (file: TransactionFile) => void;
    selectTransaction: (transaction: Transaction) => void;
    clearSelection: () => void;
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
    // Initial state
    currentView: 'account-list',
    sidebarCollapsed: false,
    urlContext: {},

    // Actions - simplified to only manage selection state
    selectAccount: (account: Account) => {
        set({
            currentView: 'account-detail',
            selectedAccount: account,
            selectedFile: undefined,
            selectedTransaction: undefined
        });
    },

    selectFile: (file: TransactionFile) => {
        const { selectedAccount } = get();
        if (!selectedAccount) return;

        set({
            currentView: 'file-transactions',
            selectedFile: file,
            selectedTransaction: undefined
        });
    },

    selectTransaction: (transaction: Transaction) => {
        set({
            currentView: 'transaction-detail',
            selectedTransaction: transaction
        });
    },

    clearSelection: () => {
        set({
            currentView: 'account-list',
            selectedAccount: undefined,
            selectedFile: undefined,
            selectedTransaction: undefined
        });
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

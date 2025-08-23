// Account Type Definitions
// These interfaces define the data models for accounts and related operations

import { Decimal } from 'decimal.js';

// Account Enums
export enum AccountType {
    CHECKING = "checking",
    SAVINGS = "savings",
    CREDIT_CARD = "credit_card",
    INVESTMENT = "investment",
    LOAN = "loan",
    OTHER = "other"
}

export enum Currency {
    USD = "USD",
    EUR = "EUR",
    GBP = "GBP",
    CAD = "CAD",
    JPY = "JPY",
    AUD = "AUD",
    CHF = "CHF",
    CNY = "CNY",
    OTHER = "other"
}

// Core Account Model
export interface Account {
    accountId: string;
    userId: string;
    accountName: string;
    accountType: AccountType;
    institution: string;
    balance: Decimal;
    currency: Currency;
    notes?: string;
    isActive: boolean;
    defaultFileMapId?: string;
    lastTransactionDate?: number;  // milliseconds since epoch
    createdAt: number;
    updatedAt: number;
}

// Account Creation/Update Models
export interface AccountCreate {
    accountName: string;
    accountType: AccountType;
    institution: string;
    balance: Decimal;
    currency: Currency;
    notes?: string;
    defaultFileMapId?: string;
}

export interface AccountUpdate {
    accountName?: string;
    accountType?: AccountType;
    institution?: string;
    balance?: Decimal;
    currency?: Currency;
    notes?: string;
    isActive?: boolean;
    defaultFileMapId?: string;
}

// API Response Types
export interface AccountListResponse {
    accounts: Account[];
    user: {
        id: string;
        email: string;
        auth_time: string;
    };
}

// Account Statistics
export interface AccountStats {
    totalBalance: Decimal;
    accountCount: number;
    activeAccountCount: number;
    currencyBreakdown: Array<{
        currency: Currency;
        totalBalance: Decimal;
        accountCount: number;
    }>;
    typeBreakdown: Array<{
        accountType: AccountType;
        totalBalance: Decimal;
        accountCount: number;
    }>;
    recentActivity: Array<{
        accountId: string;
        lastTransactionDate: number;
        transactionCount: number;
    }>;
}

// Account Summary (for dropdowns, lists, etc.)
export interface AccountSummary {
    accountId: string;
    accountName: string;
    accountType: AccountType;
    institution: string;
    balance: Decimal;
    currency: Currency;
    isActive: boolean;
}

// Form State Types
export interface AccountFormState {
    account: Partial<Account>;
    isEditing: boolean;
    isDirty: boolean;
    isValid: boolean;
    errors: Record<string, string>;
}

// Error Types
export interface AccountError {
    code: string;
    message: string;
    field?: string;
    details?: any;
}

export interface AccountApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: AccountError;
    message?: string;
}

// Utility Types
export type AccountSortField = keyof Account;
export type AccountSortOrder = 'asc' | 'desc';

// Account Filtering
export interface AccountFilters {
    accountTypes?: AccountType[];
    currencies?: Currency[];
    institutions?: string[];
    isActive?: boolean;
    hasTransactions?: boolean;
    balanceRange?: {
        min: Decimal;
        max: Decimal;
    };
}

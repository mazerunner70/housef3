import { useState, useEffect, useCallback } from 'react';
import {
    listAccounts as serviceListAccounts,
    createAccount as serviceCreateAccount,
    updateAccount as serviceUpdateAccount,
    deleteAccount as serviceDeleteAccount,
    Account as ServiceAccount,
    AccountType as ServiceAccountTypeEnum,
    Currency as ServiceCurrencyEnum,
} from '../../services/AccountService';
import Decimal from 'decimal.js';

// This should align with the Account type in AccountsView and backend responses
// Consider moving to a shared types file: frontend/src/types/account.ts for example
export interface Account {
    id: string;
    name: string;
    type: string;
    number: string; // Masked or full, depending on API and usage
    currency: string;
    openingBalance?: number;
    bankName?: string;
    transactionFilesCount?: number; // Usually comes from a separate calculation or join
    // Add other relevant fields from your backend model
    userId?: string; // If relevant for frontend logic or requests
}

// For POST/PUT requests, we might send a subset of fields
export interface AccountInputData {
    name: string;
    type: string;
    accountNumber: string; // Usually the full, unmasked number for creation/update
    openingBalance: Decimal;
    currency: string;
    bankName?: string;
}

// UI-facing Account type (as previously defined in this hook)
export interface UIAccount {
    id: string;
    name: string;
    type: string;
    currency: string;
    balance?: Decimal;    // Changed from Decimal to number temporarily
    bankName?: string;
}

// Input data type for UI forms (as previously defined)
export interface UIAccountInputData {
    name: string;
    type: string;
    currency: string;
    balance?: string;      // Optional: Input as string, defaults to '0' if not provided for new accounts
    bankName?: string;
}

// --- Robust Enum Mapping ---
const uiToServiceAccountTypeMap: { [key: string]: ServiceAccountTypeEnum } = {
    "checking": ServiceAccountTypeEnum.CHECKING,
    "savings": ServiceAccountTypeEnum.SAVINGS,
    "credit_card": ServiceAccountTypeEnum.CREDIT_CARD,
    "investment": ServiceAccountTypeEnum.INVESTMENT,
    "loan": ServiceAccountTypeEnum.LOAN,
    "other": ServiceAccountTypeEnum.OTHER,
};

const uiToServiceCurrencyMap: { [key: string]: ServiceCurrencyEnum } = {
    "usd": ServiceCurrencyEnum.USD,
    "eur": ServiceCurrencyEnum.EUR,
    "gbp": ServiceCurrencyEnum.GBP,
    "cad": ServiceCurrencyEnum.CAD,
    "jpy": ServiceCurrencyEnum.JPY,
    "aud": ServiceCurrencyEnum.AUD,
    "chf": ServiceCurrencyEnum.CHF,
    "cny": ServiceCurrencyEnum.CNY,
    // "other": ServiceCurrencyEnum.OTHER, // Removed for now, add if UI supports it
};

// --- MAPPING FUNCTIONS ---
const mapServiceAccountToUiAccount = (serviceAcc: ServiceAccount): UIAccount => {
    return {
        id: serviceAcc.accountId,
        name: serviceAcc.accountName,
        type: serviceAcc.accountType.toString().toLowerCase(),
        currency: serviceAcc.currency.toString().toUpperCase(),
        balance: serviceAcc.balance !== undefined && serviceAcc.balance !== null ? new Decimal(serviceAcc.balance.toString()) : undefined,
        bankName: serviceAcc.institution,
    };
};

const mapUiInputToServiceInput = (uiInput: UIAccountInputData, isNewAccount: boolean): Partial<ServiceAccount> => {
    const serviceAccountType = uiToServiceAccountTypeMap[uiInput.type.toLowerCase()];
    if (!serviceAccountType) {
        throw new Error(`Invalid account type: "${uiInput.type}". Supported: ${Object.keys(uiToServiceAccountTypeMap).join(', ')}`);
    }

    const serviceCurrency = uiToServiceCurrencyMap[uiInput.currency.toLowerCase()];
    if (!serviceCurrency) {
        throw new Error(`Invalid currency: "${uiInput.currency}". Supported: ${Object.keys(uiToServiceCurrencyMap).map(c => c.toUpperCase()).join(', ')}`);
    }
    
    const balanceString = uiInput.balance === undefined && isNewAccount ? '0' : uiInput.balance;
    let finalBalanceForService: Decimal | undefined = undefined;

    if (balanceString !== undefined) {
        try {
            const decimalBalance = new Decimal(balanceString);
            if (decimalBalance.isNaN()) throw new Error('Balance is not a valid number.');
            finalBalanceForService = decimalBalance;
        } catch (e: any) {
            throw new Error(`Invalid balance format for "${balanceString}": ${e.message}`);
        }
    }

    const serviceInput: Partial<ServiceAccount> = {
        accountName: uiInput.name,
        accountType: serviceAccountType,
        institution: uiInput.bankName,
        currency: serviceCurrency,
        isActive: true,
    };

    if (finalBalanceForService !== undefined) {
        serviceInput.balance = finalBalanceForService;
    }
    
    if (serviceInput.institution === undefined) delete serviceInput.institution;
    return serviceInput;
};

interface UseAccountsReturn {
    accounts: UIAccount[];
    isLoading: boolean;
    error: string | null;
    fetchAccounts: () => Promise<void>;
    createAccount: (accountData: UIAccountInputData) => Promise<UIAccount | null>;
    updateAccount: (accountId: string, accountData: UIAccountInputData) => Promise<UIAccount | null>; 
    deleteAccount: (accountId: string) => Promise<boolean>;
    clearError: () => void;
}

const useAccounts = (): UseAccountsReturn => {
    const [accounts, setAccounts] = useState<UIAccount[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const clearError = () => setError(null);

    const fetchAccounts = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await serviceListAccounts(); 
            setAccounts(response.accounts.map(mapServiceAccountToUiAccount));
        } catch (err: any) {
            console.error("Error in fetchAccounts:", err);
            setError(err.message || 'Failed to fetch accounts');
        }
        setIsLoading(false);
    }, []);

    const createAccount = async (accountData: UIAccountInputData): Promise<UIAccount | null> => {
        setIsLoading(true);
        setError(null);
        try {
            const serviceInput = mapUiInputToServiceInput(accountData, true);
            const response = await serviceCreateAccount(serviceInput); 
            const newUiAccount = mapServiceAccountToUiAccount(response.account);
            setAccounts(prev => [...prev, newUiAccount]);
            setIsLoading(false);
            return newUiAccount;
        } catch (err: any) {
            console.error("Error in createAccount:", err);
            setError(err.message || 'Failed to create account.');
            setIsLoading(false);
            return null;
        }
    };

    const updateAccount = async (accountId: string, accountData: UIAccountInputData): Promise<UIAccount | null> => {
        setIsLoading(true);
        setError(null);
        try {
            const serviceInput = mapUiInputToServiceInput(accountData, false);
            const response = await serviceUpdateAccount(accountId, serviceInput); 
            const updatedUiAccount = mapServiceAccountToUiAccount(response.account);
            setAccounts(prev => prev.map(acc => acc.id === accountId ? updatedUiAccount : acc));
            setIsLoading(false);
            return updatedUiAccount;
        } catch (err: any) {
            console.error("Error in updateAccount:", err);
            setError(err.message || 'Failed to update account.');
            setIsLoading(false);
            return null;
        }
    };

    const deleteAccount = async (accountId: string): Promise<boolean> => {
        setIsLoading(true);
        setError(null);
        try {
            await serviceDeleteAccount(accountId); 
            setAccounts(prev => prev.filter(acc => acc.id !== accountId));
            setIsLoading(false);
            return true;
        } catch (err: any) {
            console.error("Error in deleteAccount:", err);
            setError(err.message || 'Failed to delete account');
            setIsLoading(false);
            return false;
        }
    };

    useEffect(() => {
        fetchAccounts();
    }, [fetchAccounts]);

    return { accounts, isLoading, error, fetchAccounts, createAccount, updateAccount, deleteAccount, clearError };
};

export default useAccounts; 
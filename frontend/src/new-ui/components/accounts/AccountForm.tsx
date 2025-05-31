import React, { useState, useEffect } from 'react';
import './AccountForm.css'; // Import the CSS file
import { UIAccountInputData } from '../../hooks/useAccounts'; // Import updated type
// Import enums using a namespace import to potentially resolve linter issues
import * as AccountService from '../../../services/AccountService';

// This interface should exactly match AccountInputData from useAccounts.ts
export interface AccountFormData {
    name: string;
    type: string;
    accountNumber: string;
    openingBalance: number;
    currency: string;
    bankName?: string;
    // id is not part of input data for create/update via hook, it's handled separately
}

interface AccountFormProps {
    initialData?: UIAccountInputData | null;
    onSubmit: (formData: UIAccountInputData) => void;
    onCancel: () => void;
    formTitle: string;
}

// Helper to get enum keys for dropdowns
const getEnumKeys = (e: any) => Object.keys(e).filter(k => typeof e[k as any] === 'string'); // Filter by string values to get keys

const AccountForm: React.FC<AccountFormProps> = ({ initialData, onSubmit, onCancel, formTitle }) => {
    const [formData, setFormData] = useState<UIAccountInputData>({
        name: '',
        type: AccountService.AccountType.CHECKING, // Default using namespace import
        currency: AccountService.Currency.USD,   // Default using namespace import
        balance: undefined, // Balance is optional, and not set for new accounts via this form
        bankName: '',
        ...(initialData || {}),
    });

    useEffect(() => {
        if (initialData) {
            setFormData(prev => ({ 
                ...prev, // Keep defaults if not in initialData
                ...initialData,
                // Ensure balance is string if present, or undefined if field is removed/not for new
                balance: initialData.balance !== undefined ? initialData.balance : undefined 
            }));
        } else {
            // For new account
            setFormData({
                name: '',
                type: AccountService.AccountType.CHECKING,
                currency: AccountService.Currency.USD,
                balance: undefined, // No balance field for new accounts
                bankName: '',
            });
        }
    }, [initialData]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        // Create a copy of formData to pass, explicitly managing the optional balance
        const dataToSubmit: UIAccountInputData = {
            ...formData,
            // If balance field was entirely removed and not part of formData state for new accounts:
            // balance will be undefined. The hook defaults it to '0' for create operations.
            // If editing an account, and balance field is present but optional:
            // balance: formData.balance // will be string or undefined from state
        };
        // Since balance is removed from form for new accounts, formData.balance will be undefined.
        // If editing retains an optional balance field, this would pass it through.
        // For now, assuming `balance` is not a field in the form for add/edit.
        onSubmit(dataToSubmit);
    };

    // Use AccountService.AccountType and AccountService.Currency for options
    const accountTypeOptions = getEnumKeys(AccountService.AccountType);
    const currencyOptions = getEnumKeys(AccountService.Currency);

    return (
        <div className="account-form-modal">
            <div className="account-form-container">
                <h2>{formTitle}</h2>
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="name">Account Name</label>
                        <input type="text" id="name" name="name" value={formData.name} onChange={handleChange} required />
                    </div>
                    <div className="form-group">
                        <label htmlFor="type">Account Type</label>
                        <select id="type" name="type" value={formData.type} onChange={handleChange} required>
                            {accountTypeOptions.map(key => (
                                <option key={key} value={AccountService.AccountType[key as keyof typeof AccountService.AccountType]}>
                                    {key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' ')}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group">
                        <label htmlFor="currency">Currency</label>
                        <select id="currency" name="currency" value={formData.currency} onChange={handleChange} required>
                            {currencyOptions.map(key => (
                                <option key={key} value={AccountService.Currency[key as keyof typeof AccountService.Currency]}>
                                    {key} 
                                </option>
                            ))}
                        </select>
                    </div>
                    {/* Balance field removed as per request */}
                    {/* If balance needs to be editable for existing accounts, it would be added here */}
                    {/* <div className="form-group">
                        <label htmlFor="balance">Current Balance</label>
                        <input type="text" id="balance" name="balance" value={formData.balance || ''} onChange={handleChange} />
                    </div> */}
                    <div className="form-group">
                        <label htmlFor="bankName">Bank Name (Optional)</label>
                        <input type="text" id="bankName" name="bankName" value={formData.bankName || ''} onChange={handleChange} />
                    </div>
                    <div className="form-actions">
                        <button type="button" onClick={onCancel} className="cancel-button">Cancel</button>
                        <button type="submit" className="save-button">Save Account</button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AccountForm; 
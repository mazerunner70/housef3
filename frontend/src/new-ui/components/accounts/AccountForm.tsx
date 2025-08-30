import React, { useState, useEffect } from 'react';
import './AccountForm.css'; // Import the CSS file
import { UIAccountInputData } from '../../hooks/useAccounts'; // Import updated type
import { AccountType, Currency } from '../../../schemas/Account';

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
        type: AccountType.CHECKING,
        currency: Currency.USD,
        balance: undefined, // Balance is optional, and not set for new accounts via this form
        bankName: undefined, // Use undefined instead of empty string for optional field
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
                type: AccountType.CHECKING,
                currency: Currency.USD,
                balance: undefined, // No balance field for new accounts
                bankName: undefined,
            });
        }
    }, [initialData]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        // Create a copy of formData to pass, explicitly managing the optional fields
        const dataToSubmit: UIAccountInputData = {
            ...formData,
            // Convert empty string to undefined for optional bankName field
            bankName: formData.bankName?.trim() === '' ? undefined : formData.bankName,
        };
        onSubmit(dataToSubmit);
    };

    // Use AccountType and Currency for options
    const accountTypeOptions = getEnumKeys(AccountType);
    const currencyOptions = getEnumKeys(Currency);

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
                                <option key={key} value={AccountType[key as keyof typeof AccountType]}>
                                    {key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' ')}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group">
                        <label htmlFor="currency">Currency</label>
                        <select id="currency" name="currency" value={formData.currency} onChange={handleChange} required>
                            {currencyOptions.map(key => (
                                <option key={key} value={Currency[key as keyof typeof Currency]}>
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
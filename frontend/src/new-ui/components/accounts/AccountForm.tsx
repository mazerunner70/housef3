import React, { useState, useEffect } from 'react';
import './AccountForm.css'; // Import the CSS file
import { AccountCreate } from '../../../schemas/Account'; // Import updated type
import { AccountType, Currency } from '../../../schemas/Account';
import { Decimal } from 'decimal.js';

// Form now uses AccountCreate directly from schemas/Account.ts

interface AccountFormProps {
    initialData?: AccountCreate | null;
    onSubmit: (formData: AccountCreate) => void;
    onCancel: () => void;
    formTitle: string;
}

// Helper to get enum keys for dropdowns
const getEnumKeys = (e: any) => Object.keys(e).filter(k => typeof e[k as any] === 'string'); // Filter by string values to get keys

const AccountForm: React.FC<AccountFormProps> = ({ initialData, onSubmit, onCancel, formTitle }) => {
    const [formData, setFormData] = useState<AccountCreate>({
        accountName: '',
        accountType: AccountType.CHECKING,
        currency: Currency.USD,
        balance: new Decimal('0'), // Required field in AccountCreate
        institution: '', // Required field in AccountCreate
        ...(initialData || {}),
    });

    useEffect(() => {
        if (initialData) {
            setFormData((prev: AccountCreate) => ({
                ...prev, // Keep defaults if not in initialData
                ...initialData,
            }));
        } else {
            // For new account
            setFormData({
                accountName: '',
                accountType: AccountType.CHECKING,
                currency: Currency.USD,
                balance: new Decimal('0'),
                institution: '',
            });
        }
    }, [initialData]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData((prev: AccountCreate) => ({
            ...prev,
            [name]: name === 'balance' ? new Decimal(value || '0') : value
        }));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        // Create a copy of formData to pass, explicitly managing the optional fields
        const dataToSubmit: AccountCreate = {
            ...formData,
            // Convert empty string to undefined for optional institution field
            institution: formData.institution?.trim() === '' ? '' : formData.institution,
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
                        <label htmlFor="accountName">Account Name</label>
                        <input type="text" id="accountName" name="accountName" value={formData.accountName} onChange={handleChange} required />
                    </div>
                    <div className="form-group">
                        <label htmlFor="accountType">Account Type</label>
                        <select id="accountType" name="accountType" value={formData.accountType} onChange={handleChange} required>
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
                    <div className="form-group">
                        <label htmlFor="balance">Opening Balance</label>
                        <input type="number" id="balance" name="balance" value={formData.balance?.toString() || '0'} onChange={handleChange} step="0.01" required />
                    </div>
                    <div className="form-group">
                        <label htmlFor="institution">Bank Name</label>
                        <input type="text" id="institution" name="institution" value={formData.institution || ''} onChange={handleChange} required />
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
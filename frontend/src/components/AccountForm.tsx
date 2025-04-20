import React, { useState, useEffect } from 'react';
import { Account, AccountType, Currency } from '../services/AccountService';
import './AccountForm.css';

interface AccountFormProps {
  account?: Account;
  onSubmit: (accountData: Partial<Account>) => Promise<void>;
  onCancel: () => void;
}

const AccountForm: React.FC<AccountFormProps> = ({ account, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState<Partial<Account>>({
    accountName: '',
    accountType: AccountType.CHECKING,
    institution: '',
    balance: 0,
    currency: Currency.USD,
    notes: '',
    isActive: true
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (account) {
      setFormData({
        accountName: account.accountName,
        accountType: account.accountType,
        institution: account.institution,
        balance: account.balance,
        currency: account.currency,
        notes: account.notes,
        isActive: account.isActive,
        defaultFieldMapId: account.defaultFieldMapId
      });
    }
  }, [account]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.accountName || formData.accountName.length > 100) {
      newErrors.accountName = 'Account name is required and must be 100 characters or less';
    }

    if (!formData.institution || formData.institution.length > 100) {
      newErrors.institution = 'Institution name is required and must be 100 characters or less';
    }

    if (formData.notes && formData.notes.length > 1000) {
      newErrors.notes = 'Notes must be 1000 characters or less';
    }

    if (formData.balance === undefined || isNaN(formData.balance)) {
      newErrors.balance = 'Balance must be a valid number';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(formData);
    } catch (error) {
      console.error('Error submitting account:', error);
      setErrors({ submit: 'Failed to save account. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'balance' ? parseFloat(value) || 0 : value
    }));
  };

  return (
    <form className="account-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="accountName">Account Name</label>
        <input
          type="text"
          id="accountName"
          name="accountName"
          value={formData.accountName}
          onChange={handleChange}
          className={errors.accountName ? 'error' : ''}
        />
        {errors.accountName && <span className="error-message">{errors.accountName}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="accountType">Account Type</label>
        <select
          id="accountType"
          name="accountType"
          value={formData.accountType}
          onChange={handleChange}
        >
          {Object.values(AccountType).map(type => (
            <option key={type} value={type}>
              {type.replace('_', ' ').toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="institution">Institution</label>
        <input
          type="text"
          id="institution"
          name="institution"
          value={formData.institution}
          onChange={handleChange}
          className={errors.institution ? 'error' : ''}
        />
        {errors.institution && <span className="error-message">{errors.institution}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="balance">Balance</label>
        <input
          type="number"
          id="balance"
          name="balance"
          value={formData.balance}
          onChange={handleChange}
          step="0.01"
          className={errors.balance ? 'error' : ''}
        />
        {errors.balance && <span className="error-message">{errors.balance}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="currency">Currency</label>
        <select
          id="currency"
          name="currency"
          value={formData.currency}
          onChange={handleChange}
        >
          {Object.values(Currency).map(currency => (
            <option key={currency} value={currency}>
              {currency}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="notes">Notes</label>
        <textarea
          id="notes"
          name="notes"
          value={formData.notes || ''}
          onChange={handleChange}
          rows={3}
          className={errors.notes ? 'error' : ''}
        />
        {errors.notes && <span className="error-message">{errors.notes}</span>}
      </div>

      <div className="form-group checkbox">
        <label>
          <input
            type="checkbox"
            name="isActive"
            checked={formData.isActive}
            onChange={(e) => setFormData(prev => ({ ...prev, isActive: e.target.checked }))}
          />
          Active Account
        </label>
      </div>

      {errors.submit && <div className="error-message submit-error">{errors.submit}</div>}

      <div className="form-actions">
        <button type="button" onClick={onCancel} className="cancel-button">
          Cancel
        </button>
        <button type="submit" disabled={isSubmitting} className="submit-button">
          {isSubmitting ? 'Saving...' : account ? 'Update Account' : 'Create Account'}
        </button>
      </div>
    </form>
  );
};

export default AccountForm; 
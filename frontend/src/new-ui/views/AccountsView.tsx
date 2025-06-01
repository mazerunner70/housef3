import React, { useState, useEffect } from 'react';
import AccountList from '../components/accounts/AccountList';
import AccountForm from '../components/accounts/AccountForm';
import ConfirmationModal from '../components/accounts/ConfirmationModal';
import AccountDetailView from './AccountDetailView';
import './AccountsView.css';
import useAccounts, { UIAccount, UIAccountInputData } from '../hooks/useAccounts';
// import { Decimal } from 'decimal.js'; // Re-enable if using Decimal.js

// AccountFormData in AccountsView should match AccountInputData from the hook for create/update operations
// The main `Account` type from useAccounts will be used for the list display.

const AccountsView: React.FC = () => {
    const {
        accounts,
        isLoading,
        error,
        // fetchAccounts, // Fetched on mount by the hook
        createAccount,
        updateAccount,
        deleteAccount,
        clearError
    } = useAccounts();

    const [showAccountForm, setShowAccountForm] = useState(false);
    // editingAccount will store the full Account object for pre-filling form,
    // but we'll map it to AccountInputData before submitting for an update.
    const [editingAccount, setEditingAccount] = useState<UIAccount | null>(null);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deletingAccountId, setDeletingAccountId] = useState<string | null>(null);
    const [selectedAccount, setSelectedAccount] = useState<UIAccount | null>(null);

    const handleAddAccount = () => {
        setEditingAccount(null);
        setShowAccountForm(true);
        setSelectedAccount(null);
    };

    const handleEditAccount = (accountToEdit: UIAccount) => {
        setEditingAccount(accountToEdit);
        setShowAccountForm(true);
        setSelectedAccount(null);
    };

    const handleDeleteAccountRequest = (accountId: string) => {
        setDeletingAccountId(accountId);
        setShowDeleteModal(true);
        setSelectedAccount(null);
    };

    const handleViewAccountDetails = (accountId: string) => {
        const accountToView = accounts.find(acc => acc.id === accountId);
        if (accountToView) {
            setSelectedAccount(accountToView);
            setShowAccountForm(false);
            setEditingAccount(null);
        }
    };

    const handleCloseDetailView = () => {
        setSelectedAccount(null);
    };

    const handleFormSubmit = async (formDataFromForm: UIAccountInputData) => {
        clearError();
        let success = false;
        if (editingAccount && editingAccount.id) {
            const result = await updateAccount(editingAccount.id, formDataFromForm);
            if (result) success = true;
        } else {
            const result = await createAccount(formDataFromForm);
            if (result) success = true;
        }

        if (success) {
            setShowAccountForm(false);
            setEditingAccount(null);
            // accounts list is updated by the hook
        }
        // If not successful, error is set by the hook and will be displayed
    };

    const handleDeleteConfirm = async () => {
        if (deletingAccountId) {
            clearError();
            const success = await deleteAccount(deletingAccountId);
            if (success) {
                setShowDeleteModal(false);
                setDeletingAccountId(null);
                // accounts list is updated by the hook
            }
            // If not successful, error is set by the hook and will be displayed
        }
    };
    
    // Prepare initialData for AccountForm, mapping from Account to AccountInputData if editingAccount exists
    const getFormInitialData = (): UIAccountInputData | undefined => {
        if (!editingAccount) return undefined; // For new account, no initial data for form (defaults are in AccountForm)
        
        // For editing existing account:
        return {
            name: editingAccount.name,
            type: editingAccount.type, // This will be the string value, e.g., "checking"
            currency: editingAccount.currency, // This will be the string value, e.g., "USD"
            // balance is not set here as the field is removed from the form.
            // If editing allowed direct balance changes, it would be: 
            // balance: editingAccount.balance ? editingAccount.balance.toString() : undefined,
            bankName: editingAccount.bankName || '',
        };
    };

    if (selectedAccount) {
        return (
            <div className="accounts-view-container">
                <button onClick={handleCloseDetailView} className="back-button">Back to Accounts List</button>
                <AccountDetailView account={selectedAccount} />
            </div>
        );
    }

    return (
        <div className="accounts-view-container">
            <h1>My Accounts</h1>
            <button onClick={handleAddAccount} className="add-account-button">Add New Account</button>

            {isLoading && <p>Loading accounts...</p>}
            {error && <p style={{ color: 'red' }}>Error: {error} <button onClick={clearError}>Clear</button></p>}

            {!isLoading && !error && accounts && (
                <AccountList
                    accounts={accounts}
                    onEdit={handleEditAccount}
                    onDelete={handleDeleteAccountRequest}
                    onViewDetails={handleViewAccountDetails}
                />
            )}

            {showAccountForm && (
                <AccountForm
                    initialData={getFormInitialData()}
                    onSubmit={handleFormSubmit}
                    onCancel={() => {
                        setShowAccountForm(false);
                        setEditingAccount(null);
                        clearError();
                    }}
                    formTitle={editingAccount ? 'Edit Account' : 'Add New Account'}
                />
            )}

            {showDeleteModal && deletingAccountId && (
                <ConfirmationModal
                    isOpen={showDeleteModal}
                    title="Delete Account"
                    message={`Are you sure you want to delete account: ${accounts.find(acc=>acc.id === deletingAccountId)?.name || deletingAccountId}? This action cannot be undone.`}
                    onConfirm={handleDeleteConfirm}
                    onCancel={() => {
                        setShowDeleteModal(false);
                        clearError();
                    }}
                />
            )}
        </div>
    );
};

export default AccountsView; 
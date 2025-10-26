import React, { useState, useRef, useEffect } from 'react';
import AccountList, { AccountListRef } from '../components/AccountList';
import AccountForm from '../components/AccountForm';
import ConfirmationModal from '../components/ConfirmationModal';
import AccountTimeline from '../components/AccountTimeline';
import AccountDetailView from './AccountDetailView';
import TransactionFilesDialog from '../components/TransactionFilesDialog';
import './AccountsView.css';
import useAccountsWithStore from '@/components/domain/accounts/stores/useAccountsStore';
import { Account, AccountCreate } from '@/schemas/Account';

// AccountFormData in AccountsView should match AccountCreate from the hook for create/update operations
// The main `Account` type from schemas/Account.ts is used for the list display.

const AccountsView: React.FC = () => {
    const {
        accounts,
        isLoading,
        error,
        fetchAccounts, // Now we handle fetching at component level
        createAccount,
        updateAccount,
        deleteAccount,
        clearError
    } = useAccountsWithStore();

    const accountListRef = useRef<AccountListRef>(null);
    const [showAccountForm, setShowAccountForm] = useState(false);
    // editingAccount will store the full Account object for pre-filling form,
    // but we'll map it to AccountCreate before submitting for an update.
    const [editingAccount, setEditingAccount] = useState<Account | null>(null);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deletingAccountId, setDeletingAccountId] = useState<string | null>(null);
    const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
    const [showTransactionFilesDialog, setShowTransactionFilesDialog] = useState(false);
    const [transactionFilesAccountId, setTransactionFilesAccountId] = useState<string | null>(null);

    // Use ref to store fetchAccounts and prevent useEffect re-runs
    const fetchAccountsRef = useRef(fetchAccounts);
    fetchAccountsRef.current = fetchAccounts;

    // Fetch accounts on component mount with intelligent caching
    useEffect(() => {
        fetchAccountsRef.current();
    }, []); // Empty deps - only run once on mount

    const handleAddAccount = () => {
        setEditingAccount(null);
        setShowAccountForm(true);
        setSelectedAccount(null);
    };

    const handleEditAccount = (accountToEdit: Account) => {
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
        const accountToView = accounts.find(acc => acc.accountId === accountId);
        if (accountToView) {
            setSelectedAccount(accountToView);
            setShowAccountForm(false);
            setEditingAccount(null);
        }
    };

    const handleCloseDetailView = () => {
        setSelectedAccount(null);
    };

    const handleTimelineAccountClick = (accountId: string) => {
        accountListRef.current?.scrollToAccount(accountId);
    };

    const handleViewTransactions = (accountId: string) => {
        setTransactionFilesAccountId(accountId);
        setShowTransactionFilesDialog(true);
    };

    const handleCloseTransactionFilesDialog = () => {
        setShowTransactionFilesDialog(false);
        setTransactionFilesAccountId(null);
    };

    const handleFormSubmit = async (formDataFromForm: AccountCreate) => {
        clearError();
        let success = false;
        if (editingAccount?.accountId) {
            const result = await updateAccount(editingAccount.accountId, formDataFromForm);
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

    // Prepare initialData for AccountForm, mapping from Account to AccountCreate if editingAccount exists
    const getFormInitialData = (): AccountCreate | undefined => {
        if (!editingAccount) return undefined; // For new account, no initial data for form (defaults are in AccountForm)

        // For editing existing account:
        return {
            accountName: editingAccount.accountName,
            accountType: editingAccount.accountType,
            currency: editingAccount.currency,
            balance: editingAccount.balance,
            institution: editingAccount.institution,
            notes: editingAccount.notes,
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

            {isLoading && <p className="accounts-loading">Loading accounts...</p>}
            {error && (
                <div className="accounts-error-container">
                    <div className="error-content">
                        <div className="error-icon">⚠️</div>
                        <div className="error-details">
                            <h4>Unable to Load Accounts</h4>
                            <p>{error}</p>
                        </div>
                    </div>
                    <button onClick={clearError} className="clear-error-button">Dismiss</button>
                </div>
            )}

            {!isLoading && !error && accounts && (
                <div className="accounts-content">
                    <AccountTimeline
                        accounts={accounts}
                        onAccountClick={handleTimelineAccountClick}
                    />
                    <AccountList
                        ref={accountListRef}
                        accounts={accounts}
                        onEdit={handleEditAccount}
                        onDelete={handleDeleteAccountRequest}
                        onViewDetails={handleViewAccountDetails}
                        onViewTransactions={handleViewTransactions}
                    />
                </div>
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
                    message={`Are you sure you want to delete account: ${accounts.find(acc => acc.accountId === deletingAccountId)?.accountName || deletingAccountId}? This action cannot be undone.`}
                    onConfirm={handleDeleteConfirm}
                    onCancel={() => {
                        setShowDeleteModal(false);
                        clearError();
                    }}
                />
            )}

            {showTransactionFilesDialog && transactionFilesAccountId && (
                <TransactionFilesDialog
                    isOpen={showTransactionFilesDialog}
                    onClose={handleCloseTransactionFilesDialog}
                    accountId={transactionFilesAccountId}
                    accountName={accounts.find(acc => acc.accountId === transactionFilesAccountId)?.accountName || 'Unknown Account'}
                />
            )}
        </div>
    );
};

export default AccountsView; 
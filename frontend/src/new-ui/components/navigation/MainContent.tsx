import React from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import Breadcrumb from '@/new-ui/components/navigation/Breadcrumb';
import AccountListView from '@/new-ui/components/navigation/views/AccountListView';
import AccountDetailView from '@/new-ui/components/navigation/views/AccountDetailView';
import FileTransactionsView from '@/new-ui/components/navigation/views/FileTransactionsView';
import TransactionDetailView from '@/new-ui/components/navigation/views/TransactionDetailView';
import './MainContent.css';

const MainContent: React.FC = () => {
    const { currentView, selectedAccount, selectedFile, selectedTransaction } = useNavigationStore();

    const renderContent = () => {
        switch (currentView) {
            case 'account-list':
                return <AccountListView />;

            case 'account-detail':
                if (!selectedAccount) {
                    return <div className="error-state">No account selected</div>;
                }
                return <AccountDetailView account={selectedAccount} />;

            case 'file-transactions':
                if (!selectedAccount || !selectedFile) {
                    return <div className="error-state">No file selected</div>;
                }
                return <FileTransactionsView account={selectedAccount} file={selectedFile} />;

            case 'transaction-detail':
                if (!selectedTransaction) {
                    return <div className="error-state">No transaction selected</div>;
                }
                return (
                    <TransactionDetailView
                        transaction={selectedTransaction}
                        account={selectedAccount}
                        file={selectedFile}
                    />
                );

            default:
                return <div className="error-state">Unknown view: {currentView}</div>;
        }
    };

    return (
        <main className="main-content">
            <Breadcrumb />
            <div className="main-content-inner">
                {renderContent()}
            </div>
        </main>
    );
};

export default MainContent;

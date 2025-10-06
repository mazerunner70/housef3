import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useNavigationStore } from '@/stores/navigationStore';
import SidebarSection, { SidebarSectionData } from '@/components/navigation/SidebarSection';
import useAccountsWithStore from '@/stores/useAccountsStore';

interface AccountsSidebarContentProps {
    sidebarCollapsed: boolean;
}

const AccountsSidebarContent: React.FC<AccountsSidebarContentProps> = ({ sidebarCollapsed }) => {
    const location = useLocation();
    const {
        currentView,
        selectedAccount,
        selectedFile
    } = useNavigationStore();

    const { accounts } = useAccountsWithStore();

    // Generate sidebar sections based on current account navigation state
    const sections = useMemo((): SidebarSectionData[] => {
        // Route context for future use
        // const pathSegments = location.pathname.split('/').filter(Boolean);
        // const searchParams = new URLSearchParams(location.search);

        const sections: SidebarSectionData[] = [];

        // Always show accounts section
        sections.push({
            type: 'navigation',
            title: 'Accounts',
            items: accounts?.map(account => ({
                id: account.accountId,
                label: account.accountName,
                icon: getAccountIcon(account.accountType),
                active: selectedAccount?.accountId === account.accountId,
                onClick: () => {
                    window.location.href = `/accounts/${account.accountId}`;
                },
                metadata: {
                    balance: account.balance,
                    lastSync: account.lastTransactionDate
                }
            })) || [],
            collapsible: true,
            collapsed: false
        });

        // If an account is selected, show file actions (files would need to be fetched separately)
        if (selectedAccount) {
            sections.push({
                type: 'context',
                title: 'Account Actions',
                items: [
                    {
                        id: 'view-transactions',
                        label: 'View Transactions',
                        icon: '📊',
                        active: false,
                        onClick: () => {
                            window.location.href = `/transactions?account=${selectedAccount.accountId}`;
                        }
                    },
                    {
                        id: 'view-files',
                        label: 'View Files',
                        icon: '📄',
                        active: selectedFile?.fileId !== undefined,
                        onClick: () => {
                            window.location.href = `/files?account=${selectedAccount.accountId}`;
                        }
                    }
                ],
                collapsible: true,
                collapsed: false
            });
        }

        // Quick actions section
        sections.push({
            type: 'actions',
            title: 'Quick Actions',
            items: [
                {
                    id: 'add-account',
                    label: 'Add Account',
                    icon: '➕',
                    active: false,
                    onClick: () => {
                        alert('Add Account functionality to be implemented');
                    }
                },
                {
                    id: 'import-transactions',
                    label: 'Import Transactions',
                    icon: '📥',
                    active: false,
                    onClick: () => {
                        window.location.href = '/transactions?tab=imports';
                    }
                }
            ],
            collapsible: false
        });

        return sections;
    }, [location, currentView, selectedAccount, selectedFile, accounts]);

    return (
        <>
            {sections.map((section, index) => (
                <SidebarSection
                    key={`${section.type}-${index}`}
                    section={section}
                    sidebarCollapsed={sidebarCollapsed}
                />
            ))}
        </>
    );
};

// Helper function to get account icon
function getAccountIcon(accountType: string): string {
    switch (accountType?.toLowerCase()) {
        case 'checking':
            return '💳';
        case 'savings':
            return '💰';
        case 'credit':
        case 'credit_card':
            return '💳';
        case 'investment':
            return '📈';
        case 'retirement':
            return '🏦';
        case 'loan':
            return '🏠';
        default:
            return '🏦';
    }
}

export default AccountsSidebarContent;

import React from 'react';
import { useParams } from 'react-router-dom';
import { AccountFileUploadView } from '@/components/domain/accounts';

/**
 * AccountFileUploadPage - Page wrapper for account-specific file upload
 *
 * This is a thin routing wrapper that extracts the accountId from URL params
 * and passes it to the domain AccountFileUploadView component.
 */
const AccountFileUploadPage: React.FC = () => {
    const { accountId } = useParams<{ accountId: string }>();

    if (!accountId) {
        return <div>Account ID not provided</div>;
    }

    return <AccountFileUploadView accountId={accountId} />;
};

export default AccountFileUploadPage;


import React from 'react';
import { useParams } from 'react-router-dom';
import AccountFileUploadView from '@/new-ui/views/AccountFileUploadView';

/**
 * AccountFileUploadPage - Route-level container for account file upload
 * 
 * This page component handles:
 * - Route parameter extraction (accountId)
 * - Minimal logic - delegates to view component
 * - Navigation integration
 * 
 * Route: /import/account/:accountId
 */
const AccountFileUploadPage: React.FC = () => {
    const { accountId } = useParams<{ accountId: string }>();

    if (!accountId) {
        return (
            <div className="account-file-upload-error">
                <h1>Invalid Account</h1>
                <p>No account ID provided in the URL.</p>
            </div>
        );
    }

    return <AccountFileUploadView accountId={accountId} />;
};

export default AccountFileUploadPage;

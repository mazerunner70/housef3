import React from 'react';
import AssociatedFilesList from './AssociatedFilesList';
import UnlinkedFilesList from './UnlinkedFilesList';
import useAccountFiles from '@/components/domain/accounts/hooks/useAccountFiles';

interface AccountFilesTabProps {
  accountId: string;
}

const AccountFilesTab: React.FC<AccountFilesTabProps> = ({ accountId }) => {
  const {
    associatedFiles,
    unlinkedFiles,
    loading,
    error,
    linkFile,
    unlinkFile
  } = useAccountFiles(accountId);

  if (loading) return <p>Loading files...</p>;
  if (error) return <p>Error loading files: {error}</p>;

  return (
    <div className="account-files-tab">
      <h3>Associated Files</h3>
      <AssociatedFilesList
        files={associatedFiles}
        onUnlink={unlinkFile}
        accountId={accountId}
      />

      <h3>Available Unlinked Files</h3>
      <UnlinkedFilesList
        files={unlinkedFiles}
        onLink={(fileId: string) => linkFile(fileId, accountId)}
        accountId={accountId}
      />
    </div>
  );
};

export default AccountFilesTab; 
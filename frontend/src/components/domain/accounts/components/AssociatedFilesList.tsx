import React from 'react';
import { UIAssociatedFile } from '../hooks/useAccountFiles'; // Import the type

// Using UIAssociatedFile type from useAccountFiles hook

interface AssociatedFilesListProps {
  files: UIAssociatedFile[];
  onUnlink: (fileId: string) => void;
  accountId: string; // To know which account these are associated with
}

const AssociatedFilesList: React.FC<AssociatedFilesListProps> = ({ files, onUnlink, accountId }) => {

  const handleUnlink = (fileId: string) => {
    console.log(`Unlinking file ${fileId} from account ${accountId}`);
    onUnlink(fileId);
  };

  if (!files || files.length === 0) {
    return <p>No files currently associated with this account.</p>;
  }

  return (
    <div className="associated-files-list">
      <ul>
        {files.map((file) => (
          <li key={file.id}>
            <span>{file.name} ({file.uploadDate}) - Status: {file.status}, Transactions: {file.transactionCount}</span>
            <button onClick={() => handleUnlink(file.id)} className="unlink-button">Unlink</button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default AssociatedFilesList; 
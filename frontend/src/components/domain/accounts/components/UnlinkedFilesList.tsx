import React from 'react';
import { UIUnlinkedFile } from '../hooks/useAccountFiles'; // Import the type

// Using UIUnlinkedFile type from useAccountFiles hook

interface UnlinkedFilesListProps {
  files: UIUnlinkedFile[];
  onLink: (fileId: string) => void; // accountId is already known in the parent (AccountFilesTab)
  accountId: string; // To show which account it *would* be linked to if clicked
}

const UnlinkedFilesList: React.FC<UnlinkedFilesListProps> = ({ files, onLink, accountId }) => {

  const handleLink = (fileId: string) => {
    console.log(`Calling onLink for file ${fileId} to account ${accountId}`);
    onLink(fileId);
  };

  if (!files || files.length === 0) {
    return <p>No unlinked files available.</p>;
  }

  return (
    <div className="unlinked-files-list">
      <ul>
        {files.map((file) => (
          <li key={file.id}>
            <span>{file.name} ({file.uploadDate})</span>
            <button onClick={() => handleLink(file.id)}>Link to this Account</button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default UnlinkedFilesList; 
import React, { useState } from 'react';
import FileUpload from './FileUpload';
import FileList from './FileList';
import './FileManager.css';

const FileManager: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'upload' | 'list'>('list');
  const [refreshFileList, setRefreshFileList] = useState<boolean>(false);

  // Handle tab switching
  const handleTabChange = (tab: 'upload' | 'list') => {
    setActiveTab(tab);
  };

  // Handle file upload completion
  const handleUploadComplete = () => {
    // Trigger file list refresh
    setRefreshFileList(prev => !prev);
    // Switch to list tab
    setActiveTab('list');
  };

  // Handle file list refresh completion
  const handleRefreshComplete = () => {
    // Reset refresh trigger
    // No need to do anything here since we're using a boolean toggle
  };

  return (
    <div className="file-manager-container">
      <div className="file-manager-tabs">
        <button 
          className={`tab-button ${activeTab === 'list' ? 'active' : ''}`}
          onClick={() => handleTabChange('list')}
        >
          File List
        </button>
        <button 
          className={`tab-button ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => handleTabChange('upload')}
        >
          Upload File
        </button>
      </div>
      
      <div className="tab-content">
        {activeTab === 'upload' ? (
          <FileUpload onUploadComplete={handleUploadComplete} />
        ) : (
          <FileList 
            onRefreshNeeded={refreshFileList} 
            onRefreshComplete={handleRefreshComplete} 
          />
        )}
      </div>
    </div>
  );
};

export default FileManager; 
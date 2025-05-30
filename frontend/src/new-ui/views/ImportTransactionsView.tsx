import React, { useState, useCallback, useEffect } from 'react';
// Use AccountService for fetching accounts
import { listAccounts, Account as ServiceAccount } from '../../services/AccountService';
import { getUploadUrl, uploadFileToS3, listFiles, FileMetadata } from '../../services/FileService'; // Import getUploadUrl and uploadFileToS3
import { getCurrentUser } from '../../services/AuthService'; // Import getCurrentUser
import './ImportTransactionsView.css'; // Import the CSS file

// Define a local Account type for the component if its structure differs from ServiceAccount
// or if we want to add/omit properties for the view layer.
// For now, we will map ServiceAccount to this structure.
interface ViewAccount {
  id: string;    // Corresponds to accountId from ServiceAccount
  name: string;  // Corresponds to accountName from ServiceAccount
}

// Define your column mapping state structure for CSVs (will be used later)
interface CsvColumnMapping {
  [header: string]: 'date' | 'description' | 'amount' | 'payee' | 'notes' | 'skip';
}

const ImportTransactionsView: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [accounts, setAccounts] = useState<ViewAccount[]>([]); // Use local ViewAccount type
  const [currentFileId, setCurrentFileId] = useState<string | null>(null); // To store fileId after getting upload URL
  const [importHistory, setImportHistory] = useState<FileMetadata[]>([]); // State for import history
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false); // Separate loading for history
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Other state variables (importHistory, filePreviewData, etc.) are commented out for now
  // and will be re-introduced step-by-step.

  // Fetch accounts when the component mounts or currentStep becomes 1
  useEffect(() => {
    if (currentStep === 1) {
      setIsLoading(true);
      setIsLoadingHistory(true);
      setErrorMessage(null);

      Promise.all([
        listAccounts(),
        listFiles()
      ]).then(([accountsResponse, filesResponse]) => {
        // Map ServiceAccount to ViewAccount
        const viewAccounts = accountsResponse.accounts.map(acc => ({
          id: acc.accountId,
          name: acc.accountName,
        }));
        setAccounts(viewAccounts);

        // Sort files by uploadDate in descending order
        const sortedHistory = filesResponse.files.sort((a, b) => 
          new Date(b.uploadDate).getTime() - new Date(a.uploadDate).getTime()
        );
        setImportHistory(sortedHistory);

      }).catch(error => {
        console.error("Error fetching initial data for Step 1:", error);
        setErrorMessage(error.message || "Failed to load initial data. Please try again.");
      }).finally(() => {
        setIsLoading(false);
        setIsLoadingHistory(false);
      });
    }
  }, [currentStep]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
      setErrorMessage(null); 
      console.log("File selected:", event.target.files[0]);
    }
  };

  const handleFileDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      setSelectedFile(event.dataTransfer.files[0]);
      setErrorMessage(null);
      console.log("File dropped:", event.dataTransfer.files[0]);
    }
  }, []);

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  const proceedToStep2 = async () => {
    if (!selectedFile) {
      setErrorMessage('Please select a file to upload.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setCurrentFileId(null);

    try {
      const currentUser = getCurrentUser();
      if (!currentUser) {
        setErrorMessage("User not authenticated. Please log in.");
        setIsLoading(false);
        return;
      }

      console.log(`Step 1: Requesting upload URL for ${selectedFile.name}, account: ${selectedAccount || 'None'}`);
      // Step 1: Get the presigned URL
      const presignedData = await getUploadUrl(
        selectedFile.name,
        selectedFile.type,
        selectedFile.size,
        currentUser.id, // Pass userId
        selectedAccount || undefined // Pass selectedAccount if it exists, otherwise undefined
      );

      console.log("Received presigned data, fileId:", presignedData.fileId);
      setCurrentFileId(presignedData.fileId); // Store fileId

      // Step 2: Upload the file to S3
      console.log(`Step 2: Uploading ${selectedFile.name} to S3.`);
      await uploadFileToS3(
        presignedData,
        selectedFile,
        selectedAccount || undefined // Pass selectedAccount to S3 metadata if present
      );

      console.log("File upload to S3 successful:", selectedFile.name);
      alert(`File '${selectedFile.name}' uploaded successfully! File ID: ${presignedData.fileId}. Backend will process it. Next step would show preview/mapping if applicable.`);
      
      // TODO: Potentially refresh import history here or wait for a signal
      // For now, we will not automatically navigate to step 2.
      // User might want to upload multiple files or see it in history first.
      // setCurrentStep(2); 
      // setFilePreviewData(previewData); // This would be the next step

      // Reset file input for next upload
      setSelectedFile(null);
      // Optionally clear selected account or keep it for subsequent uploads
      // setSelectedAccount(''); 

    } catch (error: any) {
      console.error("Error during file upload process:", error);
      setErrorMessage(error.message || "Failed to upload file. Please try again.");
      setCurrentFileId(null);
    } finally {
      setIsLoading(false);
    }
  };
  
  const proceedToStep3 = async () => {
    alert("Proceed to Step 3 - Complete import logic to be implemented with real API call.");
    // Further logic for step 3 will be added later
  };

  const resetProcess = () => {
    setCurrentStep(1);
    setSelectedFile(null);
    setSelectedAccount('');
    setErrorMessage(null);
    // Resetting other states (filePreviewData, importResult, etc.) will be handled when they are re-introduced
  };

  if (isLoading && accounts.length === 0 && currentStep === 1) {
      return <div className="loading-overlay">Loading accounts...</div>;
  }

  // Simplified main loading check for now
  const showProcessingLoader = isLoading && currentStep !== 1;

  return (
    <div className="import-transactions-container">
      <h2>Import Transactions</h2>
      <p>Follow the steps below to import your transaction data.</p>

      {errorMessage && (
          <div className="error-message-container">{errorMessage}</div>
      )}

      {showProcessingLoader && <div className="loading-overlay">Processing...</div>}

      {currentStep === 1 && (
        <div className="step-container">
          <h3 className="import-header">Step 1: File Upload & Account Selection</h3>
          
          <label htmlFor="account-select" className="label-common">Select Account:</label>
          <select 
            id="account-select"
            value={selectedAccount} 
            onChange={e => setSelectedAccount(e.target.value)} 
            className="select-common"
            disabled={accounts.length === 0 && !isLoading} 
          >
            <option value="">{isLoading && accounts.length === 0 ? "Loading accounts..." : accounts.length === 0 ? "No accounts found" : "-- Select an Account --"}</option>
            {accounts.map(acc => <option key={acc.id} value={acc.id}>{acc.name}</option>)}
          </select>

          <label className="label-common">Upload Transaction File (OFX, QFX, CSV):</label>
          <div 
            onDrop={handleFileDrop} 
            onDragOver={handleDragOver} 
            onClick={() => document.getElementById('fileInput')?.click()} 
            className="drop-zone"
          >
            {selectedFile ? `Selected: ${selectedFile.name}` : 'Drag & drop your file here, or click to select.'}
            <input 
              id="fileInput" 
              type="file" 
              onChange={handleFileChange} 
              accept=".ofx,.qfx,.csv" 
              style={{ display: 'none' }} 
            />
          </div>
          {selectedFile && <p>File to upload: <strong>{selectedFile.name}</strong> ({Math.round(selectedFile.size / 1024)} KB)</p>}

          <button 
            onClick={proceedToStep2} 
            disabled={!selectedFile || isLoading || isLoadingHistory}
            className="button-common button-primary"
          >
            {(isLoading || isLoadingHistory) && currentStep === 1 ? 'Loading Data...' : 'Next: Preview & Map'}
          </button>

          <div style={{marginTop: '30px'}}>
            <h4 className="import-header">Import History</h4>
            {isLoadingHistory && <p>Loading history...</p>}
            {!isLoadingHistory && importHistory.length === 0 && <p>No import history found.</p>}
            {importHistory.length > 0 && (
              <table className="history-table">
                <thead>
                  <tr>
                    <th className="history-th-td">File Name</th>
                    <th className="history-th-td">Account</th>
                    <th className="history-th-td">Upload Date</th>
                    <th className="history-th-td">Status</th>
                    <th className="history-th-td">Format</th>
                    <th className="history-th-td">Size (KB)</th>
                    {/* Add more columns as needed, e.g., Transaction Count */}
                  </tr>
                </thead>
                <tbody>
                  {importHistory.map(file => (
                    <tr key={file.fileId}>
                      <td className="history-th-td">{file.fileName}</td>
                      <td className="history-th-td">{file.accountName || 'N/A'}</td>
                      <td className="history-th-td">{new Date(file.uploadDate).toLocaleDateString()}</td>
                      <td className="history-th-td">{file.processingStatus || 'N/A'}</td>
                      <td className="history-th-td">{file.fileFormat || 'N/A'}</td>
                      <td className="history-th-td">{(file.fileSize / 1024).toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {currentStep === 2 && (
        <div className="step-container">
            <h3 className="import-header">Step 2: Preview, Mapping (CSV), & Confirmation</h3>
            <p><i>Transaction preview and CSV mapping will appear here.</i></p>
            <button onClick={() => setCurrentStep(1)} className="button-common" disabled={isLoading}>Back</button>
            <button onClick={proceedToStep3} className="button-common button-primary" disabled={isLoading}>
                {isLoading ? 'Importing...' : 'Complete Import'}
            </button>
        </div>
      )}

      {currentStep === 3 && (
        <div className="step-container">
            <h3 className="import-header">Step 3: Completion Summary</h3>
            <p><i>Import results will be displayed here.</i></p>
            <button onClick={resetProcess} className="button-common button-primary" style={{ display: 'block', margin: '20px auto 0'}}>
                Import Another File
            </button>
        </div>
      )}
    </div>
  );
};

export default ImportTransactionsView; 
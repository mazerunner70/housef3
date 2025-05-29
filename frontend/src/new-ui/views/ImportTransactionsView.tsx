import React, { useState, useCallback, useEffect } from 'react';
// Use AccountService for fetching accounts
import { listAccounts, Account as ServiceAccount } from '../../services/AccountService';
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
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Other state variables (importHistory, filePreviewData, etc.) are commented out for now
  // and will be re-introduced step-by-step.

  // Fetch accounts when the component mounts or currentStep becomes 1
  useEffect(() => {
    if (currentStep === 1) {
      setIsLoading(true);
      setErrorMessage(null);
      listAccounts()
        .then((response) => {
          // Map ServiceAccount to ViewAccount
          const viewAccounts = response.accounts.map(acc => ({
            id: acc.accountId,
            name: acc.accountName,
          }));
          setAccounts(viewAccounts);
        })
        .catch(error => {
          console.error("Error fetching accounts:", error);
          setErrorMessage(error.message || "Failed to load accounts. Please try again.");
        })
        .finally(() => setIsLoading(false));
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
    // This check is slightly redundant if button is disabled without a file, but good for robustness
    if (!selectedFile) {
      setErrorMessage('Please select a file to upload.');
      return;
    }
    
    // Account selection check removed for now, will be handled later.

    // If all checks pass (currently just file selection), clear previous error messages
    setErrorMessage(null);

    // Placeholder for actual Step 2 logic (e.g., API call for preview)
    // When account association is added back, selectedAccount will be needed here.
    console.log(`Proceeding to step 2 with file: ${selectedFile.name}. Account association will be handled later.`);
    alert(`Simulating processing for: ${selectedFile.name}. Account association will be handled later. Next step would show preview/mapping.`);
    // setIsLoading(true); 
    // try {
    //   // const previewData = await uploadFileForPreview(selectedFile, /* selectedAccount will be needed */);
    //   // setFilePreviewData(previewData);
    //   // setCurrentStep(2);
    // } catch (error: any) {
    //   setErrorMessage(error.message || "Failed to process file.");
    // } finally {
    //   setIsLoading(false);
    // }
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

  return (
    <div className="import-transactions-container">
      <h2>Import Transactions</h2>
      <p>Follow the steps below to import your transaction data.</p>

      {errorMessage && (
          <div className="error-message-container">{errorMessage}</div>
      )}

      {isLoading && currentStep !== 1 && <div className="loading-overlay">Processing...</div>}

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
            <option value="">{isLoading ? "Loading accounts..." : accounts.length === 0 ? "No accounts found" : "-- Select an Account --"}</option>
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
            disabled={!selectedFile || isLoading}
            className="button-common button-primary"
          >
            {isLoading ? 'Processing...' : 'Next: Preview & Map'}
          </button>

          <div style={{marginTop: '30px'}}>
            <h4 className="import-header">Import History & Saved Mappings</h4>
            <p><i>Import history will be displayed here.</i></p>
            {/* Import history table will be re-instated later */}
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
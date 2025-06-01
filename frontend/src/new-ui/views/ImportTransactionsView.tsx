import React, { useState, useCallback, useEffect } from 'react';
// Use AccountService for fetching accounts
import { listAccounts, Account as ServiceAccount } from '../../services/AccountService';
import { getUploadUrl, uploadFileToS3, listFiles, FileMetadata, deleteFile, parseFile } from '../../services/FileService'; // Added parseFile
import { listFieldMaps, FieldMap, getFieldMap } from '../../services/FileMapService'; // Import getFieldMap
import { getCurrentUser } from '../../services/AuthService'; // Import getCurrentUser
import ImportStep2Preview from '../components/ImportStep2Preview'; // Import the new component
import type { TransactionRow, ColumnMapping } from '../components/ImportStep2Preview'; // Import types
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
  [header: string]: 'date' | 'description' | 'amount' | 'debitOrCredit' | 'currency' | 'skip';
}

// Define target transaction fields for mapping
const TARGET_TRANSACTION_FIELDS = [
  { field: 'date', label: 'Date', regex: '^\\d{4}-\\d{2}-\\d{2}$|^\\d{2}/\\d{2}/\\d{4}$' },
  { field: 'description', label: 'Description', regex: '.+' },
  { field: 'amount', label: 'Amount', regex: '^-?([0-9]{1,3}(,[0-9]{3})*(\\.[0-9]+)?|[0-9]+(\\.[0-9]+)?)$' },
  { field: 'debitOrCredit', label: 'Type (Debit/Credit)', regex: '.+' },
  { field: 'currency', label: 'Currency', regex: '^[A-Z]{3}$' },
];

const ImportTransactionsView: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [accounts, setAccounts] = useState<ViewAccount[]>([]); // Use local ViewAccount type
  const [currentFileId, setCurrentFileId] = useState<string | null>(null); // To store fileId after getting upload URL
  const [importHistory, setImportHistory] = useState<FileMetadata[]>([]); // State for import history
  const [selectedHistoryFileId, setSelectedHistoryFileId] = useState<string | null>(null); // State for selected history file
  const [fieldMapsData, setFieldMapsData] = useState<Record<string, string>>({}); // State for field maps (ID -> Name)
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false); // Separate loading for history
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // State for Step 2
  const [parsedTransactionData, setParsedTransactionData] = useState<TransactionRow[]>([]);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [fileTypeForStep2, setFileTypeForStep2] = useState<'csv' | 'ofx' | 'qfx'>('csv');
  const [existingMappingsForStep2, setExistingMappingsForStep2] = useState<ColumnMapping[] | undefined>(undefined); // Re-introduced

  // Fetch accounts and history when the component mounts or currentStep becomes 1
  const fetchInitialData = useCallback(async () => {
    setIsLoading(true);
    setIsLoadingHistory(true);
    setErrorMessage(null);
    setSelectedHistoryFileId(null); // Reset selection when refetching

    try {
      const [accountsResponse, filesResponse, fieldMapsResponse] = await Promise.all([
        listAccounts(),
        listFiles(),
        listFieldMaps()
      ]);

      const viewAccounts = accountsResponse.accounts.map(acc => ({
        id: acc.accountId,
        name: acc.accountName,
      }));
      setAccounts(viewAccounts);

      const sortedHistory = filesResponse.files.sort((a, b) =>
        new Date(b.uploadDate).getTime() - new Date(a.uploadDate).getTime()
      );
      setImportHistory(sortedHistory);

      const mapsData: Record<string, string> = {};
      fieldMapsResponse.fieldMaps.forEach(fm => {
        // Guard against undefined fileMapId if it can be optional in FieldMap type
        if (fm.fileMapId) {
          mapsData[fm.fileMapId] = fm.name;
        }
      });
      setFieldMapsData(mapsData);

    } catch (error: any) {
      console.error("Error fetching initial data for Step 1:", error);
      setErrorMessage(error.message || "Failed to load initial data. Please try again.");
    } finally {
      setIsLoading(false);
      setIsLoadingHistory(false);
    }
  }, []); 

  useEffect(() => {
    if (currentStep === 1) {
      fetchInitialData();
      // Reset Step 2 specific states
      setParsedTransactionData([]);
      setCsvHeaders([]);
      setFileTypeForStep2('csv');
      setCurrentFileId(null);
      setExistingMappingsForStep2(undefined); // Reset this too
    }
  }, [currentStep, fetchInitialData]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
      setErrorMessage(null);
      setSelectedHistoryFileId(null); // Clear history selection
      console.log("File selected:", event.target.files[0]);
    }
  };

  const handleFileDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      setSelectedFile(event.dataTransfer.files[0]);
      setErrorMessage(null);
      setSelectedHistoryFileId(null); // Clear history selection when new file is dropped
      console.log("File dropped:", event.dataTransfer.files[0]);
    }
  }, []);

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  const handleHistoryRowClick = (fileId: string) => {
    setSelectedHistoryFileId(prev => (prev === fileId ? null : fileId));
    setSelectedFile(null); // Clear new file selection when history item is clicked
    setErrorMessage(null);
  };

  const handleDeleteHistoryFile = async () => {
    if (!selectedHistoryFileId) {
      setErrorMessage("No file selected from history to delete.");
      return;
    }

    const fileToDelete = importHistory.find(f => f.fileId === selectedHistoryFileId);
    if (!fileToDelete) {
      setErrorMessage("Selected file not found in history.");
      return;
    }

    if (window.confirm(`Are you sure you want to delete "${fileToDelete.fileName}"? This action cannot be undone.`)) {
      setIsLoadingHistory(true); // Use history loader for this action
      setErrorMessage(null);
      try {
        await deleteFile(selectedHistoryFileId);
        alert(`File "${fileToDelete.fileName}" deleted successfully.`);
        setSelectedHistoryFileId(null);
        // Refresh history
        await fetchInitialData(); // Re-fetch all initial data which includes history
      } catch (error: any) {
        console.error("Error deleting file:", error);
        setErrorMessage(error.message || `Failed to delete file "${fileToDelete.fileName}". Please try again.`);
      } finally {
        setIsLoadingHistory(false);
      }
    }
  };
  
  const handleProceedWithSelectedHistoryFile = async () => {
    if (!selectedHistoryFileId) {
      alert("Please select a file from the history to proceed.");
      return;
    }

    const historyFileMeta = importHistory.find(f => f.fileId === selectedHistoryFileId);
    if (!historyFileMeta) {
      setErrorMessage("Selected history file metadata not found.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setCurrentFileId(selectedHistoryFileId);

    try {
      console.log(`Parsing history file with ID: ${selectedHistoryFileId}`);
      const parseResult = await parseFile(selectedHistoryFileId);

      if (parseResult.error) {
        setErrorMessage(`Error parsing file: ${parseResult.error}`);
        setIsLoading(false);
        return;
      }

      const rawFileFormat = historyFileMeta.fileFormat?.toLowerCase() || parseResult.file_format || 'csv';
       if (rawFileFormat === 'csv' || rawFileFormat === 'ofx' || rawFileFormat === 'qfx') {
            setFileTypeForStep2(rawFileFormat as 'csv' | 'ofx' | 'qfx');
        } else {
            setErrorMessage(`Cannot process history file: unsupported or unknown format (${rawFileFormat})`);
            setIsLoading(false);
            return;
        }

      if (fileTypeForStep2 === 'csv') {
        if (!parseResult.headers || !parseResult.data) {
          setErrorMessage("CSV parsing did not return headers or data.");
          setIsLoading(false);
          return;
        }
        setCsvHeaders(parseResult.headers);
        const transactions = parseResult.data.map((item: any, index: number) => ({ id: item.id || `csv-hist-${index}`, ...item }));
        setParsedTransactionData(transactions);
      } else { // OFX, QFX
         if (!parseResult.data) {
          setErrorMessage(`${fileTypeForStep2.toUpperCase()} parsing did not return data.`);
          setIsLoading(false);
          return;
        }
        const transactions = parseResult.data.map((item: any, index: number) => ({ id: item.id || `parsed-hist-${index}`, ...item }));
        setParsedTransactionData(transactions);
        setCsvHeaders([]); 
      }

      // Fetch existing mapping if fileMapId exists
      if (historyFileMeta.fieldMap?.fileMapId) {
        console.log("Fetching existing mapping for ID:", historyFileMeta.fieldMap.fileMapId);
        try {
          const map = await getFieldMap(historyFileMeta.fieldMap.fileMapId);
          if (map && map.mappings) {
            const loadedMappings = map.mappings.map((m: any) => ({ 
              csvColumn: m.sourceField, 
              targetField: m.targetField, 
              isValid: undefined // Let ImportStep2Preview validate initially
            }));
            setExistingMappingsForStep2(loadedMappings);
            console.log("Loaded existing mappings:", loadedMappings);
          }
        } catch (mapError: any) {
          console.error("Error fetching existing field map:", mapError);
          setErrorMessage("Could not load saved mapping for this file. Proceeding without it.");
          setExistingMappingsForStep2(undefined); // Ensure it's undefined on error
        }
      } else {
        setExistingMappingsForStep2(undefined); // No map ID, so no existing map
      }
      
      console.log("History file processed, proceeding to Step 2 (Preview/Mapping)");
      setCurrentStep(2);

    } catch (error: any) {
      console.error("Error processing history file:", error);
      setErrorMessage(error.message || "Failed to process history file. Please try again.");
      setCurrentFileId(null); 
    } finally {
      setIsLoading(false);
    }
  };

  const proceedToStep2 = async () => {
    if (!selectedFile) { // Simplified: only handles new file upload for now
      setErrorMessage('Please select a file to upload.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    // setCurrentFileId(null); // currentFileId will be set after successful upload

    try {
      const currentUser = getCurrentUser();
      if (!currentUser) {
        setErrorMessage("User not authenticated. Please log in.");
        setIsLoading(false);
        return;
      }

      console.log(`Step 1: Requesting upload URL for ${selectedFile.name}, account: ${selectedAccount || 'None'}`);
      const presignedData = await getUploadUrl(
        selectedFile.name,
        selectedFile.type,
        selectedFile.size,
        currentUser.id, 
        selectedAccount || undefined
      );

      console.log("Received presigned data, fileId:", presignedData.fileId);
      const newFileId = presignedData.fileId; // Use a new const for clarity
      setCurrentFileId(newFileId); 

      console.log(`Step 2: Uploading ${selectedFile.name} to S3.`);
      await uploadFileToS3(presignedData, selectedFile, selectedAccount || undefined);
      console.log("File upload to S3 successful:", selectedFile.name);
      
      // Step 3: Parse the uploaded file
      console.log(`Parsing file with ID: ${newFileId}`);
      const parseResult = await parseFile(newFileId); // Call new parseFile service

      if (parseResult.error) {
        setErrorMessage(`Error parsing file: ${parseResult.error}`);
        setIsLoading(false);
        return;
      }
      
      const determinedFileType = parseResult.file_format || 'csv'; // Default to csv if not returned
      setFileTypeForStep2(determinedFileType);

      if (determinedFileType === 'csv') {
        if (!parseResult.headers || !parseResult.data) {
          setErrorMessage("CSV parsing did not return headers or data.");
          setIsLoading(false);
          return;
        }
        setCsvHeaders(parseResult.headers);
        const transactions = parseResult.data.map((item: any, index: number) => ({ id: item.id || `csv-${index}`, ...item }));
        setParsedTransactionData(transactions);
      } else { // OFX, QFX
         if (!parseResult.data) {
          setErrorMessage(`${determinedFileType.toUpperCase()} parsing did not return data.`);
          setIsLoading(false);
          return;
        }
        const transactions = parseResult.data.map((item: any, index: number) => ({ id: item.id || `parsed-${index}`, ...item }));
        setParsedTransactionData(transactions);
        setCsvHeaders([]); 
      }
      
      setExistingMappingsForStep2(undefined); // No existing mapping for new uploads initially
      console.log("File parsed, proceeding to Step 2 (Preview/Mapping)");
      setCurrentStep(2);
      // setSelectedFile(null); // Reset selected file after processing for Step 2

    } catch (error: any) {
      console.error("Error during file upload and parse process:", error);
      setErrorMessage(error.message || "Failed to process file. Please try again.");
      setCurrentFileId(null); 
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompleteImportStep2 = async (mappedData: TransactionRow[], mappingConfig?: ColumnMapping[]) => {
    console.log("Step 2 Complete. Data to import:", mappedData);
    if (mappingConfig) {
        console.log("Mapping configuration received (deferring save):", mappingConfig);
        // Placeholder for future: await saveFieldMap(mappingConfig, currentFileId, selectedAccount || undefined);
        // alert("Mapping would be saved here.");
    }
    
    setIsLoading(true);
    console.log("Simulating final import API call with mapped data...");
    await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
    setIsLoading(false);
    console.log("Simulated final import successful.");
    
    // Reset relevant states after successful import and before going to step 3
    setSelectedFile(null); 
    // Optionally clear selectedAccount or other relevant states from step 1 / 2
    // setCurrentFileId(null); // currentFileId might be needed for step 3 summary or can be cleared
    
    proceedToStep3();
  };

  const handleCancelStep2 = () => {
    console.log("Step 2 Cancelled. Returning to Step 1.");
    setCurrentStep(1); 
    // States like selectedFile, selectedAccount are reset by useEffect for currentStep === 1
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
            {(isLoading && currentStep === 1 && !isLoadingHistory && selectedFile) ? 'Uploading & Parsing...' : (isLoadingHistory && currentStep === 1) ? 'Loading Data...' : 'Upload & Continue'}
          </button>

          <div style={{marginTop: '30px'}}>
            <h4 className="import-header">Import History</h4>
            {isLoadingHistory && <p>Loading history...</p>}
            {!isLoadingHistory && importHistory.length === 0 && <p>No import history found.</p>}
            {importHistory.length > 0 && (
              <>
                <table className="history-table">
                  <thead>
                    <tr>
                      <th className="history-th-td">File Name</th>
                      <th className="history-th-td">Account</th>
                      <th className="history-th-td">Upload Date</th>
                      <th className="history-th-td">Mapping</th>
                      <th className="history-th-td">Format</th>
                      <th className="history-th-td">Size (KB)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importHistory.map(file => (
                      <tr 
                        key={file.fileId} 
                        onClick={() => handleHistoryRowClick(file.fileId)}
                        className={selectedHistoryFileId === file.fileId ? 'selected-row' : ''}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="history-th-td">{file.fileName}</td>
                        <td className="history-th-td">{file.accountName || 'N/A'}</td>
                        <td className="history-th-td">{new Date(file.uploadDate).toLocaleDateString()}</td>
                        <td className="history-th-td">
                          {file.fieldMap?.fileMapId && fieldMapsData[file.fieldMap.fileMapId] 
                            ? fieldMapsData[file.fieldMap.fileMapId] 
                            : file.fieldMap?.name || '--'}
                        </td>
                        <td className="history-th-td">{file.fileFormat || 'N/A'}</td>
                        <td className="history-th-td">{(file.fileSize / 1024).toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div style={{ marginTop: '10px' }}>
                  <button
                    onClick={handleProceedWithSelectedHistoryFile} // This now triggers full Step 2 logic
                    disabled={!selectedHistoryFileId || isLoading || isLoadingHistory}
                    className="button-common button-primary"
                    style={{ marginRight: '10px' }}
                  >
                    {(isLoading && selectedHistoryFileId) ? 'Processing...' : 'Next (Selected History)'}
                  </button>
                  <button
                    onClick={handleDeleteHistoryFile}
                    disabled={!selectedHistoryFileId || isLoadingHistory}
                    className="button-common button-danger"
                  >
                    Delete Selected
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {currentStep === 2 && currentFileId && (
        <ImportStep2Preview
          parsedData={parsedTransactionData}
          fileType={fileTypeForStep2}
          csvHeaders={csvHeaders}
          existingMapping={existingMappingsForStep2} // Pass existingMappingsForStep2
          onCompleteImport={handleCompleteImportStep2}
          onCancel={handleCancelStep2}
          targetTransactionFields={TARGET_TRANSACTION_FIELDS}
        />
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
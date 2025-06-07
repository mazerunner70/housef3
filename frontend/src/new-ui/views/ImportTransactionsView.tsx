import React, { useState, useCallback, useEffect } from 'react';
// Use AccountService for fetching accounts
import { listAccounts, Account as ServiceAccount } from '../../services/AccountService';
import { getUploadUrl, uploadFileToS3, listFiles, FileMetadata, deleteFile, parseFile, updateFileFieldMapAssociation, getProcessedFileMetadata, FileProcessResult, updateFileBalance } from '../../services/FileService'; // Added parseFile and updateFileBalance
import { listFieldMaps, getFieldMap, createFieldMap, updateFieldMap, FieldMap } from '../../services/FileMapService'; // Import more from FileMapService
import { getCurrentUser } from '../../services/AuthService'; // Import getCurrentUser
import ImportStep2Preview from '../components/ImportStep2Preview'; // Import the new component
import type { TransactionRow, ColumnMapping } from '../components/ImportStep2Preview'; // Import types
import './ImportTransactionsView.css'; // Import the CSS file
import ImportCompletionView from './ImportCompletionView'; // Import the new component

// Define TARGET_TRANSACTION_FIELDS (should match what ImportStep2Preview expects)
const TARGET_TRANSACTION_FIELDS = [
  { field: 'date', label: 'Transaction Date', regex: '^\\d{4}-\\d{2}-\\d{2}$' }, // YYYY-MM-DD
  { field: 'description', label: 'Description', regex: '.+' }, // Any non-empty string
  { field: 'amount', label: 'Amount', regex: '^-?(\\d+|\\d{1,3}(,\\d{3})*)(\\.\\d+)?$' }, // Number, allows commas, optional negative/decimal
  { field: 'debitOrCredit', label: 'Debit/Credit', regex: '^(debit|credit|CRDT|DBIT|DR|CR)$' }, // Specific values
  { field: 'currency', label: 'Currency', regex: '^[A-Z]{3}$' }, // 3 uppercase letters
];

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

// Type for available field maps in dropdown
interface AvailableMapInfo {
  id: string;
  name: string;
}

interface ImportResultForView {
  success: boolean;
  message?: string;
  transactionCount?: number;
  fileName?: string;
  accountName?: string;
  errorDetails?: string;
}

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

  // New state for named field map management
  const [availableFieldMaps, setAvailableFieldMaps] = useState<AvailableMapInfo[]>([]);
  const [currentlyLoadedFieldMapDetails, setCurrentlyLoadedFieldMapDetails] = useState<ColumnMapping[] | undefined>(undefined);
  const [initialFieldMapForStep2, setInitialFieldMapForStep2] = useState<{id: string, name: string} | undefined>(undefined);
  const [isLoadingFieldMaps, setIsLoadingFieldMaps] = useState<boolean>(false);

  // New state for default mapping dropdown
  const [selectedDefaultMapping, setSelectedDefaultMapping] = useState<string>('');
  const [defaultMappingName, setDefaultMappingName] = useState<string>('');
  const [isLoadingDefaultMapping, setIsLoadingDefaultMapping] = useState<boolean>(false);

  // New state for import results
  const [importResult, setImportResult] = useState<ImportResultForView | null>(null);

  // State for inline editing of opening balance
  const [editingFileId, setEditingFileId] = useState<string | null>(null);
  const [editingOpeningBalance, setEditingOpeningBalance] = useState<string>('');

  // Fetch accounts and history when the component mounts or currentStep becomes 1
  const fetchInitialData = useCallback(async () => {
    setIsLoading(true);
    setIsLoadingHistory(true);
    setIsLoadingFieldMaps(true); // For named maps
    setErrorMessage(null);
    setSelectedHistoryFileId(null); // Reset selection when refetching

    try {
      const [accountsResponse, filesResponse, fieldMapsListResponse] = await Promise.all([
        listAccounts(),
        listFiles(),
        listFieldMaps() // Fetch available field maps
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
      fieldMapsListResponse.fieldMaps.forEach(fm => {
        // Guard against undefined fileMapId if it can be optional in FieldMap type
        if (fm.fileMapId) {
          mapsData[fm.fileMapId] = fm.name;
        }
      });
      setFieldMapsData(mapsData);

      // Populate availableFieldMaps for the dropdown
      const mapsForDropdown = fieldMapsListResponse.fieldMaps.map(fm => ({
        id: fm.fileMapId!, // Assuming fileMapId is always present for listed maps
        name: fm.name,
      }));
      setAvailableFieldMaps(mapsForDropdown);
      console.log("[ImportTransactionsView] Fetched available field maps:", mapsForDropdown);

    } catch (error: any) {
      console.error("Error fetching initial data for Step 1:", error);
      setErrorMessage(error.message || "Failed to load initial data. Please try again.");
    } finally {
      setIsLoading(false);
      setIsLoadingHistory(false);
      setIsLoadingFieldMaps(false);
    }
  }, []); 

  const fetchDefaultMapping = async (accountId: string) => {
    try {
      setIsLoadingDefaultMapping(true);
      setDefaultMappingName('');
      setSelectedDefaultMapping('');
      
      // Get the account details to retrieve the defaultFieldMapId
      const response = await listAccounts();
      const account = response.accounts.find(acc => acc.accountId === accountId);
      
      if (account && account.defaultFieldMapId) {
        // Fetch the field map details
        const fieldMap = await getFieldMap(account.defaultFieldMapId);
        setDefaultMappingName(fieldMap.name);
        setSelectedDefaultMapping(account.defaultFieldMapId);
      } else {
        setDefaultMappingName('');
        setSelectedDefaultMapping('');
      }
    } catch (error) {
      console.error('Failed to fetch default mapping:', error);
      setDefaultMappingName('');
      setSelectedDefaultMapping('');
    } finally {
      setIsLoadingDefaultMapping(false);
    }
  };

  useEffect(() => {
    if (currentStep === 1) {
      fetchInitialData();
      // Reset Step 2 specific states
      setParsedTransactionData([]);
      setCsvHeaders([]);
      setFileTypeForStep2('csv');
      setCurrentFileId(null);
      setExistingMappingsForStep2(undefined); // Reset this too
      setCurrentlyLoadedFieldMapDetails(undefined); // Reset loaded map details
      setInitialFieldMapForStep2(undefined); // Reset initial map to load
    }
  }, [currentStep, fetchInitialData]);

  // Effect to fetch default mapping when account is selected
  useEffect(() => {
    if (selectedAccount) {
      fetchDefaultMapping(selectedAccount);
    } else {
      setDefaultMappingName('');
      setSelectedDefaultMapping('');
    }
  }, [selectedAccount]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
      setErrorMessage(null);
      setSelectedHistoryFileId(null); // Clear history selection
      setInitialFieldMapForStep2(undefined); // Reset for new file
      setCurrentlyLoadedFieldMapDetails(undefined);
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
      setInitialFieldMapForStep2(undefined); // Reset for new file
      setCurrentlyLoadedFieldMapDetails(undefined);
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
    // Initial map will be determined when proceeding with this history file
    setInitialFieldMapForStep2(undefined);
    setCurrentlyLoadedFieldMapDetails(undefined);
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
      if (rawFileFormat === 'csv') {
        if (!parseResult.headers || !parseResult.data) {
          setErrorMessage("CSV parsing did not return headers or data.");
          setIsLoading(false);
          return;
        }
        setCsvHeaders(parseResult.headers);
        const transactions = parseResult.data.map((item: any, index: number) => ({ id: item.id || `csv-hist-${index}`, ...item }));
        setParsedTransactionData(transactions);
      } else { 
         if (!parseResult.data) {
          setErrorMessage(`${rawFileFormat.toUpperCase()} parsing did not return data.`);
          setIsLoading(false);
          return;
        }
        const transactions = parseResult.data.map((item: any, index: number) => ({ id: item.id || `parsed-hist-${index}`, ...item }));
        setParsedTransactionData(transactions);
        setCsvHeaders([]); 
      }
      // Now call the common logic to set up for step 2, including field map determination
      await proceedToStep2Logic(historyFileMeta);
    } catch (error: any) {
      console.error("Error processing history file:", error);
      setErrorMessage(error.message || "Failed to process history file. Please try again.");
      setCurrentFileId(null); 
    } finally {
      setIsLoading(false);
    }
  };

  const proceedToStep2Logic = async (fileMetaForMapLookup?: FileMetadata) => {
    // 1. Determine initialFieldMapForStep2
    let initialMap: {id: string, name: string} | undefined = undefined;
    if (fileMetaForMapLookup?.fieldMap?.fileMapId && fileMetaForMapLookup?.fieldMap?.name) {
        initialMap = { 
            id: fileMetaForMapLookup.fieldMap.fileMapId, 
            name: fileMetaForMapLookup.fieldMap.name 
        };
        console.log("[ImportTransactionsView] Found initial field map for Step 2 from file metadata:", initialMap);
        setInitialFieldMapForStep2(initialMap);
        // Pre-load its details
        if (initialMap) {
            await handleLoadFieldMapDetails(initialMap.id); // This will set currentlyLoadedFieldMapDetails
        }
    } else {
        console.log("[ImportTransactionsView] No initial field map found for this file for Step 2.");
        setInitialFieldMapForStep2(undefined);
        setCurrentlyLoadedFieldMapDetails(undefined);
    }
    setCurrentStep(2);
  };

  const proceedToStep2 = async () => {
    if (!selectedFile) {
      setErrorMessage('Please select a file to upload.');
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const currentUser = getCurrentUser();
      if (!currentUser) {
        setErrorMessage("User not authenticated. Please log in.");
        setIsLoading(false);
        return;
      }
      const presignedData = await getUploadUrl(
        selectedFile.name, selectedFile.type, selectedFile.size, currentUser.id, selectedAccount || undefined
      );
      const newFileId = presignedData.fileId;
      setCurrentFileId(newFileId);
      await uploadFileToS3(presignedData, selectedFile, selectedAccount || undefined);
      const parseResult = await parseFile(newFileId);
      if (parseResult.error) {
        setErrorMessage(`Error parsing file: ${parseResult.error}`);
        setIsLoading(false);
        return;
      }
      const determinedFileType = parseResult.file_format || 'csv';
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
      } else { 
         if (!parseResult.data) {
          setErrorMessage(`${determinedFileType.toUpperCase()} parsing did not return data.`);
          setIsLoading(false);
          return;
        }
        const transactions = parseResult.data.map((item: any, index: number) => ({ id: item.id || `parsed-${index}`, ...item }));
        setParsedTransactionData(transactions);
        setCsvHeaders([]); 
      }
      // For new files, fieldMap association would likely happen after save in Step2, or if backend auto-applies one.
      // For now, assume no initial map. If backend provides it in parseResult.file_metadata, use it.
      let newFileMetaForMapLookup: FileMetadata | undefined = undefined;
      // Safely access file_metadata, assuming parseResult might not always have it or it might not have fieldMap
      if (parseResult && typeof parseResult === 'object' && 'file_metadata' in parseResult) {
        const meta = (parseResult as any).file_metadata as FileMetadata; // Cast to any then FileMetadata
        if (meta && meta.fieldMap) {
            newFileMetaForMapLookup = meta;
        }
      }
      await proceedToStep2Logic(newFileMetaForMapLookup);
    } catch (error: any) {
      console.error("Error during file upload and parse process:", error);
      setErrorMessage(error.message || "Failed to process file. Please try again.");
      setCurrentFileId(null); 
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompleteImportStep2 = async (
    mappedData: TransactionRow[], // Currently unused as backend does processing
    finalFieldMapToAssociate?: { id: string; name: string } // Passed from ImportStep2Preview
  ) => {
    if (!currentFileId) {
      setErrorMessage("No current file to process for final import step.");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setImportResult(null); // Clear previous results

    const historyFile = importHistory.find(f => f.fileId === currentFileId);
    let preliminaryFileName = selectedFile?.name || historyFile?.fileName || 'Unknown File';
    let preliminaryAccountName = accounts.find(a => a.id === selectedAccount)?.name || historyFile?.accountName || 'Unassigned';

    try {
      let processApiResult: FileProcessResult;

      if (fileTypeForStep2 === 'csv' && finalFieldMapToAssociate?.id) {
        console.log(`[ImportTransactionsView] Associating map '${finalFieldMapToAssociate.name}' (${finalFieldMapToAssociate.id}) with file ${currentFileId} and processing.`);
        processApiResult = await updateFileFieldMapAssociation(currentFileId, finalFieldMapToAssociate.id);
      } else {
        console.log(`[ImportTransactionsView] Finalizing import for non-CSV or CSV without explicit map association. File ID: ${currentFileId}. Fetching latest metadata.`);
        processApiResult = await getProcessedFileMetadata(currentFileId);
      }

      const success = processApiResult.statusCode === 200;

      setImportResult({
        success: success,
        message: processApiResult.message,
        transactionCount: processApiResult.transactionCount,
        fileName: processApiResult.fileName || preliminaryFileName,
        accountName: processApiResult.accountName || preliminaryAccountName,
        errorDetails: !success ? (processApiResult.message || 'Processing failed.') : undefined,
      });
      setCurrentStep(3);

    } catch (error: any) {
      console.error("[ImportTransactionsView] Error completing import step 2 (finalization):", error);
      setImportResult({
        success: false,
        message: "Import Finalization Failed",
        errorDetails: error.message || "An unexpected error occurred during final processing.",
        fileName: preliminaryFileName,
        accountName: preliminaryAccountName,
      });
      setCurrentStep(3); 
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelStep2 = () => {
    console.log("Step 2 Cancelled. Returning to Step 1.");
    setCurrentStep(1); 
    // States like selectedFile, selectedAccount are reset by useEffect for currentStep === 1
  };
  
  const resetProcess = () => {
    setCurrentStep(1);
    setSelectedFile(null);
    setSelectedAccount('');
    setErrorMessage(null);
    // Resetting other states (filePreviewData, importResult, etc.) will be handled when they are re-introduced
  };

  // Callback for ImportStep2Preview to load details of a selected field map
  const handleLoadFieldMapDetails = useCallback(async (fieldMapId: string): Promise<ColumnMapping[] | undefined> => {
    console.log("[ImportTransactionsView] Attempting to load field map details for ID:", fieldMapId);
    try {
      const fieldMapData = await getFieldMap(fieldMapId);
      if (fieldMapData && fieldMapData.mappings) {
        // Transform FileMapService's mapping format to ColumnMapping[] for Step2Preview
        const transformedMappings: ColumnMapping[] = fieldMapData.mappings.map(m => ({
          csvColumn: m.sourceField, // In FileMapService, it's sourceField
          targetField: m.targetField,
          isValid: undefined, // Validity will be re-calculated by ImportStep2Preview
        }));
        console.log("[ImportTransactionsView] Transformed mappings for Step2:", transformedMappings);
        setCurrentlyLoadedFieldMapDetails(transformedMappings); // Update state to pass as prop
        return transformedMappings;
      }
      setCurrentlyLoadedFieldMapDetails(undefined); // Clear if not found or no mappings
      return undefined;
    } catch (error) {
      console.error("[ImportTransactionsView] Error loading field map details:", fieldMapId, error);
      setCurrentlyLoadedFieldMapDetails(undefined); // Clear on error
      throw error; // Re-throw so ImportStep2Preview can catch and display message
    }
  }, []);

  // Callback for ImportStep2Preview to save or update a field map
  const handleSaveOrUpdateFieldMap = useCallback(async (
    params: {
      mapIdToUpdate?: string;
      name: string;
      mappingsToSave: Array<{ csvColumn: string; targetField: string }>;
    }
  ): Promise<{ newMapId?: string; newName?: string; success: boolean; message?: string }> => {
    const { mapIdToUpdate, name, mappingsToSave } = params;
    console.log(`[ImportTransactionsView] Saving/Updating map. ID: ${mapIdToUpdate}, Name: ${name}`);
    try {
      let serviceResponse: FieldMap;
      const preparedMappings = mappingsToSave.map(m => ({ sourceField: m.csvColumn, targetField: m.targetField }));

      if (mapIdToUpdate) {
        // updateFieldMap expects fileMapId and a Partial<FieldMap> object for updates
        serviceResponse = await updateFieldMap(mapIdToUpdate, { name, mappings: preparedMappings });
      } else {
        // createFieldMap expects an Omit<FieldMap, 'fileMapId' | 'createdAt' | 'updatedAt'> object
        serviceResponse = await createFieldMap({
            name,
            mappings: preparedMappings,
            // Optionally include accountId if relevant and available
            // accountId: selectedAccount || undefined, 
            // description can also be added if there's a UI for it
        });
      }
      // After successful save/update, refresh the list of available maps
      const fieldMapsListResponse = await listFieldMaps();
      const mapsForDropdown = fieldMapsListResponse.fieldMaps.map(fm => ({ id: fm.fileMapId!, name: fm.name }));
      setAvailableFieldMaps(mapsForDropdown);
      console.log("[ImportTransactionsView] Refreshed available field maps after save/update.");

      // If this was a new save or an update to the map currently associated with the file,
      // update initialFieldMapForStep2 so the child component reflects it.
      if (serviceResponse.fileMapId && (!mapIdToUpdate || mapIdToUpdate === initialFieldMapForStep2?.id)) {
        setInitialFieldMapForStep2({ id: serviceResponse.fileMapId, name: serviceResponse.name });
        // And if it was the initial map, also update currentlyLoadedFieldMapDetails as it might have changed (e.g. name)
        if (mapIdToUpdate && mapIdToUpdate === initialFieldMapForStep2?.id) {
            const transformed = serviceResponse.mappings.map(m => ({csvColumn: m.sourceField, targetField: m.targetField, isValid: undefined}));
            setCurrentlyLoadedFieldMapDetails(transformed);
        }
      }
      
      return { success: true, newMapId: serviceResponse.fileMapId, newName: serviceResponse.name, message: mapIdToUpdate ? 'Updated' : 'Saved' };
    } catch (error: any) {
      console.error("[ImportTransactionsView] Error saving/updating field map:", error);
      return { success: false, message: error.message || "Failed to save/update mapping." };
    }
  }, [currentFileId, selectedAccount, initialFieldMapForStep2?.id]); // Add initialFieldMapForStep2.id to dependencies

  const handleSaveOpeningBalance = async (fileId: string, balanceStr: string) => {
    const newBalance = parseFloat(balanceStr);
    if (isNaN(newBalance)) {
      setErrorMessage("Invalid balance amount.");
      return;
    }

    setIsLoadingHistory(true); // Indicate loading state for the history section
    setErrorMessage(null);

    try {
      // Call the service to update the balance
      const updatedFile = await updateFileBalance(fileId, newBalance);
      
      // Update the import history state
      setImportHistory(prevHistory => 
        prevHistory.map(file => 
          file.fileId === fileId 
            ? { ...file, openingBalance: updatedFile.openingBalance } 
            : file
        )
      );
      
      // Exit editing mode
      setEditingFileId(null);
      setEditingOpeningBalance('');
      alert("Opening balance updated successfully!"); // Or a more subtle notification

    } catch (error: any) {
      console.error("Error updating opening balance:", error);
      setErrorMessage(error.message || "Failed to update opening balance.");
      // Optionally, you might want to keep the cell in edit mode or clear it
      // For now, we will clear it as per existing Escape/✗ logic
      setEditingFileId(null);
      setEditingOpeningBalance('');
    } finally {
      setIsLoadingHistory(false);
    }
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
          
          <div className="account-selection-row">
            <div className="account-select-group">
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
            </div>
            
            <div className="default-mapping-group">
              <label htmlFor="default-mapping-select" className="label-common">Default Mapping:</label>
              <select 
                id="default-mapping-select"
                value={selectedDefaultMapping} 
                onChange={e => setSelectedDefaultMapping(e.target.value)}
                className="select-common"
                disabled={!selectedAccount || isLoadingDefaultMapping}
              >
                <option value="">
                  {!selectedAccount ? "Select account first" : 
                   isLoadingDefaultMapping ? "Loading mapping..." : 
                   !defaultMappingName ? "No default mapping" : 
                   "-- Select Default Mapping --"}
                </option>
                {defaultMappingName && (
                  <option value={selectedDefaultMapping}>{defaultMappingName}</option>
                )}
              </select>
            </div>
          </div>

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
                      <th className="history-th-td">Opening Balance</th>
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
                        <td className="history-th-td">
                          {file.accountId 
                            ? (accounts.find(acc => acc.id === file.accountId)?.name || file.accountName || 'N/A') 
                            : (file.accountName || 'N/A')}
                        </td>
                        <td className="history-th-td">{new Date(file.uploadDate).toLocaleDateString()}</td>
                        <td className="history-th-td">
                          {file.fieldMap?.fileMapId && fieldMapsData[file.fieldMap.fileMapId] 
                            ? fieldMapsData[file.fieldMap.fileMapId] 
                            : file.fieldMap?.name || '--'}
                        </td>
                        <td className="history-th-td">{file.fileFormat || 'N/A'}</td>
                        {editingFileId === file.fileId ? (
                          <td className="history-th-td">
                            <input
                              type="number"
                              value={editingOpeningBalance}
                              onChange={(e) => setEditingOpeningBalance(e.target.value.replace(/[^\d.-]/g, ''))}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  handleSaveOpeningBalance(file.fileId, editingOpeningBalance);
                                }
                                if (e.key === 'Escape') {
                                  setEditingFileId(null);
                                  setEditingOpeningBalance('');
                                }
                              }}
                              style={{ width: '80px', marginRight: '5px' }}
                              autoFocus
                            />
                            <button onClick={() => handleSaveOpeningBalance(file.fileId, editingOpeningBalance)}>✓</button>
                            <button onClick={() => { setEditingFileId(null); setEditingOpeningBalance(''); }}>✗</button>
                          </td>
                        ) : (
                          <td 
                            className="history-th-td"
                            onClick={() => {
                              setEditingFileId(file.fileId);
                              setEditingOpeningBalance(typeof file.openingBalance === 'number' ? file.openingBalance.toString() : '');
                            }}
                            style={{ cursor: 'pointer' }}
                          >
                            {typeof file.openingBalance === 'number' ? file.openingBalance.toFixed(2) : 'N/A'}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div style={{ marginTop: '10px' }}>
                  <button
                    onClick={handleProceedWithSelectedHistoryFile} 
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
          existingMapping={currentlyLoadedFieldMapDetails}
          onCompleteImport={handleCompleteImportStep2}
          onCancel={handleCancelStep2}
          targetTransactionFields={TARGET_TRANSACTION_FIELDS}
          availableFieldMaps={availableFieldMaps}
          initialFieldMapToLoad={initialFieldMapForStep2}
          onLoadFieldMapDetails={handleLoadFieldMapDetails}
          onSaveOrUpdateFieldMap={handleSaveOrUpdateFieldMap}
        />
      )}

      {currentStep === 3 && importResult && (
        <ImportCompletionView
          success={importResult.success}
          message={importResult.message}
          transactionCount={importResult.transactionCount}
          fileName={importResult.fileName}
          accountName={importResult.accountName}
          errorDetails={importResult.errorDetails}
          onViewTransactions={() => {
            alert('Navigate to transactions list (pre-filtered for this import if possible).');
            setCurrentStep(1); 
          }}
          onImportAnother={() => setCurrentStep(1)}
          onGoToStatements={() => {
            alert('Navigate to Statements & Imports main tab/view.');
            setCurrentStep(1); 
          }}
        />
      )}
    </div>
  );
};

export default ImportTransactionsView; 
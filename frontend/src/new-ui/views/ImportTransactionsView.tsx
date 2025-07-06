import React, { useState, useCallback, useEffect } from 'react';
// Use AccountService for fetching accounts
import { listAccounts, Account as ServiceAccount } from '../../services/AccountService';
import { getUploadUrl, uploadFileToS3, listFiles, FileMetadata, deleteFile, parseFile, updateFileFieldMapAssociation, getProcessedFileMetadata, FileProcessResult, updateFileBalance, updateFileClosingBalance, associateFileWithAccount } from '../../services/FileService'; // Added parseFile, updateFileBalance, updateFileClosingBalance, and associateFileWithAccount
import { listFieldMaps, getFieldMap, createFieldMap, updateFieldMap, FieldMap } from '../../services/FileMapService'; // Import more from FileMapService
import { getCurrentUser } from '../../services/AuthService'; // Import getCurrentUser
import ImportStep2Preview from '../components/ImportStep2Preview'; // Import the new component
import type { TransactionRow, ColumnMapping } from '../components/ImportStep2Preview'; // Import types
import TransactionFileUpload from '../components/TransactionFileUpload'; // Enhanced file upload
import ImportHistoryTable from '../components/ImportHistoryTable'; // Import the new reusable table
import { FileValidationResult } from '../utils/fileValidation'; // File validation types
import { detectFileType } from '../utils/fileValidation'; // Import file type detection
import './ImportTransactionsView.css'; // Import the CSS file
import Decimal from 'decimal.js';

// Define TARGET_TRANSACTION_FIELDS (should match what ImportStep2Preview expects)
const TARGET_TRANSACTION_FIELDS = [
  { 
    field: 'date', 
    label: 'Transaction Date', 
    required: true,
    regex: [
      '^\\d{4}-\\d{2}-\\d{2}$',           // YYYY-MM-DD (ISO format)
      '^\\d{2}/\\d{2}/\\d{4}$',           // MM/DD/YYYY (US format)
      '^\\d{1,2}/\\d{1,2}/\\d{4}$',       // M/D/YYYY or MM/D/YYYY or M/DD/YYYY
      '^\\d{2}-\\d{2}-\\d{4}$',           // MM-DD-YYYY
      '^\\d{1,2}-\\d{1,2}-\\d{4}$',       // M-D-YYYY or MM-D-YYYY or M-DD-YYYY
      '^\\d{4}/\\d{2}/\\d{2}$',           // YYYY/MM/DD
      '^\\d{4}/\\d{1,2}/\\d{1,2}$',       // YYYY/M/D or YYYY/MM/D or YYYY/M/DD
      '^\\d{2}\\.\\d{2}\\.\\d{4}$',       // DD.MM.YYYY (European format with dots)
      '^\\d{1,2}\\.\\d{1,2}\\.\\d{4}$',   // D.M.YYYY or DD.M.YYYY or D.MM.YYYY
      '^\\d{4}\\.\\d{2}\\.\\d{2}$',       // YYYY.MM.DD
      '^\\d{4}\\.\\d{1,2}\\.\\d{1,2}$',   // YYYY.M.D or YYYY.MM.D or YYYY.M.DD
      '^\\d{2}\\d{2}\\d{4}$',             // MMDDYYYY (no separators)
      '^\\d{4}\\d{2}\\d{2}$',             // YYYYMMDD (no separators)
      '^\\d{1,2}\\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{4}$', // D MMM YYYY
      '^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{1,2},?\\s+\\d{4}$', // MMM D, YYYY
    ]
  },
  { field: 'description', label: 'Description', required: true, regex: ['.+'] }, // Any non-empty string
  { field: 'amount', label: 'Amount', required: true, regex: ['^-?(\\d+|\\d{1,3}(,\\d{3})*)(\\.\\d+)?$'] }, // Number, allows commas, optional negative/decimal
  { field: 'debitOrCredit', label: 'Debit/Credit', required: false, regex: ['^(debit|credit|CRDT|DBIT|DR|CR)$'] }, // Optional but validated if mapped
  { field: 'currency', label: 'Currency', required: false, regex: ['^[A-Z]{3}$'] }, // Optional but validated if mapped
];

// Define a local Account type for the component if its structure differs from ServiceAccount
// or if we want to add/omit properties for the view layer.
// For now, we will map ServiceAccount to this structure.
interface ViewAccount {
  id: string;    // Corresponds to accountId from ServiceAccount
  name: string;  // Corresponds to accountName from ServiceAccount
  defaultfileMapid?: string; // For tracking the account's default mapping
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
  const [fileTypeForStep2, setFileTypeForStep2] = useState<'csv' | 'ofx' | 'qfx' | 'qif'>('csv');
  const [existingMappingsForStep2, setExistingMappingsForStep2] = useState<ColumnMapping[] | undefined>(undefined); // Re-introduced

  // New state for named field map management
  const [availableFileMaps, setAvailableFileMaps] = useState<AvailableMapInfo[]>([]);
  const [currentlyLoadedFieldMapDetails, setCurrentlyLoadedFieldMapDetails] = useState<ColumnMapping[] | undefined>(undefined);
  const [currentlyLoadedFieldMapData, setCurrentlyLoadedFieldMapData] = useState<FieldMap | undefined>(undefined); // Store full field map data
  const [initialFieldMapForStep2, setInitialFieldMapForStep2] = useState<{id: string, name: string} | undefined>(undefined);
  const [isLoadingFieldMaps, setIsLoadingFieldMaps] = useState<boolean>(false);

  // New state for default mapping dropdown
  const [selectedDefaultMapping, setSelectedDefaultMapping] = useState<string>('');
  const [defaultMappingName, setDefaultMappingName] = useState<string>('');
  const [isLoadingDefaultMapping, setIsLoadingDefaultMapping] = useState<boolean>(false);

  // New state for import results - replaced with success alert
  const [successAlert, setSuccessAlert] = useState<ImportResultForView | null>(null);

  // Note: Inline editing state is now managed by ImportHistoryTable component
  
  // State for enhanced file validation
  const [fileValidation, setFileValidation] = useState<FileValidationResult>({ isValid: false });

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
        defaultfilemapid: acc.defaultFileMapId,
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
      setAvailableFileMaps(mapsForDropdown);
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
      
      console.log(`[ImportTransactionsView] Fetching default mapping for account: ${accountId}`);
      console.log(`[ImportTransactionsView] Available file maps:`, availableFileMaps);
      
      // Get the account details to retrieve the defaultFieldMapId  
      const response = await listAccounts();
      const account = response.accounts.find(acc => acc.accountId === accountId);
      
      console.log(`[ImportTransactionsView] Found account:`, account);
      console.log(`[ImportTransactionsView] Account defaultFileMapId:`, account?.defaultFileMapId);
      
      if (account && account.defaultFileMapId) {
        // Check if the default mapping exists in available field maps
        const mappingExists = availableFileMaps.some(map => map.id === account.defaultFileMapId);
        console.log(`[ImportTransactionsView] Default mapping ${account.defaultFileMapId} exists in available maps:`, mappingExists);
        
        if (!mappingExists) {
          console.warn(`[ImportTransactionsView] Account's default mapping ${account.defaultFileMapId} not found in available field maps. Available maps:`, availableFileMaps.map((m: AvailableMapInfo) => m.id));
          setDefaultMappingName('');
          setSelectedDefaultMapping('');
          return;
        }
        
        // Fetch the field map details
        const fieldMap = await getFieldMap(account.defaultFileMapId);
        setDefaultMappingName(fieldMap.name);
        // Automatically set the default mapping when account is selected
        setSelectedDefaultMapping(account.defaultFileMapId);
        console.log(`[ImportTransactionsView] Auto-selected default mapping for account ${account.accountName}: ${fieldMap.name} (${account.defaultFileMapId})`);
      } else {
        setDefaultMappingName('');
        setSelectedDefaultMapping('');
        console.log(`[ImportTransactionsView] No default mapping found for account ${account?.accountName || accountId}. Account object:`, account);
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
      setCurrentlyLoadedFieldMapData(undefined); // Reset loaded map data
      setInitialFieldMapForStep2(undefined); // Reset initial map to load
      // Don't clear success alert here since we want to show it on return to step 1
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

  // Enhanced file selection handler for TransactionFileUpload
  const handleEnhancedFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setErrorMessage(null);
    setSelectedHistoryFileId(null); // Clear history selection
    setInitialFieldMapForStep2(undefined); // Reset for new file
    setCurrentlyLoadedFieldMapDetails(undefined);
    setCurrentlyLoadedFieldMapData(undefined);
    if (file) {
      console.log("Enhanced file selected:", file);
    }
  };

  // File validation change handler
  const handleFileValidationChange = (result: FileValidationResult) => {
    setFileValidation(result);
    if (result.error) {
      setErrorMessage(result.error);
    } else {
      setErrorMessage(null);
    }
  };



  const handleHistoryRowClick = (fileId: string) => {
    setSelectedHistoryFileId(prev => (prev === fileId ? null : fileId));
    setSelectedFile(null); // Clear new file selection when history item is clicked
    setErrorMessage(null);
    // Initial map will be determined when proceeding with this history file
    setInitialFieldMapForStep2(undefined);
    setCurrentlyLoadedFieldMapDetails(undefined);
  };

  const handleDeleteHistoryFile = async (fileId: string) => {
    const fileToDelete = importHistory.find(f => f.fileId === fileId);
    if (!fileToDelete) {
      setErrorMessage("Selected file not found in history.");
      return;
    }

    setIsLoadingHistory(true); // Use history loader for this action
    setErrorMessage(null);
    try {
      await deleteFile(fileId);
      alert(`File "${fileToDelete.fileName}" deleted successfully.`);
      if (selectedHistoryFileId === fileId) {
        setSelectedHistoryFileId(null);
      }
      // Refresh history
      await fetchInitialData(); // Re-fetch all initial data which includes history
    } catch (error: any) {
      console.error("Error deleting file:", error);
      setErrorMessage(error.message || `Failed to delete file "${fileToDelete.fileName}". Please try again.`);
    } finally {
      setIsLoadingHistory(false);
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
      
      // Detect file type and provide appropriate MIME type if empty
      let mimeType = selectedFile.type;
      if (!mimeType || mimeType.trim() === '') {
        const detectedType = detectFileType(selectedFile.name);
        switch (detectedType) {
          case 'ofx':
            mimeType = 'application/x-ofx';
            break;
          case 'qfx':
            mimeType = 'application/vnd.intu.qfx';
            break;
          case 'csv':
            mimeType = 'text/csv';
            break;
          case 'qif':
            mimeType = 'application/x-quicken';
            break;
          default:
            mimeType = 'application/octet-stream'; // Generic fallback
        }
        console.log(`[ImportTransactionsView] Empty MIME type detected for ${selectedFile.name}. Using fallback: ${mimeType}`);
      }
      
      const presignedData = await getUploadUrl(
        selectedFile.name, mimeType, selectedFile.size, currentUser.id, selectedAccount || undefined
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
      // Check if a default mapping is selected - if so, bypass Step 2 and go straight to import
      if (selectedDefaultMapping && defaultMappingName) {
        console.log(`[ImportTransactionsView] Default mapping selected: ${defaultMappingName} (${selectedDefaultMapping}). Bypassing Step 2.`);
        
        // Associate the selected default mapping with the file and complete import
        const preliminaryFileName = selectedFile?.name || 'Unknown File';
        const preliminaryAccountName = accounts.find(a => a.id === selectedAccount)?.name || 'Unassigned';
        
        try {
          // Associate the mapping and process the file
          const processApiResult = await updateFileFieldMapAssociation(newFileId, selectedDefaultMapping);
          const success = processApiResult.statusCode === 200;

          setSuccessAlert({
            success: success,
            message: processApiResult.message,
            transactionCount: processApiResult.transactionCount,
            fileName: processApiResult.fileName || preliminaryFileName,
            accountName: processApiResult.accountName || preliminaryAccountName,
            errorDetails: !success ? (processApiResult.message || 'Processing failed.') : undefined,
          });
          setCurrentStep(1);
          
        } catch (error: any) {
          console.error("[ImportTransactionsView] Error with direct import using default mapping:", error);
          setSuccessAlert({
            success: false,
            message: "Import with Default Mapping Failed",
            errorDetails: error.message || "An unexpected error occurred during processing with default mapping.",
            fileName: preliminaryFileName,
            accountName: preliminaryAccountName,
          });
          setCurrentStep(1);
        }
      } else {
        // No default mapping selected, proceed to Step 2 for manual mapping
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
      }
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
    setSuccessAlert(null); // Clear previous results

    const historyFile = importHistory.find(f => f.fileId === currentFileId);
    let preliminaryFileName = selectedFile?.name || historyFile?.fileName || 'Unknown File';
    let preliminaryAccountName = accounts.find(a => a.id === selectedAccount)?.name || historyFile?.accountName || 'Unassigned';

    try {
      let processApiResult: FileProcessResult;

      if ((fileTypeForStep2 === 'csv' || fileTypeForStep2 === 'ofx' || fileTypeForStep2 === 'qfx' || fileTypeForStep2 === 'qif') && finalFieldMapToAssociate?.id) {
        console.log(`[ImportTransactionsView] Associating map '${finalFieldMapToAssociate.name}' (${finalFieldMapToAssociate.id}) with ${fileTypeForStep2.toUpperCase()} file ${currentFileId} and processing.`);
        processApiResult = await updateFileFieldMapAssociation(currentFileId, finalFieldMapToAssociate.id);
      } else {
        console.log(`[ImportTransactionsView] Finalizing import for ${fileTypeForStep2.toUpperCase()} without explicit map association. File ID: ${currentFileId}. Fetching latest metadata.`);
        processApiResult = await getProcessedFileMetadata(currentFileId);
      }

      const success = processApiResult.statusCode === 200;

      setSuccessAlert({
        success: success,
        message: processApiResult.message,
        transactionCount: processApiResult.transactionCount,
        fileName: processApiResult.fileName || preliminaryFileName,
        accountName: processApiResult.accountName || preliminaryAccountName,
        errorDetails: !success ? (processApiResult.message || 'Processing failed.') : undefined,
      });
      setCurrentStep(1);

    } catch (error: any) {
      console.error("[ImportTransactionsView] Error completing import step 2 (finalization):", error);
      setSuccessAlert({
        success: false,
        message: "Import Finalization Failed",
        errorDetails: error.message || "An unexpected error occurred during final processing.",
        fileName: preliminaryFileName,
        accountName: preliminaryAccountName,
      });
      setCurrentStep(1); 
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelStep2 = () => {
    console.log("Step 2 Cancelled. Returning to Step 1.");
    setCurrentStep(1);
    setSuccessAlert(null);
    // States like selectedFile, selectedAccount are reset by useEffect for currentStep === 1
  };
  
  const resetProcess = () => {
    setCurrentStep(1);
    setSelectedFile(null);
    setSelectedAccount('');
    setErrorMessage(null);
    setSuccessAlert(null);
    // Resetting other states (filePreviewData, etc.) will be handled when they are re-introduced
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
        console.log("[ImportTransactionsView] Field map reverseAmounts flag:", fieldMapData.reverseAmounts);
        setCurrentlyLoadedFieldMapDetails(transformedMappings); // Update state to pass as prop
        // Store the reverseAmounts flag to be accessed by the child component
        setCurrentlyLoadedFieldMapData(fieldMapData); // Store full field map data
        return transformedMappings;
      }
      setCurrentlyLoadedFieldMapDetails(undefined); // Clear if not found or no mappings
      setCurrentlyLoadedFieldMapData(undefined);
      return undefined;
    } catch (error) {
      console.error("[ImportTransactionsView] Error loading field map details:", fieldMapId, error);
      setCurrentlyLoadedFieldMapDetails(undefined); // Clear on error
      setCurrentlyLoadedFieldMapData(undefined);
      throw error; // Re-throw so ImportStep2Preview can catch and display message
    }
  }, []);

  // Callback for ImportStep2Preview to save or update a field map
  const handleSaveOrUpdateFieldMap = useCallback(async (
    params: {
      mapIdToUpdate?: string;
      name: string;
      mappingsToSave: Array<{ csvColumn: string; targetField: string }>;
      reverseAmounts?: boolean;
    }
  ): Promise<{ newMapId?: string; newName?: string; success: boolean; message?: string }> => {
    const { mapIdToUpdate, name, mappingsToSave, reverseAmounts } = params;
    console.log(`[ImportTransactionsView] Saving/Updating map. ID: ${mapIdToUpdate}, Name: ${name}`);
    try {
      let serviceResponse: FieldMap;
      const preparedMappings = mappingsToSave.map(m => ({ sourceField: m.csvColumn, targetField: m.targetField }));

      if (mapIdToUpdate) {
        // updateFieldMap expects fileMapId and a Partial<FieldMap> object for updates
        serviceResponse = await updateFieldMap(mapIdToUpdate, { 
          name, 
          mappings: preparedMappings,
          reverseAmounts: reverseAmounts || false 
        });
      } else {
        // createFieldMap expects an Omit<FieldMap, 'fileMapId' | 'createdAt' | 'updatedAt'> object
        serviceResponse = await createFieldMap({
            name,
            mappings: preparedMappings,
            reverseAmounts: reverseAmounts || false,
            // Optionally include accountId if relevant and available
            // accountId: selectedAccount || undefined, 
            // description can also be added if there's a UI for it
        });
      }
      // After successful save/update, refresh the list of available maps
      const fieldMapsListResponse = await listFieldMaps();
      const mapsForDropdown = fieldMapsListResponse.fieldMaps.map(fm => ({ id: fm.fileMapId!, name: fm.name }));
      setAvailableFileMaps(mapsForDropdown);
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
    let newBalance: Decimal;
    try {
      newBalance = new Decimal(balanceStr);
    } catch (error) {
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
      
      alert("Opening balance updated successfully!"); // Or a more subtle notification

    } catch (error: any) {
      console.error("Error updating opening balance:", error);
      setErrorMessage(error.message || "Failed to update opening balance.");
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleSaveClosingBalance = async (fileId: string, balanceStr: string) => {
    let newBalance: Decimal;
    try {
      newBalance = new Decimal(balanceStr);
    } catch (error) {
      setErrorMessage("Invalid balance amount.");
      return;
    }

    setIsLoadingHistory(true); // Indicate loading state for the history section
    setErrorMessage(null);

    try {
      // Call the service to update the closing balance (which calculates new opening balance)
      const updatedFile = await updateFileClosingBalance(fileId, newBalance);
      
      // Update the import history state with the complete updated file from backend
      setImportHistory(prevHistory => 
        prevHistory.map(file => 
          file.fileId === fileId 
            ? updatedFile  // Replace entire file object with backend response
            : file
        )
      );
      
      alert("Closing balance updated successfully! Opening balance has been recalculated."); // Or a more subtle notification

    } catch (error: any) {
      console.error("Error updating closing balance:", error);
      setErrorMessage(error.message || "Failed to update closing balance.");
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleSaveMapping = async (fileId: string, mappingId: string) => {
    if (!mappingId) {
      setErrorMessage("Please select a valid mapping.");
      return;
    }

    setIsLoadingHistory(true);
    setErrorMessage(null);

    try {
      // Associate the new mapping with the file
      await updateFileFieldMapAssociation(fileId, mappingId);
      
      // Get the mapping name for display
      const mappingName = fieldMapsData[mappingId] || availableFileMaps.find(m => m.id === mappingId)?.name || 'Unknown';
      
      // Update the import history state
      setImportHistory(prevHistory => 
        prevHistory.map(file => 
          file.fileId === fileId 
            ? { 
                ...file, 
                fieldMap: { 
                  fileMapId: mappingId, 
                  name: mappingName 
                } 
              } 
            : file
        )
      );
      
      alert("Mapping updated successfully!");

    } catch (error: any) {
      console.error("Error updating mapping:", error);
      setErrorMessage(error.message || "Failed to update mapping.");
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleSaveAccount = async (fileId: string, accountId: string) => {
    setIsLoadingHistory(true);
    setErrorMessage(null);

    try {
      // Call the API to associate the file with the account
      await associateFileWithAccount(fileId, accountId);
      
      // Get the account name for display
      const accountName = accounts.find(acc => acc.id === accountId)?.name || 'Unknown';
      
      // Update the import history state after successful API call
      setImportHistory(prevHistory => 
        prevHistory.map(file => 
          file.fileId === fileId 
            ? { 
                ...file, 
                accountId: accountId || undefined,
                accountName: accountName 
              } 
            : file
        )
      );
      
      alert("Account updated successfully!");

    } catch (error: any) {
      console.error("Error updating account:", error);
      setErrorMessage(error.message || "Failed to update account.");
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Helper function to format balance for display
  const formatBalanceDisplay = (balance: Decimal | undefined): string => {
    return balance ? balance.toFixed(2) : 'N/A';
  };

  // Helper function to convert Decimal to number for editing
  const decimalToNumber = (balance: Decimal | undefined): number | undefined => {
    return balance ? balance.toNumber() : undefined;
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

      {successAlert && (
        <div className={`alert-panel ${successAlert.success ? 'alert-success' : 'alert-error'}`}>
          <div className="alert-content">
            <div className="alert-icon">
              {successAlert.success ? (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
              )}
            </div>
            <div className="alert-text">
              <h3>{successAlert.success ? 'Import Successful!' : 'Import Failed'}</h3>
              {successAlert.success && successAlert.transactionCount !== undefined && successAlert.fileName && successAlert.accountName && (
                <p>
                  <strong>{successAlert.transactionCount}</strong> transaction{successAlert.transactionCount === 1 ? '' : 's'} from <strong>'{successAlert.fileName}'</strong>{' '}
                  {successAlert.accountName !== 'Unassigned' && successAlert.accountName !== '' ? <>have been added to <strong>'{successAlert.accountName}'</strong>.</> : <>have been imported.</>}
                </p>
              )}
              {successAlert.message && <p className="alert-message">{successAlert.message}</p>}
              {successAlert.errorDetails && <p className="alert-error-details">Details: {successAlert.errorDetails}</p>}
            </div>
            <button className="alert-close" onClick={() => setSuccessAlert(null)}>
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
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
                disabled={!selectedAccount || isLoadingDefaultMapping || isLoadingFieldMaps}
              >
                <option value="">
                  {!selectedAccount ? "Select account first" : 
                   isLoadingDefaultMapping || isLoadingFieldMaps ? "Loading mappings..." : 
                   "-- Select Mapping --"}
                </option>
                  {availableFileMaps.map(mapping => (
                  <option key={mapping.id} value={mapping.id}>
                    {mapping.name} {mapping.id === (accounts.find(acc => acc.id === selectedAccount)?.defaultfileMapid) ? "(Account Default)" : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Enhanced File Upload Section */}
          <div className="enhanced-file-upload-section">
            <TransactionFileUpload
              selectedFile={selectedFile}
              onFileSelect={handleEnhancedFileSelect}
              onValidationChange={handleFileValidationChange}
              disabled={ isLoading}
              showPreview={true}
            />
          </div>

          {/* File validation warnings */}
          {fileValidation.warnings && fileValidation.warnings.length > 0 && (
            <div className="validation-warnings">
              <h4>⚠️ File Warnings</h4>
              <ul>
                {fileValidation.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
              <p>You can still proceed, but the import may not work as expected.</p>
            </div>
          )}

          <button 
            onClick={proceedToStep2} 
            disabled={!selectedFile || !fileValidation.isValid || isLoading || isLoadingHistory}
            className="button-common button-primary"
          >
            {(isLoading && currentStep === 1 && !isLoadingHistory && selectedFile) ? 'Uploading & Processing...' : 
             (isLoadingHistory && currentStep === 1) ? 'Loading Data...' : 
             (selectedDefaultMapping && defaultMappingName) ? 'Upload & Import with Default Mapping' : 
             'Upload & Continue'}
          </button>

          <div style={{marginTop: '30px'}}>
            <h4 className="import-header">Import History</h4>
            <ImportHistoryTable
              importHistory={importHistory}
              accounts={accounts}
              availableFileMaps={availableFileMaps}
              isLoading={isLoadingHistory}
                             selectedHistoryFileId={selectedHistoryFileId || undefined}
              onRowClick={handleHistoryRowClick}
              onUpdateAccount={handleSaveAccount}
              onUpdateMapping={handleSaveMapping}
              onUpdateOpeningBalance={handleSaveOpeningBalance}
              onUpdateClosingBalance={handleSaveClosingBalance}
              onDeleteFile={handleDeleteHistoryFile}
              showSelection={true}
              showActions={true}
              sortable={true}
              helpText={selectedHistoryFileId 
                ? "Click on any field above to edit file attributes. Opening and closing balances are editable inline." 
                : "Select a file to edit its attributes, mapping, or metadata."}
            />
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
          availableFieldMaps={availableFileMaps}
          initialFieldMapToLoad={initialFieldMapForStep2}
          onLoadFieldMapDetails={handleLoadFieldMapDetails}
          onSaveOrUpdateFieldMap={handleSaveOrUpdateFieldMap}
          currentlyLoadedFieldMapData={currentlyLoadedFieldMapData}
        />
      )}


    </div>
  );
};

export default ImportTransactionsView; 
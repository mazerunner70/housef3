import React, { useState, useCallback } from 'react';

// Placeholder for API calls - replace with your actual service calls
const FAKE_API = {
  fetchAccounts: async () => {
    console.log('Fetching accounts...');
    await new Promise(resolve => setTimeout(resolve, 500));
    return [
      { id: 'acc_123', name: 'Checking Account' },
      { id: 'acc_456', name: 'Savings Account' },
      { id: 'acc_789', name: 'Credit Card' },
    ];
  },
  fetchImportHistory: async () => {
    console.log('Fetching import history...');
    await new Promise(resolve => setTimeout(resolve, 500));
    return [
      { id: 'hist_1', fileName: 'jan_transactions.csv', accountName: 'Checking Account', mappingName: 'My Bank CSV', dateImported: '2023-02-01' },
      { id: 'hist_2', fileName: 'statement_feb.ofx', accountName: 'Savings Account', mappingName: 'N/A (OFX)', dateImported: '2023-03-05' },
    ];
  },
  uploadFile: async (file: File, accountId: string) => {
    console.log(`Uploading ${file.name} for account ${accountId}`);
    await new Promise(resolve => setTimeout(resolve, 1000));
    // Simulate parsing and preview data
    return {
      previewTransactions: [
        { id: 'txn_prev_1', date: '2023-01-05', description: 'Coffee Shop', amount: -5.75, potentialCategory: 'Food' },
        { id: 'txn_prev_2', date: '2023-01-06', description: 'Salary Deposit', amount: 2500, potentialCategory: 'Income' },
      ],
      duplicates: [
        { id: 'txn_prev_3', date: '2023-01-07', description: 'Already imported item', amount: -20.00 },
      ],
      // For CSV, this would be more complex
      detectedHeaders: file.type === 'text/csv' ? ['Date', 'Description', 'Amount'] : [],
    };
  },
  completeImport: async (previewData: any, csvMapping: any, duplicateStrategy: string) => {
    console.log('Completing import with data:', previewData, 'mapping:', csvMapping, 'strategy:', duplicateStrategy);
    await new Promise(resolve => setTimeout(resolve, 1000));
    return { success: true, importedCount: previewData.previewTransactions.length, newTransactionsLink: '/transactions?import_id=new_import_123' };
  }
};

// Placeholder types - define these more robustly based on your actual data models
interface Account {
  id: string;
  name: string;
}

interface ImportHistoryItem {
  id: string;
  fileName: string;
  accountName: string;
  mappingName: string;
  dateImported: string;
}

interface TransactionPreview {
  id: string;
  date: string;
  description: string;
  amount: number;
  potentialCategory?: string;
}

interface FilePreviewData {
  previewTransactions: TransactionPreview[];
  duplicates: TransactionPreview[];
  detectedHeaders: string[]; // For CSV
}

// Define your column mapping state structure for CSVs
interface CsvColumnMapping {
  [header: string]: 'date' | 'description' | 'amount' | 'payee' | 'notes' | 'skip';
}

const ImportTransactionsView: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [importHistory, setImportHistory] = useState<ImportHistoryItem[]>([]);
  const [filePreviewData, setFilePreviewData] = useState<FilePreviewData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [importResult, setImportResult] = useState<{ success: boolean; message: string; link?: string } | null>(null);
  const [csvColumnMapping, setCsvColumnMapping] = useState<CsvColumnMapping>({});
  const [duplicateStrategy, setDuplicateStrategy] = useState<'skip' | 'import' | 'overwrite'>('skip');


  // Fetch initial data for step 1
  React.useEffect(() => {
    if (currentStep === 1) {
      setIsLoading(true);
      Promise.all([FAKE_API.fetchAccounts(), FAKE_API.fetchImportHistory()])
        .then(([accs, history]) => {
          setAccounts(accs);
          setImportHistory(history);
        })
        .catch(error => console.error("Error fetching initial data:", error))
        .finally(() => setIsLoading(false));
    }
  }, [currentStep]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
      console.log("File selected:", event.target.files[0]);
    }
  };

  const handleFileDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      setSelectedFile(event.dataTransfer.files[0]);
      console.log("File dropped:", event.dataTransfer.files[0]);
    }
  }, []);

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  const proceedToStep2 = async () => {
    if (!selectedFile || !selectedAccount) {
      alert('Please select a file and an account.');
      return;
    }
    setIsLoading(true);
    try {
      const previewData = await FAKE_API.uploadFile(selectedFile, selectedAccount);
      setFilePreviewData(previewData);
      if (selectedFile.type === 'text/csv' && previewData.detectedHeaders) {
        // Initialize basic mapping for CSV
        const initialMapping: CsvColumnMapping = {};
        previewData.detectedHeaders.forEach(header => {
            // Basic auto-detection - can be improved
            if (header.toLowerCase().includes('date')) initialMapping[header] = 'date';
            else if (header.toLowerCase().includes('desc')) initialMapping[header] = 'description';
            else if (header.toLowerCase().includes('amount')) initialMapping[header] = 'amount';
            else initialMapping[header] = 'skip';
        });
        setCsvColumnMapping(initialMapping);
      }
      setCurrentStep(2);
    } catch (error) {
      console.error("Error uploading file:", error);
      alert("Failed to process file. See console for details.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleMappingChange = (header: string, mapTo: CsvColumnMapping[string]) => {
    setCsvColumnMapping(prev => ({ ...prev, [header]: mapTo }));
  };
  
  const proceedToStep3 = async () => {
    if (!filePreviewData) return;
    setIsLoading(true);
    try {
      const result = await FAKE_API.completeImport(filePreviewData, csvColumnMapping, duplicateStrategy);
      if (result.success) {
        setImportResult({ success: true, message: `Successfully imported ${result.importedCount} transactions.`, link: result.newTransactionsLink });
      } else {
        setImportResult({ success: false, message: "Import failed. Please try again." });
      }
      setCurrentStep(3);
    } catch (error) {
      console.error("Error completing import:", error);
      setImportResult({ success: false, message: "Import failed. An unexpected error occurred." });
      setCurrentStep(3);
    } finally {
      setIsLoading(false);
    }
  };

  const resetProcess = () => {
    setCurrentStep(1);
    setSelectedFile(null);
    setSelectedAccount('');
    setFilePreviewData(null);
    setImportResult(null);
    setCsvColumnMapping({});
  };

  const styles: { [key: string]: React.CSSProperties } = {
    container: { padding: '20px', fontFamily: 'Arial, sans-serif' },
    stepContainer: { border: '1px solid #eee', padding: '20px', borderRadius: '8px', marginBottom: '20px', background: '#f9f9f9' },
    header: { marginBottom: '20px', borderBottom: '1px solid #ddd', paddingBottom: '10px' },
    button: { padding: '10px 15px', margin: '5px', fontSize: '16px', cursor: 'pointer', borderRadius: '5px', border: '1px solid #ccc', background: '#e7e7e7' },
    primaryButton: { background: '#007bff', color: 'white', border: '1px solid #007bff' },
    input: { padding: '10px', margin: '5px 0 15px 0', border: '1px solid #ccc', borderRadius: '4px', width: 'calc(100% - 22px)' },
    select: { padding: '10px', margin: '5px 0 15px 0', border: '1px solid #ccc', borderRadius: '4px', width: '100%' },
    dropZone: { border: '2px dashed #ccc', padding: '30px', textAlign: 'center', marginBottom: '20px', background: '#fff', borderRadius: '8px' },
    historyTable: { width: '100%', borderCollapse: 'collapse', marginTop: '15px' },
    historyThTd: { border: '1px solid #ddd', padding: '8px', textAlign: 'left' },
    previewTable: { width: '100%', borderCollapse: 'collapse', marginTop: '15px' },
    previewThTd: { border: '1px solid #ddd', padding: '8px', textAlign: 'left' },
    label: { display: 'block', marginBottom: '5px', fontWeight: 'bold'},
    mappingSelect: { padding: '8px', marginLeft: '10px', borderRadius: '4px', border: '1px solid #ccc' },
    duplicateOptions: { marginTop: '15px', marginBottom: '15px' },
    duplicateLabel: { marginRight: '10px' },
    resultMessage: { padding: '15px', borderRadius: '5px', marginTop: '20px', textAlign: 'center' },
    successMessage: { background: '#d4edda', color: '#155724', border: '1px solid #c3e6cb' },
    errorMessage: { background: '#f8d7da', color: '#721c24', border: '1px solid #f5c6cb' },
    loadingOverlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'white', fontSize: '20px', zIndex: 1000 }
  };

  if (isLoading) {
    return <div style={styles.loadingOverlay}>Loading...</div>;
  }

  return (
    <div style={styles.container}>
      <h2>Import Transactions</h2>
      <p>Follow the steps below to import your transaction data.</p>

      {currentStep === 1 && (
        <div style={styles.stepContainer}>
          <h3 style={styles.header}>Step 1: File Upload & Account Selection</h3>
          
          <label htmlFor="account-select" style={styles.label}>Select Account:</label>
          <select 
            id="account-select"
            value={selectedAccount} 
            onChange={e => setSelectedAccount(e.target.value)} 
            style={styles.select}
            disabled={accounts.length === 0}
          >
            <option value="">{accounts.length === 0 ? "Loading accounts..." : "-- Select an Account --"}</option>
            {accounts.map(acc => <option key={acc.id} value={acc.id}>{acc.name}</option>)}
          </select>

          <label style={styles.label}>Upload Transaction File (OFX, QFX, CSV):</label>
          <div 
            onDrop={handleFileDrop} 
            onDragOver={handleDragOver} 
            style={styles.dropZone}
          >
            {selectedFile ? `Selected: ${selectedFile.name}` : 'Drag & drop your file here, or click to select.'}
            <input 
              type="file" 
              onChange={handleFileChange} 
              accept=".ofx,.qfx,.csv" 
              style={{ display: 'block', marginTop: '10px', opacity: selectedFile ? 0 : 1 }} // Hide if file already selected via drag/drop to simplify UI
              onClick={(e) => { if (selectedFile) e.preventDefault(); /* To allow re-selecting if needed, or just remove this */ }}
            />
          </div>
          {selectedFile && <p>File to upload: <strong>{selectedFile.name}</strong> ({Math.round(selectedFile.size / 1024)} KB)</p>}

          <button 
            onClick={proceedToStep2} 
            disabled={!selectedFile || !selectedAccount || isLoading}
            style={{...styles.button, ...styles.primaryButton}}
          >
            {isLoading ? 'Processing...' : 'Next: Preview & Map'}
          </button>

          <div style={{marginTop: '30px'}}>
            <h4 style={styles.header}>Import History & Saved Mappings</h4>
            {importHistory.length > 0 ? (
              <table style={styles.historyTable}>
                <thead>
                  <tr>
                    <th style={styles.historyThTd}>File Name</th>
                    <th style={styles.historyThTd}>Account</th>
                    <th style={styles.historyThTd}>Mapping/Type</th>
                    <th style={styles.historyThTd}>Date Imported</th>
                    <th style={styles.historyThTd}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {importHistory.map(item => (
                    <tr key={item.id}>
                      <td style={styles.historyThTd}>{item.fileName}</td>
                      <td style={styles.historyThTd}>{item.accountName}</td>
                      <td style={styles.historyThTd}>{item.mappingName}</td>
                      <td style={styles.historyThTd}>{item.dateImported}</td>
                      <td style={styles.historyThTd}>
                        <button style={{...styles.button, padding: '5px 10px'}} onClick={() => alert('Re-use mapping for ' + item.fileName + ' (not implemented)')}>Re-use Mapping</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p>No import history found.</p>}
          </div>
        </div>
      )}

      {currentStep === 2 && filePreviewData && (
        <div style={styles.stepContainer}>
          <h3 style={styles.header}>Step 2: Preview, Mapping (CSV), & Confirmation</h3>
          
          {selectedFile?.type === 'text/csv' && filePreviewData.detectedHeaders.length > 0 && (
            <div>
              <h4>CSV Column Mapping</h4>
              <p>Map the columns from your CSV file to the standard transaction fields.</p>
              {filePreviewData.detectedHeaders.map(header => (
                <div key={header} style={{ marginBottom: '10px' }}>
                  <strong>{header}:</strong>
                  <select 
                    value={csvColumnMapping[header] || 'skip'}
                    onChange={e => handleMappingChange(header, e.target.value as CsvColumnMapping[string])}
                    style={styles.mappingSelect}
                  >
                    <option value="skip">Skip this column</option>
                    <option value="date">Date</option>
                    <option value="description">Description</option>
                    <option value="amount">Amount</option>
                    <option value="payee">Payee</option>
                    <option value="notes">Notes</option>
                    {/* Add other target fields as needed */}
                  </select>
                </div>
              ))}
            </div>
          )}

          <h4>Transaction Preview</h4>
          {filePreviewData.previewTransactions.length > 0 ? (
            <table style={styles.previewTable}>
              <thead>
                <tr>
                  <th style={styles.previewThTd}>Date</th>
                  <th style={styles.previewThTd}>Description</th>
                  <th style={styles.previewThTd}>Amount</th>
                  <th style={styles.previewThTd}>Potential Category</th>
                </tr>
              </thead>
              <tbody>
                {filePreviewData.previewTransactions.map(txn => (
                  <tr key={txn.id}>
                    <td style={styles.previewThTd}>{txn.date}</td>
                    <td style={styles.previewThTd}>{txn.description}</td>
                    <td style={styles.previewThTd}>{txn.amount.toFixed(2)}</td>
                    <td style={styles.previewThTd}>{txn.potentialCategory || 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p>No transactions to preview. This might indicate an issue with the file or an empty file.</p>}

          {filePreviewData.duplicates.length > 0 && (
            <div style={{marginTop: '20px'}}>
              <h4>Potential Duplicates Found ({filePreviewData.duplicates.length})</h4>
              <p>The following transactions appear to be duplicates of existing ones:</p>
              {/* Ideally, list duplicates here similarly to preview table */}
              <div style={styles.duplicateOptions}>
                <strong style={styles.label}>How to handle duplicates:</strong>
                <label style={styles.duplicateLabel}>
                  <input type="radio" name="duplicateStrategy" value="skip" checked={duplicateStrategy === 'skip'} onChange={() => setDuplicateStrategy('skip')} /> Skip
                </label>
                <label style={styles.duplicateLabel}>
                  <input type="radio" name="duplicateStrategy" value="import" checked={duplicateStrategy === 'import'} onChange={() => setDuplicateStrategy('import')} /> Import Anyway
                </label>
                <label style={styles.duplicateLabel}>
                  <input type="radio" name="duplicateStrategy" value="overwrite" checked={duplicateStrategy === 'overwrite'} onChange={() => setDuplicateStrategy('overwrite')} /> Overwrite Existing (Use with caution)
                </label>
              </div>
            </div>
          )}
          
          <p style={{marginTop: '20px'}}>
            Summary: About to import <strong>{filePreviewData.previewTransactions.length}</strong> new transactions.
            {filePreviewData.duplicates.length > 0 && ` Found ${filePreviewData.duplicates.length} potential duplicates which will be ${duplicateStrategy === 'skip' ? 'skipped' : duplicateStrategy === 'import' ? 'imported' : 'overwritten'}.`}
          </p>

          <button onClick={() => setCurrentStep(1)} style={styles.button} disabled={isLoading}>Back</button>
          <button onClick={proceedToStep3} style={{...styles.button, ...styles.primaryButton}} disabled={isLoading}>
            {isLoading ? 'Importing...' : 'Complete Import'}
          </button>
        </div>
      )}

      {currentStep === 3 && importResult && (
        <div style={styles.stepContainer}>
          <h3 style={styles.header}>Step 3: Completion Summary</h3>
          <div style={{...styles.resultMessage, ...(importResult.success ? styles.successMessage : styles.errorMessage)}}>
            {importResult.message}
          </div>
          {importResult.success && importResult.link && (
            <p style={{textAlign: 'center', marginTop: '15px'}}>
              <a href={importResult.link} style={{...styles.button, textDecoration: 'none'}}>View Imported Transactions</a>
            </p>
          )}
          <button onClick={resetProcess} style={{...styles.button, ...styles.primaryButton, display: 'block', margin: '20px auto 0'}}>
            Import Another File
          </button>
        </div>
      )}
    </div>
  );
};

export default ImportTransactionsView; 
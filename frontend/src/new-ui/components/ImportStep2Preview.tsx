import React, { useState, useEffect } from 'react';

// Define types for the component's props and state
export interface TransactionRow {
  // Example fields - adjust based on actual parsed data structure
  id: string | number;
  date?: string;
  description?: string;
  amount?: number;
  // ... other potential fields
  [key: string]: any; // Allow arbitrary columns from CSV
}

export interface ColumnMapping {
  csvColumn: string | null; // Allow null for unmapped or initially loaded state
  targetField: string;    // Target field is now always defined for a mapping entry
  isValid?: boolean;       // For regex validation visual cue
}

interface ImportStep2PreviewProps {
  parsedData: TransactionRow[];
  fileType: 'csv' | 'ofx' | 'qfx'; // To determine if mapping is needed
  // Headers from the CSV file, if applicable
  csvHeaders?: string[];
  // Pre-existing mapping configuration, if any
  existingMapping?: ColumnMapping[];
  onCompleteImport: (mappedData: TransactionRow[], mappingConfig?: ColumnMapping[]) => void;
  onCancel: () => void;
  // Target fields that the user can map CSV columns to
  targetTransactionFields: { field: string; label: string; regex?: string }[];
}

const ImportStep2Preview: React.FC<ImportStep2PreviewProps> = ({
  parsedData,
  fileType,
  csvHeaders = [],
  existingMapping,
  onCompleteImport,
  onCancel,
  targetTransactionFields,
}) => {
  const [transactionData, setTransactionData] = useState<TransactionRow[]>(parsedData);
  const [columnMappings, setColumnMappings] = useState<ColumnMapping[]>([]);
  const [isMappingValid, setIsMappingValid] = useState(false);

  useEffect(() => {
    console.log("[ImportStep2Preview] Props received - parsedData:", parsedData);
    console.log("[ImportStep2Preview] Props received - fileType:", fileType);
    console.log("[ImportStep2Preview] Props received - csvHeaders:", csvHeaders);
    console.log("[ImportStep2Preview] Props received - existingMapping:", existingMapping);
  }, [parsedData, fileType, csvHeaders, existingMapping]);

  // Effect to initialize/reset columnMappings based on targetTransactionFields or existingMapping prop
  useEffect(() => {
    if (fileType === 'csv') {
      const initialMappings = targetTransactionFields.map(ttf => {
        // Find if an existing mapping was provided for this target field
        const loadedMapping = (existingMapping || []).find(em => em.targetField === ttf.field);
        return {
          targetField: ttf.field, // The target field itself
          csvColumn: loadedMapping?.csvColumn || null, // The CSV column mapped to it
          isValid: loadedMapping?.isValid, // Carry over validity if loaded
        };
      });
      console.log("[ImportStep2Preview] CSV - Initializing columnMappings based on target fields:", initialMappings);
      setColumnMappings(initialMappings);
    } else {
      setColumnMappings([]); // Clear mappings for non-CSV types
      setIsMappingValid(true);
      console.log("[ImportStep2Preview] Non-CSV - Cleared columnMappings, set isMappingValid to true.");
    }
  }, [fileType, csvHeaders, targetTransactionFields, existingMapping]); // csvHeaders is included to re-init if they change

  useEffect(() => {
    console.log("[ImportStep2Preview] Mapping useEffect triggered. fileType:", fileType, "parsedData length:", parsedData.length, "columnMappings:", columnMappings);
    if (fileType === 'csv') {
      // Wait for columnMappings to be initialized for CSV files
      if (columnMappings.length === 0 && csvHeaders.length > 0) {
        console.log("[ImportStep2Preview] CSV - columnMappings not yet initialized, skipping data processing in this effect run.");
        return; // Exit early if columnMappings isn't ready
      }

      const hasActiveMappings = columnMappings.some(m => m.csvColumn !== null);
      console.log("[ImportStep2Preview] CSV - hasActiveMappings:", hasActiveMappings);

      if (hasActiveMappings) {
        const updatedData = parsedData.map(row => {
          const newRow: TransactionRow = { id: row.id };
          columnMappings.forEach(mapping => {
            // Ensure mapping.csvColumn is a valid string before using it as an index
            if (mapping.targetField && mapping.csvColumn && row[mapping.csvColumn] !== undefined) {
              const targetFieldConfig = targetTransactionFields.find(f => f.field === mapping.targetField);
              let isValid = true;
              if (targetFieldConfig?.regex) {
                isValid = new RegExp(targetFieldConfig.regex).test(String(row[mapping.csvColumn]));
              }
              newRow[mapping.targetField] = row[mapping.csvColumn]; // Safe now
            }
          });
          return newRow;
        });
        console.log("[ImportStep2Preview] CSV - Transformed data based on active mappings (updatedData):", updatedData);
        setTransactionData(updatedData);
      } else {
        // No active mappings yet, show raw parsedData
        console.log("[ImportStep2Preview] CSV - No active mappings, setting transactionData to raw parsedData:", parsedData);
        setTransactionData(parsedData);
      }

      // Validation logic for isMappingValid (can be adjusted based on whether raw preview is considered 'valid' for import)
      const requiredTargetFields = targetTransactionFields.filter(f => f.regex).map(f => f.field);
      const mappedTargetFields = columnMappings.map(m => m.targetField).filter(Boolean);
      const allRequiredFieldsMapped = requiredTargetFields.every(rf => mappedTargetFields.includes(rf));
      const allIndividualMappingsValid = columnMappings.every(m => m.targetField ? m.isValid !== false : true);
      console.log("[ImportStep2Preview] CSV - Validation: allRequiredFieldsMapped:", allRequiredFieldsMapped, "allIndividualMappingsValid:", allIndividualMappingsValid);
      setIsMappingValid(allRequiredFieldsMapped && allIndividualMappingsValid);

    } else {
      console.log("[ImportStep2Preview] Non-CSV - Setting transactionData directly from parsedData:", parsedData);
      setTransactionData(parsedData);
      setIsMappingValid(true);
    }
  }, [columnMappings, parsedData, fileType, targetTransactionFields]);

  const handleMappingChange = (targetFieldToMap: string, selectedCsvColumn: string | null) => {
    setColumnMappings(prevMappings => {
      let newMappings = prevMappings.map(m => {
        // If the selectedCsvColumn (if not null) was previously used by a *different* target field,
        // unmap that other target field to enforce one-to-one CSV column usage.
        if (selectedCsvColumn && m.csvColumn === selectedCsvColumn && m.targetField !== targetFieldToMap) {
          return { ...m, csvColumn: null, isValid: undefined };
        }
        // If this is the target field we are updating, set its new csvColumn.
        if (m.targetField === targetFieldToMap) {
          return { ...m, csvColumn: selectedCsvColumn, isValid: undefined }; // isValid will be recalculated.
        }
        return m;
      });

      // Recalculate isValid for all mappings that now have a csvColumn assigned.
      if (parsedData && parsedData.length > 0) {
        newMappings = newMappings.map(mapping => {
          if (mapping.targetField && mapping.csvColumn) { // Only if actively mapped
            const targetFieldConfig = targetTransactionFields.find(f => f.field === mapping.targetField);
            if (targetFieldConfig?.regex) {
              const isColumnDataValid = parsedData.every(rawRow => {
                const cellValue = rawRow[mapping.csvColumn!]; // csvColumn is asserted non-null here
                // If cellValue is undefined/null, regex test might be misleading. Treat as valid if regex allows empty or field isn't strictly required.
                // For now, if cellValue is undefined, it won't match most regexes unless they account for it (e.g. `.*` or `^$`).
                return cellValue !== undefined ? new RegExp(targetFieldConfig.regex!).test(String(cellValue)) : false; // Consider undefined cell data as not matching
              });
              return { ...mapping, isValid: isColumnDataValid };
            }
            return { ...mapping, isValid: true }; // No regex for this target field, so consider it valid if mapped.
          }
          // If not actively mapped (no csvColumn), clear isValid.
          return { ...mapping, isValid: undefined }; 
        });
      }
      console.log("[ImportStep2Preview] handleMappingChange - newMappings with updated isValid:", newMappings);
      return newMappings;
    });
  };
  
  const handleSaveMapping = () => {
    // Logic to save columnMappings (e.g., to localStorage or send to backend)
    console.log("Saving mapping configuration:", columnMappings);
    alert("Mapping saved!"); // Placeholder
  };

  const renderCsvMappingControls = () => {
    if (fileType !== 'csv') return null;

    // Get a list of CSV column names that are already mapped to some target field.
    const mappedCsvColumns = columnMappings
      .map(m => m.csvColumn)
      .filter((csvCol): csvCol is string => csvCol !== null); // Type guard for filtering nulls

    return (
      <div className="mb-4 p-4 border rounded-md">
        <h3 className="text-lg font-semibold mb-2">Map Target Fields to CSV Columns</h3>
        <p className="text-sm text-gray-600 mb-3">Select which CSV column corresponds to each target transaction field. Each CSV column can only be used once.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-4">
          {targetTransactionFields.map(targetFieldConfig => {
            const currentMapping = columnMappings.find(m => m.targetField === targetFieldConfig.field);
            const currentlyMappedCsvColumn = currentMapping?.csvColumn || '';

            // Options for this dropdown: unmapped csvHeaders + the one currently mapped to this targetField (if any).
            const dropdownOptions = csvHeaders.filter(
              header => header !== '' && (!mappedCsvColumns.includes(header) || header === currentlyMappedCsvColumn)
            );

            return (
              <div 
                key={targetFieldConfig.field} 
                className={`p-3 border rounded-lg shadow-sm ${currentMapping?.isValid === true ? 'border-green-500' : currentMapping?.isValid === false ? 'border-red-500' : 'border-gray-200'}`}
              >
                <label htmlFor={`map-target-${targetFieldConfig.field}`} className="block text-sm font-medium text-gray-800 mb-1">
                  {targetFieldConfig.label}
                </label>
                {targetFieldConfig.regex && (
                  <p className="text-xs text-gray-500 mb-1 italic">Expected format (regex): {targetFieldConfig.regex}</p>
                )}
                <select
                  id={`map-target-${targetFieldConfig.field}`}
                  value={currentlyMappedCsvColumn}
                  onChange={e => handleMappingChange(targetFieldConfig.field, e.target.value || null)}
                  className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="">-- Unmapped --</option>
                  {dropdownOptions.map(header => (
                    <option key={header} value={header}>
                      {header}
                    </option>
                  ))}
                </select>
                {currentMapping?.csvColumn && currentMapping.isValid === false && (
                  <p className="text-xs text-red-600 mt-1">
                    Data in mapped CSV column ('{currentMapping.csvColumn}') does not match expected format.
                  </p>
                )}
                {currentMapping?.csvColumn && currentMapping.isValid === true && (
                  <p className="text-xs text-green-600 mt-1">
                    Mapped to '{currentMapping.csvColumn}' - format OK.
                  </p>
                )}
              </div>
            );
          })}
        </div>
        {/* <button onClick={handleSaveMapping} ...>Save Current Mapping</button> */}
      </div>
    );
  };

  const renderTransactionPreviewTable = () => {
    console.log("[ImportStep2Preview] renderTransactionPreviewTable - transactionData:", transactionData);
    if (!transactionData || transactionData.length === 0) {
      console.log("[ImportStep2Preview] renderTransactionPreviewTable - No transactions to preview.");
      return <p>No transactions to preview.</p>;
    }

    let headers: string[] = [];
    if (fileType === 'csv') {
      // Check if there are any *active* user mappings (csvColumn is not null)
      const hasActiveMappings = columnMappings.some(m => m.csvColumn !== null);
      if (hasActiveMappings) {
        headers = columnMappings
          .filter(m => m.targetField && m.csvColumn) // Only include targetFields that are actively mapped
          .map(m => m.targetField);
      } else {
        headers = csvHeaders;
      }
    } else {
      if (transactionData.length > 0) {
        headers = Object.keys(transactionData[0]).filter(key => key !== 'id');
      }
    }

    const displayHeaders = headers.filter(h => h !== 'id' && h !== '');
    console.log("[ImportStep2Preview] renderTransactionPreviewTable - displayHeaders:", displayHeaders);

    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {displayHeaders.map(header => (
                <th
                  key={header}
                  scope="col"
                  className="px-6 py-3 text-left font-medium text-gray-500 uppercase tracking-wider"
                  style={{ fontSize: '0.6rem' }}
                >
                  {targetTransactionFields.find(f => f.field === header)?.label || header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {transactionData.map((row, rowIndex) => {
              console.log(`[ImportStep2Preview] Rendering Row ${rowIndex} data:`, row); // Log the whole row object
              return (
                <tr key={row.id || rowIndex}>
                  {displayHeaders.map(header => {
                    const cellValue = row[header];
                    // Log details for each cell
                    console.log(`[ImportStep2Preview] Row ${rowIndex}, Header '${header}', Value: '${cellValue}', Type: ${typeof cellValue}`);
                    return (
                      <td 
                        key={header} 
                        className="px-6 py-4 whitespace-nowrap text-gray-500"
                        style={{ fontSize: '0.7rem' }}
                      >
                        {/* More explicit rendering for debugging */}
                        {cellValue === undefined
                          ? "(undefined)"
                          : cellValue === null
                          ? "(null)"
                          : String(cellValue).trim() === ''
                          ? "(empty str)"
                          : String(cellValue)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="p-4 md:p-6">
      <h2 className="text-xl md:text-2xl font-semibold mb-4">Step 2: Preview, Map Columns (if CSV), and Confirm</h2>

      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">Transaction Preview</h3>
        {renderTransactionPreviewTable()}
      </div>

      {fileType === 'csv' && renderCsvMappingControls()}

      <div className="flex justify-end space-x-3 mt-6">
        <button
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          Cancel
        </button>
        <button
          onClick={() => onCompleteImport(transactionData, fileType === 'csv' ? columnMappings : undefined)}
          disabled={!isMappingValid}
          className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
        >
          Complete Import
        </button>
      </div>
    </div>
  );
};

export default ImportStep2Preview; 
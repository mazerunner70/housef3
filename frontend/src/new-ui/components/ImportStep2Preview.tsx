import React, { useState, useEffect } from 'react';
import './ImportStep2Preview.css'; // Import the new CSS file

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

  // Effect to process data and set overall form validity (and update columnMappings isValid status)
  useEffect(() => {
    console.log("[ImportStep2Preview] Mapping/Validation useEffect. fileType:", fileType, "parsedData length:", parsedData.length, "columnMappings:", columnMappings);
    if (fileType === 'csv') {
      if (columnMappings.length === 0 && csvHeaders.length > 0) {
        console.log("[ImportStep2Preview] CSV - columnMappings not yet initialized, skipping validation in this effect run.");
        return;
      }

      // This effect will now primarily be for updating the isValid status in columnMappings
      // and the overall isMappingValid for the import button.
      // transactionData for the table will be set directly from parsedData.
      setTransactionData(parsedData); // Always show raw parsedData in the table
      console.log("[ImportStep2Preview] CSV - Set transactionData to raw parsedData for table display.", parsedData);

      // Validate individual mappings (this part is for the mapping controls UI)
      const updatedMappingsWithValidity = columnMappings.map(mapping => {
        if (mapping.targetField && mapping.csvColumn) {
          const targetFieldConfig = targetTransactionFields.find(f => f.field === mapping.targetField);
          if (targetFieldConfig?.regex && parsedData.length > 0) {
            const isColumnDataValid = parsedData.every(rawRow => {
              const cellValue = rawRow[mapping.csvColumn!];
              return cellValue !== undefined ? new RegExp(targetFieldConfig.regex!).test(String(cellValue)) : false;
            });
            return { ...mapping, isValid: isColumnDataValid };
          }
          return { ...mapping, isValid: true }; // No regex or no data to check, consider valid if mapped
        }
        return { ...mapping, isValid: undefined }; // Not actively mapped, clear isValid
      });
      // Only update if there are actual changes in validity to avoid potential loops if objects are different but content same
      if (JSON.stringify(columnMappings) !== JSON.stringify(updatedMappingsWithValidity)) {
         console.log("[ImportStep2Preview] CSV - Updating columnMappings with new validity states:", updatedMappingsWithValidity);
        setColumnMappings(updatedMappingsWithValidity);
      }
      
      // Overall form validity for the import button
      const requiredTargetFields = targetTransactionFields.filter(f => f.regex).map(f => f.field);
      const mappedTargetFieldsWithCsvColumn = columnMappings.filter(m => m.csvColumn !== null).map(m => m.targetField);
      const allRequiredFieldsMapped = requiredTargetFields.every(rf => mappedTargetFieldsWithCsvColumn.includes(rf));
      const allCurrentlyMappedColumnsValid = columnMappings.every(m => m.csvColumn ? m.isValid === true : true); // Only check validity if mapped

      console.log("[ImportStep2Preview] CSV - Validation for import: allRequiredFieldsMapped:", allRequiredFieldsMapped, "allCurrentlyMappedColumnsValid:", allCurrentlyMappedColumnsValid);
      setIsMappingValid(allRequiredFieldsMapped && allCurrentlyMappedColumnsValid);

    } else { // Non-CSV
      console.log("[ImportStep2Preview] Non-CSV - Setting transactionData directly from parsedData:", parsedData);
      setTransactionData(parsedData);
      setIsMappingValid(true); // Non-CSV files are considered valid for import by default
    }
  }, [columnMappings, parsedData, fileType, targetTransactionFields, csvHeaders]); // Added csvHeaders as it's used in guard

  const handleMappingChange = (targetFieldToMap: string, selectedCsvColumn: string | null) => {
    // When a mapping changes, we trigger a re-calculation of validity in the useEffect above
    // by updating columnMappings. The useEffect will then handle setting isValid.
    setColumnMappings(prevMappings => {
      const newMappings = prevMappings.map(m => {
        if (selectedCsvColumn && m.csvColumn === selectedCsvColumn && m.targetField !== targetFieldToMap) {
          return { ...m, csvColumn: null, isValid: undefined };
        }
        if (m.targetField === targetFieldToMap) {
          return { ...m, csvColumn: selectedCsvColumn, isValid: undefined }; // Set isValid to undefined, useEffect will re-calc
        }
        return m;
      });
      console.log("[ImportStep2Preview] handleMappingChange - Proposed newMappings (isValid will be re-calculated by effect):", newMappings);
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

    const mappedCsvColumns = columnMappings
      .map(m => m.csvColumn)
      .filter((csvCol): csvCol is string => csvCol !== null);

    return (
      // Main container for the mapping section
      <div className="csv-mapping-controls-container">
        <h3 className="csv-mapping-header">Map Target Fields to CSV Columns</h3>
        <p className="csv-mapping-description">Select CSV column for each target field. Used CSV columns become unavailable for other fields.</p>
        {/* Grid container for individual mapping items */}
        <div className="csv-mapping-grid">
          {targetTransactionFields.map(targetFieldConfig => {
            const currentMapping = columnMappings.find(m => m.targetField === targetFieldConfig.field);
            const currentlyMappedCsvColumn = currentMapping?.csvColumn || '';

            const dropdownOptions = csvHeaders.filter(
              header => header !== '' && (!mappedCsvColumns.includes(header) || header === currentlyMappedCsvColumn)
            );
            
            // Determine border class based on validity for the item wrapper
            let itemWrapperClass = "csv-mapping-item";
            if (currentMapping?.isValid === true) {
              itemWrapperClass += ' item-valid';
            } else if (currentMapping?.isValid === false) {
              itemWrapperClass += ' item-invalid';
            }

            return (
              <div key={targetFieldConfig.field} className={itemWrapperClass}>
                <label htmlFor={`map-target-${targetFieldConfig.field}`} className="csv-mapping-item-label">
                  {targetFieldConfig.label}
                </label>
                <select
                  id={`map-target-${targetFieldConfig.field}`}
                  value={currentlyMappedCsvColumn}
                  onChange={e => handleMappingChange(targetFieldConfig.field, e.target.value || null)}
                  className="csv-mapping-item-select"
                >
                  <option value="">-- Unmapped --</option>
                  {dropdownOptions.map(header => (
                    <option key={header} value={header}>
                      {header}
                    </option>
                  ))}
                </select>
                {currentMapping?.csvColumn && currentMapping.isValid === false && (
                  <p className="csv-mapping-item-error-message">
                    Data in mapped CSV column ('{currentMapping.csvColumn}') does not match expected format.
                  </p>
                )}
                {currentMapping?.csvColumn && currentMapping.isValid === true && (
                  <p className="csv-mapping-item-success-message">
                    Mapped to '{currentMapping.csvColumn}' - format OK.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderTransactionPreviewTable = () => {
    console.log("[ImportStep2Preview] renderTransactionPreviewTable - transactionData (should be raw parsedData):", transactionData);
    if (!transactionData || transactionData.length === 0) {
      console.log("[ImportStep2Preview] renderTransactionPreviewTable - No transactions to preview.");
      return <p>No transactions to preview.</p>;
    }

    const displayHeaders = (fileType === 'csv' ? csvHeaders : 
                           (transactionData.length > 0 ? Object.keys(transactionData[0]) : []))
                           .filter(h => h !== 'id' && h !== '');
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
              console.log(`[ImportStep2Preview] Rendering Row ${rowIndex} (raw data):`, row);
              return (
                <tr key={row.id || rowIndex}>
                  {displayHeaders.map(originalCsvHeader => {
                    const cellValue = row[originalCsvHeader];
                    const mappingInfo = columnMappings.find(m => m.csvColumn === originalCsvHeader);
                    
                    let cellClassName = "px-6 py-4 whitespace-nowrap text-gray-500 preview-table-cell";
                    if (mappingInfo && mappingInfo.isValid === true) {
                      cellClassName += ' cell-valid-border';
                    } else if (mappingInfo && mappingInfo.isValid === false) {
                      cellClassName += ' cell-invalid-border';
                    }

                    return (
                      <td 
                        key={originalCsvHeader} 
                        className={cellClassName}
                        style={{ fontSize: '0.7rem' }}
                      >
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
    <div className="import-step2-preview-container">
      <h2 className="step2-main-header">Step 2: Preview, Map Columns (if CSV), and Confirm</h2>

      {fileType === 'csv' && renderCsvMappingControls()}

      <div className="transaction-preview-section">
        <h3 className="transaction-preview-header">Transaction Preview</h3>
        {renderTransactionPreviewTable()}
      </div>

      <div className="step2-action-buttons">
        <button
          onClick={onCancel}
          className="button-cancel"
        >
          Cancel
        </button>
        <button
          onClick={() => onCompleteImport(transactionData, fileType === 'csv' ? columnMappings : undefined)}
          disabled={!isMappingValid}
          className="button-confirm"
        >
          Complete Import
        </button>
      </div>
    </div>
  );
};

export default ImportStep2Preview; 
import React, { useState, useEffect, useCallback } from 'react';
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
  onCompleteImport: (
    mappedData: TransactionRow[], 
    // Changed: now expects an object with id and name of the field map to associate, or undefined
    finalFieldMapToAssociate?: { id: string; name: string }
  ) => void;
  onCancel: () => void;
  // Target fields that the user can map CSV columns to
  targetTransactionFields: { field: string; label: string; regex?: string }[];

  // New props for named field map management
  availableFieldMaps: Array<{ id: string; name: string }>;
  initialFieldMapToLoad?: { id: string; name: string }; // ID and Name of map associated with the current file (if any)
  onLoadFieldMapDetails: (fieldMapId: string) => Promise<ColumnMapping[] | undefined>; // To fetch details when user selects
  onSaveOrUpdateFieldMap: (
    params: {
      mapIdToUpdate?: string; // If present, it's an update
      name: string;
      // Mappings to save should be in the format { csvColumn: string, targetField: string }
      // Only include mappings where csvColumn is actually set.
      mappingsToSave: Array<{ csvColumn: string; targetField: string }>;
    }
  ) => Promise<{ newMapId?: string; newName?: string; success: boolean; message?: string }>;
}

const ImportStep2Preview: React.FC<ImportStep2PreviewProps> = ({
  parsedData,
  fileType,
  csvHeaders = [],
  existingMapping,
  onCompleteImport,
  onCancel,
  targetTransactionFields,
  // New props
  availableFieldMaps,
  initialFieldMapToLoad, // Will be used to set initial state for dropdown and name
  onLoadFieldMapDetails,
  onSaveOrUpdateFieldMap,
}) => {
  const [transactionData, setTransactionData] = useState<TransactionRow[]>(parsedData);
  const [columnMappings, setColumnMappings] = useState<ColumnMapping[]>([]);
  const [isMappingValid, setIsMappingValid] = useState(false);

  // New state for named field map management
  const [selectedFieldMapId, setSelectedFieldMapId] = useState<string | null>(null);
  const [fieldMapNameInput, setFieldMapNameInput] = useState<string>('');
  const [isSavingMapping, setIsSavingMapping] = useState<boolean>(false); // For loading state on save button
  const [mappingSaveMessage, setMappingSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    console.log("[ImportStep2Preview] Props received - parsedData:", parsedData);
    console.log("[ImportStep2Preview] Props received - fileType:", fileType);
    console.log("[ImportStep2Preview] Props received - csvHeaders:", csvHeaders);
    console.log("[ImportStep2Preview] Props received - existingMapping:", existingMapping);
  }, [parsedData, fileType, csvHeaders, existingMapping]);

  // Effect to set initial selectedFieldMapId and fieldMapNameInput if initialFieldMapToLoad is provided
  // This effect also relies on existingMapping being potentially set by the parent after loading details
  useEffect(() => {
    if (initialFieldMapToLoad) {
      console.log("[ImportStep2Preview] Initial field map to load received:", initialFieldMapToLoad);
      setSelectedFieldMapId(initialFieldMapToLoad.id);
      setFieldMapNameInput(initialFieldMapToLoad.name);
      // existingMapping prop should contain the detailed mappings if successfully loaded by parent
      // The columnMappings initialization effect below will pick up this existingMapping.
    } else {
      // If no initial map, reset
      setSelectedFieldMapId(null);
      setFieldMapNameInput('');
    }
  }, [initialFieldMapToLoad]);

  // Effect to initialize/reset columnMappings based on targetTransactionFields or existingMapping prop
  useEffect(() => {
    if (fileType === 'csv') {
      const initialMappingsFromProps = existingMapping || []; // Use existingMapping if provided by parent
      
      // If existingMapping is provided, it means a map was pre-loaded. 
      // Otherwise, initialize based on targetTransactionFields for a new mapping setup.
      let determinedInitialMappings: ColumnMapping[];
      if (initialMappingsFromProps.length > 0) {
        console.log("[ImportStep2Preview] Using pre-loaded existingMapping for columnMappings:", initialMappingsFromProps);
        // Ensure all target fields are present, even if not in the loaded map (e.g. if target fields changed)
        determinedInitialMappings = targetTransactionFields.map(ttf => {
          const found = initialMappingsFromProps.find(em => em.targetField === ttf.field);
          return found || { targetField: ttf.field, csvColumn: null, isValid: undefined };
        });
      } else {
        console.log("[ImportStep2Preview] No pre-loaded mapping, initializing columnMappings based on target fields.");
        determinedInitialMappings = targetTransactionFields.map(ttf => ({
          targetField: ttf.field,
          csvColumn: null,
          isValid: undefined,
        }));
      }
      console.log("[ImportStep2Preview] CSV - Setting columnMappings:", determinedInitialMappings);
      setColumnMappings(determinedInitialMappings);
    } else {
      setColumnMappings([]);
      setIsMappingValid(true);
      console.log("[ImportStep2Preview] Non-CSV - Cleared columnMappings, set isMappingValid to true.");
    }
  }, [fileType, csvHeaders, targetTransactionFields, existingMapping]); // existingMapping is key here

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
  
  const handleFieldMapSelectionChange = useCallback(async (event: React.ChangeEvent<HTMLSelectElement>) => {
    const mapId = event.target.value;
    setMappingSaveMessage(null);
    if (mapId) {
      setSelectedFieldMapId(mapId);
      const selectedMap = availableFieldMaps.find(m => m.id === mapId);
      setFieldMapNameInput(selectedMap ? selectedMap.name : '');
      console.log(`[ImportStep2Preview] User selected field map ID: ${mapId}, Name: ${selectedMap?.name}`);
      try {
        const loadedMappings = await onLoadFieldMapDetails(mapId); // Parent fetches and transforms
        if (loadedMappings) {
            // Ensure all target fields are represented, merging with loaded mappings
            const newColMappings = targetTransactionFields.map(ttf => {
                const found = loadedMappings.find(lm => lm.targetField === ttf.field);
                return found || { targetField: ttf.field, csvColumn: null, isValid: undefined };
            });
            setColumnMappings(newColMappings);
            console.log("[ImportStep2Preview] Successfully loaded and set column mappings for selected map:", newColMappings);
        } else {
            console.warn("[ImportStep2Preview] Selected field map details could not be loaded or were empty.");
            // Optionally reset columnMappings to default if load fails or is empty
            setColumnMappings(targetTransactionFields.map(ttf => ({ targetField: ttf.field, csvColumn: null, isValid: undefined })));
        }
      } catch (error) {
        console.error("[ImportStep2Preview] Error loading field map details:", error);
        setMappingSaveMessage({ type: 'error', text: 'Error loading selected mapping details.' });
        // Reset to a default state for columnMappings if loading fails
        setColumnMappings(targetTransactionFields.map(ttf => ({ targetField: ttf.field, csvColumn: null, isValid: undefined })));
      }
    } else {
      // "-- Select a Mapping --" chosen
      setSelectedFieldMapId(null);
      setFieldMapNameInput(''); // Clear name input
      // Reset columnMappings to default (unmapped state)
      setColumnMappings(targetTransactionFields.map(ttf => ({
        targetField: ttf.field,
        csvColumn: null,
        isValid: undefined,
      })));
      console.log("[ImportStep2Preview] User deselected field map. Resetting column mappings.");
    }
  }, [availableFieldMaps, onLoadFieldMapDetails, targetTransactionFields]);

  const handlePersistCurrentMapping = async () => {
    if (!fieldMapNameInput.trim()) {
      setMappingSaveMessage({ type: 'error', text: 'Mapping name cannot be empty.' });
      return;
    }
    setIsSavingMapping(true);
    setMappingSaveMessage(null);

    const mappingsToSave = columnMappings
      .filter(m => m.csvColumn !== null) // Only include where a CSV column is actually selected
      .map(m => ({ csvColumn: m.csvColumn!, targetField: m.targetField })); // Transform to {csvColumn, targetField}

    if (mappingsToSave.length === 0) {
        setMappingSaveMessage({ type: 'error', text: 'No columns have been mapped. Please map at least one column.' });
        setIsSavingMapping(false);
        return;
    }

    console.log("[ImportStep2Preview] Attempting to save/update mapping. Name:", fieldMapNameInput, "ID to update:", selectedFieldMapId, "Mappings:", mappingsToSave);
    try {
      const result = await onSaveOrUpdateFieldMap({
        mapIdToUpdate: selectedFieldMapId || undefined, // Pass ID if updating
        name: fieldMapNameInput.trim(),
        mappingsToSave,
      });

      if (result.success) {
        setMappingSaveMessage({ type: 'success', text: selectedFieldMapId ? 'Mapping updated successfully!' : 'Mapping saved successfully!'});
        // If it was a new save and we got a new ID, or if name was updated for existing
        if (result.newMapId) {
            setSelectedFieldMapId(result.newMapId);
        }
        if (result.newName) { // Parent might return the (potentially sanitized/unique) name
            setFieldMapNameInput(result.newName);
        }
        // Parent should refresh the availableFieldMaps list and pass it down again, causing a re-render.
        // For now, we assume parent handles refresh. Or we could have a prop like `onMappingPersisted` to trigger parent refresh.
      } else {
        setMappingSaveMessage({ type: 'error', text: result.message || (selectedFieldMapId ? 'Failed to update mapping.' : 'Failed to save mapping.') });
      }
    } catch (error) {
      console.error("[ImportStep2Preview] Error persisting mapping:", error);
      setMappingSaveMessage({ type: 'error', text: 'An unexpected error occurred while saving.' });
    } finally {
      setIsSavingMapping(false);
    }
  };

  const renderCsvMappingControls = () => {
    if (fileType !== 'csv') return null;

    const mappedCsvColumns = columnMappings
      .map(m => m.csvColumn)
      .filter((csvCol): csvCol is string => csvCol !== null);

    return (
      <div className="csv-mapping-controls-container">
        {/* New Section for Selecting/Saving Named Mappings */}
        <div className="named-mapping-section">
          <h4 className="named-mapping-header">Field Mappings Profile</h4>
          {mappingSaveMessage && (
            <div className={`mapping-save-message ${mappingSaveMessage.type === 'success' ? 'message-success' : 'message-error'}`}>
              {mappingSaveMessage.text}
            </div>
          )}
          <div className="named-mapping-controls">
            <div className="named-mapping-control-item">
              <label htmlFor="field-map-select" className="named-mapping-label">Select Existing Profile:</label>
              <select 
                id="field-map-select"
                value={selectedFieldMapId || ''}
                onChange={handleFieldMapSelectionChange}
                className="named-mapping-select"
                disabled={isSavingMapping}
              >
                <option value="">-- Select a Mapping or Create New --</option>
                {availableFieldMaps.map(map => (
                  <option key={map.id} value={map.id}>{map.name}</option>
                ))}
              </select>
            </div>
            <div className="named-mapping-control-item">
              <label htmlFor="field-map-name" className="named-mapping-label">Profile Name:</label>
              <input 
                type="text" 
                id="field-map-name"
                value={fieldMapNameInput}
                onChange={e => { setFieldMapNameInput(e.target.value); setMappingSaveMessage(null); }}
                placeholder="Enter name for this mapping"
                className="named-mapping-input"
                disabled={isSavingMapping}
              />
            </div>
            <button 
              onClick={handlePersistCurrentMapping}
              className="named-mapping-button"
              disabled={isSavingMapping || !fieldMapNameInput.trim()}
            >
              {isSavingMapping ? 'Saving...' : (selectedFieldMapId ? 'Update Existing Profile' : 'Save as New Profile')}
            </button>
          </div>
        </div>

        {/* Existing Section Header for Column by Column mapping */}
        <h3 className="csv-mapping-header">Map Target Fields to CSV Columns</h3>
        <p className="csv-mapping-description">Select CSV column for each target field. Used CSV columns become unavailable for other fields.</p>
        <div className="csv-mapping-grid">
          {targetTransactionFields.map(targetFieldConfig => {
            const currentMapping = columnMappings.find(m => m.targetField === targetFieldConfig.field);
            const currentlyMappedCsvColumn = currentMapping?.csvColumn || '';
            
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
                  disabled={isSavingMapping} // Disable if a save operation is in progress
                >
                  <option value="">-- Unmapped --</option>
                  {csvHeaders.filter(
                    header => header !== '' && (!mappedCsvColumns.includes(header) || header === currentlyMappedCsvColumn)
                  ).map(header => (
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

  const handleCompleteImportClick = () => {
    let fieldMapToAssociate: { id: string; name: string } | undefined = undefined;
    if (fileType === 'csv' && selectedFieldMapId && fieldMapNameInput.trim()) {
      // Only pass if a map is selected AND has a name (could be an existing one or a newly named one)
      // This assumes that if `selectedFieldMapId` is set, `fieldMapNameInput` also reflects its name
      // or the new name if it was just typed in for a new save.
      fieldMapToAssociate = { id: selectedFieldMapId, name: fieldMapNameInput.trim() };
    }
    // If it's not a CSV, or if no map is actively selected/named, pass undefined.
    // The parent (ImportTransactionsView) will decide if it needs to fetch latest metadata
    // or proceed with a map association.
    onCompleteImport(transactionData, fieldMapToAssociate);
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
          onClick={handleCompleteImportClick}
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
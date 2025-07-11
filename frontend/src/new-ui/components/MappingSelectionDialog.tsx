import React, { useState, useEffect } from 'react';
import { parseFile } from '../../services/FileService';
import { listFieldMaps, getFieldMap, createFieldMap, updateFieldMap } from '../../services/FileMapService';
import ImportMappingDialog from './ImportMappingDialog';
import type { EditableCellDialogProps, EditableCellOption } from './ui/EditableCell';
import type { TransactionRow, ColumnMapping } from './ImportStep2Preview';

interface MappingSelectionDialogProps extends EditableCellDialogProps {
  fileId: string;
  targetTransactionFields: { field: string; label: string; required?: boolean; regex?: string | string[] }[];
}

const MappingSelectionDialog: React.FC<MappingSelectionDialogProps> = ({
  value,
  displayValue,
  options,
  onSave,
  onCancel,
  isOpen,
  fileId,
  targetTransactionFields,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parsedData, setParsedData] = useState<TransactionRow[]>([]);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [fileType, setFileType] = useState<'csv' | 'ofx' | 'qfx' | 'qif'>('csv');
  const [currentMapping, setCurrentMapping] = useState<ColumnMapping[] | undefined>(undefined);
  const [availableFieldMaps, setAvailableFieldMaps] = useState<EditableCellOption[]>([]);

  // Diagnostic logging on every render
  console.log(`[MappingSelectionDialog] RENDER - isOpen: ${isOpen}, fileId: ${fileId}, value: ${value}, displayValue: ${displayValue}`);
  console.log(`[MappingSelectionDialog] RENDER - State: isLoading=${isLoading}, error=${error}, parsedData.length=${parsedData.length}, availableFieldMaps.length=${availableFieldMaps.length}`);
  
  // Component mount/unmount logging
  useEffect(() => {
    console.log(`[MappingSelectionDialog] COMPONENT MOUNTED`);
    return () => {
      console.log(`[MappingSelectionDialog] COMPONENT UNMOUNTED`);
    };
  }, []);

  // Log props changes
  useEffect(() => {
    console.log(`[MappingSelectionDialog] PROPS CHANGED - isOpen: ${isOpen}, fileId: ${fileId}, value: "${value}", displayValue: "${displayValue}"`);
    console.log(`[MappingSelectionDialog] PROPS - options:`, options);
    console.log(`[MappingSelectionDialog] PROPS - targetTransactionFields:`, targetTransactionFields);
  }, [isOpen, fileId, value, displayValue, options, targetTransactionFields]);

  // Log state changes
  useEffect(() => {
    console.log(`[MappingSelectionDialog] STATE CHANGE - isLoading: ${isLoading}`);
  }, [isLoading]);

  useEffect(() => {
    console.log(`[MappingSelectionDialog] STATE CHANGE - error: ${error}`);
  }, [error]);

  useEffect(() => {
    console.log(`[MappingSelectionDialog] STATE CHANGE - parsedData.length: ${parsedData.length}`, parsedData);
  }, [parsedData]);

  useEffect(() => {
    console.log(`[MappingSelectionDialog] STATE CHANGE - csvHeaders.length: ${csvHeaders.length}`, csvHeaders);
  }, [csvHeaders]);

  useEffect(() => {
    console.log(`[MappingSelectionDialog] STATE CHANGE - fileType: ${fileType}`);
  }, [fileType]);

  useEffect(() => {
    console.log(`[MappingSelectionDialog] STATE CHANGE - currentMapping:`, currentMapping);
  }, [currentMapping]);

  useEffect(() => {
    console.log(`[MappingSelectionDialog] STATE CHANGE - availableFieldMaps.length: ${availableFieldMaps.length}`, availableFieldMaps);
  }, [availableFieldMaps]);

  // Load file data and current mapping when dialog opens
  useEffect(() => {
    console.log(`[MappingSelectionDialog] LOAD EFFECT TRIGGERED - isOpen: ${isOpen}, fileId: ${fileId}, value: ${value}, displayValue: ${displayValue}`);
    
    if (isOpen && fileId) {
      console.log(`[MappingSelectionDialog] CONDITIONS MET - Starting loadFileDataAndMapping()`);
      console.log(`[MappingSelectionDialog] Dialog opened for file ${fileId} with selected mapping: ${value || 'none'} (${displayValue || 'no display value'})`);
      loadFileDataAndMapping().catch((err) => {
        console.error(`[MappingSelectionDialog] ERROR in loadFileDataAndMapping:`, err);
        setError(`Failed to load file data: ${err.message}`);
        setIsLoading(false);
      });
    } else {
      console.log(`[MappingSelectionDialog] CONDITIONS NOT MET - isOpen: ${isOpen}, fileId: ${fileId}`);
      if (!isOpen) {
        console.log(`[MappingSelectionDialog] Dialog is closed, resetting state`);
        // Reset state when dialog closes
        setParsedData([]);
        setCsvHeaders([]);
        setCurrentMapping(undefined);
        setError(null);
        setIsLoading(false);
      }
    }
  }, [isOpen, fileId, value, displayValue]);

  const loadFileDataAndMapping = async () => {
    console.log(`[MappingSelectionDialog] LOAD START - Setting loading=true, clearing error`);
    setIsLoading(true);
    setError(null);

    try {
      console.log(`[MappingSelectionDialog] CALLING parseFile(${fileId}) and listFieldMaps() in parallel`);
      
      // Load file data and available field maps in parallel
      const [parseResult, fieldMapsResponse] = await Promise.all([
        parseFile(fileId),
        listFieldMaps()
      ]);

      console.log(`[MappingSelectionDialog] PARSE RESULT:`, parseResult);
      console.log(`[MappingSelectionDialog] FIELD MAPS RESPONSE:`, fieldMapsResponse);

      if (parseResult.error) {
        console.error(`[MappingSelectionDialog] Parse error: ${parseResult.error}`);
        setError(parseResult.error);
        return;
      }

      console.log(`[MappingSelectionDialog] SETTING PARSED DATA - data.length: ${parseResult.data?.length || 0}, headers.length: ${parseResult.headers?.length || 0}, format: ${parseResult.file_format}`);
      const dataToSet = parseResult.data || [];
      const headersToSet = parseResult.headers || [];
      const fileFormatToSet = parseResult.file_format || 'csv';
      
      console.log(`[MappingSelectionDialog] CALLING setParsedData with:`, dataToSet);
      setParsedData(dataToSet);
      
      console.log(`[MappingSelectionDialog] CALLING setCsvHeaders with:`, headersToSet);
      setCsvHeaders(headersToSet);
      
      console.log(`[MappingSelectionDialog] CALLING setFileType with:`, fileFormatToSet);
      setFileType(fileFormatToSet);

      // Set available field maps
      const fieldMapOptions = fieldMapsResponse.fieldMaps.map(fm => ({
        id: fm.fileMapId,
        name: fm.name,
      }));
      console.log(`[MappingSelectionDialog] SETTING FIELD MAP OPTIONS - count: ${fieldMapOptions.length}`, fieldMapOptions);
      setAvailableFieldMaps(fieldMapOptions);

      // Pre-load the selected mapping if one is provided
      if (value && value.trim()) {
        console.log(`[MappingSelectionDialog] Pre-loading mapping with ID: ${value}`);
        try {
          console.log(`[MappingSelectionDialog] CALLING getFieldMap(${value})`);
          const fieldMapDetails = await getFieldMap(value);
          console.log(`[MappingSelectionDialog] FIELD MAP DETAILS:`, fieldMapDetails);
          
          const mappings: ColumnMapping[] = fieldMapDetails.mappings.map(m => ({
            csvColumn: m.sourceField,
            targetField: m.targetField,
          }));
          console.log(`[MappingSelectionDialog] CONVERTED MAPPINGS:`, mappings);
          console.log(`[MappingSelectionDialog] CALLING setCurrentMapping with ${mappings.length} mappings`);
          setCurrentMapping(mappings);
          console.log(`[MappingSelectionDialog] Successfully loaded mapping "${fieldMapDetails.name}" with ${mappings.length} field mappings`);
        } catch (err) {
          console.warn(`[MappingSelectionDialog] Could not load field map details for ID ${value}:`, err);
          console.log(`[MappingSelectionDialog] CALLING setCurrentMapping with undefined due to error`);
          setCurrentMapping(undefined);
        }
      } else {
        console.log('[MappingSelectionDialog] No mapping ID provided, starting with empty mapping');
        console.log(`[MappingSelectionDialog] CALLING setCurrentMapping with undefined (no mapping selected)`);
        setCurrentMapping(undefined);
      }

      console.log(`[MappingSelectionDialog] LOAD COMPLETE - Setting loading=false`);

    } catch (error: any) {
      console.error(`[MappingSelectionDialog] ERROR during loading:`, error);
      console.error(`[MappingSelectionDialog] ERROR stack:`, error.stack);
      setError(error.message || 'Failed to load file data');
    } finally {
      console.log(`[MappingSelectionDialog] LOAD FINALLY - Setting loading=false`);
      setIsLoading(false);
    }
  };

  const handleCompleteImport = async (
    mappedData: TransactionRow[], 
    finalFieldMapToAssociate?: { id: string; name: string }
  ) => {
    try {
      if (finalFieldMapToAssociate) {
        console.log(`[MappingSelectionDialog] Saving mapping selection: ${finalFieldMapToAssociate.name} (${finalFieldMapToAssociate.id})`);
        
        // Check if this is a new mapping that needs to be added to available options
        const existingMapping = availableFieldMaps.find(fm => fm.id === finalFieldMapToAssociate.id);
        const updatedOptions = existingMapping 
          ? availableFieldMaps // Mapping already exists, no need to add
          : [...availableFieldMaps, finalFieldMapToAssociate]; // Add new mapping to options
        
        await onSave(finalFieldMapToAssociate.id, updatedOptions);
        console.log(`[MappingSelectionDialog] Successfully saved mapping selection`);
      } else {
        console.log('[MappingSelectionDialog] Clearing mapping selection');
        await onSave('');
      }
    } catch (error: any) {
      console.error('Error saving mapping selection:', error);
      setError(error.message || 'Failed to save mapping selection');
    }
  };

  const handleLoadFieldMapDetails = async (fieldMapId: string): Promise<ColumnMapping[] | undefined> => {
    try {
      const fieldMapDetails = await getFieldMap(fieldMapId);
      const mappings: ColumnMapping[] = fieldMapDetails.mappings.map(m => ({
        csvColumn: m.sourceField,
        targetField: m.targetField,
      }));
      setCurrentMapping(mappings);
      return mappings;
    } catch (error) {
      console.error('Error loading field map details:', error);
      return undefined;
    }
  };

  const handleSaveOrUpdateFieldMap = async (params: {
    mapIdToUpdate?: string;
    name: string;
    mappingsToSave: Array<{ csvColumn: string; targetField: string }>;
    reverseAmounts?: boolean;
  }): Promise<{ newMapId?: string; newName?: string; success: boolean; message?: string }> => {
    try {
      const mappings = params.mappingsToSave.map(m => ({
        sourceField: m.csvColumn,
        targetField: m.targetField,
      }));

      if (params.mapIdToUpdate) {
        // Update existing field map
        const updatedFieldMap = await updateFieldMap(params.mapIdToUpdate, {
          name: params.name,
          mappings,
          reverseAmounts: params.reverseAmounts,
        });
        
        // Update available field maps
        setAvailableFieldMaps(prev => 
          prev.map(fm => 
            fm.id === params.mapIdToUpdate 
              ? { ...fm, name: params.name }
              : fm
          )
        );

        return {
          newMapId: updatedFieldMap.fileMapId,
          newName: updatedFieldMap.name,
          success: true,
          message: 'Field map updated successfully',
        };
      } else {
        // Create new field map
        const newFieldMap = await createFieldMap({
          name: params.name,
          mappings,
          reverseAmounts: params.reverseAmounts,
        });

        // Add to available field maps
        const newOption = { id: newFieldMap.fileMapId, name: newFieldMap.name };
        setAvailableFieldMaps(prev => [...prev, newOption]);

        return {
          newMapId: newFieldMap.fileMapId,
          newName: newFieldMap.name,
          success: true,
          message: 'Field map created successfully',
        };
      }
    } catch (error: any) {
      console.error('Error saving field map:', error);
      return {
        success: false,
        message: error.message || 'Failed to save field map',
      };
    }
  };

  if (!isOpen) {
    console.log(`[MappingSelectionDialog] RENDER - Dialog not open, returning null`);
    return null;
  }

  if (error) {
    console.log(`[MappingSelectionDialog] RENDER - Showing error state: ${error}`);
    return (
      <div className="import-mapping-dialog-overlay" onClick={onCancel}>
        <div className="import-mapping-dialog" onClick={(e) => e.stopPropagation()}>
          <div className="dialog-header">
            <h3>Error Loading File</h3>
            <button className="close-btn" onClick={onCancel}>×</button>
          </div>
          <div className="dialog-content">
            <p style={{ color: 'red', padding: '20px' }}>{error}</p>
            <div style={{ padding: '20px', textAlign: 'right' }}>
              <button onClick={onCancel} className="button-common">Close</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    console.log(`[MappingSelectionDialog] RENDER - Showing loading state`);
    return (
      <div className="import-mapping-dialog-overlay">
        <div className="import-mapping-dialog">
          <div className="dialog-content">
            <p style={{ padding: '40px', textAlign: 'center' }}>Loading file data...</p>
          </div>
        </div>
      </div>
    );
  }

  // Check if we have all the necessary data before rendering the dialog
  const hasRequiredData = parsedData.length > 0 && csvHeaders.length > 0 && availableFieldMaps.length > 0;
  if (!hasRequiredData) {
    console.log(`[MappingSelectionDialog] RENDER - Missing required data, showing loading state`);
    console.log(`[MappingSelectionDialog] RENDER - parsedData.length: ${parsedData.length}, csvHeaders.length: ${csvHeaders.length}, availableFieldMaps.length: ${availableFieldMaps.length}`);
    return (
      <div className="import-mapping-dialog-overlay">
        <div className="import-mapping-dialog">
          <div className="dialog-content">
            <p style={{ padding: '40px', textAlign: 'center' }}>Loading file data...</p>
          </div>
        </div>
      </div>
    );
  }

  // Get the correct display name for the selected mapping
  const getSelectedMappingInfo = () => {
    if (!value || !value.trim()) return undefined;
    
    // Try to find the name from available field maps first
    const selectedMapping = availableFieldMaps.find(fm => fm.id === value);
    if (selectedMapping) {
      return { id: value, name: selectedMapping.name };
    }
    
    // Fall back to displayValue or value if not found in available maps
    return { id: value, name: displayValue || value };
  };

  const selectedMappingInfo = getSelectedMappingInfo();
  console.log(`[MappingSelectionDialog] RENDER - Rendering ImportMappingDialog with:`);
  console.log(`[MappingSelectionDialog] RENDER - isOpen: ${isOpen}`);
  console.log(`[MappingSelectionDialog] RENDER - parsedData.length: ${parsedData.length}`);
  console.log(`[MappingSelectionDialog] RENDER - csvHeaders.length: ${csvHeaders.length}`);
  console.log(`[MappingSelectionDialog] RENDER - fileType: ${fileType}`);
  console.log(`[MappingSelectionDialog] RENDER - currentMapping (existingMapping):`, currentMapping);
  console.log(`[MappingSelectionDialog] RENDER - availableFieldMaps.length: ${availableFieldMaps.length}`);
  console.log(`[MappingSelectionDialog] RENDER - selectedMappingInfo (initialFieldMapToLoad):`, selectedMappingInfo);
  console.log(`[MappingSelectionDialog] RENDER - targetTransactionFields.length: ${targetTransactionFields.length}`);



  return (
    <ImportMappingDialog
      isOpen={isOpen}
      onClose={onCancel}
      title="Select or Create Field Mapping"
      parsedData={parsedData}
      fileType={fileType}
      csvHeaders={csvHeaders}
      existingMapping={currentMapping}
      onCompleteImport={handleCompleteImport}
      targetTransactionFields={targetTransactionFields}
      availableFieldMaps={availableFieldMaps}
      initialFieldMapToLoad={selectedMappingInfo}
      onLoadFieldMapDetails={handleLoadFieldMapDetails}
      onSaveOrUpdateFieldMap={handleSaveOrUpdateFieldMap}
      currentlyLoadedFieldMapData={undefined}
    />
  );
};

export default MappingSelectionDialog; 
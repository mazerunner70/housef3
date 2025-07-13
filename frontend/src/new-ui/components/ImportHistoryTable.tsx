import React, { useState, useMemo } from 'react';
import { Decimal } from 'decimal.js';
import './ImportHistoryTable.css';
import {
  DateCell,
  LookupCell,
  NumberCell,
  RowActions,
  CurrencyAmount,
  EditableCell,
  StatusBadge,
  FileFormatDisplay,
  type ActionConfig,
  type EditableCellOption,
  type EditableCellDialogProps
} from './ui';
import ImportMappingDialog from './ImportMappingDialog';
import type { TransactionRow, ColumnMapping } from './ImportStep2Preview';
import { parseFile } from '../../services/FileService';
import { listFieldMaps, getFieldMap, createFieldMap, updateFieldMap } from '../../services/FileMapService';

// Types for the component
export interface FileMetadata {
  fileId: string;
  fileName: string;
  accountId?: string;
  accountName?: string;
  uploadDate: string;
  fieldMap?: {
    fileMapId?: string;
    name?: string;
  };
  fileFormat?: string;
  processingStatus?: string;
  openingBalance?: Decimal;
  closingBalance?: Decimal;
}

export interface ViewAccount {
  id: string;
  name: string;
  defaultfilemapid?: string;
}

export interface AvailableMapInfo {
  id: string;
  name: string;
}

export interface ImportHistoryTableProps {
  importHistory: FileMetadata[];
  accounts: ViewAccount[];
  availableFileMaps: AvailableMapInfo[];
  isLoading: boolean;
  selectedHistoryFileId?: string;
  onRowClick?: (fileId: string) => void;
  onUpdateAccount?: (fileId: string, accountId: string) => Promise<void>;
  onUpdateMapping?: (fileId: string, mappingId: string) => Promise<void>;
  onUpdateOpeningBalance?: (fileId: string, balance: string) => Promise<void>;
  onUpdateClosingBalance?: (fileId: string, balance: string) => Promise<void>;
  onDeleteFile?: (fileId: string) => Promise<void>;
  className?: string;
  showActions?: boolean;
  showSelection?: boolean;
  sortable?: boolean;
  emptyMessage?: string;
  loadingMessage?: string;
  helpText?: string;
}

export interface SortConfig {
  key: keyof FileMetadata | null;
  direction: 'ascending' | 'descending';
}

// Target transaction fields for mapping dialog
const TARGET_TRANSACTION_FIELDS = [
  { field: 'date', label: 'Date', required: true },
  { field: 'amount', label: 'Amount', required: true },
  { field: 'description', label: 'Description', required: true },
  { field: 'category', label: 'Category', required: false },
  { field: 'account', label: 'Account', required: false },
];

const ImportHistoryTable: React.FC<ImportHistoryTableProps> = ({
  importHistory,
  accounts,
  availableFileMaps,
  isLoading,
  selectedHistoryFileId,
  onRowClick,
  onUpdateAccount,
  onUpdateMapping,
  onUpdateOpeningBalance,
  onUpdateClosingBalance,
  onDeleteFile,
  className = '',
  showActions = true,
  showSelection = true,
  sortable = true,
  emptyMessage = 'No import history found.',
  loadingMessage = 'Loading history...',
  helpText = 'Click on any row to select it for import, or click on individual cells to edit them.',
}) => {
  // State for editing cells
  const [editingAccountFileId, setEditingAccountFileId] = useState<string | null>(null);
  const [editingMappingFileId, setEditingMappingFileId] = useState<string | null>(null);
  const [editingOpeningFileId, setEditingOpeningFileId] = useState<string | null>(null);
  const [editingClosingFileId, setEditingClosingFileId] = useState<string | null>(null);

  // State for mapping dialog
  const [mappingDialogOpen, setMappingDialogOpen] = useState<boolean>(false);
  const [mappingDialogFileId, setMappingDialogFileId] = useState<string | null>(null);
  const [mappingDialogCurrentValue, setMappingDialogCurrentValue] = useState<string>('');
  const [mappingDialogDisplayValue, setMappingDialogDisplayValue] = useState<string>('');

  // New state for direct ImportMappingDialog integration
  const [parsedData, setParsedData] = useState<TransactionRow[]>([]);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [fileType, setFileType] = useState<'csv' | 'ofx' | 'qfx' | 'qif'>('csv');
  const [currentMapping, setCurrentMapping] = useState<ColumnMapping[] | undefined>(undefined);
  const [currentFieldMapData, setCurrentFieldMapData] = useState<any>(undefined); // Store full field map data
  const [isLoadingMappingData, setIsLoadingMappingData] = useState<boolean>(false);
  const [mappingError, setMappingError] = useState<string | null>(null);

  // State for sorting
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'uploadDate', direction: 'descending' });

  // Create lookup maps for efficient rendering
  const accountsMap = useMemo(() => {
    const map = new Map<string, string>();
    accounts.forEach(acc => {
      map.set(acc.id, acc.name);
    });
    return map;
  }, [accounts]);

  const fieldMapsMap = useMemo(() => {
    const map = new Map<string, string>();
    availableFileMaps.forEach(fm => {
      map.set(fm.id, fm.name);
    });
    return map;
  }, [availableFileMaps]);

  // Convert accounts and field maps to EditableCell options
  const accountOptions = useMemo((): EditableCellOption[] => 
    accounts.map(acc => ({ id: acc.id, name: acc.name })), 
    [accounts]
  );

  const fieldMapOptions = useMemo((): EditableCellOption[] => 
    availableFileMaps.map(fm => ({ id: fm.id, name: fm.name })), 
    [availableFileMaps]
  );

  // Sorting logic
  const sortedHistory = useMemo(() => {
    if (!sortable || !sortConfig.key) return importHistory;

    const sorted = [...importHistory].sort((a, b) => {
      const aValue = a[sortConfig.key!];
      const bValue = b[sortConfig.key!];

      if (aValue === undefined || bValue === undefined) return 0;

      // Handle different data types
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortConfig.direction === 'ascending' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      if (aValue instanceof Decimal && bValue instanceof Decimal) {
        return sortConfig.direction === 'ascending' 
          ? aValue.comparedTo(bValue)
          : bValue.comparedTo(aValue);
      }

      return 0;
    });

    return sorted;
  }, [importHistory, sortConfig, sortable]);

  // Handlers for sorting
  const handleSort = (key: keyof FileMetadata) => {
    if (!sortable) return;
    
    let direction: 'ascending' | 'descending' = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  const getSortIndicator = (key: keyof FileMetadata) => {
    if (!sortable || sortConfig.key !== key) return '';
    return sortConfig.direction === 'ascending' ? ' ↑' : ' ↓';
  };

  // Handlers for editing
  const handleStartEditAccount = (fileId: string) => {
    setEditingAccountFileId(fileId);
  };

  const handleEndEditAccount = () => {
    setEditingAccountFileId(null);
  };

  const handleSaveAccount = async (fileId: string, accountId: string) => {
    if (onUpdateAccount) {
      await onUpdateAccount(fileId, accountId);
    }
  };

  const handleStartEditMapping = (fileId: string) => {
    setEditingMappingFileId(fileId);
  };

  const handleEndEditMapping = () => {
    setEditingMappingFileId(null);
  };

  const handleSaveMapping = async (fileId: string, mappingId: string) => {
    if (onUpdateMapping) {
      await onUpdateMapping(fileId, mappingId);
    }
  };

  // Mapping dialog handlers
  const handleOpenMappingDialog = (fileId: string, currentValue: string, displayValue: string) => {
    setMappingDialogFileId(fileId);
    setMappingDialogCurrentValue(currentValue);
    setMappingDialogDisplayValue(displayValue);
    setMappingDialogOpen(true);
    loadFileDataForMapping(fileId, currentValue);
  };

  const handleCloseMappingDialog = () => {
    setMappingDialogOpen(false);
    setMappingDialogFileId(null);
    setMappingDialogCurrentValue('');
    setMappingDialogDisplayValue('');
    setParsedData([]);
    setCsvHeaders([]);
    setCurrentMapping(undefined);
    setCurrentFieldMapData(undefined);
    setMappingError(null);
  };

  const handleSaveMappingDialog = async (newValue: string, newOptions?: EditableCellOption[]) => {
    if (mappingDialogFileId) {
      await handleSaveMapping(mappingDialogFileId, newValue);
      handleCloseMappingDialog();
    }
  };

  // New function to load file data for mapping dialog
  const loadFileDataForMapping = async (fileId: string, currentMappingId: string) => {
    setIsLoadingMappingData(true);
    setMappingError(null);

    try {
      // Load file data and available field maps in parallel
      const [parseResult, fieldMapsResponse] = await Promise.all([
        parseFile(fileId),
        listFieldMaps()
      ]);

      if (parseResult.error) {
        setMappingError(parseResult.error);
        return;
      }

      setParsedData(parseResult.data || []);
      setCsvHeaders(parseResult.headers || []);
      setFileType(parseResult.file_format || 'csv');

      // Pre-load the selected mapping if one is provided
      if (currentMappingId && currentMappingId.trim()) {
        try {
          const fieldMapDetails = await getFieldMap(currentMappingId);
          const mappings: ColumnMapping[] = fieldMapDetails.mappings.map(m => ({
            csvColumn: m.sourceField,
            targetField: m.targetField,
          }));
          setCurrentMapping(mappings);
          setCurrentFieldMapData(fieldMapDetails); // Store full field map data
        } catch (err) {
          console.warn(`Could not load field map details for ID ${currentMappingId}:`, err);
          setCurrentMapping(undefined);
          setCurrentFieldMapData(undefined);
        }
      } else {
        setCurrentMapping(undefined);
        setCurrentFieldMapData(undefined);
      }

    } catch (error: any) {
      setMappingError(error.message || 'Failed to load file data');
    } finally {
      setIsLoadingMappingData(false);
    }
  };

  // Handler for completing import from mapping dialog
  const handleCompleteImport = async (
    mappedData: TransactionRow[], 
    finalFieldMapToAssociate?: { id: string; name: string }
  ) => {
    try {
      if (finalFieldMapToAssociate && mappingDialogFileId) {
        await handleSaveMapping(mappingDialogFileId, finalFieldMapToAssociate.id);
      }
      handleCloseMappingDialog();
    } catch (error: any) {
      setMappingError(error.message || 'Failed to save mapping selection');
    }
  };

  // Handlers for field map operations in the dialog
  const handleLoadFieldMapDetails = async (fieldMapId: string): Promise<ColumnMapping[] | undefined> => {
    try {
      const fieldMapDetails = await getFieldMap(fieldMapId);
      const mappings: ColumnMapping[] = fieldMapDetails.mappings.map(m => ({
        csvColumn: m.sourceField,
        targetField: m.targetField,
      }));
      setCurrentMapping(mappings);
      setCurrentFieldMapData(fieldMapDetails); // Store full field map data
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
        const updatedFieldMap = await updateFieldMap(params.mapIdToUpdate, {
          name: params.name,
          mappings,
          reverseAmounts: params.reverseAmounts,
        });

        return {
          newMapId: updatedFieldMap.fileMapId,
          newName: updatedFieldMap.name,
          success: true,
          message: 'Field map updated successfully',
        };
      } else {
        const newFieldMap = await createFieldMap({
          name: params.name,
          mappings,
          reverseAmounts: params.reverseAmounts,
        });

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

  const handleStartEditOpeningBalance = (fileId: string) => {
    setEditingOpeningFileId(fileId);
  };

  const handleEndEditOpeningBalance = () => {
    setEditingOpeningFileId(null);
  };

  const handleSaveOpeningBalance = async (fileId: string, balance: string) => {
    if (onUpdateOpeningBalance) {
      await onUpdateOpeningBalance(fileId, balance);
    }
  };

  const handleStartEditClosingBalance = (fileId: string) => {
    setEditingClosingFileId(fileId);
  };

  const handleEndEditClosingBalance = () => {
    setEditingClosingFileId(null);
  };

  const handleSaveClosingBalance = async (fileId: string, balance: string) => {
    if (onUpdateClosingBalance) {
      await onUpdateClosingBalance(fileId, balance);
    }
  };

  // Format balance for display
  const formatBalanceDisplay = (balance: Decimal | undefined): string => {
    if (!balance) return 'N/A';
    return balance.toFixed(2);
  };

  // Get balance as number for editing
  const decimalToNumber = (balance: Decimal | undefined): number | undefined => {
    if (!balance) return undefined;
    return balance.toNumber();
  };

  // Row actions
  const getRowActions = (fileId: string): ActionConfig[] => {
    const actions: ActionConfig[] = [];
    
    if (onDeleteFile) {
      actions.push({
        key: 'delete',
        icon: '🗑️',
        label: 'Delete file',
        onClick: () => {
          if (window.confirm('Are you sure you want to delete this file?')) {
            onDeleteFile(fileId).catch(console.error);
          }
        },
        variant: 'danger'
      });
    }

    return actions;
  };

  // Render loading state
  if (isLoading) {
    return (
      <div className={`import-history-table-container ${className}`}>
        <div className="import-history-loading">{loadingMessage}</div>
      </div>
    );
  }

  // Render empty state
  if (importHistory.length === 0) {
    return (
      <div className={`import-history-table-container ${className}`}>
        <div className="import-history-empty">{emptyMessage}</div>
      </div>
    );
  }

  return (
    <div className={`import-history-table-container ${className}`}>
      {helpText && (
        <div className="import-history-help-text">
          {helpText}
        </div>
      )}
      
      <div className="import-history-table-wrapper">
        <table className="import-history-table">
          <thead>
            <tr>
              {showSelection && <th className="import-history-th">Select</th>}
              <th 
                className={`import-history-th ${sortable ? 'sortable' : ''}`}
                onClick={() => handleSort('fileName')}
              >
                File Name{getSortIndicator('fileName')}
              </th>
              <th 
                className={`import-history-th ${sortable ? 'sortable' : ''}`}
                onClick={() => handleSort('accountName')}
              >
                Account{getSortIndicator('accountName')}
              </th>
              <th 
                className={`import-history-th ${sortable ? 'sortable' : ''}`}
                onClick={() => handleSort('uploadDate')}
              >
                Upload Date{getSortIndicator('uploadDate')}
              </th>
              <th className="import-history-th">Mapping</th>
              <th className="import-history-th">Format</th>
              <th 
                className={`import-history-th ${sortable ? 'sortable' : ''}`}
                onClick={() => handleSort('processingStatus')}
              >
                Status{getSortIndicator('processingStatus')}
              </th>
              <th className="import-history-th">Opening Balance</th>
              <th className="import-history-th">Closing Balance</th>
              {showActions && <th className="import-history-th">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {sortedHistory.map(file => (
              <tr 
                key={file.fileId}
                className={`import-history-row ${selectedHistoryFileId === file.fileId ? 'selected' : ''}`}
                onClick={onRowClick ? () => onRowClick(file.fileId) : undefined}
                style={{ cursor: onRowClick ? 'pointer' : 'default' }}
              >
                {showSelection && (
                  <td className="import-history-td">
                    <input 
                      type="radio" 
                      checked={selectedHistoryFileId === file.fileId}
                      onChange={() => onRowClick && onRowClick(file.fileId)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </td>
                )}
                
                <td className="import-history-td">
                  {file.fileName}
                </td>
                
                <td className="import-history-td">
                  <EditableCell
                    value={file.accountId || ''}
                    displayValue={file.accountId ? accountsMap.get(file.accountId) || file.accountName : file.accountName}
                    options={accountOptions}
                    onSave={(accountId) => handleSaveAccount(file.fileId, accountId)}
                    type="select"
                    isEditing={editingAccountFileId === file.fileId}
                    onStartEdit={() => handleStartEditAccount(file.fileId)}
                    onEndEdit={handleEndEditAccount}
                    placeholder="Select account"
                  />
                </td>
                
                <td className="import-history-td">
                  <DateCell date={file.uploadDate} />
                </td>
                
                <td className="import-history-td">
                  <EditableCell
                    value={file.fieldMap?.fileMapId || ''}
                    displayValue={file.fieldMap?.fileMapId ? fieldMapsMap.get(file.fieldMap.fileMapId) || file.fieldMap.name : file.fieldMap?.name}
                    options={fieldMapOptions}
                    onSave={(mappingId) => handleSaveMapping(file.fileId, mappingId)}
                    type="select"
                    isEditing={editingMappingFileId === file.fileId}
                    onStartEdit={() => {
                      // Open custom mapping dialog instead of inline editing
                      let currentValue = file.fieldMap?.fileMapId || '';
                      let displayValue = '';
                      
                      if (file.fieldMap?.fileMapId) {
                        // We have a field map ID, use it
                        displayValue = fieldMapsMap.get(file.fieldMap.fileMapId) || file.fieldMap.name || '';
                      } else if (file.fieldMap?.name) {
                        // No field map ID but we have a name, try to find the ID
                        const matchingFieldMap = availableFileMaps.find(fm => fm.name === file.fieldMap?.name);
                        if (matchingFieldMap) {
                          currentValue = matchingFieldMap.id;
                          displayValue = matchingFieldMap.name;
                        } else {
                          // Can't find matching field map, keep empty currentValue but show the name
                          displayValue = file.fieldMap.name;
                        }
                      }
                      
                      handleOpenMappingDialog(file.fileId, currentValue, displayValue);
                    }}
                    onEndEdit={handleEndEditMapping}
                    placeholder="Select mapping"
                  />
                </td>
                
                <td className="import-history-td">
                  <FileFormatDisplay format={file.fileFormat || 'unknown'} />
                </td>
                
                <td className="import-history-td">
                  <StatusBadge status={file.processingStatus || 'UNKNOWN'} />
                </td>
                
                <td className="import-history-td">
                  <EditableCell
                    value={decimalToNumber(file.openingBalance)?.toString() || ''}
                    displayValue={formatBalanceDisplay(file.openingBalance)}
                    onSave={(balance) => handleSaveOpeningBalance(file.fileId, balance)}
                    type="number"
                    isEditing={editingOpeningFileId === file.fileId}
                    onStartEdit={() => handleStartEditOpeningBalance(file.fileId)}
                    onEndEdit={handleEndEditOpeningBalance}
                    placeholder="0.00"
                    step={0.01}
                  />
                </td>
                
                <td className="import-history-td">
                  <EditableCell
                    value={decimalToNumber(file.closingBalance)?.toString() || ''}
                    displayValue={formatBalanceDisplay(file.closingBalance)}
                    onSave={(balance) => handleSaveClosingBalance(file.fileId, balance)}
                    type="number"
                    isEditing={editingClosingFileId === file.fileId}
                    onStartEdit={() => handleStartEditClosingBalance(file.fileId)}
                    onEndEdit={handleEndEditClosingBalance}
                    placeholder="0.00"
                    step={0.01}
                  />
                </td>
                
                {showActions && (
                  <td className="import-history-td">
                    <RowActions
                      itemId={file.fileId}
                      actions={getRowActions(file.fileId)}
                      size="small"
                    />
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Single mapping dialog instance */}
      {mappingDialogFileId && (
        <>
          {isLoadingMappingData ? (
            <div className="import-mapping-dialog-overlay">
              <div className="import-mapping-dialog">
                <div className="dialog-content">
                  <p style={{ padding: '40px', textAlign: 'center' }}>Loading file data...</p>
                </div>
              </div>
            </div>
          ) : mappingError ? (
            <div className="import-mapping-dialog-overlay" onClick={handleCloseMappingDialog}>
              <div className="import-mapping-dialog" onClick={(e) => e.stopPropagation()}>
                <div className="dialog-header">
                  <h3>Error Loading File</h3>
                  <button className="close-btn" onClick={handleCloseMappingDialog}>×</button>
                </div>
                <div className="dialog-content">
                  <p style={{ color: 'red', padding: '20px' }}>{mappingError}</p>
                  <div style={{ padding: '20px', textAlign: 'right' }}>
                    <button onClick={handleCloseMappingDialog} className="button-common">Close</button>
                  </div>
                </div>
              </div>
            </div>
          ) : parsedData.length > 0 ? (
            <ImportMappingDialog
              isOpen={mappingDialogOpen}
              onClose={handleCloseMappingDialog}
              title="Select or Create Field Mapping"
              parsedData={parsedData}
              fileType={fileType}
              csvHeaders={csvHeaders}
              existingMapping={currentMapping}
              onCompleteImport={handleCompleteImport}
              targetTransactionFields={TARGET_TRANSACTION_FIELDS}
              availableFieldMaps={availableFileMaps}
              initialFieldMapToLoad={mappingDialogCurrentValue ? { 
                id: mappingDialogCurrentValue, 
                name: mappingDialogDisplayValue || mappingDialogCurrentValue 
              } : undefined}
              onLoadFieldMapDetails={handleLoadFieldMapDetails}
              onSaveOrUpdateFieldMap={handleSaveOrUpdateFieldMap}
              currentlyLoadedFieldMapData={currentFieldMapData}
            />
          ) : null}
        </>
      )}
    </div>
  );
};

export default ImportHistoryTable; 
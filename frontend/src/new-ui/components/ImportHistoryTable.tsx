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
import MappingSelectionDialog from './MappingSelectionDialog';

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
  };

  const handleCloseMappingDialog = () => {
    setMappingDialogOpen(false);
    setMappingDialogFileId(null);
    setMappingDialogCurrentValue('');
    setMappingDialogDisplayValue('');
  };

  const handleSaveMappingDialog = async (newValue: string, newOptions?: EditableCellOption[]) => {
    if (mappingDialogFileId) {
      await handleSaveMapping(mappingDialogFileId, newValue);
      handleCloseMappingDialog();
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
        <MappingSelectionDialog
          value={mappingDialogCurrentValue}
          displayValue={mappingDialogDisplayValue}
          options={fieldMapOptions}
          onSave={handleSaveMappingDialog}
          onCancel={handleCloseMappingDialog}
          isOpen={mappingDialogOpen}
          fileId={mappingDialogFileId}
          targetTransactionFields={TARGET_TRANSACTION_FIELDS}
        />
      )}
    </div>
  );
};

export default ImportHistoryTable; 
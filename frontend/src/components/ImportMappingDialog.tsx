import React, { useEffect } from 'react';
import ImportStep2Preview, { TransactionRow, ColumnMapping } from './ImportStep2Preview';
import './ImportMappingDialog.css';

interface ImportMappingDialogProps {
  isOpen: boolean;
  onClose: () => void;
  parsedData: TransactionRow[];
  fileType: 'csv' | 'ofx' | 'qfx' | 'qif';
  csvHeaders?: string[];
  existingMapping?: ColumnMapping[];
  onCompleteImport: (
    mappedData: TransactionRow[],
    finalFieldMapToAssociate?: { id: string; name: string }
  ) => void;
  targetTransactionFields: { field: string; label: string; required?: boolean; regex?: string | string[] }[];
  availableFieldMaps: Array<{ id: string; name: string }>;
  initialFieldMapToLoad?: { id: string; name: string };
  onLoadFieldMapDetails: (fieldMapId: string) => Promise<ColumnMapping[] | undefined>;
  onSaveOrUpdateFieldMap: (
    params: {
      mapIdToUpdate?: string;
      name: string;
      mappingsToSave: Array<{ csvColumn: string; targetField: string }>;
      reverseAmounts?: boolean;
    }
  ) => Promise<{ newMapId?: string; newName?: string; success: boolean; message?: string }>;
  currentlyLoadedFieldMapData?: any;
  title?: string;
}

const ImportMappingDialog: React.FC<ImportMappingDialogProps> = ({
  isOpen,
  onClose,
  title = "Import Field Mapping",
  ...importStep2Props
}) => {
  // Handle escape key to close dialog
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Prevent body scroll when dialog is open
      document.body.style.overflow = 'hidden';
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
        document.body.style.overflow = 'unset';
      };
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleCompleteImport = (mappedData: TransactionRow[], finalFieldMapToAssociate?: { id: string; name: string }) => {
    importStep2Props.onCompleteImport(mappedData, finalFieldMapToAssociate);
    // Note: Parent should handle closing the dialog after successful import
  };

  const handleCancel = () => {
    onClose();
  };

  return (
    <button
      type="button"
      className="import-mapping-dialog-overlay"
      onClick={handleOverlayClick}
      onKeyDown={(e) => {
        if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
          handleCancel();
        }
      }}
      aria-label="Close dialog by clicking overlay"
    >
      <dialog
        className="import-mapping-dialog"
        open
        aria-labelledby="dialog-title"
      >
        <div className="dialog-header">
          <h3 id="dialog-title">{title}</h3>
          <button className="close-btn" onClick={onClose} aria-label="Close dialog">
            ×
          </button>
        </div>

        <div className="dialog-content">
          <ImportStep2Preview
            {...importStep2Props}
            onCompleteImport={handleCompleteImport}
            onCancel={handleCancel}
          />
        </div>
      </dialog>
    </button>
  );
};

export default ImportMappingDialog; 
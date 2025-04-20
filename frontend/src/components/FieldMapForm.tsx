import React, { useState, useEffect } from 'react';
import FieldMapService, { FieldMap } from '../services/FieldMapService';
import { DataPreviewPanel } from './DataPreviewPanel';
import FileService, { FileMetadata } from '../services/FileService';
import './FieldMapForm.css';
import { transactionFields } from '../services/TransactionService';
import { parseCSV as parseCSVContent } from '../utils/csvParser';

interface FieldMapping {
  sourceField: string;
  targetField: string;
}

interface FieldMapFormProps {
  fieldMap?: FieldMap;
  onSave: (fieldMap: FieldMap) => void;
  onCancel: () => void;
  accountId?: string;
  fileId?: string;
}

export const FieldMapForm: React.FC<FieldMapFormProps> = ({
  fieldMap,
  onSave,
  onCancel,
  accountId,
  fileId
}) => {
  const [name, setName] = useState(fieldMap?.name || '');
  const [description, setDescription] = useState(fieldMap?.description || '');
  const [mappings, setMappings] = useState<FieldMapping[]>(() => {
    if (fieldMap?.mappings) {
      return transactionFields.map(targetField => ({
        sourceField: fieldMap.mappings.find(m => m.targetField === targetField)?.sourceField || '',
        targetField
      }));
    }
    return transactionFields.map(targetField => ({
      sourceField: '',
      targetField
    }));
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [previewData, setPreviewData] = useState<Array<Record<string, any>>>([]);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | undefined>();
  const [availableFieldMaps, setAvailableFieldMaps] = useState<FieldMap[]>([]);
  const [selectedFieldMapId, setSelectedFieldMapId] = useState<string | undefined>(fieldMap?.fieldMapId);
  const [availableColumns, setAvailableColumns] = useState<string[]>([]);

  useEffect(() => {
    loadFieldMaps();
    if (fileId) {
      loadPreviewData();
    }
  }, [fileId]);

  const loadFieldMaps = async () => {
    try {
      const response = await FieldMapService.listFieldMaps();
      setAvailableFieldMaps(response.fieldMaps);
    } catch (error) {
      console.error('Error loading field maps:', error);
      setError('Failed to load existing field maps');
    }
  };

  const handleFieldMapSelect = async (fieldMapId: string) => {
    const selectedMap = availableFieldMaps.find(fm => fm.fieldMapId === fieldMapId);
    if (selectedMap) {
      setSelectedFieldMapId(fieldMapId);
      setName(selectedMap.name);
      setDescription(selectedMap.description || '');
      setMappings(transactionFields.map(targetField => ({
        sourceField: selectedMap.mappings.find(m => m.targetField === targetField)?.sourceField || '',
        targetField
      })));
    }
  };

  const parseCSV = (content: string): Array<Record<string, any>> => {
    const result = parseCSVContent(content);
    if (result.data.length > 0) {
      setAvailableColumns(Object.keys(result.data[0]));
    }
    return result.data;
  };

  const parseOFX = (content: string): Array<Record<string, any>> => {
    // Simple OFX parsing - you might want to use a proper OFX parser
    const transactions: Array<Record<string, any>> = [];
    const transactionMatches = content.match(/<STMTTRN>(.*?)<\/STMTTRN>/gs);

    if (!transactionMatches) return [];

    // Process all transactions
    transactionMatches.forEach(transaction => {
      const dateMatch = transaction.match(/<DTPOSTED>(.*?)<\/DTPOSTED>/);
      const amountMatch = transaction.match(/<TRNAMT>(.*?)<\/TRNAMT>/);
      const nameMatch = transaction.match(/<NAME>(.*?)<\/NAME>/);
      const memoMatch = transaction.match(/<MEMO>(.*?)<\/MEMO>/);

      transactions.push({
        Date: dateMatch?.[1] || '',
        Amount: amountMatch?.[1] || '',
        Name: nameMatch?.[1] || '',
        Memo: memoMatch?.[1] || ''
      });
    });

    return transactions;
  };

  const loadPreviewData = async () => {
    if (!fileId) return;

    setLoadingPreview(true);
    setPreviewError(undefined);

    try {
      const metadata = await FileService.getFileMetadata(fileId);
      const downloadResponse = await FileService.getDownloadUrl(fileId);
      const contentResponse = await fetch(downloadResponse.downloadUrl);
      const content = await contentResponse.text();
      
      let parsedData: Array<Record<string, any>> = [];

      const contentType = metadata.contentType || '';
      const fileName = metadata.fileName || '';
      const fileExtension = fileName.split('.').pop()?.toLowerCase() || '';

      if (contentType.includes('csv') || fileExtension === 'csv') {
        parsedData = parseCSV(content);
      } else if (
        contentType.includes('ofx') || 
        ['ofx', 'qfx'].includes(fileExtension)
      ) {
        parsedData = parseOFX(content);
      }

      setPreviewData(parsedData);
    } catch (error) {
      console.error('Error loading preview data:', error);
      setPreviewError('Failed to load preview data');
      setPreviewData([]);
    } finally {
      setLoadingPreview(false);
    }
  };

  const isMappingMismatched = (sourceField: string): boolean => {
    return sourceField !== '' && !availableColumns.includes(sourceField);
  };

  return (
    <div className="field-map-form-container">
      <div className="field-map-selector">
        <label htmlFor="fieldMapSelect">Use Existing Field Map:</label>
        <select
          id="fieldMapSelect"
          value={selectedFieldMapId || ''}
          onChange={(e) => handleFieldMapSelect(e.target.value)}
          className="field-map-select"
        >
          <option value="">Create New Map</option>
          {availableFieldMaps.map(fm => (
            <option key={fm.fieldMapId} value={fm.fieldMapId}>
              {fm.name}
            </option>
          ))}
        </select>
      </div>

      <div className="field-map-form-content">
        <div className="field-map-form">
          <div className="form-group">
            <label htmlFor="name">Name:</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter field map name"
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description:</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter field map description"
            />
          </div>

          <div className="mappings-section">
            <h3>Field Mappings</h3>
            {mappings.map((mapping, index) => (
              <div key={mapping.targetField} className={`mapping-row ${isMappingMismatched(mapping.sourceField) ? 'mapping-mismatch' : ''}`}>
                <div className="mapping-fields">
                  <input
                    type="text"
                    value={mapping.sourceField}
                    onChange={(e) => {
                      const newMappings = [...mappings];
                      newMappings[index].sourceField = e.target.value;
                      setMappings(newMappings);
                    }}
                    placeholder="Source field"
                    list="availableColumns"
                  />
                  <span className="mapping-arrow">→</span>
                  <input
                    type="text"
                    value={mapping.targetField}
                    disabled
                    title="Target field cannot be changed"
                  />
                </div>
                {isMappingMismatched(mapping.sourceField) && (
                  <span className="mapping-warning" title="This column is not found in the file">⚠️</span>
                )}
              </div>
            ))}
            <datalist id="availableColumns">
              {availableColumns.map(column => (
                <option key={column} value={column} />
              ))}
            </datalist>
          </div>

          <div className="form-actions">
            <button onClick={onCancel} className="cancel-button">
              Cancel
            </button>
            <button
              onClick={() => onSave({
                fieldMapId: selectedFieldMapId || '',
                name,
                description,
                mappings: mappings.map(m => ({
                  sourceField: m.sourceField,
                  targetField: m.targetField
                }))
              })}
              className="save-button"
              disabled={saving || !name || (!selectedFieldMapId && mappings.some(m => !m.sourceField))}
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>

        {fileId && (
          <div className="field-map-preview">
            <h3>File Preview</h3>
            {loadingPreview ? (
              <div>Loading preview...</div>
            ) : previewError ? (
              <div className="preview-error">{previewError}</div>
            ) : (
              <DataPreviewPanel data={previewData} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}; 
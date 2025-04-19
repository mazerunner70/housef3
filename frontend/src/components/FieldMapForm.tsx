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
  const [mappings, setMappings] = useState<FieldMapping[]>(
    fieldMap?.mappings || [
      { sourceField: '', targetField: 'date' },
      { sourceField: '', targetField: 'description' },
      { sourceField: '', targetField: 'amount' },
      { sourceField: '', targetField: 'type' },
      { sourceField: '', targetField: 'balance' }
    ]
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [previewData, setPreviewData] = useState<Array<Record<string, any>>>([]);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | undefined>();

  useEffect(() => {
    if (fileId) {
      loadPreviewData();
    }
  }, [fileId]);

  const parseCSV = (content: string): Array<Record<string, any>> => {
    const result = parseCSVContent(content);
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
      // First get the file metadata
      const metadata = await FileService.getFileMetadata(fileId);
      
      // Then get the file content using the download URL
      const downloadResponse = await FileService.getDownloadUrl(fileId);
      const contentResponse = await fetch(downloadResponse.downloadUrl);
      const content = await contentResponse.text();
      
      let parsedData: Array<Record<string, any>> = [];

      // Safely check content type and file extension
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

  const handleAddMapping = () => {
    setMappings([...mappings, { sourceField: '', targetField: '' }]);
  };

  const handleRemoveMapping = (index: number) => {
    setMappings(mappings.filter((_, i) => i !== index));
  };

  const handleMappingChange = (index: number, field: 'sourceField' | 'targetField', value: string) => {
    const newMappings = [...mappings];
    newMappings[index] = { ...newMappings[index], [field]: value };
    setMappings(newMappings);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    if (mappings.length === 0) {
      setError('At least one field mapping is required');
      return;
    }

    if (mappings.some(m => !m.sourceField || !m.targetField)) {
      setError('All mappings must have both source and target fields');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const fieldMapData = {
        name,
        description,
        mappings,
        accountId
      };

      const savedFieldMap = fieldMap
        ? await FieldMapService.updateFieldMap(fieldMap.fieldMapId, fieldMapData)
        : await FieldMapService.createFieldMap(fieldMapData);

      onSave(savedFieldMap);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save field map');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="field-map-form-container">
      <div className="field-map-form-content">
        <div className="field-map-form">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="name">Name *</label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter field map name"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter description (optional)"
                rows={3}
              />
            </div>

            <div className="mappings-section">
              <h3>Field Mappings</h3>
              {transactionFields.map((field, index) => (
                <div key={index} className="mapping-row">
                  <div className="mapping-fields">
                    <select
                      value={mappings[index]?.sourceField || ''}
                      onChange={(e) => handleMappingChange(index, 'sourceField', e.target.value)}
                    >
                      <option value="" disabled>Select source field</option>
                      {previewData[0] && Object.keys(previewData[0]).map((column, idx) => (
                        <option key={idx} value={column}>{column}</option>
                      ))}
                    </select>
                    <span className="mapping-arrow">→</span>
                    <span>{field}</span>
                  </div>
                  <button
                    type="button"
                    className="remove-mapping-button"
                    onClick={() => handleRemoveMapping(index)}
                    title="Remove mapping"
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                type="button"
                className="add-mapping-button"
                onClick={handleAddMapping}
              >
                + Add Field Mapping
              </button>
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="form-actions">
              <button
                type="button"
                className="cancel-button"
                onClick={onCancel}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="save-button"
                disabled={saving}
              >
                {saving ? 'Saving...' : (fieldMap ? 'Update' : 'Create')}
              </button>
            </div>
          </form>
        </div>
        <div className="field-map-preview">
          <DataPreviewPanel
            data={previewData}
            loading={loadingPreview}
            error={previewError}
          />
        </div>
      </div>
    </div>
  );
}; 
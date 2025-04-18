import React, { useState, useEffect } from 'react';
import './FieldMapList.css';
import FieldMapService, { FieldMap } from '../services/FieldMapService';
import { Account } from '../services/AccountService';

interface FieldMapListProps {
  onSelectMap?: (map: FieldMap) => void;
  onCreateMap?: () => void;
  onEditMap?: (map: FieldMap) => void;
  onDeleteMap?: (map: FieldMap) => void;
  selectedAccountId?: string;
}

const FieldMapList: React.FC<FieldMapListProps> = ({
  onSelectMap,
  onCreateMap,
  onEditMap,
  onDeleteMap,
  selectedAccountId
}) => {
  const [fieldMaps, setFieldMaps] = useState<FieldMap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchFieldMaps();
  }, []);

  const fetchFieldMaps = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await FieldMapService.listFieldMaps();
      setFieldMaps(response.fieldMaps);
    } catch (err) {
      setError('Failed to load field maps. Please try again.');
      console.error('Error fetching field maps:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteMap = async (map: FieldMap) => {
    if (!onDeleteMap) return;
    
    try {
      await FieldMapService.deleteFieldMap(map.fieldMapId);
      onDeleteMap(map);
      await fetchFieldMaps(); // Refresh the list
    } catch (err) {
      setError('Failed to delete field map. Please try again.');
      console.error('Error deleting field map:', err);
    }
  };

  const filteredMaps = selectedAccountId
    ? fieldMaps.filter(map => !map.accountId || map.accountId === selectedAccountId)
    : fieldMaps;

  if (loading) {
    return <div className="field-map-list-loading">Loading field maps...</div>;
  }

  if (error) {
    return <div className="field-map-list-error">{error}</div>;
  }

  if (filteredMaps.length === 0) {
    return (
      <div className="field-map-list-empty">
        <p>No field maps found.</p>
        {onCreateMap && (
          <button onClick={onCreateMap} className="create-map-button">
            Create New Map
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="field-map-list">
      {onCreateMap && (
        <div className="field-map-list-header">
          <button onClick={onCreateMap} className="create-map-button">
            Create New Map
          </button>
        </div>
      )}
      <div className="field-map-grid">
        {filteredMaps.map((map) => (
          <div key={map.fieldMapId} className="field-map-card">
            <div className="field-map-card-content">
              <h3>{map.name}</h3>
              {map.description && <p>{map.description}</p>}
              <div className="field-map-card-actions">
                {onSelectMap && (
                  <button
                    onClick={() => onSelectMap(map)}
                    className="select-map-button"
                  >
                    Select
                  </button>
                )}
                {onEditMap && (
                  <button
                    onClick={() => onEditMap(map)}
                    className="edit-map-button"
                  >
                    Edit
                  </button>
                )}
                {onDeleteMap && (
                  <button
                    onClick={() => handleDeleteMap(map)}
                    className="delete-map-button"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FieldMapList; 
import React from 'react';
import './FileFieldMapStatus.css';

interface FieldMap {
  fieldMapId: string;
  name: string;
  description?: string;
}

interface FileFieldMapStatusProps {
  fieldMap?: FieldMap;
  onSelectMap: () => void;
  onCreateMap: () => void;
  className?: string;
}

const FileFieldMapStatus: React.FC<FileFieldMapStatusProps> = ({
  fieldMap,
  onSelectMap,
  onCreateMap,
  className = ''
}) => {
  return (
    <div className={`file-field-map-status ${className}`}>
      {fieldMap ? (
        <div className="field-map-info">
          <span className="field-map-name" title={fieldMap.description || ''}>
            {fieldMap.name}
          </span>
          <button
            className="change-map-button"
            onClick={onSelectMap}
            title="Change field map"
          >
            Change
          </button>
        </div>
      ) : (
        <div className="no-field-map">
          <span className="warning-text">No field map selected</span>
          <div className="action-buttons">
            <button
              className="select-map-button"
              onClick={onSelectMap}
              title="Select an existing field map"
            >
              Select Map
            </button>
            <button
              className="create-map-button"
              onClick={onCreateMap}
              title="Create a new field map"
            >
              Create Map
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileFieldMapStatus; 
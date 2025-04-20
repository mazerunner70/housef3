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
          <div className="field-map-details">
            <span 
              className="field-map-name clickable" 
              title={fieldMap.description || 'Click to change field map'} 
              onClick={onSelectMap}
            >
              {fieldMap.name}
            </span>
            {fieldMap.description && (
              <span className="field-map-description" title={fieldMap.description}>
                {fieldMap.description}
              </span>
            )}
          </div>
        </div>
      ) : (
        <button
          className="link-button"
          onClick={onSelectMap}
          title="Link to a field map"
        >
          Link
        </button>
      )}
    </div>
  );
};

export default FileFieldMapStatus; 
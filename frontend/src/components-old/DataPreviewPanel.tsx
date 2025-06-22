import React from 'react';
import './DataPreviewPanel.css';

interface DataPreviewPanelProps {
  data: Array<Record<string, any>>;
  loading?: boolean;
  error?: string;
}

export const DataPreviewPanel: React.FC<DataPreviewPanelProps> = ({
  data,
  loading = false,
  error
}) => {
  if (loading) {
    return (
      <div className="data-preview-panel">
        <div className="data-preview-loading">Loading data preview...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="data-preview-panel">
        <div className="data-preview-error">{error}</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="data-preview-panel">
        <div className="data-preview-empty">No data available for preview</div>
      </div>
    );
  }

  // Get all unique columns from the data
  const columns = Array.from(
    new Set(data.flatMap(row => Object.keys(row)))
  );

  return (
    <div className="data-preview-panel">
      <h3>Data Preview</h3>
      <div className="data-preview-table-container">
        <table className="data-preview-table">
          <thead>
            <tr>
              {columns.map((column, index) => (
                <th key={index}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((column, colIndex) => (
                  <td key={`${rowIndex}-${colIndex}`}>
                    {row[column] !== undefined ? String(row[column]) : ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}; 
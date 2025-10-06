import React from 'react';

export type FileFormat = 'csv' | 'ofx' | 'qif' | 'qfx' | 'xlsx' | 'xls' | 'unknown';

interface FileFormatDisplayProps {
  format: string;
  showIcon?: boolean;
  className?: string;
  size?: 'small' | 'medium' | 'large';
  variant?: 'badge' | 'text' | 'chip';
}

const FileFormatDisplay: React.FC<FileFormatDisplayProps> = ({
  format,
  showIcon = true,
  className = '',
  size = 'medium',
  variant = 'badge',
}) => {
  // Normalize format to standard types
  const normalizeFormat = (formatText: string): FileFormat => {
    const lowerFormat = formatText.toLowerCase().trim();
    
    if (lowerFormat.includes('csv')) return 'csv';
    if (lowerFormat.includes('ofx')) return 'ofx';
    if (lowerFormat.includes('qif')) return 'qif';
    if (lowerFormat.includes('qfx')) return 'qfx';
    if (lowerFormat.includes('xlsx')) return 'xlsx';
    if (lowerFormat.includes('xls')) return 'xls';
    
    return 'unknown';
  };

  const getFormatIcon = (formatType: FileFormat): string => {
    const icons = {
      csv: '📊',
      ofx: '🏦',
      qif: '📋',
      qfx: '🔢',
      xlsx: '📈',
      xls: '📊',
      unknown: '📄'
    };
    return icons[formatType] || icons.unknown;
  };

  const getFormatColor = (formatType: FileFormat): string => {
    const colors = {
      csv: '#28a745',    // green
      ofx: '#007bff',    // blue
      qif: '#6f42c1',    // purple
      qfx: '#17a2b8',    // teal
      xlsx: '#28a745',   // green
      xls: '#ffc107',    // yellow
      unknown: '#6c757d' // gray
    };
    return colors[formatType] || colors.unknown;
  };

  const getFormatDescription = (formatType: FileFormat): string => {
    const descriptions = {
      csv: 'Comma-Separated Values',
      ofx: 'Open Financial Exchange',
      qif: 'Quicken Interchange Format',
      qfx: 'Quicken Financial Exchange',
      xlsx: 'Excel Spreadsheet',
      xls: 'Excel Legacy Format',
      unknown: 'Unknown Format'
    };
    return descriptions[formatType] || descriptions.unknown;
  };

  const normalizedFormat = normalizeFormat(format);
  const icon = getFormatIcon(normalizedFormat);
  const color = getFormatColor(normalizedFormat);
  const description = getFormatDescription(normalizedFormat);

  const displayText = format.toUpperCase();

  const formatClasses = [
    'file-format-display',
    `file-format-${variant}`,
    `file-format-${size}`,
    `file-format-${normalizedFormat}`,
    className
  ].filter(Boolean).join(' ');

  const formatStyle = variant === 'badge' ? { 
    color: 'white', 
    backgroundColor: color,
    borderColor: color
  } : variant === 'chip' ? {
    color: color,
    backgroundColor: `${color}20`,
    borderColor: color
  } : {
    color: color
  };

  return (
    <span
      className={formatClasses}
      style={formatStyle}
      title={`${displayText} - ${description}`}
    >
      {showIcon && <span className="format-icon">{icon}</span>}
      <span className="format-text">{displayText}</span>
    </span>
  );
};

export default FileFormatDisplay; 
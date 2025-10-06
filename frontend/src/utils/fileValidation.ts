// File validation utilities for transaction imports

export interface FileValidationConfig {
  maxSizeBytes: number;
  allowedExtensions: string[];
  allowedMimeTypes: string[];
}

export interface FileValidationResult {
  isValid: boolean;
  error?: string;
  fileType?: 'csv' | 'qif' | 'ofx' | 'qfx';
  fileSize?: number;
  warnings?: string[];
}

// Default configuration for transaction files
export const DEFAULT_VALIDATION_CONFIG: FileValidationConfig = {
  maxSizeBytes: 10 * 1024 * 1024, // 10MB
  allowedExtensions: ['.csv', '.qif', '.ofx', '.qfx'],
  allowedMimeTypes: [
    'text/csv',
    'application/csv',
    'text/plain',
    'application/x-ofx',
    'application/xml',
    'text/xml',
    'application/x-quicken',
    'application/vnd.intu.qfx'
  ]
};

/**
 * Extract file extension from filename
 */
export const getFileExtension = (filename: string): string => {
  return filename.toLowerCase().substring(filename.lastIndexOf('.'));
};

/**
 * Detect file type based on extension
 */
export const detectFileType = (filename: string): 'csv' | 'qif' | 'ofx' | 'qfx' | null => {
  const extension = getFileExtension(filename);
  switch (extension) {
    case '.csv':
      return 'csv';
    case '.qif':
      return 'qif';
    case '.ofx':
      return 'ofx';
    case '.qfx':
      return 'qfx';
    default:
      return null;
  }
};

/**
 * Validate file extension
 */
export const validateFileExtension = (filename: string, config: FileValidationConfig = DEFAULT_VALIDATION_CONFIG): boolean => {
  const extension = getFileExtension(filename);
  return config.allowedExtensions.includes(extension);
};

/**
 * Validate MIME type
 */
export const validateMimeType = (mimeType: string, config: FileValidationConfig = DEFAULT_VALIDATION_CONFIG): boolean => {
  return config.allowedMimeTypes.includes(mimeType.toLowerCase());
};

/**
 * Basic OFX content validation
 * Checks for OFX-specific headers and structure
 */
export const validateOFXContent = async (file: File): Promise<{ isValid: boolean; warnings?: string[] }> => {
  if (!file.name.toLowerCase().endsWith('.ofx')) {
    return { isValid: true }; // Skip validation for non-OFX files
  }

  try {
    // Read first 2KB of file to check for OFX headers
    const chunk = file.slice(0, 2048);
    const text = await chunk.text();
    
    const warnings: string[] = [];
    
    // Check for OFX header indicators
    const hasOFXHeader = text.includes('<OFX>') || 
                        text.includes('OFXHEADER:') || 
                        text.includes('VERSION:');
    
    const hasTransactionData = text.includes('<STMTRS>') ||
                              text.includes('<CCSTMTRS>') ||
                              text.includes('<STMTTRN>');
    
    if (!hasOFXHeader) {
      warnings.push('File may not have a proper OFX header');
    }
    
    if (!hasTransactionData) {
      warnings.push('No transaction data detected in file preview');
    }
    
    // Check for common OFX version indicators
    if (text.includes('VERSION:102') || text.includes('VERSION:103')) {
      warnings.push('Older OFX version detected - may have limited support');
    }
    
    return {
      isValid: hasOFXHeader || hasTransactionData,
      warnings: warnings.length > 0 ? warnings : undefined
    };
    
  } catch (error) {
    console.warn('Could not validate OFX content:', error);
    return { 
      isValid: true, // Allow file if we can't validate content
      warnings: ['Could not validate file content - proceeding with caution']
    };
  }
};

/**
 * Enhanced QIF content validation
 */
export const validateQIFContent = async (file: File): Promise<{ isValid: boolean; warnings?: string[] }> => {
  if (!file.name.toLowerCase().endsWith('.qif')) {
    return { isValid: true };
  }

  try {
    const chunk = file.slice(0, 2048);
    const text = await chunk.text();
    
    const warnings: string[] = [];
    
    // Check for QIF type header
    const hasTypeHeader = /!Type:(Bank|Cash|CCard|Invst|Oth A|Oth L)/.test(text);
    
    // Check for transaction structure
    const hasTransactionData = text.includes('D') && text.includes('T') && text.includes('^');
    
    // Check for account header (multi-account files)
    const hasAccountHeader = text.includes('!Account');
    
    if (!hasTypeHeader && !hasAccountHeader) {
      warnings.push('No QIF type header found - file may not be valid QIF format');
    }
    
    if (!hasTransactionData) {
      warnings.push('No transaction data detected in file preview');
    }
    
    // Check for potential encoding issues
    if (text.includes('�') || text.includes('\ufffd')) {
      warnings.push('File may have encoding issues - ensure it is saved as plain text');
    }
    
    const isValid = hasTypeHeader || hasAccountHeader || hasTransactionData;
    
    return {
      isValid,
      warnings: warnings.length > 0 ? warnings : undefined
    };
    
  } catch (error) {
    console.warn('Could not validate QIF content:', error);
    return { 
      isValid: true,
      warnings: ['Could not validate file content - proceeding with caution']
    };
  }
};

/**
 * Validate QFX content (similar to OFX but Quicken-specific)
 */
export const validateQFXContent = async (file: File): Promise<{ isValid: boolean; warnings?: string[] }> => {
  if (!file.name.toLowerCase().endsWith('.qfx')) {
    return { isValid: true };
  }

  try {
    const chunk = file.slice(0, 2048);
    const text = await chunk.text();
    
    const warnings: string[] = [];
    
    // QFX files are similar to OFX but may have Quicken-specific elements
    const hasQFXIndicators = text.includes('<OFX>') || 
                            text.includes('QFXHEADER:') ||
                            text.includes('<SONRS>') ||
                            text.includes('<STMTRS>');
    
    if (!hasQFXIndicators) {
      warnings.push('File may not be a valid QFX format');
    }
    
    return {
      isValid: hasQFXIndicators,
      warnings: warnings.length > 0 ? warnings : undefined
    };
    
  } catch (error) {
    console.warn('Could not validate QFX content:', error);
    return { 
      isValid: true,
      warnings: ['Could not validate file content']
    };
  }
};

/**
 * Validate CSV content structure
 */
export const validateCSVContent = async (file: File): Promise<{ isValid: boolean; warnings?: string[] }> => {
  if (!file.name.toLowerCase().endsWith('.csv')) {
    return { isValid: true };
  }

  try {
    const chunk = file.slice(0, 1024);
    const text = await chunk.text();
    
    const warnings: string[] = [];
    const lines = text.split('\n');
    
    if (lines.length < 2) {
      warnings.push('CSV file appears to have very few rows');
    }
    
    // Check for common CSV issues
    const firstLine = lines[0];
    if (!firstLine.includes(',') && !firstLine.includes(';') && !firstLine.includes('\t')) {
      warnings.push('File may not be properly formatted CSV (no common delimiters found)');
    }
    
    return {
      isValid: true, // CSV validation is more permissive
      warnings: warnings.length > 0 ? warnings : undefined
    };
    
  } catch (error) {
    console.warn('Could not validate CSV content:', error);
    return { isValid: true };
  }
};

/**
 * Comprehensive file validation
 */
export const validateTransactionFile = async (
  file: File, 
  config: FileValidationConfig = DEFAULT_VALIDATION_CONFIG
): Promise<FileValidationResult> => {
  const warnings: string[] = [];
  
  // Check file size
  if (file.size > config.maxSizeBytes) {
    return {
      isValid: false,
      error: `File is too large. Maximum size is ${Math.round(config.maxSizeBytes / 1024 / 1024)}MB`
    };
  }

  // Check minimum file size
  if (file.size < 10) {
    return {
      isValid: false,
      error: 'File appears to be empty or corrupted'
    };
  }

  // Check file extension
  if (!validateFileExtension(file.name, config)) {
    return {
      isValid: false,
      error: `Unsupported file type. Supported formats: ${config.allowedExtensions.join(', ')}`
    };
  }

  // Check MIME type (if available) - warn but don't fail
  if (file.type && !validateMimeType(file.type, config)) {
    warnings.push(`Unexpected MIME type: ${file.type}`);
  }

  // Detect file type
  const fileType = detectFileType(file.name);
  if (!fileType) {
    return {
      isValid: false,
      error: 'Could not determine file type from extension'
    };
  }

  // Content validation based on file type
  let contentValidation: { isValid: boolean; warnings?: string[] };
  
  switch (fileType) {
    case 'ofx':
      contentValidation = await validateOFXContent(file);
      break;
    case 'qfx':
      contentValidation = await validateQFXContent(file);
      break;
    case 'qif':
      contentValidation = await validateQIFContent(file);
      break;
    case 'csv':
      contentValidation = await validateCSVContent(file);
      break;
    default:
      contentValidation = { isValid: true };
  }

  if (!contentValidation.isValid) {
    return {
      isValid: false,
      error: `File does not appear to be a valid ${fileType.toUpperCase()} file. Please check the file format.`
    };
  }

  // Combine warnings
  if (contentValidation.warnings) {
    warnings.push(...contentValidation.warnings);
  }

  return {
    isValid: true,
    fileType,
    fileSize: file.size,
    warnings: warnings.length > 0 ? warnings : undefined
  };
};

/**
 * Format file size for display
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Get file type icon emoji
 */
export const getFileTypeIcon = (fileType: string): string => {
  switch (fileType.toLowerCase()) {
    case 'ofx':
      return '📄';
    case 'qfx':
      return '💳';
    case 'csv':
      return '📊';
    case 'qif':
      return '💰';
    default:
      return '📋';
  }
};

/**
 * Get file type description
 */
export const getFileTypeDescription = (fileType: string): string => {
  switch (fileType.toLowerCase()) {
    case 'ofx':
      return 'Open Financial Exchange - Standard bank format';
    case 'qfx':
      return 'Quicken Financial Exchange - Quicken format';
    case 'csv':
      return 'Comma Separated Values - Spreadsheet format';
    case 'qif':
      return 'Quicken Interchange Format - Legacy Quicken format';
    default:
      return 'Unknown format';
  }
}; 
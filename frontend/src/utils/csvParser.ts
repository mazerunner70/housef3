export interface ParsedCSV {
  headers: string[];
  data: Array<Record<string, string>>;
}

export const parseCSV = (content: string): ParsedCSV => {
  const lines = content.split('\n');
  if (!content.trim()) return { headers: [], data: [] };

  // Parse header row
  const headerLine = lines[0].trim().replace(/,+$/, ''); // Remove one or more trailing commas
  const headers = headerLine.split(',').map(h => h.trim().replace(/^["']|["']$/g, ''));
  // Parse all data rows
  const data = lines.slice(1).map(line => {
    // Skip empty lines
    if (!line.trim()) return null;
    
    // Remove trailing comma from data line
    const cleanLine = line.trim().replace(/,+$/, ''); // Remove one or more trailing commas

    // Split the line by commas, but be careful with unquoted fields containing commas
    const values: string[] = [];
    let currentValue = '';
    let inQuotes = false;
    
    for (let i = 0; i < cleanLine.length; i++) {
      const char = cleanLine[i];
      
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        values.push(currentValue.trim().replace(/^["']|["']$/g, ''));
        currentValue = '';
      } else {
        currentValue += char;
      }
    }
    
    // Add the last value
    values.push(currentValue.trim().replace(/^["']|["']$/g, ''));
    
    /* If we have more values than headers:
       1) if there are more values than headers, look for a freetext field (Merchant, description.payee) that likely should hold the extra commas
       2) let a variable extraFields = the number of values minus the number of headers
       3) join the next extraFields number of value fields into the freetext field to 
       4) shift left all the extra fields
    */
    if (values.length > headers.length) {
      const freeTextIndex = headers.findIndex(h => 
        h.toLowerCase().includes('description') || 
        h.toLowerCase().includes('merchant') ||
        h.toLowerCase().includes('payee')
      );
      
      if (freeTextIndex !== -1 && freeTextIndex < values.length - 1) {
        const extraFields = values.length - headers.length;
        // Keep the original merchant/description value and the next value (amount)
        const newDescValue = values.slice(freeTextIndex, freeTextIndex + extraFields+1).join(',');
        values[freeTextIndex] = newDescValue;
        // Remove the extra fields
        values.splice(freeTextIndex + 1, extraFields);
      }
    }
    
    return headers.reduce((obj, header, index) => {
      obj[header] = values[index] || '';
      return obj;
    }, {} as Record<string, string>);
  }).filter((row): row is Record<string, string> => row !== null); // Remove empty lines

  return { headers, data };
};

// Based on frontend/src/services/TransactionService.ts
export const PREDEFINED_TRANSACTION_FIELDS = ['date', 'description', 'amount', 'debitOrCredit', 'currency'] as const;
export type TransactionField = typeof PREDEFINED_TRANSACTION_FIELDS[number];
export type ColumnMapTarget = TransactionField | 'skip'; // 'skip' means the column won't be imported

export interface CsvColumnMapping {
  [csvHeader: string]: ColumnMapTarget;
}

export const suggestColumnMappings = (csvHeaders: string[]): CsvColumnMapping => {
  const suggestions: CsvColumnMapping = {};
  const lowerCaseHeaders = csvHeaders.map(h => h.toLowerCase().trim());

  const commonPatterns: Record<TransactionField, string[]> = {
    date: ['date', 'transaction date', 'posting date', 'valuedate'],
    description: ['description', 'details', 'memo', 'narrative', 'transaction details', 'payee', 'merchant'],
    amount: ['amount', 'value', 'sum', 'total', 'price'],
    debitOrCredit: ['type', 'transaction type', 'debit/credit', 'cr/dr', 'kind', 'credit', 'debit'],
    currency: ['currency', 'ccy', 'curr.', 'transaction currency'],
  };

  lowerCaseHeaders.forEach((header, index) => {
    let mappedField: ColumnMapTarget = 'skip'; // Default to skip
    // Ensure all PREDEFINED_TRANSACTION_FIELDS are checked
    for (const field of PREDEFINED_TRANSACTION_FIELDS) {
      // Check if commonPatterns has an entry for the field before trying to access it
      if (commonPatterns[field] && commonPatterns[field].some(pattern => header.includes(pattern))) {
        mappedField = field;
        break;
      }
    }
    suggestions[csvHeaders[index]] = mappedField; // Use original header as key
  });
  return suggestions;
};

export const FIELD_VALIDATION_REGEXES: Partial<Record<TransactionField, RegExp>> = {
  date: /^(0?[1-9]|1[0-2])[-/.](0?[1-9]|[12][0-9]|3[01])[-/.](\d{2}|\d{4})$|^\d{4}[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12][0-9]|3[01])$/,
  amount: /^-?\$?\s*\d{1,3}(?:,?\d{3})*(?:\.\d{1,2})?$/,
  debitOrCredit: /^(debit|credit|dr|cr|d|c)$/i,
  currency: /^[A-Z]{3}$/i,
};

export const isValidFieldData = (value: string, fieldType: TransactionField): boolean => {
  if (!value) return true; // Allow empty optional fields
  const regex = FIELD_VALIDATION_REGEXES[fieldType];
  if (regex) {
    return regex.test(value.trim());
  }
  return true; // Default to true if no regex (e.g., for description)
}; 
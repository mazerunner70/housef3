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
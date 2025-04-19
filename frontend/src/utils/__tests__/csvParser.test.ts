import { parseCSV } from '../csvParser';

describe('CSV Parser', () => {
  test('should handle empty content', () => {
    const result = parseCSV('');
    expect(result.headers).toEqual([]);
    expect(result.data).toEqual([]);
  });

  test('should parse basic CSV content', () => {
    const content = `Name,Age,City
John,30,New York
Jane,25,Los Angeles`;
    
    const result = parseCSV(content);
    expect(result.headers).toEqual(['Name', 'Age', 'City']);
    expect(result.data).toEqual([
      { Name: 'John', Age: '30', City: 'New York' },
      { Name: 'Jane', Age: '25', City: 'Los Angeles' }
    ]);
  });

  test('should handle quoted fields', () => {
    const content = `Name,Description,Amount
John,"Software Engineer, Senior",1000
Jane,"Product Manager, Lead",2000`;
    
    const result = parseCSV(content);
    expect(result.headers).toEqual(['Name', 'Description', 'Amount']);
    expect(result.data).toEqual([
      { Name: 'John', Description: 'Software Engineer, Senior', Amount: '1000' },
      { Name: 'Jane', Description: 'Product Manager, Lead', Amount: '2000' }
    ]);
  });

  test('should handle trailing commas', () => {
    const content = `Name,Description,Amount,
John,Software Engineer,1000,
Jane,Product Manager,2000,`;
    
    const result = parseCSV(content);
    expect(result.headers).toEqual(['Name', 'Description', 'Amount']);
    expect(result.data).toEqual([
      { Name: 'John', Description: 'Software Engineer', Amount: '1000' },
      { Name: 'Jane', Description: 'Product Manager', Amount: '2000' }
    ]);
  });

  test('should handle unquoted fields with commas', () => {
    const content = `Date,Merchant,Amount
2023-01-01,GITHUB,INC.,1000
2023-01-02,AMAZON.COM,2000`;
    
    const result = parseCSV(content);
    expect(result.headers).toEqual(['Date', 'Merchant', 'Amount']);
    expect(result.data).toEqual([
      { Date: '2023-01-01', Merchant: 'GITHUB,INC.', Amount: '1000' },
      { Date: '2023-01-02', Merchant: 'AMAZON.COM', Amount: '2000' }
    ]);
  });

  test('should handle unquoted fields with commas, plus trailing comma', () => {
    const content = `Date,Merchant,Amount,
2023-01-01,GITHUB,INC.,1000
2023-01-02,AMAZON.COM,2000,`;
    
    const result = parseCSV(content);
    expect(result.headers).toEqual(['Date', 'Merchant', 'Amount']);
    expect(result.data).toEqual([
      { Date: '2023-01-01', Merchant: 'GITHUB,INC.', Amount: '1000' },
      { Date: '2023-01-02', Merchant: 'AMAZON.COM', Amount: '2000' }
    ]);
  });




  test('should handle empty lines', () => {
    const content = `Date,Merchant,Amount

2023-01-01,GITHUB,INC.,1000

2023-01-02,AMAZON.COM,2000
`;
    
    const result = parseCSV(content);
    expect(result.headers).toEqual(['Date', 'Merchant', 'Amount']);
    expect(result.data).toEqual([
      { Date: '2023-01-01', Merchant: 'GITHUB,INC.', Amount: '1000' },
      { Date: '2023-01-02', Merchant: 'AMAZON.COM', Amount: '2000' }
    ]);
  });
}); 

test('handle a windows saved csv file with line feeds', () => {
  const content = `Date,Merchant,Amount\r\n2023-01-01,GITHUB,INC.,1000\r\n2023-01-02,AMAZON.COM,2000\r\n`;

  const result = parseCSV(content);
  expect(result.headers).toEqual(['Date', 'Merchant', 'Amount']);
  expect(result.data).toEqual([
    { Date: '2023-01-01', Merchant: 'GITHUB,INC.', Amount: '1000' },
    { Date: '2023-01-02', Merchant: 'AMAZON.COM', Amount: '2000' }
  ]);
  
})
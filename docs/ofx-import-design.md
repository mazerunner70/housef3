# OFX File Import Expansion Design Document

## Overview
This document describes the approach for expanding the transaction import system to support OFX (Open Financial Exchange) files, in addition to existing formats (CSV, QIF, etc.).

## Background
OFX is a widely used XML-based format for exchanging financial data between institutions and personal finance software. Supporting OFX will allow users to import transactions from a broader range of banks and credit card providers.

---

## Goals
- Allow users to upload and import OFX files via the existing import UI
- Parse OFX files on the backend and extract transaction data
- Map OFX fields to the internal transaction model
- Handle common OFX variants and edge cases (e.g., different date formats, missing fields)
- Provide clear error messages for unsupported or malformed OFX files
- Maintain security and privacy of imported data

---

## Technical Approach

### 1. File Detection & Upload (Frontend)
- **File Type Detection**: Update the file picker to accept `.ofx` files (in addition to `.csv`, `.qif`, etc.)
- **MIME Type**: Accept `application/x-ofx`, `application/xml`, and `text/xml` for OFX
- **UI Update**: Update help text and file filter to mention OFX support
- **Validation**: Basic client-side validation for file extension and size

### 2. Backend OFX Parsing
- **Library Selection**: Use a robust OFX parsing library (e.g., `ofxparse` for Python, `ofx` for Node.js, or similar)
- **Parser Integration**:
  - Add an OFX parser module to the backend import pipeline
  - Detect file type by extension and/or file signature
  - Route OFX files to the new parser
- **Field Mapping**:
  - Map OFX fields (e.g., `<STMTTRN>`, `<DTPOSTED>`, `<TRNAMT>`, `<NAME>`, `<MEMO>`) to internal transaction fields
  - Handle date parsing (OFX dates are often in `YYYYMMDD` or `YYYYMMDDHHMMSS` format)
  - Normalize currency, account, and payee fields
- **Error Handling**:
  - Catch and report malformed OFX files
  - Provide user-friendly error messages for common issues (e.g., unsupported OFX version, missing transactions)
- **Security**:
  - Sanitize all parsed data
  - Reject files with suspicious or invalid content

### 3. Transaction Model Mapping
- **OFX → Internal Model**:
  - `DTPOSTED` → `date`
  - `TRNAMT` → `amount`
  - `NAME` or `PAYEE` → `description`/`payee`
  - `MEMO` → `notes`
  - `FITID` → `externalId` (for deduplication)
  - `CHECKNUM` → `checkNumber` (optional)
  - `CURRENCY` → `currency`
  - `ACCTID` → `accountId` (if present)
- **Deduplication**:
  - Use `FITID` (Financial Institution Transaction ID) to prevent duplicate imports

### 4. Import Pipeline Integration
- **Unified Import Flow**:
  - Integrate OFX parsing into the existing import pipeline
  - Reuse validation, deduplication, and transaction creation logic
  - Support batch import and preview before commit
- **Feedback to User**:
  - Show summary of imported transactions (count, date range, total amount)
  - Highlight any skipped/duplicate/invalid entries

### 5. Testing & Validation
- **Unit Tests**:
  - Test OFX parser with a variety of real-world OFX files (different banks, credit cards, date formats)
  - Test error handling for malformed or partial files
- **Integration Tests**:
  - End-to-end tests for uploading and importing OFX files via the UI
  - Ensure correct mapping to internal transaction model
- **Sample Files**:
  - Collect a set of OFX files from different institutions for test coverage

### 6. Documentation & Support
- **User Documentation**:
  - Update help docs to explain OFX support and any limitations
  - Provide troubleshooting tips for common OFX import issues
- **Developer Documentation**:
  - Document OFX parser integration and mapping logic
  - List supported OFX versions and known edge cases

---

## Implementation Steps

1. **Frontend**
   - Update file picker and UI to accept OFX
   - Update documentation/help text
2. **Backend**
   - Integrate OFX parsing library
   - Implement OFX-to-internal mapping logic
   - Add error handling and deduplication
   - Integrate with existing import pipeline
3. **Testing**
   - Add unit and integration tests
   - Validate with real-world OFX files
4. **Docs**
   - Update user and developer documentation

---

## Risks & Mitigations
- **OFX Variants**: Some banks use non-standard OFX; mitigate by supporting most common variants and providing clear error messages
- **Large Files**: OFX files can be large; ensure streaming parsing and file size limits
- **Security**: OFX is XML-based; guard against XML attacks (e.g., entity expansion, XXE)
- **Deduplication**: Ensure robust use of `FITID` to prevent duplicate transactions

---

## Success Criteria
- Users can successfully import OFX files from major banks/credit cards
- Transactions are correctly parsed and mapped
- Duplicates are avoided
- Errors are clearly reported
- No security vulnerabilities introduced

---

## References
- [OFX Specification](https://www.ofx.net/downloads/OFX%202.2.pdf)
- [ofxparse (Python)](https://github.com/csingley/ofxparse)
- [ofx (Node.js)](https://www.npmjs.com/package/ofx) 
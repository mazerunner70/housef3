# Implementation Plan

## Field Mapping System

### 1. Data Models

#### FieldMap Model
```typescript
interface FieldMap {
  fieldMapId: string;
  userId: string;
  accountId?: string;  // Optional - for default account mappings
  name: string;
  description?: string;
  mappings: FieldMapping[];
  createdAt: string;
  updatedAt: string;
}

interface FieldMapping {
  sourceField: string;  // Column name/identifier in source file
  targetField: string;  // Transaction model field name
  transformation?: string;  // Optional transformation logic
}
```

#### Updates to Existing Models
- Add `fieldMapId` to `TransactionFile` model
- Add `defaultFieldMapId` to `Account` model

### 2. Database Changes

#### New DynamoDB Table: field_maps
- Primary Key: `fieldMapId` (string)
- GSI1: `userId-index` on `userId`
- GSI2: `accountId-index` on `accountId`

#### Table Updates
- Update `transaction_files` table to include `fieldMapId` field
- Update `accounts` table to include `defaultFieldMapId` field

### 3. Backend Implementation

#### New Lambda Functions
1. `field_map_operations.py`:
   - Create field map
   - Update field map
   - Delete field map
   - List field maps by user
   - Get field map by ID
   - List account default maps

#### Updates to Existing Functions
1. `file_processor.py`:
   - Update to require field map before processing
   - Implement field mapping logic during file parsing
   - Add validation for required fields

2. `file_operations.py`:
   - Add endpoints for associating field maps with files
   - Update file status to include field map status

3. `account_operations.py`:
   - Add endpoints for managing default field maps

### 4. Frontend Implementation

#### New Components
1. `FieldMapList.tsx`:
   - Display all field maps for user
   - Filter by account
   - Create/edit/delete maps

2. `FieldMapEditor.tsx`:
   - Drag-and-drop interface for mapping fields
   - Preview of mapping results
   - Validation feedback

3. `FileFieldMapStatus.tsx`:
   - Visual indicator for field map status
   - Quick actions for mapping assignment

#### Updates to Existing Components
1. `FileList.tsx`:
   - Add field map status indicator
   - Add "View/Edit Mapping" button
   - Update file upload flow to handle mappings

2. `AccountSettings.tsx`:
   - Add default field map management
   - Preview of default mappings

3. `FileUpload.tsx`:
   - Add field map selection step
   - Option to create new mapping during upload

### 5. API Endpoints

#### New Endpoints
```
POST   /field-maps                 # Create new field map
GET    /field-maps                 # List user's field maps
GET    /field-maps/{id}           # Get specific field map
PUT    /field-maps/{id}           # Update field map
DELETE /field-maps/{id}           # Delete field map
GET    /accounts/{id}/field-maps  # Get account default maps
PUT    /files/{id}/field-map      # Associate map with file
```

### 6. User Interface Flow

1. File Upload Flow:
   - Upload file
   - Select existing map or create new
   - Preview mapping results
   - Confirm and process

2. Field Map Management:
   - List view of all maps
   - Edit interface with drag-drop
   - Preview capabilities
   - Default map assignment

3. File List View:
   - Status indicator for mapping
   - Quick actions for mapping
   - Filter by mapping status

### 7. Implementation Phases

#### Phase 1: Core Infrastructure
- Create field_maps table
- Implement basic CRUD operations
- Update file and account models

#### Phase 2: Backend Processing
- Implement mapping logic in file processor
- Add validation and error handling
- Update file processing workflow

#### Phase 3: Frontend Basic
- Add field map status to file list
- Implement basic mapping interface
- Update file upload flow

#### Phase 4: Frontend Advanced
- Implement drag-drop interface
- Add preview capabilities
- Enhance validation feedback

#### Phase 5: Testing & Refinement
- End-to-end testing
- Performance optimization
- UX improvements

### 8. Testing Strategy

1. Unit Tests:
   - Field map CRUD operations
   - Mapping logic validation
   - File processing with maps

2. Integration Tests:
   - File upload with mapping
   - Account default maps
   - Error handling

3. UI Tests:
   - Mapping interface usability
   - Status indicators
   - Preview functionality

### 9. Monitoring & Metrics

1. Track:
   - Mapping success rates
   - Common mapping patterns
   - Processing times
   - Error rates

2. Alerts:
   - High failure rates
   - Processing delays
   - Error spikes

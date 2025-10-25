# FZIP Domain

This domain provides complete backup and restore functionality for financial profiles using the FZIP (Financial ZIP) format.

## Overview

The FZIP domain is a self-contained feature that handles:
- Creating and managing financial profile backups
- Uploading and restoring FZIP backup files
- Real-time progress tracking for backup/restore operations
- Comprehensive validation and error handling

## Structure

```
components/domain/fzip/
├── FZIPPage.tsx                    # Entry point (routing jump off)
├── FZIPDashboard.tsx               # Main component (tabbed interface)
├── components/                     # Supporting components
│   ├── FZIPBackupCreator.tsx       # Backup creation form
│   ├── FZIPBackupList.tsx          # Backup jobs list
│   ├── FZIPRestoreUpload.tsx       # File upload interface
│   ├── FZIPRestoreList.tsx         # Restore jobs list
│   ├── FZIPRestoreSummary.tsx      # Restore summary modal
│   ├── FZIPRestoreResults.tsx      # Restore results modal
│   └── FZIPRestoreError.tsx        # Restore error modal
├── hooks/                          # Domain-specific hooks
│   ├── useFZIPBackups.ts           # Backup state and operations
│   ├── useFZIPRestore.ts           # Restore state and operations
│   └── useFZIPRestoreStatus.ts     # Restore status polling
├── index.ts                        # Domain exports
└── *.css                           # Component styles
```

## Routing

- **Primary Route**: `/fzip` - Main FZIP backup and restore page
- **Legacy Route**: `/backup` - Redirects to `/fzip` for backward compatibility

## Features

### Backup Features
- Multiple backup types (complete, accounts only, etc.)
- Optional analytics inclusion
- Backup descriptions and metadata
- Real-time progress tracking
- Quality validation with scoring
- Automatic status refresh
- Download management
- Backup expiration handling

### Restore Features
- Empty profile validation
- Drag & drop file upload
- File validation (format, size)
- Real-time restore progress
- Multi-phase progress tracking
- Validation results display
- Restore results summary
- Error handling with user guidance

## Usage

### Direct Navigation
```typescript
// Navigate to FZIP page
navigate('/fzip');
```

### Import Components
```typescript
import { FZIPPage, FZIPDashboard } from '@/components/domain/fzip';

// Or import specific components
import { 
  FZIPBackupCreator, 
  FZIPBackupList,
  useFZIPBackups 
} from '@/components/domain/fzip';
```

### Using Hooks
```typescript
import { useFZIPBackups, useFZIPRestore } from '@/components/domain/fzip';

function MyComponent() {
  const { backups, createBackup, deleteBackup } = useFZIPBackups();
  const { restoreJobs, refreshRestoreJobs } = useFZIPRestore();
  
  // Use backup and restore functionality
}
```

## API Integration

Integrates with the backend FZIP API endpoints:

### Backup Endpoints
- `POST /fzip/backup` - Create backup
- `GET /fzip/backup/{id}/status` - Get backup status
- `GET /fzip/backup/{id}/download` - Download backup
- `GET /fzip/backup` - List backups
- `DELETE /fzip/backup/{id}` - Delete backup

### Restore Endpoints
- `POST /fzip/restore` - Create restore job
- `GET /fzip/restore/{id}/status` - Get restore status
- `GET /fzip/restore` - List restore jobs
- `DELETE /fzip/restore/{id}` - Delete restore job
- File upload via S3 presigned URLs

## Design Principles

1. **Self-Contained**: All FZIP-specific code lives in this domain
2. **Single Feature**: Focused solely on backup/restore functionality
3. **Not Reused**: Components are specific to FZIP and not shared with other features
4. **Routable**: Has dedicated routing entry point
5. **Progressive Disclosure**: Tabbed interface for backup vs restore operations

## State Management

The domain uses React hooks for state management:
- `useFZIPBackups` - Manages backup list, creation, and operations
- `useFZIPRestore` - Manages restore jobs and upload workflow
- `useFZIPRestoreStatus` - Handles restore status polling for active jobs

No global state is used - all state is local to the domain.

## Testing

Test files are located in `components/__tests__/`:
- `FZIPRestoreList.test.tsx` - Tests for restore list component
- `FZIPRestoreUpload.test.tsx` - Tests for upload component

Run tests:
```bash
npm test -- FZIPRestore
```

## Architecture Notes

- **Entry Point Pattern**: `FZIPPage.tsx` is thin (navigation context only)
- **Main Component**: `FZIPDashboard.tsx` contains all business logic
- **Tabbed Interface**: Backup and Restore tabs in single unified view
- **Real-time Updates**: Polling for job status updates
- **Error Boundaries**: Comprehensive error handling at all levels
- **Responsive Design**: Mobile, tablet, and desktop layouts

## Future Enhancements

Potential improvements for this domain:
- Backup scheduling
- Incremental backups
- Backup comparison tools
- Restore preview mode
- Backup encryption options
- Multi-profile restore


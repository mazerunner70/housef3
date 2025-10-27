import React, { useState } from 'react';
import { FZIPBackupType, InitiateFZIPBackupRequest } from '@/services/FZIPService';
import Button from '@/components/ui/Button';
import './FZIPBackupCreator.css';

interface FZIPBackupCreatorProps {
  onCreateBackup: (request: InitiateFZIPBackupRequest) => Promise<string>;
  isLoading?: boolean;
  disabled?: boolean;
}

const FZIPBackupCreator: React.FC<FZIPBackupCreatorProps> = ({
  onCreateBackup,
  isLoading = false,
  disabled = false
}) => {
  const [backupType, setBackupType] = useState<FZIPBackupType>(FZIPBackupType.COMPLETE);
  const [includeAnalytics, setIncludeAnalytics] = useState(false);
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateBackup = async () => {
    if (isCreating || disabled) return;

    setIsCreating(true);
    try {
      const request: InitiateFZIPBackupRequest = {
        backupType,
        includeAnalytics,
        description: description.trim() || undefined
      };

      await onCreateBackup(request);

      // Reset form after successful creation
      setDescription('');
    } catch (error) {
      console.error('Failed to create backup:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const isFormDisabled = isLoading || disabled || isCreating;

  return (
    <div className="fzip-backup-creator">
      <div className="fzip-backup-creator__header">
        <h3>Create Financial Profile Backup</h3>
        <p>Create a complete backup of your financial data including accounts, transactions, categories, and files.</p>
      </div>

      <div className="fzip-backup-creator__form">
        <div className="form-group">
          <label htmlFor="backup-type" className="form-label">
            Backup Type
          </label>
          <select
            id="backup-type"
            value={backupType}
            onChange={(e) => setBackupType(e.target.value as FZIPBackupType)}
            disabled={isFormDisabled}
            className="form-select"
          >
            <option value={FZIPBackupType.COMPLETE}>Complete Profile</option>
            <option value={FZIPBackupType.ACCOUNTS_ONLY}>Accounts Only</option>
            <option value={FZIPBackupType.TRANSACTIONS_ONLY}>Transactions Only</option>
            <option value={FZIPBackupType.CATEGORIES_ONLY}>Categories Only</option>
          </select>
          <small className="form-help">
            {backupType === FZIPBackupType.COMPLETE && 'Includes all accounts, transactions, categories, file maps, and transaction files'}
            {backupType === FZIPBackupType.ACCOUNTS_ONLY && 'Includes only account information'}
            {backupType === FZIPBackupType.TRANSACTIONS_ONLY && 'Includes only transaction data'}
            {backupType === FZIPBackupType.CATEGORIES_ONLY && 'Includes only category definitions and rules'}
          </small>
        </div>

        <div className="form-group">
          <label className="form-checkbox">
            <input
              type="checkbox"
              checked={includeAnalytics}
              onChange={(e) => setIncludeAnalytics(e.target.checked)}
              disabled={isFormDisabled}
            />
            <span className="checkmark"></span>
            <span className="checkbox-label">Include analytics data</span>
          </label>
          <small className="form-help">
            Analytics data can be regenerated after restore, but including it may speed up the restore process.
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="backup-description" className="form-label">
            Description (Optional)
          </label>
          <input
            id="backup-description"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g., Monthly backup, Pre-migration backup"
            disabled={isFormDisabled}
            className="form-input"
            maxLength={200}
          />
          <small className="form-help">
            Add a description to help identify this backup later.
          </small>
        </div>

        <div className="fzip-backup-creator__actions">
          <Button
            variant="primary"
            onClick={handleCreateBackup}
            disabled={isFormDisabled}
          >
            {isCreating ? 'Creating Backup...' : 'Create Backup'}
          </Button>
        </div>
      </div>

      {backupType === FZIPBackupType.COMPLETE && (
        <div className="fzip-backup-creator__info">
          <h4>What's included in a complete backup:</h4>
          <ul>
            <li><strong>Accounts:</strong> All account information, balances, and settings</li>
            <li><strong>Transactions:</strong> All transaction records with amounts, dates, and descriptions</li>
            <li><strong>Categories:</strong> Category hierarchy and categorization rules</li>
            <li><strong>File Maps:</strong> Field mapping configurations for transaction files</li>
            <li><strong>Transaction Files:</strong> Original transaction files and metadata</li>
            <li><strong>Relationships:</strong> All data relationships and referential integrity</li>
          </ul>

          <div className="backup-requirements">
            <h4>Backup Requirements:</h4>
            <ul>
              <li>Backup packages are in FZIP (Financial ZIP) format</li>
              <li>Backups are valid for 24 hours after creation</li>
              <li>Restore requires a completely empty financial profile</li>
              <li>All data is encrypted in transit and at rest</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default FZIPBackupCreator;
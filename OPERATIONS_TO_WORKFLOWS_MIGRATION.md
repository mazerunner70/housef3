# Operations to Workflows Table Migration Guide

This guide covers the complete migration process from the `housef3-dev-operations` table to the `housef3-dev-workflows` table.

## Overview

The migration renames the DynamoDB table from `operations` to `workflows` while maintaining identical structure and functionality. This is a zero-downtime migration that preserves all existing data.

## Migration Components

### 1. Infrastructure Changes
- **File**: `infrastructure/terraform/dynamo_operations.tf`
- **Changes**: 
  - Renamed table resource from `operations` to `workflows`
  - Updated table name to use `workflows` suffix
  - Updated output names to reflect new table

### 2. Backend Code Updates
- **File**: `backend/src/utils/db_utils.py`
  - Added `get_workflows_table()` function
  - Removed deprecated `get_operations_table()` function
  - Updated environment variable from `OPERATIONS_TABLE` to `WORKFLOWS_TABLE`

- **File**: `backend/src/services/operation_tracking_service.py`
  - Updated to use `get_workflows_table()` instead of `get_operations_table()`

### 3. Lambda Environment Variables
- **Files**: `infrastructure/terraform/lambda.tf`, `infrastructure/terraform/lambda_consumers.tf`
- **Changes**: 
  - Updated all Lambda functions to reference the new workflows table
  - Changed environment variable name from `OPERATIONS_TABLE` to `WORKFLOWS_TABLE`

### 4. Diagnostic Scripts
- **Files**: 
  - `python-scripts/workflow-diagnostics/workflow_diagnostics.py`
  - `scripts/workflow-diagnostics/workflow_diagnostics.py`
  - `python-scripts/workflow-diagnostics/workflow_config.env`
- **Changes**: 
  - Updated table references to use workflows table
  - Changed environment variable references from `OPERATIONS_TABLE` to `WORKFLOWS_TABLE`

## Migration Steps

### Step 1: Deploy Infrastructure Changes

```bash
cd infrastructure/terraform
terraform plan
terraform apply
```

This creates the new `housef3-dev-workflows` table while keeping the old `housef3-dev-operations` table intact.

### Step 2: Migrate Data

Run the migration script to copy all data from the old table to the new table:

```bash
# Dry run first to verify the migration plan
python3 scripts/migrate_operations_to_workflows.py --environment dev --dry-run

# Run the actual migration
python3 scripts/migrate_operations_to_workflows.py --environment dev --batch-size 25
```

The migration script will:
- Scan all items from the operations table
- Copy them to the workflows table with identical structure
- Provide progress reporting and verification
- Ensure data integrity

### Step 3: Deploy Code Changes

Deploy the backend code changes that update references to use the new table:

```bash
# Build and deploy backend
cd backend
./build_lambda_package.sh
# Deploy via your deployment process
```

### Step 4: Verify Migration

1. **Check table contents**:
   ```bash
   # Compare item counts
   aws dynamodb describe-table --table-name housef3-dev-operations --query 'Table.ItemCount'
   aws dynamodb describe-table --table-name housef3-dev-workflows --query 'Table.ItemCount'
   ```

2. **Test functionality**:
   - Trigger a file deletion operation
   - Monitor the workflows table for new entries
   - Verify operation tracking works correctly

3. **Run diagnostics**:
   ```bash
   python3 python-scripts/workflow-diagnostics/workflow_diagnostics.py summary
   ```

### Step 5: Cleanup Old Table (Optional)

After verifying the migration is successful, you can remove the old table:

```bash
# With S3 backup (recommended)
python3 scripts/cleanup_old_operations_table.py --environment dev --backup-to-s3

# Without backup (use with caution)
python3 scripts/cleanup_old_operations_table.py --environment dev
```

## Rollback Plan

If issues are discovered after migration:

### Immediate Rollback (Code Level)
1. Revert the backend code changes in `db_utils.py` and `operation_tracking_service.py`
2. Revert the Terraform environment variable changes
3. Redeploy both infrastructure and backend
4. This will make the system use the old operations table again

### Full Rollback (Infrastructure Level)
1. Revert the Terraform changes in `dynamo_operations.tf`
2. Run `terraform apply` to restore the old table configuration
3. Revert all code changes
4. Redeploy the system

## Safety Measures

### Data Integrity
- The migration script includes verification steps
- Original data remains in the old table until cleanup
- Batch processing with error handling
- Dry-run mode for testing

### Breaking Changes
- `get_operations_table()` function removed - use `get_workflows_table()` instead
- Environment variable changed from `OPERATIONS_TABLE` to `WORKFLOWS_TABLE`
- All Lambda functions must be redeployed with new environment variables

### Monitoring
- Migration script provides detailed logging
- Verification steps ensure data consistency
- Diagnostic tools updated to work with new table

## Troubleshooting

### Migration Script Issues
- **Error**: "Table not found"
  - Ensure Terraform changes are applied first
  - Verify AWS credentials and region

- **Error**: "Batch write failed"
  - Check DynamoDB write capacity
  - Reduce batch size if needed

### Post-Migration Issues
- **Error**: "Workflows table not found" or "Operations table not found"
  - Verify backend deployment completed
  - Check Lambda environment variables are updated to `WORKFLOWS_TABLE`
  - Ensure Terraform changes are applied

- **Error**: "Data missing in workflows table"
  - Run migration verification
  - Check migration script logs

### Performance Issues
- Monitor DynamoDB metrics for both tables
- Adjust read/write capacity if needed
- Use batch operations for large data sets

## Verification Checklist

- [ ] New workflows table created successfully
- [ ] Data migration completed without errors
- [ ] Item counts match between old and new tables
- [ ] Backend code deployed and using new table
- [ ] Lambda functions updated with new environment variables
- [ ] Diagnostic scripts working with new table
- [ ] File operations creating entries in workflows table
- [ ] Operation tracking service functioning correctly
- [ ] No errors in CloudWatch logs

## Environment-Specific Notes

### Development Environment
- Safe to test migration process
- Can use force flags for testing
- Backup not strictly necessary

### Staging Environment
- Should mirror production process
- Always create backups
- Test rollback procedures

### Production Environment
- **CRITICAL**: Always create S3 backups
- Plan maintenance window
- Have rollback plan ready
- Monitor system closely post-migration

## Contact

For issues or questions about this migration:
- Check CloudWatch logs for detailed error information
- Review migration script output for specific failures
- Use diagnostic scripts to verify system health

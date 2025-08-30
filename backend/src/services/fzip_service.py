"""
Unified FZIP Service for backup/restore operations.
Handles data collection, package building, restore processing, and backup operations.
"""
import hashlib
import json
import logging
import os
import tempfile
import uuid
import zipfile
import io
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal

from models.fzip import (
    FZIPJob, FZIPManifest, FZIPDataSummary, FZIPCompatibilityInfo,
    FZIPStatus, FZIPType, FZIPFormat, FZIPBackupType
)
from models.account import Account, AccountType
from models.transaction import Transaction
from models.category import Category
from models.file_map import FileMap
from models.transaction_file import TransactionFile
from models.analytics import AnalyticsData
from models.money import Currency
from models.events import (
    BackupInitiatedEvent, BackupCompletedEvent, BackupFailedEvent,
    RestoreInitiatedEvent, RestoreCompletedEvent, RestoreFailedEvent
)

from utils.db_utils import (
    list_user_accounts, list_user_transactions, list_categories_by_user_from_db,
    list_file_maps_by_user, list_user_files, get_analytics_data,
    create_fzip_job, update_fzip_job, get_fzip_job, list_user_fzip_jobs,
    delete_fzip_job, cleanup_expired_fzip_jobs, create_account,
    update_account, create_category_in_db, update_category_in_db,
    create_file_map, update_file_map, create_transaction_file,
    update_transaction_file, create_transaction, update_transaction
)
from utils.s3_dao import get_object_content, put_object, get_presigned_url_simple
from utils.fzip_metrics import fzip_metrics
from services.event_service import event_service
from services.export_data_processors import (
    AccountExporter, TransactionExporter, CategoryExporter, 
    FileMapExporter, TransactionFileExporter, ExportException
)
from services.s3_file_handler import S3FileStreamer, ExportPackageBuilder, FileStreamingOptions


class ImportException(Exception):
    """Custom exception for import processing errors"""
    pass

class CanceledException(Exception):
    """Raised to indicate a user-initiated cancel should stop processing."""
    pass


logger = logging.getLogger(__name__)


class FZIPService:
    """Unified service for handling FZIP (backup/restore) operations"""
    
    def __init__(self):
        self.housef3_version = "2.5.0"  # Current version
        self.fzip_format_version = "1.0"
        # Bucket used to store exported backup packages
        self.fzip_bucket = os.environ.get('FZIP_PACKAGES_BUCKET', 'housef3-dev-fzip-packages')
        # Bucket used to receive uploaded restore packages
        self.restore_packages_bucket = os.environ.get(
            'FZIP_RESTORE_PACKAGES_BUCKET',
            os.environ.get('FZIP_PACKAGES_BUCKET', 'housef3-dev-fzip-packages')
        )
        self.file_storage_bucket = os.environ.get('FILE_STORAGE_BUCKET', 'housef3-dev-file-storage')
        self.batch_size = 1000  # For large datasets
        
    # =============================================================================
    # Backup Operations
    # =============================================================================
    
    def initiate_backup(self, user_id: str, backup_type: FZIPBackupType,
                       include_analytics: bool = False, description: Optional[str] = None,
                       backup_format: FZIPFormat = FZIPFormat.FZIP,
                       **kwargs) -> FZIPJob:
        """
        Initiate a new backup job
        
        Args:
            user_id: User identifier
            backup_type: Type of backup to perform
            include_analytics: Whether to include analytics data
            description: Optional description for the backup
            backup_format: Format of the backup package
            **kwargs: Additional backup parameters
            
        Returns:
            FZIPJob: Created backup job
        """
        try:
            # Create backup job
            backup_job = FZIPJob(
                userId=user_id,
                jobType=FZIPType.BACKUP,
                status=FZIPStatus.BACKUP_INITIATED,
                backupType=backup_type,
                packageFormat=backup_format,
                includeAnalytics=include_analytics,
                description=description,
                parameters=kwargs
            )
            
            # Set expiration time (24 hours from now)
            expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
            backup_job.expires_at = int(expiry_time.timestamp() * 1000)
            
            # Save to database
            create_fzip_job(backup_job)
            
            # Publish backup initiated event
            event = BackupInitiatedEvent(
                user_id=user_id,
                backup_id=str(backup_job.job_id),
                description=description,
                backup_type=backup_type,
                include_analytics=include_analytics
            )
            event_service.publish_event(event)
            
            logger.info(f"Backup job initiated: {backup_job.job_id} for user {user_id}")
            return backup_job
            
        except Exception as e:
            logger.error(f"Failed to initiate backup for user {user_id}: {str(e)}")
            # We don't have a job ID yet, so we can't publish a perfect event,
            # but we can do our best.
            event_service.publish_event(BackupFailedEvent(
                user_id=user_id,
                backup_id='unknown',
                error=str(e)
            ))
            raise
    
    def collect_backup_data(self, user_id: str, backup_type: FZIPBackupType,
                         include_analytics: bool = False,
                         **filters) -> Dict[str, Any]:
        """
        Collect all user data for backup using specialized entity exporters
        Args:
            user_id: User identifier
            backup_type: Type of backup
            include_analytics: Whether to include analytics
            **filters: Additional filters for selective backups
            
        Returns:
            Dictionary containing all collected data
        """
        try:
            logger.info(f"Collecting data for user {user_id}, backup type: {backup_type}")
            
            collected_data = {}
            export_summaries = {}
            
            # Use specialized exporters for enhanced data collection
            
            # Collect accounts
            account_exporter = AccountExporter(user_id, self.batch_size)
            collected_data['accounts'] = account_exporter.collect_data(filters)
            export_summaries['accounts'] = account_exporter.get_export_summary()
            
            # Collect transactions
            transaction_exporter = TransactionExporter(user_id, self.batch_size)
            collected_data['transactions'] = transaction_exporter.collect_data(filters)
            export_summaries['transactions'] = transaction_exporter.get_export_summary()
            
            # Collect categories
            category_exporter = CategoryExporter(user_id, self.batch_size)
            collected_data['categories'] = category_exporter.collect_data(filters)
            export_summaries['categories'] = category_exporter.get_export_summary()
            
            # Collect file maps
            file_map_exporter = FileMapExporter(user_id, self.batch_size)
            collected_data['file_maps'] = file_map_exporter.collect_data(filters)
            export_summaries['file_maps'] = file_map_exporter.get_export_summary()
            
            # Collect transaction files
            transaction_file_exporter = TransactionFileExporter(user_id, self.batch_size)
            collected_data['transaction_files'] = transaction_file_exporter.collect_data(filters)
            export_summaries['transaction_files'] = transaction_file_exporter.get_export_summary()
            
            # Collect analytics if requested
            if include_analytics:
                analytics = self._collect_analytics(user_id)
                collected_data['analytics'] = analytics
            
            # Add export summaries for reporting
            collected_data['_export_summaries'] = export_summaries
            
            # Record data volume metrics
            entity_counts = {
                entity_type: summary['processed_count'] 
                for entity_type, summary in export_summaries.items()
            }
            fzip_metrics.record_backup_data_volume(entity_counts, backup_type)
            
            logger.info("Enhanced data collection complete using specialized exporters")
            for entity_type, summary in export_summaries.items():
                logger.info(
                    "%s: %d items, %.1f%% success rate",
                    entity_type,
                    summary['processed_count'],
                    summary.get('success_rate', 100)
                )
            
            return collected_data
            
        except ExportException as e:
            logger.error(f"Export-specific error collecting data for user {user_id}: {str(e)}")
            fzip_metrics.record_backup_error(
                error_type=type(e).__name__,
                error_message=str(e),
                backup_type=backup_type,
                phase="data_collection"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to collect data for user {user_id}: {str(e)}")
            fzip_metrics.record_backup_error(
                error_type=type(e).__name__,
                error_message=str(e),
                backup_type=backup_type,
                phase="data_collection"
            )
            raise
    
    def _collect_analytics(self, user_id: str) -> List[Dict[str, Any]]:
        """Collect user analytics data"""
        try:
            # This would need to be implemented based on analytics data structure
            # For now, return empty list
            logger.info(f"Analytics collection not yet implemented for user {user_id}")
            return []
            
        except Exception as e:
            logger.error(f"Failed to collect analytics for user {user_id}: {str(e)}")
            return []
    
    def build_backup_package(self, backup_job: FZIPJob, collected_data: Dict[str, Any]) -> Tuple[str, int]:
        """
        Build backup package using enhanced streaming and compression capabilities
        
        Args:
            backup_job: Backup job details
            collected_data: Collected user data
            
        Returns:
            Tuple of (s3_key, package_size)
        """
        try:
            logger.info(f"Building enhanced backup package for job {backup_job.job_id}")
            
            # Configure streaming options for large backups
            streaming_options = FileStreamingOptions(
                enable_compression=True,
                compression_level=6,
                enable_checksum=True,
                max_memory_usage=200 * 1024 * 1024  # 200MB for larger backups
            )
            
            # Create enhanced package builder with file storage bucket for transaction files
            package_builder = ExportPackageBuilder(self.fzip_bucket, streaming_options, self.file_storage_bucket)
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Build package with streaming capabilities
                package_dir, processing_summary = package_builder.build_package_with_streaming(
                    export_data=collected_data,
                    transaction_files=collected_data.get('transaction_files', []),
                    package_dir=os.path.join(temp_dir, "backup_package")
                )
                
                # Create manifest with processing summary
                manifest = self._create_enhanced_manifest(backup_job, collected_data, processing_summary)
                manifest_file = os.path.join(package_dir, "manifest.json")
                with open(manifest_file, 'w') as f:
                    json.dump(manifest.model_dump(by_alias=True), f, indent=2, default=str)
                
                # Create compressed ZIP file
                zip_path = os.path.join(temp_dir, f"backup_{backup_job.job_id}.zip")
                
                # Use enhanced compression for large packages
                compression_method = zipfile.ZIP_DEFLATED
                if processing_summary['total_original_size'] > 50 * 1024 * 1024:  # > 50MB
                    try:
                        compression_method = zipfile.ZIP_LZMA  # Better compression for large files
                    except AttributeError:
                        compression_method = zipfile.ZIP_DEFLATED
                
                with zipfile.ZipFile(zip_path, 'w', compression_method, compresslevel=6) as zipf:
                    for root, dirs, files in os.walk(package_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, package_dir)
                            zipf.write(file_path, arcname)
                
                # Upload to S3 with retry logic
                s3_key = f"backups/{backup_job.user_id}/{backup_job.job_id}/backup_package.zip"
                package_size = os.path.getsize(zip_path)
                
                # Upload to S3
                logger.info(f"Uploading backup package to S3: {s3_key}")
                with open(zip_path, 'rb') as f:
                    put_object(s3_key, f.read(), 'application/zip', self.fzip_bucket)
                
                # Publish backup completed event
                event_service.publish_event(BackupCompletedEvent(
                    user_id=backup_job.user_id,
                    backup_id=str(backup_job.job_id),
                    package_size=package_size,
                    s3_key=s3_key,
                    data_summary=processing_summary
                ))

                # Record package size metrics
                backup_type = backup_job.backup_type if backup_job.backup_type else "complete"
                fzip_metrics.record_backup_package_size(package_size, backup_type)
                
                logger.info(f"Enhanced backup package created: {s3_key}")
                logger.info(f"Package size: {package_size} bytes, "
                          f"Compression ratio: {processing_summary.get('compression_ratio', 0):.1f}%")
                logger.info(f"Files processed: {processing_summary['transaction_files_processed']}, "
                          f"Failed: {processing_summary['transaction_files_failed']}")
                
                return s3_key, package_size
                
        except Exception as e:
            logger.error(f"Failed to build enhanced backup package for job {backup_job.job_id}: {str(e)}")
            # Record error metrics
            backup_type = backup_job.backup_type if backup_job.backup_type else "complete"
            fzip_metrics.record_backup_error(
                error_type=type(e).__name__,
                error_message=str(e),
                backup_type=backup_type,
                phase="package_building"
            )
            event_service.publish_event(BackupFailedEvent(
                user_id=backup_job.user_id,
                backup_id=str(backup_job.job_id),
                error=str(e)
            ))
            raise
    
    def _create_enhanced_manifest(self, backup_job: FZIPJob, collected_data: Dict[str, Any], 
                                processing_summary: Dict[str, Any]) -> FZIPManifest:
        """Create enhanced backup manifest with processing summary"""
        data_summary = FZIPDataSummary(
            accountsCount=len(collected_data.get('accounts', [])),
            transactionsCount=len(collected_data.get('transactions', [])),
            categoriesCount=len(collected_data.get('categories', [])),
            fileMapsCount=len(collected_data.get('file_maps', [])),
            transactionFilesCount=len(collected_data.get('transaction_files', [])),
            analyticsIncluded=backup_job.include_analytics and bool(collected_data.get('analytics'))
        )
        
        compatibility = FZIPCompatibilityInfo(
            minimumVersion="2.0.0",
            supportedVersions=["2.0.0", "2.5.0"]
        )
        
        # Create basic manifest
        manifest = FZIPManifest(
            backupFormatVersion=self.fzip_format_version,
            backupTimestamp=datetime.now(timezone.utc).isoformat(),
            userId=backup_job.user_id,
            housef3Version=self.housef3_version,
            dataSummary=data_summary,
            checksums={},  # Will be populated by package builder if needed
            compatibility=compatibility,
            jobId=backup_job.job_id,
            backupType=backup_job.backup_type or FZIPBackupType.COMPLETE,
            includeAnalytics=backup_job.include_analytics
        )
        
        # Add processing summary as metadata in the manifest data
        manifest_dict = manifest.model_dump(by_alias=True)
        manifest_dict['processingSummary'] = processing_summary
        
        # Add export summaries if available
        if '_export_summaries' in collected_data:
            manifest_dict['exportSummaries'] = collected_data['_export_summaries']
        
        return FZIPManifest.model_validate(manifest_dict)
    
    def generate_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for backup download"""
        try:
            return get_presigned_url_simple(self.fzip_bucket, s3_key, 'get', expires_in)
        except Exception as e:
            logger.error(f"Failed to generate download URL for {s3_key}: {str(e)}")
            raise
    
    # =============================================================================
    # Restore Operations
    # =============================================================================
    
    def initiate_restore(self, user_id: str, restore_type: FZIPBackupType,
                        description: Optional[str] = None,
                        **kwargs) -> FZIPJob:
        """
        Initiate a new restore job for empty profile
        
        Args:
            user_id: User identifier  
            restore_type: Type of restore to perform
            description: Optional description for the restore
            **kwargs: Additional restore parameters
            
        Returns:
            FZIPJob: Created restore job
            
        Note:
            Restores only work with completely empty financial profiles.
            Any existing data will cause validation failure.
        """
        try:
            # Create restore job (no merge strategy needed for empty profile restore)
            restore_job = FZIPJob(
                userId=user_id,
                jobType=FZIPType.RESTORE,
                status=FZIPStatus.RESTORE_UPLOADED,
                backupType=restore_type,
                # Note: No merge strategy needed for empty profile restores
                description=description,
                parameters=kwargs
            )
            
            # Set expiration time (24 hours from now)
            expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
            restore_job.expires_at = int(expiry_time.timestamp() * 1000)
            
            
            # Perform initial validation for empty profile
            empty_check = self._validate_empty_profile(user_id)
            if not empty_check['valid']:
                error_message = "Validation failed: " + " ".join(empty_check['errors'])
                self._fail_job(restore_job, error_message)
                # Note: Consider raising an exception here to notify the caller immediately
                return restore_job  # Or handle as per API contract for immediate failure
            
            # Save to database
            create_fzip_job(restore_job)
            
            # Publish restore initiated event
            event = RestoreInitiatedEvent(
                user_id=user_id,
                restore_id=str(restore_job.job_id),
                description=description,
                backup_id=kwargs.get('backup_id', ''),
                s3_key=kwargs.get('s3_key', '')
            )
            event_service.publish_event(event)
            
            logger.info(f"Restore job initiated: {restore_job.job_id} for user {user_id}")
            return restore_job
            
        except Exception as e:
            logger.error(f"Failed to initiate restore for user {user_id}: {str(e)}")
            raise
    
    def _fail_job(self, job: FZIPJob, error_message: str, status: FZIPStatus = FZIPStatus.RESTORE_VALIDATION_FAILED):
        """Helper to fail a job and log the error"""
        job.status = status
        job.error = error_message
        update_fzip_job(job)
        logger.error(f"Job {job.job_id} failed: {error_message}")
        if job.job_type == FZIPType.RESTORE:
            event_service.publish_event(RestoreFailedEvent(
                user_id=job.user_id,
                restore_id=str(job.job_id),
                backup_id=job.backup_id or '',
                error=error_message
            ))

    def start_restore(self, restore_job: FZIPJob, package_s3_key: str):
        """Start restore processing."""
        try:
            # Update job with package location
            restore_job.s3_key = package_s3_key
            restore_job.status = FZIPStatus.RESTORE_VALIDATING
            restore_job.current_phase = "parsing_package"
            restore_job.progress = 10
            update_fzip_job(restore_job)
            
            # Parse package
            package_data = self._parse_package(package_s3_key)
            
            # Ensure validation_results is initialized before assigning nested keys
            restore_job.validation_results = restore_job.validation_results or {}
            
            # Validate schema
            restore_job.current_phase = "validating_schema"
            restore_job.progress = 20
            update_fzip_job(restore_job)
            
            schema_results = self._validate_schema(package_data)
            restore_job.validation_results['schema'] = schema_results
            
            if not schema_results['valid']:
                restore_job.status = FZIPStatus.RESTORE_VALIDATION_FAILED
                restore_job.error = "Schema validation failed"
                update_fzip_job(restore_job)
                return
            
            # Validate business rules
            restore_job.current_phase = "validating_business_rules"
            restore_job.progress = 30
            update_fzip_job(restore_job)
            
            # Business rules validation for empty profile restore
            business_results = self._validate_business_rules(
                package_data, restore_job.user_id
            )
            restore_job.validation_results['business'] = business_results
            
            if not business_results['valid']:
                restore_job.status = FZIPStatus.RESTORE_VALIDATION_FAILED
                restore_job.error = "Business validation failed"
                update_fzip_job(restore_job)
                return
            
            # Generate detailed summary for user review
            restore_job.current_phase = "generating_summary"
            restore_job.progress = 40
            update_fzip_job(restore_job)
            
            summary_data = self._generate_summary_data(package_data)
            restore_job.summary = summary_data
            
            # Stop here and wait for user confirmation
            restore_job.status = FZIPStatus.RESTORE_AWAITING_CONFIRMATION
            restore_job.progress = 50
            restore_job.current_phase = "awaiting_user_confirmation"
            
            # Add validation results for frontend display
            restore_job.validation_results.update({
                'profileEmpty': True,  # Assumed valid in this flow
                'schemaValid': schema_results.get('valid', False),
                'businessValid': business_results.get('valid', False),
                'ready': True  # All validations passed, ready for user confirmation
            })
            
            update_fzip_job(restore_job)
            
            # DON'T proceed to _restore_data() automatically
            # User must explicitly call start handler to proceed
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            restore_job.status = FZIPStatus.RESTORE_FAILED
            restore_job.error = str(e)
            update_fzip_job(restore_job)
            event_service.publish_event(RestoreFailedEvent(
                user_id=restore_job.user_id,
                restore_id=str(restore_job.job_id),
                backup_id=restore_job.backup_id or '',
                error=str(e)
            ))
    
    def resume_restore(self, restore_job: FZIPJob):
        """Resume restore processing from validation passed state."""
        try:
            # Update status to processing
            restore_job.status = FZIPStatus.RESTORE_PROCESSING
            restore_job.current_phase = "Starting restore..."
            restore_job.progress = 50
            update_fzip_job(restore_job)
            
            # Re-parse the package to get the data
            package_data = self._parse_package(restore_job.s3_key)
            
            # Continue with data restoration
            self._restore_data(restore_job, package_data)
            
        except Exception as e:
            logger.error(f"Resume restore failed: {str(e)}")
            restore_job.status = FZIPStatus.RESTORE_FAILED
            restore_job.error = str(e)
            update_fzip_job(restore_job)
            event_service.publish_event(RestoreFailedEvent(
                user_id=restore_job.user_id,
                restore_id=str(restore_job.job_id),
                backup_id=restore_job.backup_id or '',
                error=str(e)
            ))
    
    def _parse_package(self, package_s3_key: str) -> Dict[str, Any]:
        """Parse the ZIP package and extract data."""
        try:
            # Download package from S3
            # Read the uploaded restore package from the restore bucket
            package_data = get_object_content(package_s3_key, self.restore_packages_bucket)
            if not package_data:
                raise ImportException("Could not download package from S3")
            
            # Parse ZIP file
            with zipfile.ZipFile(io.BytesIO(package_data), 'r') as zipf:
                # Read manifest
                manifest_data = zipf.read('manifest.json')
                manifest = json.loads(manifest_data.decode('utf-8'))
                
                # Read data files (handle both compressed and uncompressed)
                data = {}
                for entity_type in ['accounts', 'transactions', 'categories', 'file_maps', 'transaction_files']:
                    try:
                        # Try compressed file first (.gz)
                        try:
                            entity_data = zipf.read(f'data/{entity_type}.json.gz')
                            import gzip
                            data[entity_type] = json.loads(gzip.decompress(entity_data).decode('utf-8'))
                        except KeyError:
                            # Fall back to uncompressed file
                            entity_data = zipf.read(f'data/{entity_type}.json')
                            data[entity_type] = json.loads(entity_data.decode('utf-8'))
                    except KeyError:
                        data[entity_type] = []
                
                return {
                    'manifest': manifest,
                    'data': data,
                    'raw': package_data
                }
                
        except Exception as e:
            logger.error(f"Error parsing package: {str(e)}")
            raise ImportException(f"Failed to parse import package: {str(e)}")
    
    def _validate_schema(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the package schema."""
        try:
            manifest = package_data['manifest']
            data = package_data['data']
            
            # Check required manifest fields (match FZIPManifest model aliases)
            required_manifest_fields = ['backupFormatVersion', 'backupTimestamp', 'userId', 'housef3Version']
            for field in required_manifest_fields:
                if field not in manifest:
                    return {
                        'valid': False,
                        'errors': [f"Missing required manifest field: {field}"]
                    }
            
            # Validate data structure
            errors = []
            for entity_type, entities in data.items():
                if not isinstance(entities, list):
                    errors.append(f"Invalid data structure for {entity_type}")
                    continue
                
                for i, entity in enumerate(entities):
                    if not isinstance(entity, dict):
                        errors.append(f"Invalid entity at index {i} in {entity_type}")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'summary': {
                    'accounts': len(data.get('accounts', [])),
                    'transactions': len(data.get('transactions', [])),
                    'categories': len(data.get('categories', [])),
                    'file_maps': len(data.get('file_maps', [])),
                    'transaction_files': len(data.get('transaction_files', []))
                }
            }
            
        except Exception as e:
            logger.error(f"Schema validation error: {str(e)}")
            return {
                'valid': False,
                'errors': [f"Schema validation failed: {str(e)}"]
            }
    
    def _validate_business_rules(self, package_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Validate business rules: user ownership, empty profile, and package consistency."""
        try:
            data = package_data['data']
            manifest = package_data['manifest']
            
            # User ownership check removed - allow cross-user package loading
            
            # Validate data relationships (internal package consistency)
            errors = []
            
            # Check that all transaction account IDs exist in accounts
            account_ids = {acc['accountId'] for acc in data.get('accounts', [])}
            for transaction in data.get('transactions', []):
                if transaction.get('accountId') and transaction['accountId'] not in account_ids:
                    errors.append(f"Transaction references non-existent account: {transaction.get('transactionId')}")
            
            # Check that all file map account IDs exist in accounts
            for file_map in data.get('file_maps', []):
                if file_map.get('accountId') and file_map['accountId'] not in account_ids:
                    errors.append(f"File map references non-existent account: {file_map.get('fileMapId')}")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Business validation error: {str(e)}")
            return {
                'valid': False,
                'errors': [f"Business validation failed: {str(e)}"]
            }
    
    def _generate_summary_data(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed summary for user review"""
        try:
            data = package_data['data']
            
            # Analyze accounts
            accounts = data.get('accounts', [])
            account_summary = {
                "count": len(accounts),
                "items": [
                    {
                        "name": acc.get('accountName', 'Unknown Account'), 
                        "type": acc.get('accountType', 'unknown')
                    }
                    for acc in accounts[:10]  # Show first 10 accounts
                ]
            }
            
            # Analyze categories with hierarchy
            categories = data.get('categories', [])
            category_summary = self._analyze_category_hierarchy(categories)
            
            # Analyze transactions with date range
            transactions = data.get('transactions', [])
            transaction_summary = self._analyze_transaction_range(transactions)
            
            # Analyze file maps
            file_maps = data.get('file_maps', [])
            file_map_summary = {
                "count": len(file_maps),
                "totalSize": self._calculate_total_size_from_file_maps(file_maps)
            }
            
            # Analyze transaction files
            transaction_files = data.get('transaction_files', [])
            transaction_file_summary = {
                "count": len(transaction_files),
                "totalSize": self._calculate_transaction_files_size(transaction_files),
                "fileTypes": list(set(tf.get('fileFormat', 'unknown') for tf in transaction_files))
            }
            
            return {
                "accounts": account_summary,
                "categories": category_summary,
                "file_maps": file_map_summary,
                "transaction_files": transaction_file_summary,
                "transactions": transaction_summary
            }
            
        except Exception as e:
            logger.error(f"Error generating summary data: {str(e)}")
            return {
                "error": f"Failed to generate summary: {str(e)}"
            }
    
    def _analyze_category_hierarchy(self, categories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze category hierarchy and structure"""
        try:
            if not categories:
                return {"count": 0, "hierarchyDepth": 0, "items": []}
            
            # Calculate hierarchy depth
            max_depth = 0
            top_level_categories = []
            
            for category in categories:
                # Count depth by parent relationships or path separators
                parent_id = category.get('parentCategoryId')
                if not parent_id:
                    # Top-level category
                    children_count = sum(1 for c in categories if c.get('parentCategoryId') == category.get('categoryId'))
                    top_level_categories.append({
                        "name": category.get('name', 'Unknown Category'),
                        "level": 1,
                        "children": children_count
                    })
                    max_depth = max(max_depth, 1)
                else:
                    # Calculate depth for nested categories
                    depth = self._calculate_category_depth(category, categories, 1)
                    max_depth = max(max_depth, depth)
            
            return {
                "count": len(categories),
                "hierarchyDepth": max_depth,
                "items": top_level_categories[:5]  # Show first 5 top-level categories
            }
            
        except Exception as e:
            logger.error(f"Error analyzing category hierarchy: {str(e)}")
            return {"count": len(categories), "hierarchyDepth": 0, "items": []}
    
    def _calculate_category_depth(self, category: Dict[str, Any], all_categories: List[Dict[str, Any]], current_depth: int) -> int:
        """Recursively calculate category depth"""
        parent_id = category.get('parentCategoryId')
        if not parent_id:
            return current_depth
        
        parent = next((c for c in all_categories if c.get('categoryId') == parent_id), None)
        if not parent:
            return current_depth
        
        return self._calculate_category_depth(parent, all_categories, current_depth + 1)
    
    def _analyze_transaction_range(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze transaction date range and counts"""
        try:
            if not transactions:
                return {"count": 0}
            
            # Extract dates and find range
            dates = []
            for transaction in transactions:
                date_timestamp = transaction.get('date')
                if date_timestamp:
                    try:
                        # Convert milliseconds timestamp to date string
                        if isinstance(date_timestamp, (int, float)):
                            date_obj = datetime.fromtimestamp(date_timestamp / 1000, tz=timezone.utc)
                            dates.append(date_obj.strftime('%Y-%m-%d'))
                        elif isinstance(date_timestamp, str):
                            # Handle string dates that might be already formatted
                            date_part = date_timestamp.split('T')[0] if 'T' in date_timestamp else date_timestamp
                            dates.append(date_part)
                    except Exception:
                        continue
            
            if dates:
                dates.sort()
                return {
                    "count": len(transactions),
                    "dateRange": {
                        "earliest": dates[0],
                        "latest": dates[-1]
                    }
                }
            else:
                return {"count": len(transactions)}
                
        except Exception as e:
            logger.error(f"Error analyzing transaction range: {str(e)}")
            return {"count": len(transactions)}
    
    def _calculate_total_size_from_file_maps(self, file_maps: List[Dict[str, Any]]) -> str:
        """Calculate total size from file maps"""
        try:
            total_bytes = 0
            for file_map in file_maps:
                file_size = file_map.get('file_size_bytes', 0)
                if isinstance(file_size, (int, float)):
                    total_bytes += int(file_size)
            
            return self._format_file_size(total_bytes)
        except Exception:
            return "Unknown"
    
    def _calculate_transaction_files_size(self, transaction_files: List[Dict[str, Any]]) -> str:
        """Calculate total size from transaction files"""
        try:
            total_bytes = 0
            for tf in transaction_files:
                file_size = tf.get('file_size_bytes', 0)
                if isinstance(file_size, (int, float)):
                    total_bytes += int(file_size)
            
            return self._format_file_size(total_bytes)
        except Exception:
            return "Unknown"
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f}{size_names[i]}"
    
    def _validate_empty_profile(self, user_id: str) -> Dict[str, Any]:
        """Validate that user profile is completely empty for restore."""
        try:
            artifacts = []
            
            # Check for existing accounts
            accounts = list_user_accounts(user_id)
            if accounts:
                artifacts.append(f"{len(accounts)} account(s)")
            
            # Check for existing categories
            categories = list_categories_by_user_from_db(user_id)
            if categories:
                artifacts.append(f"{len(categories)} category(ies)")
            
            # Check for existing file maps
            file_maps = list_file_maps_by_user(user_id)
            if file_maps:
                artifacts.append(f"{len(file_maps)} file map(s)")
            
            # Check for existing transaction files
            transaction_files = list_user_files(user_id)
            if transaction_files:
                artifacts.append(f"{len(transaction_files)} transaction file(s)")
            
            # Check for existing transactions (if we have a method for this)
            # Note: We could add transaction check here if needed
            
            if artifacts:
                return {
                    'valid': False,
                    'errors': [f"Profile not empty. Found: {', '.join(artifacts)}. FZIP restore requires completely empty profile."]
                }
            
            return {
                'valid': True,
                'errors': []
            }

        except Exception as e:
            logger.error(f"Error validating empty profile: {str(e)}")
            return {
                'valid': False,
                'errors': [f"Profile validation failed: {str(e)}"]
            }
    
    def _restore_data(self, restore_job: FZIPJob, package_data: Dict[str, Any]):
        """Restore all data from the package."""
        try:
            restore_job.status = FZIPStatus.RESTORE_PROCESSING
            data = package_data['data']
            results = {}
            
            # Restore in dependency order
            
            # 1. Restore accounts first
            self._check_cancel(restore_job)
            restore_job.current_phase = "restoring_accounts"
            restore_job.progress = 50
            update_fzip_job(restore_job)
            
            # Restore to empty profile - no merge strategy needed
            account_results = self._restore_accounts(
                data.get('accounts', []), restore_job.user_id
            )
            results['accounts'] = account_results
            
            # 2. Restore categories
            self._check_cancel(restore_job)
            restore_job.current_phase = "restoring_categories"
            restore_job.progress = 60
            update_fzip_job(restore_job)
            
            category_results = self._restore_categories(
                data.get('categories', []), restore_job.user_id
            )
            results['categories'] = category_results
            
            # 3. Restore file maps
            self._check_cancel(restore_job)
            restore_job.current_phase = "restoring_file_maps"
            restore_job.progress = 70
            update_fzip_job(restore_job)
            
            file_map_results = self._restore_file_maps(
                data.get('file_maps', []), restore_job.user_id
            )
            results['file_maps'] = file_map_results
            
            # 4. Restore transaction files
            self._check_cancel(restore_job)
            restore_job.current_phase = "restoring_transaction_files"
            restore_job.progress = 80
            update_fzip_job(restore_job)
            
            file_results = self._restore_transaction_files(
                data.get('transaction_files', []), restore_job.user_id, package_data
            )
            results['transaction_files'] = file_results
            
            # 5. Restore transactions
            self._check_cancel(restore_job)
            restore_job.current_phase = "restoring_transactions"
            restore_job.progress = 90
            update_fzip_job(restore_job)
            
            transaction_results = self._restore_transactions(
                data.get('transactions', []), restore_job.user_id
            )
            results['transactions'] = transaction_results
            
            # Complete restore
            restore_job.status = FZIPStatus.RESTORE_COMPLETED
            restore_job.progress = 100
            restore_job.current_phase = "completed"
            restore_job.restore_results = results
            restore_job.completed_at = int(datetime.now(timezone.utc).timestamp() * 1000)
            update_fzip_job(restore_job)

            # Publish restore completed event
            event_service.publish_event(RestoreCompletedEvent(
                user_id=restore_job.user_id,
                restore_id=str(restore_job.job_id),
                backup_id=restore_job.backup_id or '',
                data_summary=results
            ))
            
        except CanceledException:
            # Honor user cancellation without marking as failure
            logger.info(f"Restore {restore_job.job_id} canceled by user. Halting further processing.")
            return
        except Exception as e:
            logger.error(f"Error during data restore: {str(e)}")
            event_service.publish_event(RestoreFailedEvent(
                user_id=restore_job.user_id,
                restore_id=str(restore_job.job_id),
                backup_id=restore_job.backup_id or '',
                error=str(e)
            ))
            raise

    def _check_cancel(self, restore_job: FZIPJob) -> None:
        """Reload job and raise CanceledException if status is RESTORE_CANCELED.

        Also ensure terminal timestamp is recorded if missing.
        """
        latest = get_fzip_job(str(restore_job.job_id), restore_job.user_id)
        if latest and latest.status == FZIPStatus.RESTORE_CANCELED:
            restore_job.status = FZIPStatus.RESTORE_CANCELED
            restore_job.current_phase = "canceled"
            if not restore_job.completed_at:
                restore_job.completed_at = int(datetime.now(timezone.utc).timestamp() * 1000)
            update_fzip_job(restore_job)
            raise CanceledException("Restore canceled by user")
    
    def _restore_accounts(self, accounts: list, user_id: str) -> Dict[str, Any]:
        """Restore accounts data to empty profile (no conflicts expected)."""
        
        created = 0
        errors = []
        
        for account_data in accounts:
            try:
                # Convert export format to Account model
                account = Account(
                    accountId=uuid.UUID(account_data['accountId']),
                    userId=user_id,  # Ensure user ownership
                    accountName=account_data['accountName'],
                    accountType=AccountType(account_data['accountType']),
                    institution=account_data.get('institution', ''),
                    balance=Decimal(str(account_data['balance'])) if account_data.get('balance') else Decimal('0.00'),
                    currency=Currency(account_data.get('currency', 'USD')),
                    notes=account_data.get('notes', ''),
                    isActive=account_data.get('isActive', True),
                    defaultFileMapId=uuid.UUID(account_data['defaultFileMapId']) if account_data.get('defaultFileMapId') else None,
                    lastTransactionDate=account_data.get('lastTransactionDate'),
                    createdAt=account_data.get('createdAt'),
                    updatedAt=account_data.get('updatedAt')
                )
                
                # Create account directly - profile already validated as empty
                create_account(account)
                created += 1
                logger.debug(f"Successfully restored account: {account.account_id}")
                    
            except Exception as e:
                # Any failure indicates system issue (not conflicts - profile was validated empty)
                error_msg = f"Failed to restore account {account_data.get('accountId', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            'created': created,
            'errors': errors
        }
    
    def _restore_categories(self, categories: list, user_id: str) -> Dict[str, Any]:
        """Restore categories data to empty profile (no conflicts expected)."""
        from models.category import CategoryType, CategoryRule, MatchCondition
        
        created = 0
        errors = []
        
        for category_data in categories:
            try:
                # Convert rules from export format
                rules = []
                for rule_data in category_data.get('rules', []):
                    rule = CategoryRule(
                        ruleId=rule_data.get('ruleId'),
                        fieldToMatch=rule_data.get('fieldToMatch'),
                        condition=MatchCondition(rule_data.get('condition')),
                        value=rule_data.get('value'),
                        caseSensitive=rule_data.get('caseSensitive', False),
                        priority=rule_data.get('priority', 0),
                        enabled=rule_data.get('enabled', True),
                        confidence=rule_data.get('confidence', 100),
                        amountMin=Decimal(str(rule_data['amountMin'])) if rule_data.get('amountMin') else None,
                        amountMax=Decimal(str(rule_data['amountMax'])) if rule_data.get('amountMax') else None,
                        allowMultipleMatches=rule_data.get('allowMultipleMatches', True),
                        autoSuggest=rule_data.get('autoSuggest', True)
                    )
                    rules.append(rule)
                
                # Convert export format to Category model
                category = Category(
                    categoryId=uuid.UUID(category_data['categoryId']),
                    userId=user_id,  # Ensure user ownership
                    name=category_data['name'],
                    type=CategoryType(category_data['type']),
                    parentCategoryId=uuid.UUID(category_data['parentCategoryId']) if category_data.get('parentCategoryId') else None,
                    icon=category_data.get('icon'),
                    color=category_data.get('color'),
                    rules=rules,
                    inheritParentRules=category_data.get('inheritParentRules', True),
                    ruleInheritanceMode=category_data.get('ruleInheritanceMode', 'additive'),
                    createdAt=category_data.get('createdAt'),
                    updatedAt=category_data.get('updatedAt')
                )
                
                # Create category directly - profile already validated as empty
                create_category_in_db(category)
                created += 1
                logger.debug(f"Successfully restored category: {category.categoryId}")
                    
            except Exception as e:
                # Any failure indicates system issue (not conflicts - profile was validated empty)
                error_msg = f"Failed to restore category {category_data.get('categoryId', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            'created': created,
            'errors': errors
        }
    
    def _restore_file_maps(self, file_maps: list, user_id: str) -> Dict[str, Any]:
        """Restore file maps data to empty profile (no conflicts expected)."""
        from models.file_map import FieldMapping
        
        created = 0
        errors = []
        
        for file_map_data in file_maps:
            try:
                # Convert mappings from export format
                mappings = []
                for mapping_data in file_map_data.get('mappings', []):
                    mapping = FieldMapping(
                        sourceField=mapping_data.get('sourceField'),
                        targetField=mapping_data.get('targetField'),
                        transformation=mapping_data.get('transformation')
                    )
                    mappings.append(mapping)
                
                # Convert export format to FileMap model
                file_map = FileMap(
                    fileMapId=uuid.UUID(file_map_data['fileMapId']),
                    userId=user_id,  # Ensure user ownership
                    name=file_map_data['name'],
                    mappings=mappings,
                    accountId=uuid.UUID(file_map_data['accountId']) if file_map_data.get('accountId') else None,
                    description=file_map_data.get('description'),
                    reverseAmounts=file_map_data.get('reverseAmounts', False),
                    createdAt=file_map_data.get('createdAt'),
                    updatedAt=file_map_data.get('updatedAt')
                )
                
                # Create file map directly - profile already validated as empty
                create_file_map(file_map)
                created += 1
                logger.debug(f"Successfully restored file map: {file_map.file_map_id}")
                    
            except Exception as e:
                # Any failure indicates system issue (not conflicts - profile was validated empty)
                error_msg = f"Failed to restore file map {file_map_data.get('fileMapId', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            'created': created,
            'errors': errors
        }
    
    def _restore_transaction_files(self, transaction_files: list, user_id: str, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Restore transaction files data to empty profile and restore files to S3."""
        from models.transaction_file import ProcessingStatus, FileFormat, DateRange
        from utils.s3_dao import put_object
        
        created = 0
        errors = []
        
        with zipfile.ZipFile(io.BytesIO(package_data['raw']), 'r') as zipf:
            for file_data in transaction_files:
                try:
                    # Convert export format to TransactionFile model
                    date_range = None
                    if file_data.get('dateRange'):
                        date_range_data = file_data['dateRange']
                        date_range = DateRange(
                            startDate=date_range_data.get('start'),
                            endDate=date_range_data.get('end')
                        )
                    
                    transaction_file = TransactionFile(
                        fileId=uuid.UUID(file_data['fileId']),
                        userId=user_id,  # Ensure user ownership
                        fileName=file_data['fileName'],
                        uploadDate=file_data.get('uploadDate'),
                        fileSize=file_data.get('fileSize', 0),
                        s3Key=file_data['s3Key'],
                        processingStatus=ProcessingStatus(file_data.get('processingStatus', 'pending')),
                        processedDate=file_data.get('processedDate'),
                        fileFormat=FileFormat(file_data['fileFormat']) if file_data.get('fileFormat') else None,
                        accountId=uuid.UUID(file_data['accountId']) if file_data.get('accountId') else None,
                        fileMapId=uuid.UUID(file_data['fileMapId']) if file_data.get('fileMapId') else None,
                        recordCount=file_data.get('recordCount'),
                        dateRange=date_range,
                        errorMessage=file_data.get('errorMessage'),
                        openingBalance=Decimal(str(file_data['openingBalance'])) if file_data.get('openingBalance') else None,
                        closingBalance=Decimal(str(file_data['closingBalance'])) if file_data.get('closingBalance') else None,
                        currency=Currency(file_data['currency']) if file_data.get('currency') else None,
                        duplicateCount=file_data.get('duplicateCount'),
                        transactionCount=file_data.get('transactionCount'),
                        createdAt=file_data.get('createdAt'),
                        updatedAt=file_data.get('updatedAt')
                    )
                    
                    # Create transaction file directly - profile already validated as empty
                    create_transaction_file(transaction_file)
                    created += 1
                    
                    # Restore actual file content from FZIP package to S3
                    try:
                        file_content = zipf.read(f"files/{file_data['s3Key']}")
                        put_object(file_data['s3Key'], file_content, 'application/octet-stream', self.fzip_bucket)
                        logger.info(f"Successfully restored file content for {file_data['s3Key']}")
                    except KeyError:
                        logger.warning(f"File content not found in FZIP package for {file_data['s3Key']}")

                    logger.info(f"Transaction file metadata restored: {transaction_file.file_id}")
                        
                except Exception as e:
                    # Any failure indicates system issue (not conflicts - profile was validated empty)
                    error_msg = f"Failed to restore transaction file {file_data.get('fileId', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        return {
            'created': created,
            'errors': errors
        }
    
    def _restore_transactions(self, transactions: list, user_id: str) -> Dict[str, Any]:
        """Restore transactions data to empty profile with category assignments."""
        from models.transaction import TransactionCategoryAssignment, CategoryAssignmentStatus
        
        created = 0
        errors = []
        
        for transaction_data in transactions:
            try:
                # Convert category assignments from export format
                category_assignments = []
                for cat_data in transaction_data.get('categories', []):
                    assignment = TransactionCategoryAssignment(
                        categoryId=uuid.UUID(cat_data['categoryId']),
                        status=CategoryAssignmentStatus(cat_data.get('status', 'suggested')),
                        confidence=cat_data.get('confidence', 0.0),
                        ruleId=cat_data.get('ruleId'),
                        assignedAt=cat_data.get('assignedAt')
                    )
                    category_assignments.append(assignment)
                
                # Convert export format to Transaction model
                file_id = uuid.UUID(transaction_data['fileId']) if transaction_data.get('fileId') else None
                transaction_kwargs = {
                    'transactionId': uuid.UUID(transaction_data['transactionId']),
                    'accountId': uuid.UUID(transaction_data['accountId']),
                    'userId': user_id,  # Ensure user ownership
                    'date': transaction_data['date'],
                    'description': transaction_data['description'],
                    'amount': Decimal(str(transaction_data['amount'])),
                    'currency': Currency(transaction_data.get('currency', 'USD')),
                    'balance': Decimal(str(transaction_data['balance'])) if transaction_data.get('balance') else None,
                    'importOrder': transaction_data.get('importOrder', 0),
                    'transactionType': transaction_data.get('transactionType'),
                    'memo': transaction_data.get('memo'),
                    'checkNumber': transaction_data.get('checkNumber'),
                    'fitId': transaction_data.get('fitId'),
                    'status': transaction_data.get('status'),
                    'statusDate': transaction_data.get('statusDate'),
                    'transactionHash': transaction_data.get('transactionHash'),
                    'categories': category_assignments,
                    'primaryCategoryId': uuid.UUID(transaction_data['primaryCategoryId']) if transaction_data.get('primaryCategoryId') else None,
                    'createdAt': transaction_data.get('createdAt'),
                    'updatedAt': transaction_data.get('updatedAt')
                }
                
                # Only add fileId if it's not None
                if file_id is not None:
                    transaction_kwargs['fileId'] = file_id
                    
                transaction = Transaction(**transaction_kwargs)
                
                # Create transaction directly - profile already validated as empty
                create_transaction(transaction)
                created += 1
                logger.debug(f"Successfully restored transaction: {transaction.transaction_id}")
                    
            except Exception as e:
                # Any failure indicates system issue (not conflicts - profile was validated empty)
                error_msg = f"Failed to restore transaction {transaction_data.get('transactionId', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            'created': created,
            'errors': errors
        }
    
    # =============================================================================
    # Job Management
    # =============================================================================
    
    def get_job(self, job_id: str, user_id: str) -> Optional[FZIPJob]:
        """Get a FZIP job by ID and user ID."""
        return get_fzip_job(job_id, user_id)
    
    def list_user_jobs(self, user_id: str, job_type: Optional[str] = None, 
                      limit: int = 20, last_evaluated_key: Optional[Dict[str, Any]] = None) -> Tuple[List[FZIPJob], Optional[Dict[str, Any]]]:
        """List FZIP jobs for a user with optional filtering."""
        return list_user_fzip_jobs(user_id, job_type, limit, last_evaluated_key)
    
    def delete_job(self, job_id: str, user_id: str) -> bool:
        """Delete a FZIP job."""
        return delete_fzip_job(job_id, user_id)
    
    def cleanup_expired_jobs(self) -> int:
        """Clean up expired FZIP jobs."""
        return cleanup_expired_fzip_jobs()
    
    def update_job_status(self, job_id: str, user_id: str, status: FZIPStatus, 
                         progress: Optional[int] = None, error_message: Optional[str] = None) -> Optional[FZIPJob]:
        """Update job status and progress."""
        try:
            job = get_fzip_job(job_id, user_id)
            if not job:
                return None
            
            job.status = status
            if progress is not None:
                job.progress = progress
            if error_message:
                job.error = error_message
            
            update_fzip_job(job)
            return job
            
        except Exception as e:
            logger.error(f"Failed to update job status for {job_id}: {str(e)}")
            return None
    
    # =============================================================================
    # Utility Methods
    # =============================================================================
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return f"sha256:{hash_sha256.hexdigest()}"
    
    def cleanup_expired_backups(self, user_id: str) -> int:
        """Clean up expired backup files for a user"""
        # This would be implemented to clean up old backups from S3
        # For now, just log the operation
        logger.info(f"Cleanup operation for user {user_id} backups")
        return 0


# Global service instance
fzip_service = FZIPService()

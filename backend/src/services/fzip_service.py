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
    FZIPStatus, FZIPType, FZIPFormat, FZIPBackupType,
    # Backward compatibility imports
    FZIPExportType
)
from models.account import Account, AccountType
from models.transaction import Transaction
from models.category import Category
from models.file_map import FileMap
from models.transaction_file import TransactionFile
from models.analytics import AnalyticsData
from models import Currency
from models.events import ExportInitiatedEvent, ExportCompletedEvent, ExportFailedEvent
# TODO: Create BackupInitiatedEvent, BackupCompletedEvent, BackupFailedEvent, RestoreInitiatedEvent, RestoreCompletedEvent, RestoreFailedEvent
# For now, using export events for both backup and restore operations
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


logger = logging.getLogger(__name__)


class FZIPService:
    """Unified service for handling FZIP (backup/restore) operations"""
    
    def __init__(self):
        self.housef3_version = "2.5.0"  # Current version
        self.fzip_format_version = "1.0"
        self.fzip_bucket = os.environ.get('FZIP_PACKAGES_BUCKET', 'housef3-dev-fzip-packages')
        self.batch_size = 1000  # For large datasets
        
    # =============================================================================
    # Backup Operations
    # =============================================================================
    
    def initiate_export(self, user_id: str, export_type: FZIPExportType, 
                       include_analytics: bool = False, description: Optional[str] = None,
                       export_format: FZIPFormat = FZIPFormat.FZIP,
                       **kwargs) -> FZIPJob:
        """
        Initiate a new export job
        
        Args:
            user_id: User identifier
            export_type: Type of export to perform
            include_analytics: Whether to include analytics data
            description: Optional description for the export
            export_format: Format of the export package
            **kwargs: Additional export parameters
            
        Returns:
            FZIPJob: Created export job
        """
        try:
            # Create export job
            export_job = FZIPJob(
                userId=user_id,
                jobType=FZIPType.BACKUP,
                status=FZIPStatus.BACKUP_INITIATED,
                backupType=export_type,
                packageFormat=export_format,
                includeAnalytics=include_analytics,
                description=description,
                parameters=kwargs
            )
            
            # Set expiration time (24 hours from now)
            expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
            export_job.expires_at = int(expiry_time.timestamp() * 1000)
            
            # Save to database
            create_fzip_job(export_job)
            
            # Publish export initiated event
            event = ExportInitiatedEvent(
                user_id=user_id,
                export_id=str(export_job.job_id),
                export_type=export_type.value,
                include_analytics=include_analytics,
                description=description
            )
            event_service.publish_event(event)
            
            logger.info(f"Export job initiated: {export_job.job_id} for user {user_id}")
            return export_job
            
        except Exception as e:
            logger.error(f"Failed to initiate export for user {user_id}: {str(e)}")
            raise
    
    def collect_user_data(self, user_id: str, export_type: FZIPExportType,
                         include_analytics: bool = False,
                         **filters) -> Dict[str, Any]:
        """
        Collect all user data for export using specialized entity exporters
        Args:
            user_id: User identifier
            export_type: Type of export
            include_analytics: Whether to include analytics
            **filters: Additional filters for selective exports
            
        Returns:
            Dictionary containing all collected data
        """
        try:
            logger.info(f"Collecting data for user {user_id}, export type: {export_type}")
            
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
            fzip_metrics.record_export_data_volume(entity_counts, export_type.value)
            
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
            fzip_metrics.record_export_error(
                error_type=type(e).__name__,
                error_message=str(e),
                export_type=export_type.value,
                phase="data_collection"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to collect data for user {user_id}: {str(e)}")
            fzip_metrics.record_export_error(
                error_type=type(e).__name__,
                error_message=str(e),
                export_type=export_type.value,
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
    
    def build_export_package(self, export_job: FZIPJob, collected_data: Dict[str, Any]) -> Tuple[str, int]:
        """
        Build export package using enhanced streaming and compression capabilities
        
        Args:
            export_job: Export job details
            collected_data: Collected user data
            
        Returns:
            Tuple of (s3_key, package_size)
        """
        try:
            logger.info(f"Building enhanced export package for job {export_job.job_id}")
            
            # Configure streaming options for large exports
            streaming_options = FileStreamingOptions(
                enable_compression=True,
                compression_level=6,
                enable_checksum=True,
                max_memory_usage=200 * 1024 * 1024  # 200MB for larger exports
            )
            
            # Create enhanced package builder
            package_builder = ExportPackageBuilder(self.fzip_bucket, streaming_options)
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Build package with streaming capabilities
                package_dir, processing_summary = package_builder.build_package_with_streaming(
                    export_data=collected_data,
                    transaction_files=collected_data.get('transaction_files', []),
                    package_dir=os.path.join(temp_dir, "export_package")
                )
                
                # Create manifest with processing summary
                manifest = self._create_enhanced_manifest(export_job, collected_data, processing_summary)
                manifest_file = os.path.join(package_dir, "manifest.json")
                with open(manifest_file, 'w') as f:
                    json.dump(manifest.model_dump(by_alias=True), f, indent=2, default=str)
                
                # Create compressed ZIP file
                zip_path = os.path.join(temp_dir, f"export_{export_job.job_id}.zip")
                
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
                s3_key = f"exports/{export_job.user_id}/{export_job.job_id}/export_package.zip"
                package_size = os.path.getsize(zip_path)
                
                # Upload to S3
                logger.info(f"Uploading export package to S3: {s3_key}")
                with open(zip_path, 'rb') as f:
                    put_object(s3_key, f.read(), 'application/zip', self.fzip_bucket)
                
                # Record package size metrics
                export_type = export_job.backup_type.value if export_job.backup_type else "complete"
                fzip_metrics.record_export_package_size(package_size, export_type)
                
                logger.info(f"Enhanced export package created: {s3_key}")
                logger.info(f"Package size: {package_size} bytes, "
                          f"Compression ratio: {processing_summary.get('compression_ratio', 0):.1f}%")
                logger.info(f"Files processed: {processing_summary['transaction_files_processed']}, "
                          f"Failed: {processing_summary['transaction_files_failed']}")
                
                return s3_key, package_size
                
        except Exception as e:
            logger.error(f"Failed to build enhanced export package for job {export_job.job_id}: {str(e)}")
            # Record error metrics
            export_type = export_job.backup_type.value if export_job.backup_type else "complete"
            fzip_metrics.record_export_error(
                error_type=type(e).__name__,
                error_message=str(e),
                export_type=export_type,
                phase="package_building"
            )
            raise
    
    def _create_enhanced_manifest(self, export_job: FZIPJob, collected_data: Dict[str, Any], 
                                processing_summary: Dict[str, Any]) -> FZIPManifest:
        """Create enhanced export manifest with processing summary"""
        data_summary = FZIPDataSummary(
            accountsCount=len(collected_data.get('accounts', [])),
            transactionsCount=len(collected_data.get('transactions', [])),
            categoriesCount=len(collected_data.get('categories', [])),
            fileMapsCount=len(collected_data.get('file_maps', [])),
            transactionFilesCount=len(collected_data.get('transaction_files', [])),
            analyticsIncluded=export_job.include_analytics and bool(collected_data.get('analytics'))
        )
        
        compatibility = FZIPCompatibilityInfo(
            minimumVersion="2.0.0",
            supportedVersions=["2.0.0", "2.5.0"]
        )
        
        # Create basic manifest
        manifest = FZIPManifest(
            backupFormatVersion=self.fzip_format_version,
            backupTimestamp=datetime.now(timezone.utc).isoformat(),
            userId=export_job.user_id,
            housef3Version=self.housef3_version,
            dataSummary=data_summary,
            checksums={},  # Will be populated by package builder if needed
            compatibility=compatibility,
            jobId=export_job.job_id,
            backupType=export_job.backup_type or FZIPExportType.COMPLETE,
            includeAnalytics=export_job.include_analytics
        )
        
        # Add processing summary as metadata in the manifest data
        manifest_dict = manifest.model_dump(by_alias=True)
        manifest_dict['processingSummary'] = processing_summary
        
        # Add export summaries if available
        if '_export_summaries' in collected_data:
            manifest_dict['exportSummaries'] = collected_data['_export_summaries']
        
        return FZIPManifest.model_validate(manifest_dict)
    
    def generate_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for export download"""
        try:
            return get_presigned_url_simple(self.fzip_bucket, s3_key, 'get', expires_in)
        except Exception as e:
            logger.error(f"Failed to generate download URL for {s3_key}: {str(e)}")
            raise
    
    # =============================================================================
    # Restore Operations
    # =============================================================================
    
    def initiate_restore(self, user_id: str, restore_type: FZIPExportType,
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
            
            # Save to database
            create_fzip_job(restore_job)
            
            # Publish restore initiated event (using export event for now)
            event = ExportInitiatedEvent(
                user_id=user_id,
                export_id=str(restore_job.job_id),
                export_type=restore_type.value,
                description=description
            )
            event_service.publish_event(event)
            
            logger.info(f"Restore job initiated: {restore_job.job_id} for user {user_id}")
            return restore_job
            
        except Exception as e:
            logger.error(f"Failed to initiate restore for user {user_id}: {str(e)}")
            raise
    
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
            
            restore_job.status = FZIPStatus.RESTORE_VALIDATION_PASSED
            restore_job.progress = 40
            update_fzip_job(restore_job)
            
            # Begin data restore
            self._restore_data(restore_job, package_data)
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            restore_job.status = FZIPStatus.RESTORE_FAILED
            restore_job.error = str(e)
            update_fzip_job(restore_job)
    
    def _parse_package(self, package_s3_key: str) -> Dict[str, Any]:
        """Parse the ZIP package and extract data."""
        try:
            # Download package from S3
            package_data = get_object_content(package_s3_key, self.fzip_bucket)
            if not package_data:
                raise ImportException("Could not download package from S3")
            
            # Parse ZIP file
            with zipfile.ZipFile(io.BytesIO(package_data), 'r') as zipf:
                # Read manifest
                manifest_data = zipf.read('manifest.json')
                manifest = json.loads(manifest_data.decode('utf-8'))
                
                # Read data files
                data = {}
                for entity_type in ['accounts', 'transactions', 'categories', 'file_maps', 'transaction_files']:
                    try:
                        entity_data = zipf.read(f'data/{entity_type}.json')
                        data[entity_type] = json.loads(entity_data.decode('utf-8'))
                    except KeyError:
                        data[entity_type] = []
                
                return {
                    'manifest': manifest,
                    'data': data
                }
                
        except Exception as e:
            logger.error(f"Error parsing package: {str(e)}")
            raise ImportException(f"Failed to parse import package: {str(e)}")
    
    def _validate_schema(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the package schema."""
        try:
            manifest = package_data['manifest']
            data = package_data['data']
            
            # Check required manifest fields
            required_manifest_fields = ['version', 'exported_at', 'user_id', 'export_type']
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
            
            # Check user ownership
            if manifest.get('user_id') != user_id:
                return {
                    'valid': False,
                    'errors': ["Package was exported by a different user"]
                }
            
            # SINGLE VALIDATION: Check profile is completely empty
            empty_check = self._validate_empty_profile(user_id)
            if not empty_check['valid']:
                return empty_check
            
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
            restore_job.current_phase = "restoring_accounts"
            restore_job.progress = 50
            update_fzip_job(restore_job)
            
            # Restore to empty profile - no merge strategy needed
            account_results = self._restore_accounts(
                data.get('accounts', []), restore_job.user_id
            )
            results['accounts'] = account_results
            
            # 2. Restore categories
            restore_job.current_phase = "restoring_categories"
            restore_job.progress = 60
            update_fzip_job(restore_job)
            
            category_results = self._restore_categories(
                data.get('categories', []), restore_job.user_id
            )
            results['categories'] = category_results
            
            # 3. Restore file maps
            restore_job.current_phase = "restoring_file_maps"
            restore_job.progress = 70
            update_fzip_job(restore_job)
            
            file_map_results = self._restore_file_maps(
                data.get('file_maps', []), restore_job.user_id
            )
            results['file_maps'] = file_map_results
            
            # 4. Restore transaction files
            restore_job.current_phase = "restoring_transaction_files"
            restore_job.progress = 80
            update_fzip_job(restore_job)
            
            file_results = self._restore_transaction_files(
                data.get('transaction_files', []), restore_job.user_id
            )
            results['transaction_files'] = file_results
            
            # 5. Restore transactions
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
            
        except Exception as e:
            logger.error(f"Error during data restore: {str(e)}")
            raise
    
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
    
    def _restore_transaction_files(self, transaction_files: list, user_id: str) -> Dict[str, Any]:
        """Restore transaction files data to empty profile and restore files to S3."""
        from models.transaction_file import ProcessingStatus, FileFormat, DateRange
        from utils.s3_dao import put_object
        
        created = 0
        errors = []
        
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
                
                # TODO: Restore actual file content from FZIP package to S3
                # This would require extracting the file content from the FZIP package
                # and uploading it to S3 with the correct key
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
    
    def cleanup_expired_exports(self, user_id: str) -> int:
        """Clean up expired export files for a user"""
        # This would be implemented to clean up old exports from S3
        # For now, just log the operation
        logger.info(f"Cleanup operation for user {user_id} exports")
        return 0

    # =============================================================================
    # Backup Method Aliases (Legacy Export Terminology)
    # =============================================================================

    def initiate_backup(self, user_id: str, backup_type: FZIPBackupType,
                       include_analytics: bool = False, description: Optional[str] = None,
                       backup_format: FZIPFormat = FZIPFormat.FZIP,
                       **kwargs) -> FZIPJob:
        """
        Initiate a new backup job (alias for initiate_export)
        
        Args:
            user_id: User identifier
            backup_type: Type of backup to perform
            include_analytics: Whether to include analytics data
            description: Optional description for the backup
            backup_format: Format of the backup package
        """
        return self.initiate_export(user_id, backup_type, include_analytics, 
                                  description, backup_format, **kwargs)

    def collect_backup_data(self, user_id: str, backup_type: FZIPBackupType,
                           include_analytics: bool = False, **kwargs) -> Dict[str, Any]:
        """Collect user data for backup (alias for collect_user_data)"""
        return self.collect_user_data(user_id, backup_type, include_analytics, **kwargs)

    def build_backup_package(self, backup_job: FZIPJob, collected_data: Dict[str, Any]) -> Tuple[str, int]:
        """Build backup package (alias for build_export_package)"""
        return self.build_export_package(backup_job, collected_data)

    def cleanup_expired_backups(self, user_id: str) -> int:
        """Clean up expired backup files (alias for cleanup_expired_exports)"""
        return self.cleanup_expired_exports(user_id)


# Global service instance
fzip_service = FZIPService() 
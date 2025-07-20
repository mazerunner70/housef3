"""
Unified FZIP Service for import/export operations.
Handles data collection, package building, import processing, and export operations.
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
    FZIPStatus, FZIPType, FZIPFormat, FZIPExportType, FZIPMergeStrategy
)
from models.account import Account
from models.transaction import Transaction
from models.category import Category
from models.file_map import FileMap
from models.transaction_file import TransactionFile
from models.analytics import AnalyticsData
from models.events import ExportInitiatedEvent, ExportCompletedEvent, ExportFailedEvent
from utils.db_utils import (
    list_user_accounts, list_user_transactions, list_categories_by_user_from_db,
    list_file_maps_by_user, list_user_files, get_analytics_data,
    create_fzip_job, update_fzip_job, get_fzip_job, list_user_fzip_jobs,
    delete_fzip_job, cleanup_expired_fzip_jobs
)
from utils.s3_dao import get_object_content, put_object, get_presigned_url_simple
from services.event_service import event_service
from services.export_data_processors import (
    AccountExporter, TransactionExporter, CategoryExporter, 
    FileMapExporter, TransactionFileExporter, ExportException
)
from services.s3_file_handler import S3FileStreamer, ExportPackageBuilder, FileStreamingOptions


logger = logging.getLogger(__name__)


class FZIPService:
    """Unified service for handling FZIP (import/export) operations"""
    
    def __init__(self):
        self.housef3_version = "2.5.0"  # Current version
        self.fzip_format_version = "1.0"
        self.fzip_bucket = os.environ.get('FZIP_PACKAGES_BUCKET', 'housef3-dev-fzip-packages')
        self.batch_size = 1000  # For large datasets
        
    # =============================================================================
    # Export Operations
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
                jobType=FZIPType.EXPORT,
                status=FZIPStatus.EXPORT_INITIATED,
                exportType=export_type,
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
            

            
            logger.info(f"Enhanced data collection complete using specialized exporters")
            for entity_type, summary in export_summaries.items():
                logger.info(f"{entity_type}: {summary['processed_count']} items, "
                          f"{summary.get('success_rate', 100):.1f}% success rate")
            
            return collected_data
            
        except ExportException as e:
            logger.error(f"Export-specific error collecting data for user {user_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to collect data for user {user_id}: {str(e)}")
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
                
                # Use streaming upload for large files
                if package_size > 100 * 1024 * 1024:  # > 100MB
                    with open(zip_path, 'rb') as f:
                        put_object(s3_key, f.read(), 'application/zip', self.fzip_bucket)
                else:
                    with open(zip_path, 'rb') as f:
                        put_object(s3_key, f.read(), 'application/zip', self.fzip_bucket)
                

                
                logger.info(f"Enhanced export package created: {s3_key}")
                logger.info(f"Package size: {package_size} bytes, "
                          f"Compression ratio: {processing_summary.get('compression_ratio', 0):.1f}%")
                logger.info(f"Files processed: {processing_summary['transaction_files_processed']}, "
                          f"Failed: {processing_summary['transaction_files_failed']}")
                
                return s3_key, package_size
                
        except Exception as e:
            logger.error(f"Failed to build enhanced export package for job {export_job.job_id}: {str(e)}")
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
            exportFormatVersion=self.fzip_format_version,
            exportTimestamp=datetime.now(timezone.utc).isoformat(),
            userId=export_job.user_id,
            housef3Version=self.housef3_version,
            dataSummary=data_summary,
            checksums={},  # Will be populated by package builder if needed
            compatibility=compatibility,
            jobId=export_job.job_id,
            exportType=export_job.export_type or FZIPExportType.COMPLETE,
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
    # Import Operations
    # =============================================================================
    
    def initiate_import(self, user_id: str, import_type: FZIPExportType,
                       merge_strategy: FZIPMergeStrategy = FZIPMergeStrategy.FAIL_ON_CONFLICT, 
                       description: Optional[str] = None,
                       **kwargs) -> FZIPJob:
        """
        Initiate a new import job
        
        Args:
            user_id: User identifier
            import_type: Type of import to perform
            merge_strategy: Strategy for handling conflicts
            description: Optional description for the import
            **kwargs: Additional import parameters
            
        Returns:
            FZIPJob: Created import job
        """
        try:
            # Create import job
            import_job = FZIPJob(
                userId=user_id,
                jobType=FZIPType.IMPORT,
                status=FZIPStatus.IMPORT_UPLOADED,
                exportType=import_type,
                mergeStrategy=merge_strategy,
                description=description,
                parameters=kwargs
            )
            
            # Set expiration time (24 hours from now)
            expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
            import_job.expires_at = int(expiry_time.timestamp() * 1000)
            
            # Save to database
            create_fzip_job(import_job)
            
            # Publish import initiated event (using export event for now)
            event = ExportInitiatedEvent(
                user_id=user_id,
                export_id=str(import_job.job_id),
                export_type=import_type.value,
                description=description
            )
            event_service.publish_event(event)
            
            logger.info(f"Import job initiated: {import_job.job_id} for user {user_id}")
            return import_job
            
        except Exception as e:
            logger.error(f"Failed to initiate import for user {user_id}: {str(e)}")
            raise
    
    def start_import(self, import_job: FZIPJob, package_s3_key: str):
        """Start import processing."""
        try:
            # Update job with package location
            import_job.s3_key = package_s3_key
            import_job.status = FZIPStatus.IMPORT_VALIDATING
            import_job.current_phase = "parsing_package"
            import_job.progress = 10
            update_fzip_job(import_job)
            
            # Parse package
            package_data = self._parse_package(package_s3_key)
            
            # Validate schema
            import_job.current_phase = "validating_schema"
            import_job.progress = 20
            update_fzip_job(import_job)
            
            schema_results = self._validate_schema(package_data)
            import_job.validation_results['schema'] = schema_results
            
            if not schema_results['valid']:
                import_job.status = FZIPStatus.IMPORT_VALIDATION_FAILED
                import_job.error = "Schema validation failed"
                update_fzip_job(import_job)
                return
            
            # Validate business rules
            import_job.current_phase = "validating_business_rules"
            import_job.progress = 30
            update_fzip_job(import_job)
            
            merge_strategy_str = import_job.merge_strategy.value if import_job.merge_strategy else "fail_on_conflict"
            business_results = self._validate_business_rules(
                package_data, import_job.user_id, merge_strategy_str
            )
            import_job.validation_results['business'] = business_results
            
            if not business_results['valid']:
                import_job.status = FZIPStatus.IMPORT_VALIDATION_FAILED
                import_job.error = "Business validation failed"
                update_fzip_job(import_job)
                return
            
            import_job.status = FZIPStatus.IMPORT_VALIDATION_PASSED
            import_job.progress = 40
            update_fzip_job(import_job)
            
            # Begin data import
            self._import_data(import_job, package_data)
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            import_job.status = FZIPStatus.IMPORT_FAILED
            import_job.error = str(e)
            update_fzip_job(import_job)
    
    def _parse_package(self, package_s3_key: str) -> Dict[str, Any]:
        """Parse the ZIP package and extract data."""
        try:
            # Download package from S3
            package_data = get_object_content(package_s3_key, self.fzip_bucket)
            if not package_data:
                raise Exception("Could not download package from S3")
            
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
            raise Exception(f"Failed to parse import package: {str(e)}")
    
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
    
    def _validate_business_rules(self, package_data: Dict[str, Any], user_id: str, merge_strategy: str) -> Dict[str, Any]:
        """Validate business rules for the import."""
        try:
            data = package_data['data']
            manifest = package_data['manifest']
            
            # Check user ownership
            if manifest.get('user_id') != user_id:
                return {
                    'valid': False,
                    'errors': ["Package was exported by a different user"]
                }
            
            # Check for UUID conflicts if merge strategy is fail_on_conflict
            if merge_strategy == "fail_on_conflict":
                conflicts = self._check_uuid_conflicts(data, user_id)
                if conflicts:
                    return {
                        'valid': False,
                        'errors': [f"UUID conflicts found: {', '.join(conflicts)}"]
                    }
            
            # Validate data relationships
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
    
    def _check_uuid_conflicts(self, data: Dict[str, Any], user_id: str) -> list:
        """Check for UUID conflicts with existing data."""
        # This would need to be implemented with actual database queries
        # For now, return empty list (no conflicts)
        return []
    
    def _import_data(self, import_job: FZIPJob, package_data: Dict[str, Any]):
        """Import all data from the package."""
        try:
            import_job.status = FZIPStatus.IMPORT_PROCESSING
            data = package_data['data']
            results = {}
            
            # Import in dependency order
            
            # 1. Import accounts first
            import_job.current_phase = "importing_accounts"
            import_job.progress = 50
            update_fzip_job(import_job)
            
            merge_strategy_str = import_job.merge_strategy.value if import_job.merge_strategy else "fail_on_conflict"
            account_results = self._import_accounts(
                data.get('accounts', []), import_job.user_id, merge_strategy_str
            )
            results['accounts'] = account_results
            
            # 2. Import categories
            import_job.current_phase = "importing_categories"
            import_job.progress = 60
            update_fzip_job(import_job)
            
            category_results = self._import_categories(
                data.get('categories', []), import_job.user_id, merge_strategy_str
            )
            results['categories'] = category_results
            
            # 3. Import file maps
            import_job.current_phase = "importing_file_maps"
            import_job.progress = 70
            update_fzip_job(import_job)
            
            file_map_results = self._import_file_maps(
                data.get('file_maps', []), import_job.user_id, merge_strategy_str
            )
            results['file_maps'] = file_map_results
            
            # 4. Import transaction files
            import_job.current_phase = "importing_transaction_files"
            import_job.progress = 80
            update_fzip_job(import_job)
            
            file_results = self._import_transaction_files(
                data.get('transaction_files', []), import_job.user_id, merge_strategy_str
            )
            results['transaction_files'] = file_results
            
            # 5. Import transactions
            import_job.current_phase = "importing_transactions"
            import_job.progress = 90
            update_fzip_job(import_job)
            
            transaction_results = self._import_transactions(
                data.get('transactions', []), import_job.user_id, merge_strategy_str
            )
            results['transactions'] = transaction_results
            
            # Complete import
            import_job.status = FZIPStatus.IMPORT_COMPLETED
            import_job.progress = 100
            import_job.current_phase = "completed"
            import_job.import_results = results
            import_job.completed_at = int(datetime.now(timezone.utc).timestamp() * 1000)
            update_fzip_job(import_job)
            
        except Exception as e:
            logger.error(f"Error during data import: {str(e)}")
            raise
    
    def _import_accounts(self, accounts: list, user_id: str, merge_strategy: str) -> Dict[str, Any]:
        """Import accounts data."""
        # Placeholder implementation
        return {
            'created': len(accounts),
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
    
    def _import_categories(self, categories: list, user_id: str, merge_strategy: str) -> Dict[str, Any]:
        """Import categories data."""
        # Placeholder implementation
        return {
            'created': len(categories),
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
    
    def _import_file_maps(self, file_maps: list, user_id: str, merge_strategy: str) -> Dict[str, Any]:
        """Import file maps data."""
        # Placeholder implementation
        return {
            'created': len(file_maps),
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
    
    def _import_transaction_files(self, transaction_files: list, user_id: str, merge_strategy: str) -> Dict[str, Any]:
        """Import transaction files data."""
        # Placeholder implementation
        return {
            'created': len(transaction_files),
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
    
    def _import_transactions(self, transactions: list, user_id: str, merge_strategy: str) -> Dict[str, Any]:
        """Import transactions data."""
        # Placeholder implementation
        return {
            'created': len(transactions),
            'updated': 0,
            'skipped': 0,
            'errors': []
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


# Global service instance
fzip_service = FZIPService() 
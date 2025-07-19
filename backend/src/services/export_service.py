"""
Export Service for the import/export system.
Handles data collection, package building, and export operations.
"""
import hashlib
import json
import logging
import os
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal

from models.export import (
    ExportJob, ExportManifest, DataSummary, CompatibilityInfo,
    ExportStatus, ExportType, ExportFormat
)
from models.account import Account
from models.transaction import Transaction
from models.category import Category
from models.file_map import FileMap
from models.transaction_file import TransactionFile
from models.analytics import AnalyticsData
from utils.db_utils import (
    list_user_accounts, list_user_transactions, list_categories_by_user_from_db,
    list_file_maps_by_user, list_user_files, get_analytics_data
)
from utils.s3_dao import get_object_content, put_object, get_presigned_url_simple
from services.event_service import event_service
from models.events import ExportInitiatedEvent, ExportCompletedEvent, ExportFailedEvent
from services.export_data_processors import (
    AccountExporter, TransactionExporter, CategoryExporter, 
    FileMapExporter, TransactionFileExporter, ExportException
)
from services.s3_file_handler import S3FileStreamer, ExportPackageBuilder, FileStreamingOptions
from services.export_error_handler import export_error_handler, ErrorCategory

logger = logging.getLogger(__name__)


class ExportService:
    """Service for handling export operations"""
    
    def __init__(self):
        self.housef3_version = "2.5.0"  # Current version
        self.export_format_version = "1.0"
        self.export_bucket = os.environ.get('FILE_STORAGE_BUCKET', 'housef3-dev-file-storage')
        self.batch_size = 1000  # For large datasets
        
    def initiate_export(self, user_id: str, export_type: ExportType, 
                       include_analytics: bool = False, description: Optional[str] = None,
                       export_format: ExportFormat = ExportFormat.ZIP,
                       **kwargs) -> ExportJob:
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
            ExportJob: Created export job
        """
        try:
            # Create export job
            export_job = ExportJob(
                userId=user_id,
                exportType=export_type,
                exportFormat=export_format,
                includeAnalytics=include_analytics,
                description=description,
                parameters=kwargs
            )
            
            # Set expiration time (24 hours from now)
            expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
            export_job.expires_at = int(expiry_time.timestamp() * 1000)
            
            # Publish export initiated event
            event = ExportInitiatedEvent(
                user_id=user_id,
                export_id=str(export_job.export_id),
                export_type=export_type.value,
                include_analytics=include_analytics,
                description=description
            )
            event_service.publish_event(event)
            
            logger.info(f"Export job initiated: {export_job.export_id} for user {user_id}")
            return export_job
            
        except Exception as e:
            logger.error(f"Failed to initiate export for user {user_id}: {str(e)}")
            raise
    
    @export_error_handler.with_error_handling("collect_user_data", max_retries=2)
    def collect_user_data(self, user_id: str, export_type: ExportType,
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
            
            # Record success for circuit breaker
            export_error_handler.record_success("collect_user_data")
            
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
    
    def _collect_accounts(self, user_id: str, account_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collect user accounts"""
        try:
            accounts = list_user_accounts(user_id)
            
            # Filter by account IDs if specified
            if account_ids:
                account_id_set = set(account_ids)
                accounts = [acc for acc in accounts if str(acc.account_id) in account_id_set]
            
            return [self._serialize_account(account) for account in accounts]
            
        except Exception as e:
            logger.error(f"Failed to collect accounts for user {user_id}: {str(e)}")
            return []
    
    def _collect_transactions(self, user_id: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect user transactions with optional filtering"""
        try:
            # Get all transactions with pagination support
            all_transactions = []
            last_evaluated_key = None
            
            while True:
                transactions, pagination_key, _ = list_user_transactions(
                    user_id, 
                    limit=self.batch_size,
                    last_evaluated_key=last_evaluated_key
                )
                
                # Apply filters
                filtered_transactions = self._filter_transactions(transactions, filters)
                all_transactions.extend(filtered_transactions)
                
                if not pagination_key:
                    break
                last_evaluated_key = pagination_key
            
            return [self._serialize_transaction(transaction) for transaction in all_transactions]
            
        except Exception as e:
            logger.error(f"Failed to collect transactions for user {user_id}: {str(e)}")
            return []
    
    def _filter_transactions(self, transactions: List[Transaction], filters: Dict[str, Any]) -> List[Transaction]:
        """Apply filters to transactions"""
        filtered = transactions
        
        # Filter by account IDs
        if filters.get('account_ids'):
            account_id_set = set(filters['account_ids'])
            filtered = [tx for tx in filtered if str(tx.account_id) in account_id_set]
        
        # Filter by date range
        if filters.get('date_range_start') or filters.get('date_range_end'):
            start_date = filters.get('date_range_start', 0)
            end_date = filters.get('date_range_end', 9999999999999)  # Far future
            filtered = [tx for tx in filtered if start_date <= tx.date <= end_date]
        
        # Filter by category IDs
        if filters.get('category_ids'):
            category_id_set = set(str(cid) for cid in filters['category_ids'])
            filtered = [tx for tx in filtered 
                       if tx.primary_category_id and str(tx.primary_category_id) in category_id_set]
        
        return filtered
    
    def _collect_categories(self, user_id: str, category_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collect user categories"""
        try:
            categories = list_categories_by_user_from_db(user_id)
            
            # Filter by category IDs if specified
            if category_ids:
                category_id_set = set(category_ids)
                categories = [cat for cat in categories if str(cat.categoryId) in category_id_set]
            
            return [self._serialize_category(category) for category in categories]
            
        except Exception as e:
            logger.error(f"Failed to collect categories for user {user_id}: {str(e)}")
            return []
    
    def _collect_file_maps(self, user_id: str) -> List[Dict[str, Any]]:
        """Collect user file maps"""
        try:
            file_maps = list_file_maps_by_user(user_id)
            return [self._serialize_file_map(file_map) for file_map in file_maps]
            
        except Exception as e:
            logger.error(f"Failed to collect file maps for user {user_id}: {str(e)}")
            return []
    
    def _collect_transaction_files(self, user_id: str, account_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collect user transaction files"""
        try:
            files = list_user_files(user_id)
            
            # Filter by account IDs if specified
            if account_ids:
                account_id_set = set(account_ids)
                files = [f for f in files 
                        if f.account_id and str(f.account_id) in account_id_set]
            
            return [self._serialize_transaction_file(file) for file in files]
            
        except Exception as e:
            logger.error(f"Failed to collect transaction files for user {user_id}: {str(e)}")
            return []
    
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
    
    @export_error_handler.with_error_handling("build_export_package", max_retries=2)
    def build_export_package(self, export_job: ExportJob, collected_data: Dict[str, Any]) -> Tuple[str, int]:
        """
        Build export package using enhanced streaming and compression capabilities
        
        Args:
            export_job: Export job details
            collected_data: Collected user data
            
        Returns:
            Tuple of (s3_key, package_size)
        """
        try:
            logger.info(f"Building enhanced export package for job {export_job.export_id}")
            
            # Configure streaming options for large exports
            streaming_options = FileStreamingOptions(
                enable_compression=True,
                compression_level=6,
                enable_checksum=True,
                max_memory_usage=200 * 1024 * 1024  # 200MB for larger exports
            )
            
            # Create enhanced package builder
            package_builder = ExportPackageBuilder(self.export_bucket, streaming_options)
            
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
                zip_path = os.path.join(temp_dir, f"export_{export_job.export_id}.zip")
                
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
                s3_key = f"exports/{export_job.user_id}/{export_job.export_id}/export_package.zip"
                package_size = os.path.getsize(zip_path)
                
                # Use streaming upload for large files
                if package_size > 100 * 1024 * 1024:  # > 100MB
                    with open(zip_path, 'rb') as f:
                        put_object(s3_key, f.read(), 'application/zip', self.export_bucket)
                else:
                    with open(zip_path, 'rb') as f:
                        put_object(s3_key, f.read(), 'application/zip', self.export_bucket)
                
                # Record success for circuit breaker
                export_error_handler.record_success("build_export_package")
                
                logger.info(f"Enhanced export package created: {s3_key}")
                logger.info(f"Package size: {package_size} bytes, "
                          f"Compression ratio: {processing_summary.get('compression_ratio', 0):.1f}%")
                logger.info(f"Files processed: {processing_summary['transaction_files_processed']}, "
                          f"Failed: {processing_summary['transaction_files_failed']}")
                
                return s3_key, package_size
                
        except Exception as e:
            logger.error(f"Failed to build enhanced export package for job {export_job.export_id}: {str(e)}")
            raise
    
    def _download_transaction_files(self, transaction_files: List[Dict[str, Any]], files_dir: str):
        """Download transaction files from S3 to include in export"""
        try:
            for file_info in transaction_files:
                if not file_info.get('s3Key'):
                    continue
                    
                try:
                    # Create subdirectory for this file
                    file_id = file_info['fileId']
                    file_dir = os.path.join(files_dir, file_id)
                    os.makedirs(file_dir, exist_ok=True)
                    
                    # Download file content
                    content = get_object_content(file_info['s3Key'], self.export_bucket)
                    if content:
                        # Use original filename
                        filename = file_info.get('fileName', f'file_{file_id}')
                        file_path = os.path.join(file_dir, filename)
                        
                        if isinstance(content, str):
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                        else:
                            with open(file_path, 'wb') as f:
                                f.write(content)
                                
                except Exception as e:
                    logger.warning(f"Failed to download file {file_info['fileId']}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to download transaction files: {str(e)}")
            # Non-fatal error, continue without files
    
    def _create_manifest(self, export_job: ExportJob, collected_data: Dict[str, Any], 
                        checksums: Dict[str, str]) -> ExportManifest:
        """Create export manifest"""
        data_summary = DataSummary(
            accountsCount=len(collected_data.get('accounts', [])),
            transactionsCount=len(collected_data.get('transactions', [])),
            categoriesCount=len(collected_data.get('categories', [])),
            fileMapsCount=len(collected_data.get('file_maps', [])),
            transactionFilesCount=len(collected_data.get('transaction_files', [])),
            analyticsIncluded=export_job.include_analytics and bool(collected_data.get('analytics'))
        )
        
        compatibility = CompatibilityInfo(
            minimumVersion="2.0.0",
            supportedVersions=["2.0.0", "2.5.0"]
        )
        
        return ExportManifest(
            exportFormatVersion=self.export_format_version,
            exportTimestamp=datetime.now(timezone.utc).isoformat(),
            userId=export_job.user_id,
            housef3Version=self.housef3_version,
            dataSummary=data_summary,
            checksums=checksums,
            compatibility=compatibility,
            exportId=export_job.export_id,
            exportType=export_job.export_type,
            includeAnalytics=export_job.include_analytics
        )
    
    def _create_enhanced_manifest(self, export_job: ExportJob, collected_data: Dict[str, Any], 
                                processing_summary: Dict[str, Any]) -> ExportManifest:
        """Create enhanced export manifest with processing summary"""
        data_summary = DataSummary(
            accountsCount=len(collected_data.get('accounts', [])),
            transactionsCount=len(collected_data.get('transactions', [])),
            categoriesCount=len(collected_data.get('categories', [])),
            fileMapsCount=len(collected_data.get('file_maps', [])),
            transactionFilesCount=len(collected_data.get('transaction_files', [])),
            analyticsIncluded=export_job.include_analytics and bool(collected_data.get('analytics'))
        )
        
        compatibility = CompatibilityInfo(
            minimumVersion="2.0.0",
            supportedVersions=["2.0.0", "2.5.0"]
        )
        
        # Create basic manifest
        manifest = ExportManifest(
            exportFormatVersion=self.export_format_version,
            exportTimestamp=datetime.now(timezone.utc).isoformat(),
            userId=export_job.user_id,
            housef3Version=self.housef3_version,
            dataSummary=data_summary,
            checksums={},  # Will be populated by package builder if needed
            compatibility=compatibility,
            exportId=export_job.export_id,
            exportType=export_job.export_type,
            includeAnalytics=export_job.include_analytics
        )
        
        # Add processing summary as metadata in the manifest data
        manifest_dict = manifest.model_dump(by_alias=True)
        manifest_dict['processingSummary'] = processing_summary
        
        # Add export summaries if available
        if '_export_summaries' in collected_data:
            manifest_dict['exportSummaries'] = collected_data['_export_summaries']
        
        return ExportManifest.model_validate(manifest_dict)
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return f"sha256:{hash_sha256.hexdigest()}"
    
    def generate_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for export download"""
        try:
            return get_presigned_url_simple(self.export_bucket, s3_key, 'get', expires_in)
        except Exception as e:
            logger.error(f"Failed to generate download URL for {s3_key}: {str(e)}")
            raise
    
    def cleanup_expired_exports(self, user_id: str) -> int:
        """Clean up expired export files for a user"""
        # This would be implemented to clean up old exports from S3
        # For now, just log the operation
        logger.info(f"Cleanup operation for user {user_id} exports")
        return 0
    
    # Serialization methods
    def _serialize_account(self, account: Account) -> Dict[str, Any]:
        """Serialize account for export"""
        return account.model_dump(by_alias=True, exclude_none=True)
    
    def _serialize_transaction(self, transaction: Transaction) -> Dict[str, Any]:
        """Serialize transaction for export"""
        return transaction.model_dump(by_alias=True, exclude_none=True)
    
    def _serialize_category(self, category: Category) -> Dict[str, Any]:
        """Serialize category for export"""
        return category.model_dump(by_alias=True, exclude_none=True)
    
    def _serialize_file_map(self, file_map: FileMap) -> Dict[str, Any]:
        """Serialize file map for export"""
        return file_map.model_dump(by_alias=True, exclude_none=True)
    
    def _serialize_transaction_file(self, transaction_file: TransactionFile) -> Dict[str, Any]:
        """Serialize transaction file for export"""
        return transaction_file.model_dump(by_alias=True, exclude_none=True) 
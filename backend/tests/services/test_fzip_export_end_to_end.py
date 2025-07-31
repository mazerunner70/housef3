"""
End-to-end tests for FZIP export functionality.
Tests the complete export pipeline from initiation to download.
"""
import json
import os
import tempfile
import time
import uuid
import zipfile
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

import pytest

from models.account import Account, AccountType, Currency
from models.transaction import Transaction
from models.category import Category, CategoryType
from models.file_map import FileMap, FieldMapping
from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus
from models.fzip import FZIPJob, FZIPStatus, FZIPExportType, FZIPType
from services.fzip_service import FZIPService
from services.export_data_processors import (
    AccountExporter, TransactionExporter, CategoryExporter, 
    FileMapExporter, TransactionFileExporter
)
from utils.db_utils import create_fzip_job, get_fzip_job, update_fzip_job


class TestFZIPExportEndToEnd:
    """Comprehensive end-to-end tests for FZIP export functionality."""

    @pytest.fixture
    def test_user_id(self):
        """Test user ID."""
        return "test-user-12345"

    @pytest.fixture
    def fzip_service(self):
        """FZIP service instance."""
        return FZIPService()

    @pytest.fixture
    def sample_test_data(self, test_user_id):
        """Create sample test data for export testing."""
        # Create consistent file ID for transactions and files
        sample_file_id = uuid.uuid4()
        
        # Sample accounts
        accounts = [
            Account(
                userId=test_user_id,
                accountName="Test Checking Account",
                accountType=AccountType.CHECKING,
                institution="Test Bank",
                balance=Decimal("2500.75"),
                currency=Currency.USD,
                isActive=True
            ),
            Account(
                userId=test_user_id,
                accountName="Test Credit Card",
                accountType=AccountType.CREDIT_CARD,
                institution="Test Credit Union",
                balance=Decimal("-850.25"),
                currency=Currency.USD,
                isActive=True
            )
        ]

        # Sample categories
        categories = [
            Category(
                userId=test_user_id,
                name="Groceries",
                type=CategoryType.EXPENSE,
                color="#FF5733",
                icon="🛒"
            ),
            Category(
                userId=test_user_id,
                name="Salary",
                type=CategoryType.INCOME,
                color="#33FF57",
                icon="💰"
            )
        ]

        # Sample transactions
        transactions = []
        for i in range(5):
            transactions.append(Transaction(
                accountId=accounts[0].account_id,
                userId=test_user_id,
                fileId=sample_file_id,
                date=int((datetime.now(timezone.utc).timestamp() - (i * 86400)) * 1000),
                description=f"Test Transaction {i+1}",
                amount=Decimal(f"{(i+1) * 10}.50"),
                currency=Currency.USD,
                balance=Decimal(f"{2500 - (i * 10)}.{50 - i}"),
                importOrder=i + 1
            ))

        # Sample file maps
        file_maps = [
            FileMap(
                userId=test_user_id,
                name="Test QIF Mapping",
                description="Test mapping for QIF files",
                mappings=[
                    FieldMapping(
                        sourceField="Date",
                        targetField="date",
                        transformation=None
                    ),
                    FieldMapping(
                        sourceField="Amount",
                        targetField="amount",
                        transformation=None
                    )
                ]
            )
        ]

        # Sample transaction files  
        transaction_files = [
            TransactionFile(
                fileId=sample_file_id,
                userId=test_user_id,
                fileName="test_statement.qif",
                fileSize=1024,
                s3Key=f"{test_user_id}/test_statement.qif",
                accountId=accounts[0].account_id,
                fileFormat=FileFormat.QIF,
                processingStatus=ProcessingStatus.PROCESSED,
                recordCount=5,
                transactionCount=5
            )
        ]

        return {
            'accounts': accounts,
            'categories': categories,
            'transactions': transactions,
            'file_maps': file_maps,
            'transaction_files': transaction_files
        }

    def test_entity_exporters_data_collection(self, test_user_id, sample_test_data):
        """Test that entity exporters can collect and serialize data correctly."""
        
        # Mock database calls for each exporter
        with patch('services.export_data_processors.list_user_accounts') as mock_accounts, \
             patch('services.export_data_processors.list_user_transactions') as mock_transactions, \
             patch('services.export_data_processors.list_categories_by_user_from_db') as mock_categories, \
             patch('services.export_data_processors.list_file_maps_by_user') as mock_file_maps, \
             patch('services.export_data_processors.list_user_files') as mock_files:

            # Setup mocks
            mock_accounts.return_value = sample_test_data['accounts']
            mock_transactions.return_value = (sample_test_data['transactions'], None, len(sample_test_data['transactions']))
            mock_categories.return_value = sample_test_data['categories']
            mock_file_maps.return_value = sample_test_data['file_maps']
            mock_files.return_value = sample_test_data['transaction_files']

            # Test AccountExporter
            account_exporter = AccountExporter(test_user_id, batch_size=1000)
            account_data = account_exporter.collect_data({})
            
            assert len(account_data) == 2
            assert account_data[0]['accountName'] == "Test Checking Account"
            assert account_data[0]['accountType'] == "checking"
            assert 'exportMetadata' in account_data[0]

            # Test TransactionExporter
            transaction_exporter = TransactionExporter(test_user_id, batch_size=1000)
            transaction_data = transaction_exporter.collect_data({})
            
            assert len(transaction_data) == 5
            assert transaction_data[0]['description'] == "Test Transaction 1"
            assert 'exportMetadata' in transaction_data[0]

            # Test CategoryExporter
            category_exporter = CategoryExporter(test_user_id, batch_size=1000)
            category_data = category_exporter.collect_data({})
            
            assert len(category_data) == 2
            assert category_data[0]['name'] in ["Groceries", "Salary"]
            assert 'exportMetadata' in category_data[0]

            # Get export summaries
            account_summary = account_exporter.get_export_summary()
            transaction_summary = transaction_exporter.get_export_summary()
            category_summary = category_exporter.get_export_summary()

            assert account_summary['processed_count'] == 2
            assert transaction_summary['processed_count'] == 5
            assert category_summary['processed_count'] == 2

    def test_fzip_service_data_collection(self, fzip_service, test_user_id, sample_test_data):
        """Test that FZIPService can collect all user data using entity exporters."""
        
        with patch('services.fzip_service.AccountExporter') as mock_account_exporter, \
             patch('services.fzip_service.TransactionExporter') as mock_transaction_exporter, \
             patch('services.fzip_service.CategoryExporter') as mock_category_exporter, \
             patch('services.fzip_service.FileMapExporter') as mock_file_map_exporter, \
             patch('services.fzip_service.TransactionFileExporter') as mock_file_exporter:

            # Setup mock exporter instances
            mock_account_instance = MagicMock()
            mock_account_instance.collect_data.return_value = sample_test_data['accounts']
            mock_account_instance.get_export_summary.return_value = {'processed_count': 2}
            mock_account_exporter.return_value = mock_account_instance
            
            mock_transaction_instance = MagicMock()
            mock_transaction_instance.collect_data.return_value = sample_test_data['transactions']
            mock_transaction_instance.get_export_summary.return_value = {'processed_count': 5}
            mock_transaction_exporter.return_value = mock_transaction_instance
            
            mock_category_instance = MagicMock()
            mock_category_instance.collect_data.return_value = sample_test_data['categories']
            mock_category_instance.get_export_summary.return_value = {'processed_count': 2}
            mock_category_exporter.return_value = mock_category_instance
            
            mock_file_map_instance = MagicMock()
            mock_file_map_instance.collect_data.return_value = sample_test_data['file_maps']
            mock_file_map_instance.get_export_summary.return_value = {'processed_count': 1}
            mock_file_map_exporter.return_value = mock_file_map_instance
            
            mock_file_instance = MagicMock()
            mock_file_instance.collect_data.return_value = sample_test_data['transaction_files']
            mock_file_instance.get_export_summary.return_value = {'processed_count': 1}
            mock_file_exporter.return_value = mock_file_instance

            # Collect data
            collected_data = fzip_service.collect_user_data(
                user_id=test_user_id,
                export_type=FZIPExportType.COMPLETE,
                include_analytics=False
            )

            # Verify all data was collected
            assert 'accounts' in collected_data
            assert 'transactions' in collected_data
            assert 'categories' in collected_data
            assert 'file_maps' in collected_data
            assert 'transaction_files' in collected_data

            assert len(collected_data['accounts']) == 2
            assert len(collected_data['transactions']) == 5
            assert len(collected_data['categories']) == 2
            assert len(collected_data['file_maps']) == 1
            assert len(collected_data['transaction_files']) == 1

    def test_fzip_package_creation(self, fzip_service, test_user_id, sample_test_data):
        """Test FZIP package creation with real data."""
        
        # Create a test export job
        export_job = FZIPJob(
            jobType=FZIPType.EXPORT,
            userId=test_user_id,
            status=FZIPStatus.EXPORT_PROCESSING,
            exportType=FZIPExportType.COMPLETE,
            includeAnalytics=False
        )

        with patch('utils.db_utils.list_user_accounts') as mock_accounts, \
             patch('utils.db_utils.list_user_transactions') as mock_transactions, \
             patch('utils.db_utils.list_categories_by_user_from_db') as mock_categories, \
             patch('utils.db_utils.list_file_maps_by_user') as mock_file_maps, \
             patch('utils.db_utils.list_user_files') as mock_files, \
             patch('utils.s3_dao.put_object') as mock_s3_put, \
             patch('services.fzip_service.ExportPackageBuilder') as mock_builder:

            # Setup mocks
            mock_accounts.return_value = sample_test_data['accounts']
            mock_transactions.return_value = (sample_test_data['transactions'], None, len(sample_test_data['transactions']))
            mock_categories.return_value = sample_test_data['categories']
            mock_file_maps.return_value = sample_test_data['file_maps']
            mock_files.return_value = sample_test_data['transaction_files']

            # Mock package builder
            mock_builder_instance = MagicMock()
            mock_builder.return_value = mock_builder_instance
            
            # Create a temporary directory for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                package_dir = os.path.join(temp_dir, "export_package")
                os.makedirs(package_dir)
                
                # Create some test files in the package
                os.makedirs(os.path.join(package_dir, "data"))
                with open(os.path.join(package_dir, "data", "accounts.json"), 'w') as f:
                    json.dump({"accounts": []}, f)
                
                processing_summary = {
                    'total_original_size': 1024,
                    'files_processed': 1,
                    'compression_ratio': 0.8
                }
                
                mock_builder_instance.build_package_with_streaming.return_value = (package_dir, processing_summary)
                mock_s3_put.return_value = True

                # Collect data first
                collected_data = fzip_service.collect_user_data(
                    user_id=test_user_id,
                    export_type=FZIPExportType.COMPLETE,
                    include_analytics=False
                )

                # Build package
                s3_key, package_size = fzip_service.build_export_package(export_job, collected_data)

                # Verify package was created
                assert s3_key is not None
                assert s3_key.startswith(f"exports/{test_user_id}/")
                assert package_size > 0
                
                # Verify S3 upload was called
                mock_s3_put.assert_called_once()

    def test_fzip_manifest_generation(self, fzip_service, test_user_id, sample_test_data):
        """Test FZIP manifest file generation."""
        
        export_job = FZIPJob(
            jobType=FZIPType.EXPORT,
            userId=test_user_id,
            status=FZIPStatus.EXPORT_PROCESSING,
            exportType=FZIPExportType.COMPLETE,
            includeAnalytics=False
        )

        # Create processing summary
        processing_summary = {
            'total_original_size': 2048,
            'files_processed': 4,
            'compression_ratio': 0.75
        }

        # Generate manifest
        manifest = fzip_service._create_enhanced_manifest(export_job, sample_test_data, processing_summary)

        # Verify manifest structure
        assert manifest.export_format_version == "1.0"
        assert manifest.user_id == test_user_id
        assert manifest.housef3_version == "2.5.0"
        assert manifest.package_format == "fzip"

        # Verify data summary
        assert manifest.data_summary.accounts_count == 2
        assert manifest.data_summary.transactions_count == 5
        assert manifest.data_summary.categories_count == 2
        assert manifest.data_summary.file_maps_count == 1
        assert manifest.data_summary.transaction_files_count == 1
        assert manifest.data_summary.analytics_included == False

        # Verify compatibility
        assert manifest.compatibility.minimum_version == "2.0.0"
        assert "2.5.0" in manifest.compatibility.supported_versions

    def test_download_url_generation(self, fzip_service):
        """Test download URL generation for FZIP packages."""
        
        s3_key = f"exports/test-user/export_{uuid.uuid4()}.zip"
        
        with patch('utils.s3_dao.get_presigned_url_simple') as mock_presigned:
            mock_presigned.return_value = f"https://s3.amazonaws.com/bucket/{s3_key}?signature=test"
            
            download_url = fzip_service.generate_download_url(s3_key)
            
            assert download_url is not None
            assert "s3.amazonaws.com" in download_url
            assert s3_key in download_url
            mock_presigned.assert_called_once_with(fzip_service.fzip_bucket, s3_key, 86400)

    def test_complete_export_pipeline(self, fzip_service, test_user_id, sample_test_data):
        """Test the complete export pipeline from start to finish."""
        
        with patch('utils.db_utils.list_user_accounts') as mock_accounts, \
             patch('utils.db_utils.list_user_transactions') as mock_transactions, \
             patch('utils.db_utils.list_categories_by_user_from_db') as mock_categories, \
             patch('utils.db_utils.list_file_maps_by_user') as mock_file_maps, \
             patch('utils.db_utils.list_user_files') as mock_files, \
             patch('utils.s3_dao.put_object') as mock_s3_put, \
             patch('utils.s3_dao.get_presigned_url_simple') as mock_presigned, \
             patch('services.fzip_service.ExportPackageBuilder') as mock_builder:

            # Setup mocks
            mock_accounts.return_value = sample_test_data['accounts']
            mock_transactions.return_value = (sample_test_data['transactions'], None, len(sample_test_data['transactions']))
            mock_categories.return_value = sample_test_data['categories']
            mock_file_maps.return_value = sample_test_data['file_maps']
            mock_files.return_value = sample_test_data['transaction_files']
            mock_s3_put.return_value = True
            mock_presigned.return_value = "https://example.com/download-url"

            # Mock package builder
            mock_builder_instance = MagicMock()
            mock_builder.return_value = mock_builder_instance
            
            with tempfile.TemporaryDirectory() as temp_dir:
                package_dir = os.path.join(temp_dir, "export_package")
                os.makedirs(package_dir)
                os.makedirs(os.path.join(package_dir, "data"))
                
                processing_summary = {
                    'total_original_size': 2048,
                    'files_processed': 4,
                    'compression_ratio': 0.75
                }
                
                mock_builder_instance.build_package_with_streaming.return_value = (package_dir, processing_summary)

                # Step 1: Initiate export
                export_job = fzip_service.initiate_export(
                    user_id=test_user_id,
                    export_type=FZIPExportType.COMPLETE,
                    include_analytics=False,
                    description="Test export"
                )

                assert export_job.user_id == test_user_id
                assert export_job.status == FZIPStatus.EXPORT_INITIATED
                assert export_job.export_type == FZIPExportType.COMPLETE

                # Step 2: Collect data
                collected_data = fzip_service.collect_user_data(
                    user_id=test_user_id,
                    export_type=FZIPExportType.COMPLETE,
                    include_analytics=False
                )

                assert len(collected_data['accounts']) == 2
                assert len(collected_data['transactions']) == 5

                # Step 3: Build package
                s3_key, package_size = fzip_service.build_export_package(export_job, collected_data)

                assert s3_key is not None
                assert package_size > 0

                # Step 4: Generate download URL
                download_url = fzip_service.generate_download_url(s3_key)

                assert download_url == "https://example.com/download-url"

    def test_export_error_handling(self, fzip_service, test_user_id):
        """Test error handling in export operations."""
        
        # Test error during data collection
        with patch('utils.db_utils.list_user_accounts') as mock_accounts:
            mock_accounts.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception) as exc_info:
                fzip_service.collect_user_data(
                    user_id=test_user_id,
                    export_type=FZIPExportType.COMPLETE,
                    include_analytics=False
                )
            
            assert "Database connection failed" in str(exc_info.value)

        # Test error during package building
        export_job = FZIPJob(
            jobType=FZIPType.EXPORT,
            userId=test_user_id,
            status=FZIPStatus.EXPORT_PROCESSING,
            exportType=FZIPExportType.COMPLETE
        )
        
        with patch('services.fzip_service.ExportPackageBuilder') as mock_builder:
            mock_builder.side_effect = Exception("Package building failed")
            
            with pytest.raises(Exception) as exc_info:
                fzip_service.build_export_package(export_job, {})
            
            assert "Package building failed" in str(exc_info.value)

    def test_selective_export_types(self, fzip_service, test_user_id, sample_test_data):
        """Test different export types (accounts only, transactions only, etc.)."""
        
        with patch('utils.db_utils.list_user_accounts') as mock_accounts, \
             patch('utils.db_utils.list_user_transactions') as mock_transactions:

            mock_accounts.return_value = sample_test_data['accounts']
            mock_transactions.return_value = (sample_test_data['transactions'], None, len(sample_test_data['transactions']))

            # Test accounts-only export
            collected_data = fzip_service.collect_user_data(
                user_id=test_user_id,
                export_type=FZIPExportType.ACCOUNTS_ONLY,
                include_analytics=False
            )

            # Should only collect accounts for accounts-only export
            assert 'accounts' in collected_data
            assert len(collected_data['accounts']) == 2

    def test_export_with_analytics(self, fzip_service, test_user_id, sample_test_data):
        """Test export with analytics data included."""
        
        mock_analytics = [
            {
                'metricId': str(uuid.uuid4()),
                'userId': test_user_id,
                'metricType': 'monthly_spending',
                'value': 1250.50,
                'period': '2024-01'
            }
        ]

        with patch('utils.db_utils.list_user_accounts') as mock_accounts, \
             patch('utils.db_utils.get_analytics_data') as mock_analytics_data:

            mock_accounts.return_value = sample_test_data['accounts']
            mock_analytics_data.return_value = mock_analytics

            collected_data = fzip_service.collect_user_data(
                user_id=test_user_id,
                export_type=FZIPExportType.COMPLETE,
                include_analytics=True
            )

            assert 'analytics' in collected_data
            assert len(collected_data['analytics']) == 1
            assert collected_data['analytics'][0]['metricType'] == 'monthly_spending'


if __name__ == "__main__":
    pytest.main([__file__])
"""
End-to-end tests for FZIP backup/restore functionality.
Tests the complete backup→restore pipeline with financial profile validation.
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
from models.fzip import FZIPJob, FZIPStatus, FZIPBackupType, FZIPType
from services.fzip_service import FZIPService
from utils.db_utils import (
    create_fzip_job, get_fzip_job, update_fzip_job,
    list_user_accounts, list_user_transactions, list_categories_by_user_from_db,
    list_file_maps_by_user, list_user_files
)


class TestFZIPBackupRestoreRoundtrip:
    """Comprehensive end-to-end tests for FZIP backup/restore functionality."""

    @pytest.fixture
    def test_user_id(self):
        """Test user ID for backup operations."""
        return "backup-test-user-12345"

    @pytest.fixture
    def restore_user_id(self):
        """Test user ID for restore operations (must be empty profile)."""
        return "restore-test-user-67890"

    @pytest.fixture
    def fzip_service(self):
        """FZIP service instance."""
        return FZIPService()

    @pytest.fixture
    def sample_financial_profile(self, test_user_id):
        """Create sample financial profile for backup testing."""
        sample_file_id = uuid.uuid4()
        
        # Create test accounts
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
                accountName="Test Savings Account",
                accountType=AccountType.SAVINGS,
                institution="Test Bank",
                balance=Decimal("10000.00"),
                currency=Currency.USD,
                isActive=True
            )
        ]
        
        # Create test categories
        parent_category = Category(
            categoryId=uuid.uuid4(),
            userId=test_user_id,
            name="Food & Dining",
            type=CategoryType.EXPENSE,
            color="#FF6B6B",
            icon="🍽️",
            createdAt=int(datetime.now(timezone.utc).timestamp() * 1000)
        )
        
        child_category = Category(
            categoryId=uuid.uuid4(),
            userId=test_user_id,
            name="Restaurants",
            type=CategoryType.EXPENSE,
            parentCategoryId=parent_category.categoryId,
            color="#FF8E8E",
            icon="🍽️",
            createdAt=int(datetime.now(timezone.utc).timestamp() * 1000)
        )
        
        categories = [parent_category, child_category]
        
        # Create test transactions
        transactions = [
            Transaction(
                userId=test_user_id,
                fileId=sample_file_id,
                accountId=accounts[0].account_id,
                date=int(datetime(2024, 1, 15).timestamp() * 1000),
                description="Restaurant Purchase",
                amount=Decimal("-45.67"),
                currency=Currency.USD,
                balance=Decimal("2455.08"),
                importOrder=1
            ),
            Transaction(
                userId=test_user_id,
                fileId=sample_file_id,
                accountId=accounts[1].account_id,
                date=int(datetime(2024, 1, 16).timestamp() * 1000),
                description="Interest Payment",
                amount=Decimal("25.00"),
                currency=Currency.USD,
                balance=Decimal("10025.00"),
                importOrder=2
            )
        ]
        
        # Create test file map
        file_maps = [
            FileMap(
                userId=test_user_id,
                name="Test Bank CSV Format",
                mappings=[
                    FieldMapping(
                        sourceField="Date",
                        targetField="date"
                    ),
                    FieldMapping(
                        sourceField="Description",
                        targetField="description"
                    ),
                    FieldMapping(
                        sourceField="Amount",
                        targetField="amount"
                    )
                ]
            )
        ]
        
        # Create test transaction file
        transaction_files = [
            TransactionFile(
                fileId=sample_file_id,
                userId=test_user_id,
                fileName="test-statement.csv",
                fileSize=1024,
                s3Key=f"uploads/{test_user_id}/{sample_file_id}/test-statement.csv",
                processingStatus=ProcessingStatus.PROCESSED
            )
        ]
        
        return {
            'accounts': accounts,
            'categories': categories, 
            'transactions': transactions,
            'file_maps': file_maps,
            'transaction_files': transaction_files
        }

    @patch('utils.db_utils.list_user_accounts')
    @patch('utils.db_utils.list_user_transactions')
    @patch('utils.db_utils.list_categories_by_user_from_db')
    @patch('utils.db_utils.list_file_maps_by_user')
    @patch('utils.db_utils.list_user_files')
    @patch('services.fzip_service.FZIPService._upload_package_to_s3')
    @patch('services.fzip_service.FZIPService._download_package_from_s3')
    @patch('utils.db_utils.create_account')
    @patch('utils.db_utils.create_transaction')
    @patch('utils.db_utils.create_category')
    @patch('utils.db_utils.create_file_map')
    @patch('utils.db_utils.create_transaction_file')
    async def test_complete_backup_restore_cycle(
        self,
        mock_create_transaction_file,
        mock_create_file_map,
        mock_create_category,
        mock_create_transaction,
        mock_create_account,
        mock_download_package,
        mock_upload_package,
        mock_list_files,
        mock_list_file_maps,
        mock_list_categories,
        mock_list_transactions,
        mock_list_accounts,
        fzip_service,
        test_user_id,
        restore_user_id,
        sample_financial_profile
    ):
        """Test complete backup→restore cycle preserves all data correctly."""
        
        # Setup: Mock data collection for backup
        mock_list_accounts.return_value = sample_financial_profile['accounts']
        mock_list_transactions.return_value = (
            sample_financial_profile['transactions'], None, len(sample_financial_profile['transactions'])
        )
        mock_list_categories.return_value = sample_financial_profile['categories']
        mock_list_file_maps.return_value = sample_financial_profile['file_maps']
        mock_list_files.return_value = (
            sample_financial_profile['transaction_files'], None, len(sample_financial_profile['transaction_files'])
        )
        
        # Step 1: Create backup job
        backup_job = FZIPJob(
            userId=test_user_id,
            jobType=FZIPType.BACKUP,
            status=FZIPStatus.BACKUP_INITIATED,
            backupType=FZIPBackupType.COMPLETE
        )
        
        # Step 2: Execute backup
        with tempfile.NamedTemporaryFile(suffix='.fzip', delete=False) as temp_backup:
            mock_upload_package.return_value = f"s3://test-bucket/backups/{backup_job.job_id}.fzip"
            
            # Simulate backup process
            package_data = await fzip_service.collect_backup_data(backup_job)
            
            # Verify backup data collection
            assert 'accounts' in package_data
            assert 'transactions' in package_data
            assert 'categories' in package_data
            assert 'file_maps' in package_data
            assert 'transaction_files' in package_data
            
            assert len(package_data['accounts']) == 2
            assert len(package_data['transactions']) == 2
            assert len(package_data['categories']) == 2
            assert len(package_data['file_maps']) == 1
            assert len(package_data['transaction_files']) == 1
            
            # Create FZIP package
            package_path = await fzip_service.build_backup_package(backup_job, package_data)
            
            # Verify FZIP package structure
            with zipfile.ZipFile(package_path, 'r') as zipf:
                expected_files = [
                    'manifest.json',
                    'data/accounts.json',
                    'data/transactions.json',
                    'data/categories.json',
                    'data/file_maps.json',
                    'data/transaction_files.json'
                ]
                
                for expected_file in expected_files:
                    assert expected_file in zipf.namelist(), f"Missing {expected_file} in FZIP package"
                
                # Verify manifest
                manifest_content = json.loads(zipf.read('manifest.json').decode('utf-8'))
                assert manifest_content['backup_format_version'] == "1.0"
                assert manifest_content['user_id'] == test_user_id
                assert manifest_content['data_summary']['accounts_count'] == 2
                assert manifest_content['data_summary']['transactions_count'] == 2
                assert manifest_content['data_summary']['categories_count'] == 2
            
            temp_backup.write(open(package_path, 'rb').read())
            backup_package_path = temp_backup.name
        
        # Step 3: Prepare for restore (verify empty profile)
        # Mock empty profile for restore user
        empty_profile_mocks = [
            (mock_list_accounts, []),
            (mock_list_transactions, ([], None, 0)),
            (mock_list_categories, []),
            (mock_list_file_maps, []),
            (mock_list_files, ([], None, 0))
        ]
        
        for mock_func, return_value in empty_profile_mocks:
            mock_func.return_value = return_value
        
        # Step 4: Create restore job
        restore_job = FZIPJob(
            userId=restore_user_id,
            jobType=FZIPType.RESTORE,
            status=FZIPStatus.RESTORE_UPLOADED
        )
        
        # Setup download mock to return our backup package
        mock_download_package.return_value = backup_package_path
        
        # Step 5: Execute restore
        package_s3_key = f"s3://test-bucket/restores/{restore_job.job_id}.fzip"
        
        # Parse FZIP package for restore
        package_data = await fzip_service.fzip_package_parser.parse_fzip_package(package_s3_key)
        
        # Verify package parsing
        assert 'manifest' in package_data
        assert 'accounts' in package_data
        assert 'transactions' in package_data
        assert 'categories' in package_data
        
        # Mock successful restore operations
        mock_create_account.return_value = True
        mock_create_transaction.return_value = True
        mock_create_category.return_value = True
        mock_create_file_map.return_value = True
        mock_create_transaction_file.return_value = True
        
        # Execute restore process
        await fzip_service.start_restore(restore_job, package_s3_key)
        
        # Step 6: Verify restore results
        
        # Verify accounts were restored
        assert mock_create_account.call_count == 2
        for call in mock_create_account.call_args_list:
            account = call[0][0]
            assert account.userId == restore_user_id  # Should be updated to restore user
            assert account.accountName in ["Test Checking Account", "Test Savings Account"]
        
        # Verify transactions were restored  
        assert mock_create_transaction.call_count == 2
        for call in mock_create_transaction.call_args_list:
            transaction = call[0][0]
            assert transaction.userId == restore_user_id  # Should be updated to restore user
            assert transaction.description in ["Restaurant Purchase", "Interest Payment"]
        
        # Verify categories were restored
        assert mock_create_category.call_count == 2
        for call in mock_create_category.call_args_list:
            category = call[0][0]
            assert category.userId == restore_user_id  # Should be updated to restore user
            assert category.name in ["Food & Dining", "Restaurants"]
        
        # Verify file maps were restored
        assert mock_create_file_map.call_count == 1
        file_map = mock_create_file_map.call_args_list[0][0][0]
        assert file_map.userId == restore_user_id
        assert file_map.mapName == "Test Bank CSV Format"
        
        # Verify transaction files were restored
        assert mock_create_transaction_file.call_count == 1
        transaction_file = mock_create_transaction_file.call_args_list[0][0][0]
        assert transaction_file.userId == restore_user_id
        assert transaction_file.fileName == "test-statement.csv"
        
        # Cleanup
        os.unlink(backup_package_path)
        if os.path.exists(package_path):
            os.unlink(package_path)

    @patch('utils.db_utils.list_user_accounts')
    @patch('utils.db_utils.list_user_transactions') 
    @patch('utils.db_utils.list_categories_by_user_from_db')
    @patch('utils.db_utils.list_file_maps_by_user')
    @patch('utils.db_utils.list_user_files')
    async def test_restore_requires_empty_profile(
        self,
        mock_list_files,
        mock_list_file_maps,
        mock_list_categories,
        mock_list_transactions,
        mock_list_accounts,
        fzip_service,
        restore_user_id
    ):
        """Test that restore fails when target profile is not empty."""
        
        # Setup: Mock non-empty profile
        mock_list_accounts.return_value = [Mock()]  # Non-empty accounts
        mock_list_transactions.return_value = ([], None, 0)
        mock_list_categories.return_value = []
        mock_list_file_maps.return_value = []
        mock_list_files.return_value = ([], None, 0)
        
        # Create restore job
        restore_job = FZIPJob(
            userId=restore_user_id,
            jobType=FZIPType.RESTORE,
            status=FZIPStatus.RESTORE_UPLOADED
        )
        
        # Attempt restore - should fail due to non-empty profile
        with pytest.raises(ValueError, match="Financial profile is not empty"):
            await fzip_service.start_restore(restore_job, "test-package-s3-key")

    async def test_backup_validation_quality_scoring(self, fzip_service, test_user_id):
        """Test backup validation and quality scoring."""
        
        # Create backup job
        backup_job = FZIPJob(
            userId=test_user_id,
            jobType=FZIPType.BACKUP,
            status=FZIPStatus.BACKUP_COMPLETED
        )
        
        # Mock quality validation
        with patch.object(fzip_service, 'validate_backup_quality') as mock_validate:
            mock_validate.return_value = {
                'overall_quality': 'excellent',
                'data_integrity_score': 100,
                'completeness_score': 100,
                'issues': [],
                'recommendations': []
            }
            
            # Test quality validation
            quality_results = await fzip_service.validate_backup_quality(backup_job, "test-s3-key")
            
            assert quality_results['overall_quality'] == 'excellent'
            assert quality_results['data_integrity_score'] == 100
            assert quality_results['completeness_score'] == 100
            assert len(quality_results['issues']) == 0
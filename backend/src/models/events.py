"""
Event models for the event-driven architecture.
Contains base event structure and specific event types for all data state changes.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json


@dataclass
class BaseEvent:
    """Base event structure for all events in the system"""
    event_id: str
    event_type: str
    event_version: str
    timestamp: int  # Unix timestamp in milliseconds
    source: str
    user_id: str
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_eventbridge_format(self) -> Dict[str, Any]:
        """Convert to EventBridge event format"""
        return {
            'Source': self.source,
            'DetailType': self.event_type,
            'Detail': json.dumps({
                'eventId': self.event_id,
                'eventVersion': self.event_version,
                'timestamp': self.timestamp,
                'userId': self.user_id,
                'correlationId': self.correlation_id,
                'causationId': self.causation_id,
                'data': self.data or {},
                'metadata': self.metadata or {}
            })
        }


# =============================================================================
# FILE PROCESSING EVENTS
# =============================================================================

@dataclass
class FileUploadedEvent(BaseEvent):
    """Published when a file is uploaded to S3"""
    
    def __init__(self, user_id: str, file_id: str, file_name: str, 
                 file_size: int, s3_key: str, account_id: Optional[str] = None, 
                 file_format: Optional[str] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='file.uploaded',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='transaction.service',
            user_id=user_id,
            data={
                'fileId': file_id,
                'fileName': file_name,
                'fileSize': file_size,
                's3Key': s3_key,
                'accountId': account_id,
                'fileFormat': file_format,
                **kwargs
            }
        )


@dataclass
class FileProcessedEvent(BaseEvent):
    """Published when file processing completes"""
    
    def __init__(self, user_id: str, file_id: str, account_id: str, 
                 transaction_count: int, duplicate_count: int, 
                 processing_status: str = 'success', error_message: Optional[str] = None,
                 date_range: Optional[Dict[str, str]] = None, 
                 transaction_ids: Optional[List[str]] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='file.processed',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='transaction.service',
            user_id=user_id,
            data={
                'fileId': file_id,
                'accountId': account_id,
                'transactionCount': transaction_count,
                'duplicateCount': duplicate_count,
                'processingStatus': processing_status,
                'errorMessage': error_message,
                'dateRange': date_range,
                'transactionIds': transaction_ids or [],
                **kwargs
            }
        )


@dataclass
class FileAssociatedEvent(BaseEvent):
    """Published when file is associated with an account"""
    
    def __init__(self, user_id: str, file_id: str, account_id: str, 
                 previous_account_id: Optional[str] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='file.associated',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='transaction.service',
            user_id=user_id,
            data={
                'fileId': file_id,
                'accountId': account_id,
                'previousAccountId': previous_account_id,
                **kwargs
            }
        )


# =============================================================================
# TRANSACTION EVENTS
# =============================================================================




@dataclass 
class TransactionUpdatedEvent(BaseEvent):
    """Published when a transaction is manually edited"""
    
    def __init__(self, user_id: str, transaction_id: str, account_id: str, 
                 changes: List[Dict[str, Any]], **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='transaction.updated',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='transaction.service',
            user_id=user_id,
            data={
                'transactionId': transaction_id,
                'accountId': account_id,
                'changes': changes,
                **kwargs
            }
        )


@dataclass
class TransactionsDeletedEvent(BaseEvent):
    """Published when transactions are deleted"""
    
    def __init__(self, user_id: str, transaction_ids: List[str], 
                 account_ids: List[str], deletion_type: str, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='transactions.deleted',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='transaction.service',
            user_id=user_id,
            data={
                'transactionIds': transaction_ids,
                'accountIds': account_ids,
                'deletionType': deletion_type,  # 'single', 'bulk', 'file_reprocessing'
                **kwargs
            }
        )


@dataclass
class TransactionCategorizedEvent(BaseEvent):
    """Published when transaction categorization changes"""
    
    def __init__(self, user_id: str, transaction_id: str, account_id: str,
                 category_id: str, confidence: int, assignment_type: str,
                 previous_category_id: Optional[str] = None, 
                 rule_id: Optional[str] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='transaction.categorized',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='transaction.service',
            user_id=user_id,
            data={
                'transactionId': transaction_id,
                'accountId': account_id,
                'categoryId': category_id,
                'previousCategoryId': previous_category_id,
                'confidence': confidence,
                'assignmentType': assignment_type,  # 'manual', 'rule_based', 'suggested'
                'ruleId': rule_id,
                **kwargs
            }
        )


# =============================================================================
# ACCOUNT EVENTS
# =============================================================================

@dataclass
class AccountCreatedEvent(BaseEvent):
    """Published when account is created"""
    
    def __init__(self, user_id: str, account_id: str, account_name: str, 
                 account_type: str, currency: Optional[str] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='account.created',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='account.service',
            user_id=user_id,
            data={
                'accountId': account_id,
                'accountName': account_name,
                'accountType': account_type,
                'currency': currency ,
                **kwargs
            }
        )


@dataclass
class AccountUpdatedEvent(BaseEvent):
    """Published when account is updated"""
    
    def __init__(self, user_id: str, account_id: str, 
                 changes: List[Dict[str, Any]], **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='account.updated',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='account.service',
            user_id=user_id,
            data={
                'accountId': account_id,
                'changes': changes,
                **kwargs
            }
        )


@dataclass
class AccountDeletedEvent(BaseEvent):
    """Published when account is deleted"""
    
    def __init__(self, user_id: str, account_id: str, transaction_count: int, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='account.deleted',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='account.service',
            user_id=user_id,
            data={
                'accountId': account_id,
                'transactionCount': transaction_count,
                **kwargs
            }
        )


# =============================================================================
# CATEGORY EVENTS
# =============================================================================

@dataclass
class CategoryRulesAppliedEvent(BaseEvent):
    """Published when category rules are applied to transactions"""
    
    def __init__(self, user_id: str, category_id: str, rule_ids: List[str],
                 transaction_ids: List[str], application_type: str, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='category.rules_applied',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='category.service',
            user_id=user_id,
            data={
                'categoryId': category_id,
                'ruleIds': rule_ids,
                'transactionIds': transaction_ids,
                'applicationType': application_type,  # 'manual', 'bulk', 'automated'
                **kwargs
            }
        )


@dataclass
class CategoryRuleCreatedEvent(BaseEvent):
    """Published when a new category rule is created"""
    
    def __init__(self, user_id: str, category_id: str, rule_id: str,
                 rule_pattern: str, auto_apply: bool, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='category.rule_created',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='category.service',
            user_id=user_id,
            data={
                'categoryId': category_id,
                'ruleId': rule_id,
                'rulePattern': rule_pattern,
                'autoApply': auto_apply,
                **kwargs
            }
        )


# =============================================================================
# EXPORT/IMPORT EVENTS
# =============================================================================

@dataclass
class ExportInitiatedEvent(BaseEvent):
    """Published when an export job is initiated"""
    
    def __init__(self, user_id: str, export_id: str, export_type: str,
                 include_analytics: bool = False, description: Optional[str] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='export.initiated',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='export.service',
            user_id=user_id,
            data={
                'exportId': export_id,
                'exportType': export_type,
                'includeAnalytics': include_analytics,
                'description': description,
                **kwargs
            }
        )


@dataclass
class ExportCompletedEvent(BaseEvent):
    """Published when an export job is completed successfully"""
    
    def __init__(self, user_id: str, export_id: str, export_type: str,
                 package_size: int, download_url: str, s3_key: str,
                 data_summary: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='export.completed',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='export.service',
            user_id=user_id,
            data={
                'exportId': export_id,
                'exportType': export_type,
                'packageSize': package_size,
                'downloadUrl': download_url,
                's3Key': s3_key,
                'dataSummary': data_summary,
                **kwargs
            }
        )


@dataclass
class ExportFailedEvent(BaseEvent):
    """Published when an export job fails"""
    
    def __init__(self, user_id: str, export_id: str, export_type: str,
                 error: str, error_details: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='export.failed',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='export.service',
            user_id=user_id,
            data={
                'exportId': export_id,
                'exportType': export_type,
                'error': error,
                'errorDetails': error_details,
                **kwargs
            }
        )



# =============================================================================
# FZIP BACKUP/RESTORE EVENTS
# =============================================================================

@dataclass
class BackupInitiatedEvent(BaseEvent):
    """Published when a backup job is initiated"""

    def __init__(self, user_id: str, backup_id: str,
                 description: Optional[str] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='backup.initiated',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='fzip.service',
            user_id=user_id,
            data={
                'backupId': backup_id,
                'description': description,
                **kwargs
            }
        )


@dataclass
class BackupCompletedEvent(BaseEvent):
    """Published when a backup job is completed successfully"""

    def __init__(self, user_id: str, backup_id: str, package_size: int,
                 s3_key: str, data_summary: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='backup.completed',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='fzip.service',
            user_id=user_id,
            data={
                'backupId': backup_id,
                'packageSize': package_size,
                's3Key': s3_key,
                'dataSummary': data_summary,
                **kwargs
            }
        )


@dataclass
class BackupFailedEvent(BaseEvent):
    """Published when a backup job fails"""

    def __init__(self, user_id: str, backup_id: str, error: str,
                 error_details: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='backup.failed',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='fzip.service',
            user_id=user_id,
            data={
                'backupId': backup_id,
                'error': error,
                'errorDetails': error_details,
                **kwargs
            }
        )


@dataclass
class RestoreInitiatedEvent(BaseEvent):
    """Published when a restore job is initiated"""

    def __init__(self, user_id: str, restore_id: str, backup_id: str,
                 s3_key: str, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='restore.initiated',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='fzip.service',
            user_id=user_id,
            data={
                'restoreId': restore_id,
                'backupId': backup_id,
                's3Key': s3_key,
                **kwargs
            }
        )


@dataclass
class RestoreCompletedEvent(BaseEvent):
    """Published when a restore job is completed successfully"""

    def __init__(self, user_id: str, restore_id: str, backup_id: str,
                 data_summary: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='restore.completed',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='fzip.service',
            user_id=user_id,
            data={
                'restoreId': restore_id,
                'backupId': backup_id,
                'dataSummary': data_summary,
                **kwargs
            }
        )


@dataclass
class RestoreFailedEvent(BaseEvent):
    """Published when a restore job fails"""

    def __init__(self, user_id: str, restore_id: str, backup_id: str,
                 error: str, error_details: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type='restore.failed',
            event_version='1.0',
            timestamp=int(datetime.now().timestamp() * 1000),
            source='fzip.service',
            user_id=user_id,
            data={
                'restoreId': restore_id,
                'backupId': backup_id,
                'error': error,
                'errorDetails': error_details,
                **kwargs
            }
        )



# =============================================================================
# EVENT FACTORY FUNCTIONS
# =============================================================================

def create_file_uploaded_event(user_id: str, file_metadata: Dict[str, Any]) -> FileUploadedEvent:
    """Factory function to create FileUploadedEvent from file metadata"""
    return FileUploadedEvent(
        user_id=user_id,
        file_id=file_metadata.get('fileId', ''),
        file_name=file_metadata.get('fileName', ''),
        file_size=file_metadata.get('fileSize', 0),
        s3_key=file_metadata.get('s3Key', ''),
        account_id=file_metadata.get('accountId'),
        file_format=file_metadata.get('fileFormat')
    )


def create_file_processed_event(user_id: str, processing_result: Dict[str, Any]) -> FileProcessedEvent:
    """Factory function to create FileProcessedEvent from processing result"""
    return FileProcessedEvent(
        user_id=user_id,
        file_id=processing_result.get('fileId', ''),
        account_id=processing_result.get('accountId', ''),
        transaction_count=processing_result.get('transactionCount', 0),
        duplicate_count=processing_result.get('duplicateCount', 0),
        processing_status=processing_result.get('processingStatus', 'success'),
        error_message=processing_result.get('errorMessage'),
        date_range=processing_result.get('dateRange')
    )


def create_file_processed_event_with_transactions(user_id: str, file_id: str, account_id: str, 
                                               transactions: List[Any], duplicate_count: int = 0) -> FileProcessedEvent:
    """Factory function to create FileProcessedEvent with transaction details"""
    transaction_ids = [str(tx.transaction_id) for tx in transactions]
    
    # Calculate date range
    dates = [tx.date for tx in transactions if tx.date]
    date_range = None
    if dates:
        min_date = min(dates)
        max_date = max(dates)
        date_range = {
            'startDate': datetime.fromtimestamp(min_date / 1000).isoformat(),
            'endDate': datetime.fromtimestamp(max_date / 1000).isoformat()
        }
    
    return FileProcessedEvent(
        user_id=user_id,
        file_id=file_id,
        account_id=account_id,
        transaction_count=len(transactions),
        duplicate_count=duplicate_count,
        processing_status='success',
        date_range=date_range,
        transaction_ids=transaction_ids
    ) 
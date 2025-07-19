"""
Export Data Processors for the import/export system.
Contains specialized exporter classes for each entity type with enhanced processing capabilities.
"""
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Union
from decimal import Decimal

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

logger = logging.getLogger(__name__)


class ExportException(Exception):
    """Custom exception for export processing errors"""
    def __init__(self, message: str, entity_type: str, error_details: Optional[Dict[str, Any]] = None):
        self.entity_type = entity_type
        self.error_details = error_details or {}
        super().__init__(message)


class BaseExporter(ABC):
    """Base class for all entity exporters"""
    
    def __init__(self, user_id: str, batch_size: int = 1000):
        self.user_id = user_id
        self.batch_size = batch_size
        self.processed_count = 0
        self.error_count = 0
        self.warnings = []
        
    @abstractmethod
    def collect_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Collect and process entity data"""
        pass
    
    @abstractmethod
    def serialize_entity(self, entity: Any) -> Dict[str, Any]:
        """Serialize a single entity for export"""
        pass
    
    def get_export_summary(self) -> Dict[str, Any]:
        """Get summary of export processing"""
        return {
            "entity_type": self.__class__.__name__.replace("Exporter", "").lower(),
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "warnings": self.warnings,
            "success_rate": (self.processed_count / (self.processed_count + self.error_count)) * 100 
                          if (self.processed_count + self.error_count) > 0 else 100
        }
    
    def _add_warning(self, message: str, entity_id: Optional[str] = None):
        """Add a warning to the warnings list"""
        warning = {
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entity_id": entity_id
        }
        self.warnings.append(warning)
        logger.warning(f"{self.__class__.__name__}: {message}")


class AccountExporter(BaseExporter):
    """Specialized exporter for account entities"""
    
    def collect_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Collect and process account data with optional filtering
        
        Args:
            filters: Optional filters including account_ids, include_inactive, etc.
            
        Returns:
            List of serialized account dictionaries
        """
        try:
            logger.info(f"Starting account data collection for user {self.user_id}")
            
            # Get all user accounts
            accounts = list_user_accounts(self.user_id)
            
            # Apply filters
            if filters:
                accounts = self._apply_filters(accounts, filters)
            
            # Process and serialize accounts
            serialized_accounts = []
            for account in accounts:
                try:
                    serialized_account = self.serialize_entity(account)
                    
                    # Add computed fields
                    serialized_account.update(self._add_computed_fields(account))
                    
                    serialized_accounts.append(serialized_account)
                    self.processed_count += 1
                    
                except Exception as e:
                    self.error_count += 1
                    self._add_warning(f"Failed to serialize account: {str(e)}", str(account.account_id))
                    logger.error(f"Error serializing account {account.account_id}: {str(e)}")
            
            logger.info(f"Account data collection complete: {self.processed_count} accounts processed, "
                       f"{self.error_count} errors")
            
            return serialized_accounts
            
        except Exception as e:
            logger.error(f"Failed to collect account data for user {self.user_id}: {str(e)}")
            raise ExportException(f"Account data collection failed: {str(e)}", "account")
    
    def serialize_entity(self, account: Account) -> Dict[str, Any]:
        """Serialize account with export-specific formatting"""
        try:
            # Get base serialization
            serialized = account.model_dump(by_alias=True, exclude_none=True)
            
            # Ensure decimal values are strings for JSON compatibility
            if 'balance' in serialized and serialized['balance'] is not None:
                serialized['balance'] = str(serialized['balance'])
            
            # Add metadata
            serialized['exportMetadata'] = {
                'exportedAt': datetime.now(timezone.utc).isoformat(),
                'dataVersion': '1.0'
            }
            
            return serialized
            
        except Exception as e:
            raise ExportException(f"Account serialization failed: {str(e)}", "account")
    
    def _apply_filters(self, accounts: List[Account], filters: Dict[str, Any]) -> List[Account]:
        """Apply filters to account list"""
        filtered = accounts
        
        # Filter by specific account IDs
        if filters.get('account_ids'):
            account_id_set = {str(aid) for aid in filters['account_ids']}
            filtered = [acc for acc in filtered if str(acc.account_id) in account_id_set]
        
        # Filter by active status
        if filters.get('include_inactive') is False:
            filtered = [acc for acc in filtered if acc.is_active]
        
        # Filter by account types
        if filters.get('account_types'):
            type_set = set(filters['account_types'])
            filtered = [acc for acc in filtered if acc.account_type.value in type_set]
        
        # Filter by institution
        if filters.get('institutions'):
            institution_set = set(filters['institutions'])
            filtered = [acc for acc in filtered 
                       if acc.institution and acc.institution in institution_set]
        
        return filtered
    
    def _add_computed_fields(self, account: Account) -> Dict[str, Any]:
        """Add computed fields to account export"""
        return {
            'computedFields': {
                'hasTransactions': True,  # Would need to check transaction count
                'isRecentlyActive': account.last_transaction_date and 
                                  account.last_transaction_date > (datetime.now(timezone.utc).timestamp() * 1000 - 30*24*60*60*1000),
                'accountAge': int((datetime.now(timezone.utc).timestamp() * 1000 - account.created_at) / (24*60*60*1000)) if account.created_at else 0
            }
        }


class TransactionExporter(BaseExporter):
    """Specialized exporter for transaction entities with advanced filtering and batch processing"""
    
    def __init__(self, user_id: str, batch_size: int = 1000):
        super().__init__(user_id, batch_size)
        self.total_amount = Decimal('0')
        self.date_range: Dict[str, Optional[int]] = {'earliest': None, 'latest': None}
        
    def collect_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Collect transaction data with pagination and filtering
        
        Args:
            filters: Filters including account_ids, date_range, categories, etc.
            
        Returns:
            List of serialized transaction dictionaries
        """
        try:
            logger.info(f"Starting transaction data collection for user {self.user_id}")
            
            serialized_transactions = []
            last_evaluated_key: Optional[Dict[str, Any]] = None
            
            while True:
                # Get batch of transactions
                transactions, pagination_key, _ = list_user_transactions(
                    self.user_id,
                    limit=self.batch_size,
                    last_evaluated_key=last_evaluated_key
                )
                
                if not transactions:
                    break
                
                # Apply filters to this batch
                if filters:
                    transactions = self._apply_filters(transactions, filters)
                
                # Process batch
                for transaction in transactions:
                    try:
                        serialized_transaction = self.serialize_entity(transaction)
                        serialized_transactions.append(serialized_transaction)
                        
                        # Update statistics
                        self._update_statistics(transaction)
                        self.processed_count += 1
                        
                    except Exception as e:
                        self.error_count += 1
                        self._add_warning(f"Failed to serialize transaction: {str(e)}", 
                                        str(transaction.transaction_id))
                
                # Check for more data
                if not pagination_key:
                    break
                last_evaluated_key = pagination_key
            
            # Sort by date (most recent first)
            serialized_transactions.sort(key=lambda t: t.get('date', 0), reverse=True)
            
            logger.info(f"Transaction data collection complete: {self.processed_count} transactions processed, "
                       f"{self.error_count} errors")
            
            return serialized_transactions
            
        except Exception as e:
            logger.error(f"Failed to collect transaction data for user {self.user_id}: {str(e)}")
            raise ExportException(f"Transaction data collection failed: {str(e)}", "transaction")
    
    def serialize_entity(self, transaction: Transaction) -> Dict[str, Any]:
        """Serialize transaction with export-specific formatting"""
        try:
            # Get base serialization
            serialized = transaction.model_dump(by_alias=True, exclude_none=True)
            
            # Ensure decimal values are strings
            for field in ['amount', 'balance']:
                if field in serialized and serialized[field] is not None:
                    serialized[field] = str(serialized[field])
            
            # Format date for readability
            if 'date' in serialized:
                try:
                    dt = datetime.fromtimestamp(serialized['date'] / 1000, tz=timezone.utc)
                    serialized['dateFormatted'] = dt.isoformat()
                except (ValueError, TypeError):
                    pass
            
            # Add category information if available
            if transaction.categories:
                serialized['categoryAssignments'] = [
                    {
                        'categoryId': str(cat.category_id),
                        'status': cat.status.value,
                        'confidence': cat.confidence,
                        'isManual': cat.is_manual,
                        'assignedAt': cat.assigned_at,
                        'ruleId': cat.rule_id
                    }
                    for cat in transaction.categories
                ]
            
            # Add export metadata
            serialized['exportMetadata'] = {
                'exportedAt': datetime.now(timezone.utc).isoformat(),
                'dataVersion': '1.0'
            }
            
            return serialized
            
        except Exception as e:
            raise ExportException(f"Transaction serialization failed: {str(e)}", "transaction")
    
    def _apply_filters(self, transactions: List[Transaction], filters: Dict[str, Any]) -> List[Transaction]:
        """Apply filters to transaction list"""
        filtered = transactions
        
        # Filter by account IDs
        if filters.get('account_ids'):
            account_id_set = {str(aid) for aid in filters['account_ids']}
            filtered = [tx for tx in filtered if str(tx.account_id) in account_id_set]
        
        # Filter by date range
        if filters.get('date_range_start') or filters.get('date_range_end'):
            start_date = filters.get('date_range_start', 0)
            end_date = filters.get('date_range_end', 9999999999999)
            filtered = [tx for tx in filtered if start_date <= tx.date <= end_date]
        
        # Filter by category IDs
        if filters.get('category_ids'):
            category_id_set = {str(cid) for cid in filters['category_ids']}
            filtered = [tx for tx in filtered 
                       if tx.primary_category_id and str(tx.primary_category_id) in category_id_set]
        
        # Filter by amount range
        if filters.get('amount_min') or filters.get('amount_max'):
            amount_min = Decimal(str(filters.get('amount_min', '-999999999')))
            amount_max = Decimal(str(filters.get('amount_max', '999999999')))
            filtered = [tx for tx in filtered if amount_min <= tx.amount <= amount_max]
        
        # Filter by transaction types
        if filters.get('transaction_types'):
            type_set = set(filters['transaction_types'])
            filtered = [tx for tx in filtered 
                       if tx.transaction_type and tx.transaction_type in type_set]
        
        return filtered
    
    def _update_statistics(self, transaction: Transaction):
        """Update collection statistics"""
        # Update total amount
        self.total_amount += transaction.amount
        
        # Update date range
        if self.date_range['earliest'] is None or transaction.date < self.date_range['earliest']:
            self.date_range['earliest'] = transaction.date
        if self.date_range['latest'] is None or transaction.date > self.date_range['latest']:
            self.date_range['latest'] = transaction.date
    
    def get_export_summary(self) -> Dict[str, Any]:
        """Get enhanced summary with transaction-specific statistics"""
        base_summary = super().get_export_summary()
        base_summary.update({
            'totalAmount': str(self.total_amount),
            'dateRange': {
                'earliest': datetime.fromtimestamp(self.date_range['earliest'] / 1000).isoformat() 
                           if self.date_range['earliest'] else None,
                'latest': datetime.fromtimestamp(self.date_range['latest'] / 1000).isoformat() 
                         if self.date_range['latest'] else None
            }
        })
        return base_summary


class CategoryExporter(BaseExporter):
    """Specialized exporter for category entities with hierarchy preservation"""
    
    def collect_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Collect category data preserving hierarchy relationships
        
        Args:
            filters: Optional filters including category_ids, include_rules, etc.
            
        Returns:
            List of serialized category dictionaries with hierarchy preserved
        """
        try:
            logger.info(f"Starting category data collection for user {self.user_id}")
            
            # Get all user categories
            categories = list_categories_by_user_from_db(self.user_id)
            
            # Apply filters
            if filters:
                categories = self._apply_filters(categories, filters)
            
            # Build hierarchy map for parent-child relationships
            hierarchy_map = self._build_hierarchy_map(categories)
            
            # Process and serialize categories
            serialized_categories = []
            for category in categories:
                try:
                    serialized_category = self.serialize_entity(category)
                    
                    # Add hierarchy information
                    serialized_category.update(self._add_hierarchy_info(category, hierarchy_map))
                    
                    # Add computed fields
                    serialized_category.update(self._add_computed_fields(category))
                    
                    serialized_categories.append(serialized_category)
                    self.processed_count += 1
                    
                except Exception as e:
                    self.error_count += 1
                    self._add_warning(f"Failed to serialize category: {str(e)}", str(category.categoryId))
            
            # Sort categories by hierarchy (parents first, then children)
            serialized_categories = self._sort_by_hierarchy(serialized_categories)
            
            logger.info(f"Category data collection complete: {self.processed_count} categories processed, "
                       f"{self.error_count} errors")
            
            return serialized_categories
            
        except Exception as e:
            logger.error(f"Failed to collect category data for user {self.user_id}: {str(e)}")
            raise ExportException(f"Category data collection failed: {str(e)}", "category")
    
    def serialize_entity(self, category: Category) -> Dict[str, Any]:
        """Serialize category with export-specific formatting"""
        try:
            # Get base serialization
            serialized = category.model_dump(by_alias=True, exclude_none=True)
            
            # Process rules for export
            if 'rules' in serialized and serialized['rules']:
                serialized['rules'] = [self._serialize_rule(rule) for rule in serialized['rules']]
            
            # Add export metadata
            serialized['exportMetadata'] = {
                'exportedAt': datetime.now(timezone.utc).isoformat(),
                'dataVersion': '1.0',
                'ruleCount': len(serialized.get('rules', []))
            }
            
            return serialized
            
        except Exception as e:
            raise ExportException(f"Category serialization failed: {str(e)}", "category")
    
    def _serialize_rule(self, rule: Any) -> Dict[str, Any]:
        """Serialize a category rule for export"""
        if hasattr(rule, 'model_dump'):
            rule_data = rule.model_dump(by_alias=True, exclude_none=True)
        elif isinstance(rule, dict):
            rule_data = rule.copy()
        else:
            rule_data = {}
        
        # Ensure decimal fields are strings
        for field in ['amountMin', 'amountMax']:
            if field in rule_data and rule_data[field] is not None:
                rule_data[field] = str(rule_data[field])
        
        return rule_data
    
    def _apply_filters(self, categories: List[Category], filters: Dict[str, Any]) -> List[Category]:
        """Apply filters to category list"""
        filtered = categories
        
        # Filter by specific category IDs
        if filters.get('category_ids'):
            category_id_set = {str(cid) for cid in filters['category_ids']}
            filtered = [cat for cat in filtered if str(cat.categoryId) in category_id_set]
        
        # Filter by category types
        if filters.get('category_types'):
            type_set = set(filters['category_types'])
            filtered = [cat for cat in filtered if cat.type.value in type_set]
        
        # Filter by parent category
        if filters.get('parent_category_id'):
            parent_id = str(filters['parent_category_id'])
            filtered = [cat for cat in filtered 
                       if cat.parentCategoryId and str(cat.parentCategoryId) == parent_id]
        
        # Filter root categories only
        if filters.get('root_only'):
            filtered = [cat for cat in filtered if not cat.parentCategoryId]
        
        return filtered
    
    def _build_hierarchy_map(self, categories: List[Category]) -> Dict[str, Dict[str, Any]]:
        """Build a map of category hierarchy relationships"""
        hierarchy_map = {}
        
        for category in categories:
            cat_id = str(category.categoryId)
            hierarchy_map[cat_id] = {
                'children': [],
                'parent': str(category.parentCategoryId) if category.parentCategoryId else None,
                'depth': 0,
                'path': []
            }
        
        # Build children lists and calculate depths
        for category in categories:
            cat_id = str(category.categoryId)
            if category.parentCategoryId:
                parent_id = str(category.parentCategoryId)
                if parent_id in hierarchy_map:
                    hierarchy_map[parent_id]['children'].append(cat_id)
        
        # Calculate depths and paths
        def calculate_depth_and_path(cat_id: str, visited: Optional[set] = None) -> int:
            if visited is None:
                visited = set()
            
            if cat_id in visited:  # Circular reference protection
                return 0
            
            visited.add(cat_id)
            
            if cat_id not in hierarchy_map:
                return 0
            
            parent_id = hierarchy_map[cat_id]['parent']
            if not parent_id:
                hierarchy_map[cat_id]['depth'] = 0
                hierarchy_map[cat_id]['path'] = [cat_id]
                return 0
            
            parent_depth = calculate_depth_and_path(parent_id, visited)
            depth = parent_depth + 1
            hierarchy_map[cat_id]['depth'] = depth
            hierarchy_map[cat_id]['path'] = hierarchy_map[parent_id]['path'] + [cat_id]
            
            return depth
        
        for cat_id in hierarchy_map.keys():
            calculate_depth_and_path(cat_id)
        
        return hierarchy_map
    
    def _add_hierarchy_info(self, category: Category, hierarchy_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Add hierarchy information to category export"""
        cat_id = str(category.categoryId)
        hierarchy_info = hierarchy_map.get(cat_id, {})
        
        return {
            'hierarchyInfo': {
                'depth': hierarchy_info.get('depth', 0),
                'hasChildren': len(hierarchy_info.get('children', [])) > 0,
                'childrenCount': len(hierarchy_info.get('children', [])),
                'isRoot': not category.parentCategoryId,
                'fullPath': hierarchy_info.get('path', [cat_id])
            }
        }
    
    def _add_computed_fields(self, category: Category) -> Dict[str, Any]:
        """Add computed fields to category export"""
        return {
            'computedFields': {
                'ruleCount': len(category.rules) if category.rules else 0,
                'hasRules': bool(category.rules),
                'inheritanceEnabled': category.inherit_parent_rules,
                'lastModified': category.updatedAt
            }
        }
    
    def _sort_by_hierarchy(self, categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort categories by hierarchy (parents before children)"""
        return sorted(categories, key=lambda cat: (
            cat.get('hierarchyInfo', {}).get('depth', 0),
            cat.get('name', '')
        ))


class FileMapExporter(BaseExporter):
    """Specialized exporter for file map entities"""
    
    def collect_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Collect file map data with mapping configurations
        
        Args:
            filters: Optional filters including account_ids, include_unused, etc.
            
        Returns:
            List of serialized file map dictionaries
        """
        try:
            logger.info(f"Starting file map data collection for user {self.user_id}")
            
            # Get all user file maps
            file_maps = list_file_maps_by_user(self.user_id)
            
            # Apply filters
            if filters:
                file_maps = self._apply_filters(file_maps, filters)
            
            # Process and serialize file maps
            serialized_file_maps = []
            for file_map in file_maps:
                try:
                    serialized_file_map = self.serialize_entity(file_map)
                    
                    # Add computed fields
                    serialized_file_map.update(self._add_computed_fields(file_map))
                    
                    serialized_file_maps.append(serialized_file_map)
                    self.processed_count += 1
                    
                except Exception as e:
                    self.error_count += 1
                    self._add_warning(f"Failed to serialize file map: {str(e)}", str(file_map.file_map_id))
            
            logger.info(f"File map data collection complete: {self.processed_count} file maps processed, "
                       f"{self.error_count} errors")
            
            return serialized_file_maps
            
        except Exception as e:
            logger.error(f"Failed to collect file map data for user {self.user_id}: {str(e)}")
            raise ExportException(f"File map data collection failed: {str(e)}", "file_map")
    
    def serialize_entity(self, file_map: FileMap) -> Dict[str, Any]:
        """Serialize file map with export-specific formatting"""
        try:
            # Get base serialization
            serialized = file_map.model_dump(by_alias=True, exclude_none=True)
            
            # Enhance mapping information
            if 'mappings' in serialized:
                serialized['mappings'] = [self._enhance_mapping(mapping) for mapping in serialized['mappings']]
            
            # Add export metadata
            serialized['exportMetadata'] = {
                'exportedAt': datetime.now(timezone.utc).isoformat(),
                'dataVersion': '1.0',
                'mappingCount': len(serialized.get('mappings', []))
            }
            
            return serialized
            
        except Exception as e:
            raise ExportException(f"File map serialization failed: {str(e)}", "file_map")
    
    def _enhance_mapping(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance mapping information for export"""
        enhanced = mapping.copy() if isinstance(mapping, dict) else {}
        
        # Add validation info
        enhanced['validationInfo'] = {
            'isRequired': mapping.get('sourceField') in ['date', 'amount', 'description'],
            'hasTransformation': bool(mapping.get('transformation')),
            'fieldType': self._determine_field_type(mapping.get('targetField', ''))
        }
        
        return enhanced
    
    def _determine_field_type(self, target_field: str) -> str:
        """Determine the type of a target field"""
        field_types = {
            'date': 'datetime',
            'amount': 'decimal',
            'balance': 'decimal',
            'description': 'string',
            'memo': 'string',
            'checkNumber': 'string',
            'fitId': 'string',
            'transactionType': 'string'
        }
        return field_types.get(target_field, 'unknown')
    
    def _apply_filters(self, file_maps: List[FileMap], filters: Dict[str, Any]) -> List[FileMap]:
        """Apply filters to file map list"""
        filtered = file_maps
        
        # Filter by account IDs
        if filters.get('account_ids'):
            account_id_set = {str(aid) for aid in filters['account_ids']}
            filtered = [fm for fm in filtered 
                       if fm.account_id and str(fm.account_id) in account_id_set]
        
        # Filter by name pattern
        if filters.get('name_pattern'):
            pattern = filters['name_pattern'].lower()
            filtered = [fm for fm in filtered if pattern in fm.name.lower()]
        
        return filtered
    
    def _add_computed_fields(self, file_map: FileMap) -> Dict[str, Any]:
        """Add computed fields to file map export"""
        return {
            'computedFields': {
                'mappingCount': len(file_map.mappings) if file_map.mappings else 0,
                'hasAccountAssociation': file_map.account_id is not None,
                'reversesAmounts': file_map.reverse_amounts,
                'isComplete': self._validate_mapping_completeness(file_map)
            }
        }
    
    def _validate_mapping_completeness(self, file_map: FileMap) -> bool:
        """Check if file map has all required mappings"""
        if not file_map.mappings:
            return False
        
        required_fields = {'date', 'amount', 'description'}
        mapped_fields = {mapping.target_field for mapping in file_map.mappings}
        
        return required_fields.issubset(mapped_fields)


class TransactionFileExporter(BaseExporter):
    """Specialized exporter for transaction file entities with S3 file handling"""
    
    def __init__(self, user_id: str, batch_size: int = 100):  # Smaller batch size for files
        super().__init__(user_id, batch_size)
        self.total_file_size = 0
        self.file_format_counts = {}
        
    def collect_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Collect transaction file data with metadata
        
        Args:
            filters: Optional filters including account_ids, file_formats, etc.
            
        Returns:
            List of serialized transaction file dictionaries
        """
        try:
            logger.info(f"Starting transaction file data collection for user {self.user_id}")
            
            # Get all user files
            files = list_user_files(self.user_id)
            
            # Apply filters
            if filters:
                files = self._apply_filters(files, filters)
            
            # Process and serialize files
            serialized_files = []
            for file in files:
                try:
                    serialized_file = self.serialize_entity(file)
                    
                    # Add computed fields
                    serialized_file.update(self._add_computed_fields(file))
                    
                    serialized_files.append(serialized_file)
                    
                    # Update statistics
                    self._update_statistics(file)
                    self.processed_count += 1
                    
                except Exception as e:
                    self.error_count += 1
                    self._add_warning(f"Failed to serialize transaction file: {str(e)}", str(file.file_id))
            
            # Sort by upload date (most recent first)
            serialized_files.sort(key=lambda f: f.get('uploadDate', 0), reverse=True)
            
            logger.info(f"Transaction file data collection complete: {self.processed_count} files processed, "
                       f"{self.error_count} errors")
            
            return serialized_files
            
        except Exception as e:
            logger.error(f"Failed to collect transaction file data for user {self.user_id}: {str(e)}")
            raise ExportException(f"Transaction file data collection failed: {str(e)}", "transaction_file")
    
    def serialize_entity(self, file: TransactionFile) -> Dict[str, Any]:
        """Serialize transaction file with export-specific formatting"""
        try:
            # Get base serialization
            serialized = file.model_dump(by_alias=True, exclude_none=True)
            
            # Format dates for readability
            for date_field in ['uploadDate', 'processedDate']:
                if date_field in serialized and serialized[date_field]:
                    try:
                        dt = datetime.fromtimestamp(serialized[date_field] / 1000, tz=timezone.utc)
                        serialized[f'{date_field}Formatted'] = dt.isoformat()
                    except (ValueError, TypeError):
                        pass
            
            # Ensure decimal fields are strings
            for field in ['openingBalance', 'closingBalance']:
                if field in serialized and serialized[field] is not None:
                    serialized[field] = str(serialized[field])
            
            # Add file status information
            serialized['fileStatusInfo'] = {
                'isProcessed': file.processing_status.value if file.processing_status else 'unknown',
                'hasTransactions': (file.transaction_count or 0) > 0,
                'hasDuplicates': (file.duplicate_count or 0) > 0,
                'hasErrors': bool(file.error_message)
            }
            
            # Add export metadata
            serialized['exportMetadata'] = {
                'exportedAt': datetime.now(timezone.utc).isoformat(),
                'dataVersion': '1.0',
                'includeFileContent': False  # Will be set to True if file content is included
            }
            
            return serialized
            
        except Exception as e:
            raise ExportException(f"Transaction file serialization failed: {str(e)}", "transaction_file")
    
    def _apply_filters(self, files: List[TransactionFile], filters: Dict[str, Any]) -> List[TransactionFile]:
        """Apply filters to transaction file list"""
        filtered = files
        
        # Filter by account IDs
        if filters.get('account_ids'):
            account_id_set = {str(aid) for aid in filters['account_ids']}
            filtered = [f for f in filtered 
                       if f.account_id and str(f.account_id) in account_id_set]
        
        # Filter by file formats
        if filters.get('file_formats'):
            format_set = set(filters['file_formats'])
            filtered = [f for f in filtered 
                       if f.file_format and f.file_format.value in format_set]
        
        # Filter by processing status
        if filters.get('processing_status'):
            status_set = set(filters['processing_status'])
            filtered = [f for f in filtered 
                       if f.processing_status and f.processing_status.value in status_set]
        
        # Filter by upload date range
        if filters.get('upload_date_start') or filters.get('upload_date_end'):
            start_date = filters.get('upload_date_start', 0)
            end_date = filters.get('upload_date_end', 9999999999999)
            filtered = [f for f in filtered if start_date <= f.upload_date <= end_date]
        
        return filtered
    
    def _update_statistics(self, file: TransactionFile):
        """Update collection statistics"""
        # Update total file size
        self.total_file_size += file.file_size or 0
        
        # Update format counts
        if file.file_format:
            format_name = file.file_format.value
            self.file_format_counts[format_name] = self.file_format_counts.get(format_name, 0) + 1
    
    def _add_computed_fields(self, file: TransactionFile) -> Dict[str, Any]:
        """Add computed fields to transaction file export"""
        file_age_days = 0
        if file.upload_date:
            file_age_days = int((datetime.now(timezone.utc).timestamp() * 1000 - file.upload_date) / (24*60*60*1000))
        
        return {
            'computedFields': {
                'fileSizeFormatted': self._format_file_size(file.file_size or 0),
                'fileAgeInDays': file_age_days,
                'transactionDensity': (file.transaction_count or 0) / max((file.file_size or 1), 1) * 1000,  # transactions per KB
                'duplicatePercentage': ((file.duplicate_count or 0) / max((file.record_count or 1), 1)) * 100,
                'hasDateRange': bool(file.date_range)
            }
        }
    
    def _format_file_size(self, size_bytes: float) -> str:
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def get_export_summary(self) -> Dict[str, Any]:
        """Get enhanced summary with file-specific statistics"""
        base_summary = super().get_export_summary()
        base_summary.update({
            'totalFileSize': self._format_file_size(self.total_file_size),
            'totalFileSizeBytes': self.total_file_size,
            'fileFormatCounts': self.file_format_counts,
            'averageFileSize': self._format_file_size(
                self.total_file_size // max(self.processed_count, 1)
            )
        })
        return base_summary 
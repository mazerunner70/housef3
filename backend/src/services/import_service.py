import logging
import json
import zipfile
import io
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

from models.import_job import ImportJob, ImportStatus
from utils.db_utils import create_import_job, update_import_job, get_import_job
from utils.s3_dao import get_object_content

logger = logging.getLogger()

class ImportService:
    def __init__(self):
        self.import_bucket = "housef3-dev-import-packages"
        
    def start_import(self, import_job: ImportJob, package_s3_key: str):
        """Start import processing."""
        try:
            # Update job with package location
            import_job.package_s3_key = package_s3_key
            import_job.status = ImportStatus.VALIDATING
            import_job.current_phase = "parsing_package"
            import_job.progress = 10
            update_import_job(import_job)
            
            # Parse package
            package_data = self._parse_package(package_s3_key)
            
            # Validate schema
            import_job.current_phase = "validating_schema"
            import_job.progress = 20
            update_import_job(import_job)
            
            schema_results = self._validate_schema(package_data)
            import_job.validation_results['schema'] = schema_results
            
            if not schema_results['valid']:
                import_job.status = ImportStatus.VALIDATION_FAILED
                import_job.error_message = "Schema validation failed"
                update_import_job(import_job)
                return
            
            # Validate business rules
            import_job.current_phase = "validating_business_rules"
            import_job.progress = 30
            update_import_job(import_job)
            
            business_results = self._validate_business_rules(
                package_data, import_job.user_id, import_job.merge_strategy
            )
            import_job.validation_results['business'] = business_results
            
            if not business_results['valid']:
                import_job.status = ImportStatus.VALIDATION_FAILED
                import_job.error_message = "Business validation failed"
                update_import_job(import_job)
                return
            
            import_job.status = ImportStatus.VALIDATION_PASSED
            import_job.progress = 40
            update_import_job(import_job)
            
            # Begin data import
            self._import_data(import_job, package_data)
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            import_job.status = ImportStatus.FAILED
            import_job.error_message = str(e)
            update_import_job(import_job)
    
    def _parse_package(self, package_s3_key: str) -> Dict[str, Any]:
        """Parse the ZIP package and extract data."""
        try:
            # Download package from S3
            package_data = get_object_content(package_s3_key, self.import_bucket)
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
    
    def _import_data(self, import_job: ImportJob, package_data: Dict[str, Any]):
        """Import all data from the package."""
        try:
            import_job.status = ImportStatus.PROCESSING
            data = package_data['data']
            results = {}
            
            # Import in dependency order
            
            # 1. Import accounts first
            import_job.current_phase = "importing_accounts"
            import_job.progress = 50
            update_import_job(import_job)
            
            account_results = self._import_accounts(
                data.get('accounts', []), import_job.user_id, import_job.merge_strategy
            )
            results['accounts'] = account_results
            
            # 2. Import categories
            import_job.current_phase = "importing_categories"
            import_job.progress = 60
            update_import_job(import_job)
            
            category_results = self._import_categories(
                data.get('categories', []), import_job.user_id, import_job.merge_strategy
            )
            results['categories'] = category_results
            
            # 3. Import file maps
            import_job.current_phase = "importing_file_maps"
            import_job.progress = 70
            update_import_job(import_job)
            
            file_map_results = self._import_file_maps(
                data.get('file_maps', []), import_job.user_id, import_job.merge_strategy
            )
            results['file_maps'] = file_map_results
            
            # 4. Import transaction files
            import_job.current_phase = "importing_transaction_files"
            import_job.progress = 80
            update_import_job(import_job)
            
            file_results = self._import_transaction_files(
                data.get('transaction_files', []), import_job.user_id, import_job.merge_strategy
            )
            results['transaction_files'] = file_results
            
            # 5. Import transactions
            import_job.current_phase = "importing_transactions"
            import_job.progress = 90
            update_import_job(import_job)
            
            transaction_results = self._import_transactions(
                data.get('transactions', []), import_job.user_id, import_job.merge_strategy
            )
            results['transactions'] = transaction_results
            
            # Complete import
            import_job.status = ImportStatus.COMPLETED
            import_job.progress = 100
            import_job.current_phase = "completed"
            import_job.import_results = results
            import_job.completed_at = int(datetime.now(timezone.utc).timestamp() * 1000)
            update_import_job(import_job)
            
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
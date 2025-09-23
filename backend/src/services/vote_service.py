"""
Vote Service
Handles voting workflows for any business process through proper service layer
"""

import os
from typing import Dict, Any, Optional, Set, List
from datetime import datetime, timedelta

from utils.db_utils import get_workflows_table
from services.operation_tracking_service import operation_tracking_service, OperationStatus
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class VoteService:
    """Service layer for managing voting workflows"""
    
    def __init__(self):
        self.table = get_workflows_table()
        
        # Workflow configurations - can be externalized to config service
        self.workflow_configs = {
            'file.deletion': {
                'request_event': 'file.deletion.requested',
                'vote_event': 'file.deletion.vote', 
                'approved_event': 'file.deletion.approved',
                'denied_event': 'file.deletion.denied',
                'voters': {
                    'default': ['analytics_manager', 'category_manager'],
                    'large_files': ['analytics_manager', 'category_manager', 'backup_manager'],
                    'critical_accounts': ['analytics_manager', 'category_manager', 'compliance_manager']
                }
            },
            'file.upload': {
                'request_event': 'file.upload.requested',
                'vote_event': 'file.upload.vote',
                'approved_event': 'file.upload.approved', 
                'denied_event': 'file.upload.denied',
                'voters': {
                    'default': ['security_scanner', 'format_validator'],
                    'large_files': ['security_scanner', 'format_validator', 'storage_manager'],
                    'sensitive_data': ['security_scanner', 'format_validator', 'compliance_manager', 'encryption_manager']
                }
            },
            'account.modification': {
                'request_event': 'account.modification.requested',
                'vote_event': 'account.modification.vote',
                'approved_event': 'account.modification.approved',
                'denied_event': 'account.modification.denied', 
                'voters': {
                    'default': ['data_integrity_checker', 'analytics_impact_assessor'],
                    'business_accounts': ['data_integrity_checker', 'analytics_impact_assessor', 'compliance_manager'],
                    'high_value': ['data_integrity_checker', 'analytics_impact_assessor', 'risk_manager', 'audit_manager']
                }
            }
        }
    
    def get_workflow_config(self, workflow_type: str) -> Dict[str, Any]:
        """Get configuration for a specific workflow type"""
        return self.workflow_configs.get(workflow_type, {})
    
    def get_required_voters(self, workflow_type: str, context: Dict[str, Any]) -> Set[str]:
        """Determine required voters based on workflow type and context"""
        config = self.get_workflow_config(workflow_type)
        voters_config = config.get('voters', {})
        
        if workflow_type == 'file.deletion':
            transaction_count = context.get('transactionCount', 0)
            account_type = context.get('accountType', 'personal')
            
            if transaction_count > 1000:
                return set(voters_config.get('large_files', []))
            elif account_type == 'business':
                return set(voters_config.get('critical_accounts', []))
            else:
                return set(voters_config.get('default', []))
                
        elif workflow_type == 'file.upload':
            file_size = context.get('fileSize', 0)
            has_sensitive_data = context.get('hasSensitiveData', False)
            
            if has_sensitive_data:
                return set(voters_config.get('sensitive_data', []))
            elif file_size > 100 * 1024 * 1024:  # 100MB
                return set(voters_config.get('large_files', []))
            else:
                return set(voters_config.get('default', []))
                
        elif workflow_type == 'account.modification':
            account_type = context.get('accountType', 'personal')
            account_value = context.get('accountValue', 0)
            
            if account_value > 1000000:  # $1M+
                return set(voters_config.get('high_value', []))
            elif account_type == 'business':
                return set(voters_config.get('business_accounts', []))
            else:
                return set(voters_config.get('default', []))
        
        # Default fallback
        return set(voters_config.get('default', []))
    
    def register_vote_request(self, workflow_type: str, entity_id: str, request_id: str, 
                            user_id: str, context: Dict[str, Any]) -> None:
        """Register voting requirements in the existing workflow's context"""
        try:
            # Determine required voters
            required_voters = self.get_required_voters(workflow_type, context)
            
            # Update the existing workflow record's context with vote tracking info
            vote_context = {
                'voteTracking': {
                    'workflowType': workflow_type,
                    'requiredVoters': list(required_voters),
                    'votesReceived': {},
                    'status': 'waiting_for_votes',
                    'voteStartedAt': datetime.now().isoformat()
                }
            }
            
            # Merge with existing context
            updated_context = {**context, **vote_context}
            
            self.table.update_item(
                Key={'operationId': request_id},
                UpdateExpression='SET #context = :context, #status = :status',
                ExpressionAttributeNames={
                    '#context': 'context',
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':context': updated_context,
                    ':status': 'waiting_for_votes'
                }
            )
            
            logger.info(f"Registered {workflow_type} vote tracking for {entity_id} (request {request_id})")
            logger.info(f"Required voters: {required_voters}")
            
        except Exception as e:
            logger.error(f"Error registering vote request: {str(e)}")
            raise
    
    def record_vote(self, workflow_type: str, entity_id: str, request_id: str, 
                   voter: str, decision: str, reason: str = '') -> Optional[str]:
        """
        Record a vote and return decision if all votes are in
        Returns: 'approved', 'denied', or None (still waiting)
        """
        try:
            from botocore.exceptions import ClientError
            
            # First, ensure the voteTracking structure exists
            self._ensure_vote_tracking_structure(request_id, workflow_type, entity_id)
            
            # Update the vote in the workflow's context atomically
            try:
                response = self.table.update_item(
                    Key={'operationId': request_id},
                    UpdateExpression='SET #context.#voteTracking.#votesReceived.#voter = :vote_data',
                    ExpressionAttributeNames={
                        '#context': 'context',
                        '#voteTracking': 'voteTracking',
                        '#votesReceived': 'votesReceived',
                        '#voter': voter
                    },
                    ExpressionAttributeValues={
                        ':vote_data': {
                            'decision': decision,
                            'reason': reason,
                            'timestamp': datetime.now().isoformat()
                        }
                    },
                    ReturnValues='ALL_NEW'
                )
                
                item = response['Attributes']
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == 'ResourceNotFoundException':
                    logger.warning(f"Workflow record not found for request {request_id}")
                    return None
                raise
            
            # Extract vote tracking data from context
            vote_tracking = item.get('context', {}).get('voteTracking', {})
            required_voters = set(vote_tracking.get('requiredVoters', []))
            votes_received = vote_tracking.get('votesReceived', {})
            
            logger.info(f"Vote recorded: {voter} -> {decision} for {workflow_type} {entity_id}")
            logger.info(f"Votes: {len(votes_received)}/{len(required_voters)} received")
            
            # Check for immediate denial
            if decision == 'deny':
                self._update_workflow_status(request_id, 'denied')
                logger.info(f"{workflow_type} {entity_id} DENIED by {voter}: {reason}")
                
                # Update operation tracking if this is a file deletion
                if workflow_type == 'file.deletion':
                    try:
                        operation_tracking_service.update_operation_status(
                            operation_id=request_id,
                            status=OperationStatus.DENIED,
                            progress_percentage=0,
                            error_message=f"Denied by {voter}: {reason}"
                        )
                    except Exception as e:
                        logger.error(f"Error updating operation tracking for immediate denial: {str(e)}")
                
                return 'denied'
            
            # Check if all required voters have voted
            voters_who_voted = set(votes_received.keys())
            if not required_voters.issubset(voters_who_voted):
                logger.info(f"Still waiting for votes from: {required_voters - voters_who_voted}")
                return None
            
            # Check if all votes are 'proceed'
            all_approved = all(
                vote_data['decision'] == 'proceed' 
                for vote_data in votes_received.values()
            )
            
            if all_approved:
                self._update_workflow_status(request_id, 'approved')
                logger.info(f"{workflow_type} {entity_id} APPROVED by all voters")
                
                # Update operation tracking if this is a file deletion
                if workflow_type == 'file.deletion':
                    try:
                        operation_tracking_service.update_operation_status(
                            operation_id=request_id,
                            status=OperationStatus.APPROVED,
                            progress_percentage=75,
                            current_step=2,
                            step_description="All approvals received, starting deletion"
                        )
                    except Exception as e:
                        logger.error(f"Error updating operation tracking for approval: {str(e)}")
                
                return 'approved'
            else:
                self._update_workflow_status(request_id, 'denied')
                logger.info(f"{workflow_type} {entity_id} DENIED - not all voters approved")
                
                # Update operation tracking if this is a file deletion
                if workflow_type == 'file.deletion':
                    try:
                        # Find the voter who denied
                        denied_by = None
                        denial_reason = None
                        for voter_name, vote_data in votes_received.items():
                            if vote_data['decision'] == 'deny':
                                denied_by = voter_name
                                denial_reason = vote_data.get('reason', 'No reason provided')
                                break
                        
                        operation_tracking_service.update_operation_status(
                            operation_id=request_id,
                            status=OperationStatus.DENIED,
                            progress_percentage=0,
                            error_message=f"Denied by {denied_by}: {denial_reason}" if denied_by else "Denied by voters"
                        )
                    except Exception as e:
                        logger.error(f"Error updating operation tracking for denial: {str(e)}")
                
                return 'denied'
                
        except Exception as e:
            logger.error(f"Error recording vote: {str(e)}")
            raise
    
    def _ensure_vote_tracking_structure(self, request_id: str, workflow_type: str, entity_id: str) -> None:
        """Ensure the voteTracking structure exists in the workflow context"""
        try:
            # First, get the current item to check if voteTracking exists
            response = self.table.get_item(Key={'operationId': request_id})
            item = response.get('Item')
            
            if not item:
                logger.error(f"Workflow record not found for request {request_id}")
                raise ValueError(f"Workflow record not found for request {request_id}")
            
            # Check if voteTracking structure already exists
            vote_tracking = item.get('context', {}).get('voteTracking')
            if vote_tracking:
                logger.info(f"Vote tracking structure already exists for {request_id}")
                return
            
            # Get required voters for this workflow
            context = item.get('context', {})
            required_voters = self.get_required_voters(workflow_type, context)
            
            # Create the vote tracking structure
            vote_tracking_structure = {
                'workflowType': workflow_type,
                'requiredVoters': list(required_voters),
                'votesReceived': {},
                'status': 'waiting_for_votes',
                'voteStartedAt': datetime.now().isoformat()
            }
            
            # Update the workflow record to add the voteTracking structure
            self.table.update_item(
                Key={'operationId': request_id},
                UpdateExpression='SET #context.#voteTracking = :vote_tracking',
                ExpressionAttributeNames={
                    '#context': 'context',
                    '#voteTracking': 'voteTracking'
                },
                ExpressionAttributeValues={
                    ':vote_tracking': vote_tracking_structure
                }
            )
            
            logger.info(f"Created vote tracking structure for {workflow_type} {entity_id} (request {request_id})")
            logger.info(f"Required voters: {required_voters}")
            
        except Exception as e:
            logger.error(f"Error ensuring vote tracking structure: {str(e)}")
            raise

    def _update_workflow_status(self, request_id: str, status: str) -> None:
        """Update the status of a workflow record"""
        try:
            self.table.update_item(
                Key={'operationId': request_id},
                UpdateExpression='SET #status = :status, #context.#voteTracking.#status = :vote_status',
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#context': 'context',
                    '#voteTracking': 'voteTracking'
                },
                ExpressionAttributeValues={
                    ':status': status,
                    ':vote_status': status
                }
            )
        except Exception as e:
            logger.error(f"Error updating workflow status: {str(e)}")
    
    def get_vote_info(self, workflow_type: str, entity_id: str, request_id: str) -> Optional[Dict[str, Any]]:
        """Get vote tracking information from workflow context"""
        try:
            response = self.table.get_item(
                Key={'operationId': request_id}
            )
            
            item = response.get('Item')
            if not item:
                return None
                
            # Extract vote tracking from context and add workflow-level fields for compatibility
            vote_tracking = item.get('context', {}).get('voteTracking', {})
            if not vote_tracking:
                return None
                
            # Return in the format expected by the vote aggregator
            return {
                'userId': item.get('userId'),
                'votesReceived': vote_tracking.get('votesReceived', {}),
                'context': item.get('context', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting vote info: {str(e)}")
            return None
    
    def cleanup_vote_record(self, workflow_type: str, entity_id: str, request_id: str) -> None:
        """Clean up vote tracking data from workflow context"""
        try:
            self.table.update_item(
                Key={'operationId': request_id},
                UpdateExpression='REMOVE #context.#voteTracking',
                ExpressionAttributeNames={
                    '#context': 'context',
                    '#voteTracking': 'voteTracking'
                }
            )
            logger.info(f"Cleaned up vote tracking for {workflow_type}#{entity_id}#{request_id}")
        except Exception as e:
            logger.error(f"Error cleaning up vote tracking: {str(e)}")


# Global service instance
vote_service = VoteService()

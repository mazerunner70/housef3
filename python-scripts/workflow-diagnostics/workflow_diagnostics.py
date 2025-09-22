#!/usr/bin/env python3
"""
Workflow Diagnostics CLI Tool
Comprehensive diagnostic tool for tracking workflow operations, particularly file deletion success rates.

Usage:
    python3 workflow_diagnostics.py status [operation-id]     # Check specific operation status
    python3 workflow_diagnostics.py list [--status STATUS]   # List operations with filters
    python3 workflow_diagnostics.py monitor [operation-id]   # Real-time monitoring
    python3 workflow_diagnostics.py health [--hours N]       # System health analysis
    python3 workflow_diagnostics.py logs [operation-id]      # Show related logs
    python3 workflow_diagnostics.py summary                  # Quick system summary

Examples:
    # Check specific operation
    python3 workflow_diagnostics.py status op_20250120_143022_abc12345

    # Monitor all active operations
    python3 workflow_diagnostics.py monitor

    # Check system health for last 24 hours
    python3 workflow_diagnostics.py health --hours 24

    # List all failed operations
    python3 workflow_diagnostics.py list --status failed
"""

import argparse
import boto3
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
import os
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'housef3')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
WORKFLOWS_TABLE = f"{PROJECT_NAME}-{ENVIRONMENT}-workflows"
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-2')

class OperationStatus(str, Enum):
    """Standard operation statuses"""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DENIED = "denied"

class OperationType(str, Enum):
    """Supported operation types"""
    FILE_DELETION = "file_deletion"
    FILE_UPLOAD = "file_upload"
    ACCOUNT_MODIFICATION = "account_modification"
    DATA_EXPORT = "data_export"
    BULK_CATEGORIZATION = "bulk_categorization"
    ACCOUNT_MIGRATION = "account_migration"

@dataclass
class OperationInfo:
    """Operation information structure"""
    operation_id: str
    operation_type: str
    status: str
    progress_percentage: int
    current_step: int
    total_steps: int
    created_at: str
    updated_at: str
    entity_id: str
    user_id: str
    error_message: Optional[str] = None
    step_description: Optional[str] = None
    estimated_completion: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class WorkflowDiagnostics:
    """Main diagnostic tool class"""
    
    def __init__(self):
        """Initialize the diagnostic tool"""
        self.dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        self.operations_table = self.dynamodb.Table(WORKFLOWS_TABLE)
        self.logs_client = boto3.client('logs', region_name=AWS_REGION)
        
        # Verify table access
        try:
            self.operations_table.table_status
            logger.info(f"Connected to workflows table: {WORKFLOWS_TABLE}")
        except Exception as e:
            logger.error(f"Failed to connect to workflows table {WORKFLOWS_TABLE}: {e}")
            sys.exit(1)
    
    def get_operation_status(self, operation_id: str) -> Optional[OperationInfo]:
        """Get detailed status of a specific operation"""
        try:
            response = self.operations_table.get_item(
                Key={'operationId': operation_id}
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            return OperationInfo(
                operation_id=item['operationId'],
                operation_type=item.get('operationType', 'unknown'),
                status=item.get('status', 'unknown'),
                progress_percentage=int(item.get('progressPercentage', 0)),
                current_step=int(item.get('currentStep', 0)),
                total_steps=int(item.get('totalSteps', 0)),
                created_at=item.get('createdAt', ''),
                updated_at=item.get('updatedAt', ''),
                entity_id=item.get('entityId', ''),
                user_id=item.get('userId', ''),
                error_message=item.get('errorMessage'),
                step_description=item.get('currentStepDescription'),
                estimated_completion=item.get('estimatedCompletion'),
                context=item.get('context', {})
            )
        except Exception as e:
            logger.error(f"Error getting operation status: {e}")
            return None
    
    def list_operations(self, status_filter: Optional[str] = None, 
                       operation_type_filter: Optional[str] = None,
                       hours_back: int = 24, limit: int = 50) -> List[OperationInfo]:
        """List operations with optional filters"""
        try:
            # Calculate time threshold
            time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
            
            # Build filter expression
            filter_expressions = []
            expression_values = {}
            
            # Time filter
            filter_expressions.append('createdAt >= :time_threshold')
            expression_values[':time_threshold'] = time_threshold
            
            # Status filter
            if status_filter:
                filter_expressions.append('#status = :status')
                expression_values[':status'] = status_filter
            
            # Operation type filter
            if operation_type_filter:
                filter_expressions.append('operationType = :op_type')
                expression_values[':op_type'] = operation_type_filter
            
            # Perform scan with filters
            scan_kwargs = {
                'Limit': limit,
                'FilterExpression': ' AND '.join(filter_expressions),
                'ExpressionAttributeValues': expression_values
            }
            
            if status_filter:
                scan_kwargs['ExpressionAttributeNames'] = {'#status': 'status'}
            
            response = self.operations_table.scan(**scan_kwargs)
            
            operations = []
            for item in response.get('Items', []):
                operations.append(OperationInfo(
                    operation_id=item['operationId'],
                    operation_type=item.get('operationType', 'unknown'),
                    status=item.get('status', 'unknown'),
                    progress_percentage=int(item.get('progressPercentage', 0)),
                    current_step=int(item.get('currentStep', 0)),
                    total_steps=int(item.get('totalSteps', 0)),
                    created_at=item.get('createdAt', ''),
                    updated_at=item.get('updatedAt', ''),
                    entity_id=item.get('entityId', ''),
                    user_id=item.get('userId', ''),
                    error_message=item.get('errorMessage'),
                    step_description=item.get('currentStepDescription'),
                    estimated_completion=item.get('estimatedCompletion'),
                    context=item.get('context', {})
                ))
            
            # Sort by creation time (newest first)
            operations.sort(key=lambda x: x.created_at, reverse=True)
            return operations
            
        except Exception as e:
            logger.error(f"Error listing operations: {e}")
            return []
    
    def get_system_health(self, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze system health and success rates"""
        operations = self.list_operations(hours_back=hours_back, limit=1000)
        
        # Calculate statistics
        total_operations = len(operations)
        status_counts = Counter(op.status for op in operations)
        type_counts = Counter(op.operation_type for op in operations)
        
        # Success rate calculation
        completed = status_counts.get(OperationStatus.COMPLETED.value, 0)
        failed = status_counts.get(OperationStatus.FAILED.value, 0)
        cancelled = status_counts.get(OperationStatus.CANCELLED.value, 0)
        denied = status_counts.get(OperationStatus.DENIED.value, 0)
        
        finished_operations = completed + failed + cancelled + denied
        success_rate = (completed / finished_operations * 100) if finished_operations > 0 else 0
        
        # Average completion time for successful operations
        completed_ops = [op for op in operations if op.status == OperationStatus.COMPLETED.value]
        avg_completion_time = None
        if completed_ops:
            completion_times = []
            for op in completed_ops:
                try:
                    created = datetime.fromisoformat(op.created_at.replace('Z', '+00:00'))
                    updated = datetime.fromisoformat(op.updated_at.replace('Z', '+00:00'))
                    completion_times.append((updated - created).total_seconds())
                except:
                    continue
            
            if completion_times:
                avg_completion_time = sum(completion_times) / len(completion_times)
        
        # Current active operations
        active_statuses = [
            OperationStatus.INITIATED.value,
            OperationStatus.IN_PROGRESS.value,
            OperationStatus.WAITING_FOR_APPROVAL.value,
            OperationStatus.APPROVED.value,
            OperationStatus.EXECUTING.value
        ]
        active_operations = [op for op in operations if op.status in active_statuses]
        
        return {
            'total_operations': total_operations,
            'status_breakdown': dict(status_counts),
            'type_breakdown': dict(type_counts),
            'success_rate': success_rate,
            'active_operations': len(active_operations),
            'avg_completion_time_seconds': avg_completion_time,
            'time_window_hours': hours_back
        }
    
    def get_operation_logs(self, operation_id: str, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get CloudWatch logs related to an operation"""
        try:
            # Define log groups to search
            log_groups = [
                f"/aws/lambda/{PROJECT_NAME}-{ENVIRONMENT}-file-operations",
                f"/aws/lambda/{PROJECT_NAME}-{ENVIRONMENT}-file-deletion-consumer",
                f"/aws/lambda/{PROJECT_NAME}-{ENVIRONMENT}-analytics-consumer",
                f"/aws/lambda/{PROJECT_NAME}-{ENVIRONMENT}-categorization-consumer",
                f"/aws/lambda/{PROJECT_NAME}-{ENVIRONMENT}-workflow-tracking-consumer"
            ]
            
            start_time = int((datetime.now() - timedelta(hours=hours_back)).timestamp() * 1000)
            all_events = []
            
            for log_group in log_groups:
                try:
                    # Check if log group exists
                    self.logs_client.describe_log_groups(logGroupNamePrefix=log_group)
                    
                    # Search for operation ID in logs
                    response = self.logs_client.filter_log_events(
                        logGroupName=log_group,
                        startTime=start_time,
                        filterPattern=f'"{operation_id}"'
                    )
                    
                    for event in response.get('events', []):
                        all_events.append({
                            'log_group': log_group,
                            'timestamp': event['timestamp'],
                            'message': event['message'],
                            'formatted_time': datetime.fromtimestamp(
                                event['timestamp'] / 1000
                            ).strftime('%Y-%m-%d %H:%M:%S')
                        })
                        
                except Exception as e:
                    logger.debug(f"Could not search log group {log_group}: {e}")
                    continue
            
            # Sort by timestamp
            all_events.sort(key=lambda x: x['timestamp'])
            return all_events
            
        except Exception as e:
            logger.error(f"Error getting operation logs: {e}")
            return []
    
    def format_operation_display(self, operation: OperationInfo) -> str:
        """Format operation for display"""
        # Status color coding
        status_colors = {
            OperationStatus.COMPLETED.value: Colors.GREEN,
            OperationStatus.FAILED.value: Colors.RED,
            OperationStatus.CANCELLED.value: Colors.YELLOW,
            OperationStatus.DENIED.value: Colors.RED,
            OperationStatus.EXECUTING.value: Colors.BLUE,
            OperationStatus.WAITING_FOR_APPROVAL.value: Colors.YELLOW,
            OperationStatus.APPROVED.value: Colors.CYAN,
            OperationStatus.INITIATED.value: Colors.MAGENTA,
            OperationStatus.IN_PROGRESS.value: Colors.BLUE
        }
        
        color = status_colors.get(operation.status, Colors.WHITE)
        
        # Format progress bar
        progress_width = 20
        filled = int(operation.progress_percentage / 100 * progress_width)
        progress_bar = '█' * filled + '░' * (progress_width - filled)
        
        # Format time
        try:
            created_time = datetime.fromisoformat(operation.created_at.replace('Z', '+00:00'))
            time_ago = datetime.now(timezone.utc) - created_time
            if time_ago.days > 0:
                time_str = f"{time_ago.days}d ago"
            elif time_ago.seconds > 3600:
                time_str = f"{time_ago.seconds // 3600}h ago"
            else:
                time_str = f"{time_ago.seconds // 60}m ago"
        except:
            time_str = "unknown"
        
        result = f"{color}{operation.operation_id[:20]:<20}{Colors.END} "
        result += f"{operation.operation_type:<15} "
        result += f"{color}{operation.status:<20}{Colors.END} "
        result += f"[{progress_bar}] {operation.progress_percentage:3d}% "
        result += f"({operation.current_step}/{operation.total_steps}) "
        result += f"{time_str}"
        
        if operation.error_message:
            result += f"\n    {Colors.RED}Error: {operation.error_message}{Colors.END}"
        
        if operation.step_description:
            result += f"\n    Step: {operation.step_description}"
        
        return result
    
    def print_system_health(self, health_data: Dict[str, Any]):
        """Print formatted system health report"""
        print(f"\n{Colors.BOLD}🏥 System Health Report{Colors.END}")
        print(f"Time Window: Last {health_data['time_window_hours']} hours")
        print("=" * 60)
        
        # Overall statistics
        print(f"\n{Colors.BOLD}📊 Overall Statistics{Colors.END}")
        print(f"Total Operations: {health_data['total_operations']}")
        print(f"Active Operations: {health_data['active_operations']}")
        print(f"Success Rate: {Colors.GREEN}{health_data['success_rate']:.1f}%{Colors.END}")
        
        if health_data['avg_completion_time_seconds']:
            avg_time = health_data['avg_completion_time_seconds']
            if avg_time < 60:
                time_str = f"{avg_time:.1f} seconds"
            elif avg_time < 3600:
                time_str = f"{avg_time/60:.1f} minutes"
            else:
                time_str = f"{avg_time/3600:.1f} hours"
            print(f"Average Completion Time: {time_str}")
        
        # Status breakdown
        print(f"\n{Colors.BOLD}📈 Status Breakdown{Colors.END}")
        status_colors = {
            'completed': Colors.GREEN,
            'failed': Colors.RED,
            'cancelled': Colors.YELLOW,
            'denied': Colors.RED,
            'executing': Colors.BLUE,
            'waiting_for_approval': Colors.YELLOW,
            'approved': Colors.CYAN,
            'initiated': Colors.MAGENTA,
            'in_progress': Colors.BLUE
        }
        
        for status, count in health_data['status_breakdown'].items():
            color = status_colors.get(status, Colors.WHITE)
            percentage = (count / health_data['total_operations'] * 100) if health_data['total_operations'] > 0 else 0
            print(f"  {color}{status.replace('_', ' ').title():<20}{Colors.END}: {count:3d} ({percentage:5.1f}%)")
        
        # Operation type breakdown
        print(f"\n{Colors.BOLD}🔧 Operation Type Breakdown{Colors.END}")
        for op_type, count in health_data['type_breakdown'].items():
            percentage = (count / health_data['total_operations'] * 100) if health_data['total_operations'] > 0 else 0
            print(f"  {op_type.replace('_', ' ').title():<20}: {count:3d} ({percentage:5.1f}%)")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Workflow Diagnostics CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check operation status')
    status_parser.add_argument('operation_id', help='Operation ID to check')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List operations')
    list_parser.add_argument('--status', help='Filter by status')
    list_parser.add_argument('--type', help='Filter by operation type')
    list_parser.add_argument('--hours', type=int, default=24, help='Hours back to search (default: 24)')
    list_parser.add_argument('--limit', type=int, default=50, help='Maximum results (default: 50)')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Real-time monitoring')
    monitor_parser.add_argument('operation_id', nargs='?', help='Specific operation ID to monitor')
    monitor_parser.add_argument('--interval', type=int, default=5, help='Refresh interval in seconds (default: 5)')
    
    # Health command
    health_parser = subparsers.add_parser('health', help='System health analysis')
    health_parser.add_argument('--hours', type=int, default=24, help='Hours back to analyze (default: 24)')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Show operation logs')
    logs_parser.add_argument('operation_id', help='Operation ID to get logs for')
    logs_parser.add_argument('--hours', type=int, default=24, help='Hours back to search (default: 24)')
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Quick system summary')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize diagnostics tool
    try:
        diagnostics = WorkflowDiagnostics()
    except Exception as e:
        print(f"{Colors.RED}Failed to initialize diagnostics tool: {e}{Colors.END}")
        sys.exit(1)
    
    # Execute commands
    if args.command == 'status':
        operation = diagnostics.get_operation_status(args.operation_id)
        if operation:
            print(f"\n{Colors.BOLD}📋 Operation Status{Colors.END}")
            print("=" * 60)
            print(diagnostics.format_operation_display(operation))
            
            if operation.context:
                print(f"\n{Colors.BOLD}📝 Context{Colors.END}")
                for key, value in operation.context.items():
                    print(f"  {key}: {value}")
        else:
            print(f"{Colors.RED}Operation {args.operation_id} not found{Colors.END}")
    
    elif args.command == 'list':
        operations = diagnostics.list_operations(
            status_filter=args.status,
            operation_type_filter=args.type,
            hours_back=args.hours,
            limit=args.limit
        )
        
        print(f"\n{Colors.BOLD}📋 Operations List{Colors.END}")
        print(f"Showing {len(operations)} operations from last {args.hours} hours")
        print("=" * 120)
        print(f"{'Operation ID':<20} {'Type':<15} {'Status':<20} {'Progress':<25} {'Steps':<8} {'Age'}")
        print("-" * 120)
        
        for operation in operations:
            print(diagnostics.format_operation_display(operation))
    
    elif args.command == 'monitor':
        print(f"{Colors.BOLD}🔍 Real-time Operation Monitoring{Colors.END}")
        print(f"Refresh interval: {args.interval} seconds")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        try:
            while True:
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                print(f"{Colors.BOLD}🔍 Real-time Operation Monitoring{Colors.END}")
                print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 60)
                
                if args.operation_id:
                    # Monitor specific operation
                    operation = diagnostics.get_operation_status(args.operation_id)
                    if operation:
                        print(diagnostics.format_operation_display(operation))
                    else:
                        print(f"{Colors.RED}Operation {args.operation_id} not found{Colors.END}")
                else:
                    # Monitor all active operations
                    active_operations = diagnostics.list_operations(hours_back=1, limit=20)
                    active_operations = [op for op in active_operations if op.status in [
                        OperationStatus.INITIATED.value,
                        OperationStatus.IN_PROGRESS.value,
                        OperationStatus.WAITING_FOR_APPROVAL.value,
                        OperationStatus.APPROVED.value,
                        OperationStatus.EXECUTING.value
                    ]]
                    
                    if active_operations:
                        for operation in active_operations:
                            print(diagnostics.format_operation_display(operation))
                    else:
                        print("No active operations found")
                
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitoring stopped{Colors.END}")
    
    elif args.command == 'health':
        health_data = diagnostics.get_system_health(args.hours)
        diagnostics.print_system_health(health_data)
    
    elif args.command == 'logs':
        logs = diagnostics.get_operation_logs(args.operation_id, args.hours)
        
        print(f"\n{Colors.BOLD}📜 Operation Logs{Colors.END}")
        print(f"Operation ID: {args.operation_id}")
        print(f"Time window: Last {args.hours} hours")
        print("=" * 80)
        
        if logs:
            for log_entry in logs:
                log_group_short = log_entry['log_group'].split('/')[-1]
                print(f"{Colors.CYAN}[{log_entry['formatted_time']}]{Colors.END} "
                      f"{Colors.YELLOW}{log_group_short}{Colors.END}")
                print(f"  {log_entry['message']}")
                print()
        else:
            print("No logs found for this operation")
    
    elif args.command == 'summary':
        # Quick summary combining health and active operations
        health_data = diagnostics.get_system_health(24)
        active_operations = diagnostics.list_operations(hours_back=1, limit=10)
        active_operations = [op for op in active_operations if op.status in [
            OperationStatus.INITIATED.value,
            OperationStatus.IN_PROGRESS.value,
            OperationStatus.WAITING_FOR_APPROVAL.value,
            OperationStatus.APPROVED.value,
            OperationStatus.EXECUTING.value
        ]]
        
        print(f"\n{Colors.BOLD}⚡ Quick System Summary{Colors.END}")
        print("=" * 50)
        print(f"Success Rate (24h): {Colors.GREEN}{health_data['success_rate']:.1f}%{Colors.END}")
        print(f"Total Operations (24h): {health_data['total_operations']}")
        print(f"Currently Active: {len(active_operations)}")
        
        if active_operations:
            print(f"\n{Colors.BOLD}🔄 Active Operations{Colors.END}")
            for operation in active_operations[:5]:  # Show top 5
                print(f"  {operation.operation_id[:15]}... {operation.status} ({operation.progress_percentage}%)")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Debug script to diagnose FZIP restore issues.
This script helps identify why a restore added 0 objects.
"""
import json
import sys
import os
import zipfile
import io
from typing import Dict, Any, Optional

# Set up environment variables for AWS DynamoDB access
# Use eu-west-2 to match the user's AWS configuration
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-west-2')
os.environ.setdefault('DYNAMODB_ENDPOINT', '')  # Use default AWS endpoint

# Set up DynamoDB table names (assuming dev environment)
os.environ.setdefault('ENVIRONMENT', 'dev')
os.environ.setdefault('ACCOUNTS_TABLE', 'housef3-dev-accounts')
os.environ.setdefault('FILES_TABLE', 'housef3-dev-transaction-files')
os.environ.setdefault('TRANSACTIONS_TABLE', 'housef3-dev-transactions')
os.environ.setdefault('FILE_MAPS_TABLE', 'housef3-dev-file-maps')
os.environ.setdefault('CATEGORIES_TABLE_NAME', 'housef3-dev-categories')
os.environ.setdefault('FZIP_JOBS_TABLE', 'housef3-dev-fzip-jobs')
os.environ.setdefault('ANALYTICS_TABLE_NAME', 'housef3-dev-analytics-data')

# Add the src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import boto3
    from utils.db_utils import list_user_fzip_jobs, get_fzip_job, initialize_tables
    from models.fzip import FZIPType, FZIPStatus
    from utils.s3_dao import get_object_content
    
    # Force re-initialization of tables with correct region
    initialize_tables()
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the backend directory with venv activated")
    sys.exit(1)

def test_dynamodb_connection():
    """Test DynamoDB connection and table access."""
    try:
        print("Testing DynamoDB connection...")
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        
        # Test access to FZIP jobs table
        table_name = 'housef3-dev-fzip-jobs'
        table = dynamodb.Table(table_name)
        print(f"Successfully connected to table: {table_name}")
        
        # Try a simple query (this should work even if no data)
        response = table.scan(Limit=5)
        count = response.get('Count', 0)
        print(f"Table scan successful, found {count} items")
        
        # Show actual jobs in the table
        if count > 0:
            print("\nJobs in table:")
            for item in response.get('Items', []):
                print(f"  Job ID: {item.get('jobId')} | User: {item.get('userId')} | Status: {item.get('status')}")
        
        return True
        
    except Exception as e:
        print(f"DynamoDB connection test failed: {e}")
        return False

def find_job_owner(job_id: str):
    """Find who owns a specific job ID."""
    try:
        print(f"Looking up job {job_id} directly...")
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        table = dynamodb.Table('housef3-dev-fzip-jobs')
        
        response = table.get_item(Key={'jobId': job_id})
        
        if 'Item' in response:
            item = response['Item']
            print(f"Job found!")
            print(f"  Job ID: {item.get('jobId')}")
            print(f"  User ID: {item.get('userId')}")
            print(f"  Status: {item.get('status')}")
            print(f"  Job Type: {item.get('jobType')}")
            print(f"  Progress: {item.get('progress', 0)}%")
            print(f"  Current Phase: {item.get('currentPhase', 'N/A')}")
            print(f"  S3 Key: {item.get('s3Key', 'N/A')}")
            
            return item.get('userId')
        else:
            print(f"Job {job_id} not found in database")
            return None
            
    except Exception as e:
        print(f"Error looking up job: {e}")
        return None

def analyze_fzip_package(s3_key: str, bucket: str) -> Dict[str, Any]:
    """Download and analyze the contents of an FZIP package."""
    try:
        print(f"Downloading package from S3: {s3_key}")
        package_data = get_object_content(s3_key, bucket)
        
        if not package_data:
            return {"error": "Could not download package from S3"}
        
        print(f"Package size: {len(package_data)} bytes")
        
        # Parse ZIP file
        with zipfile.ZipFile(io.BytesIO(package_data), 'r') as zipf:
            file_list = zipf.namelist()
            print(f"Files in package: {file_list}")
            
            analysis = {
                "files": file_list,
                "data_analysis": {}
            }
            
            # Read manifest
            if 'manifest.json' in file_list:
                manifest_data = zipf.read('manifest.json')
                manifest = json.loads(manifest_data.decode('utf-8'))
                analysis["manifest"] = manifest
                print(f"Manifest data summary: {manifest.get('dataSummary', {})}")
            
            # Analyze data files (handle both compressed and uncompressed)
            for entity_type in ['accounts', 'transactions', 'categories', 'file_maps', 'transaction_files']:
                compressed_path = f'data/{entity_type}.json.gz'
                uncompressed_path = f'data/{entity_type}.json'
                
                entities = []
                if compressed_path in file_list:
                    entity_data = zipf.read(compressed_path)
                    import gzip
                    entities = json.loads(gzip.decompress(entity_data).decode('utf-8'))
                    print(f"{entity_type}: {len(entities)} items (compressed)")
                elif uncompressed_path in file_list:
                    entity_data = zipf.read(uncompressed_path)
                    entities = json.loads(entity_data.decode('utf-8'))
                    print(f"{entity_type}: {len(entities)} items (uncompressed)")
                else:
                    analysis["data_analysis"][entity_type] = {"count": 0, "missing": True}
                    print(f"{entity_type}: file missing")
                    continue
                
                analysis["data_analysis"][entity_type] = {
                    "count": len(entities),
                    "sample": entities[:2] if entities else []  # First 2 items
                }
            
            return analysis
            
    except Exception as e:
        return {"error": f"Failed to analyze package: {str(e)}"}

def get_recent_restore_jobs(user_id: str, limit: int = 5) -> list:
    """Get recent restore jobs for a user."""
    try:
        jobs, _ = list_user_fzip_jobs(user_id, FZIPType.RESTORE.value, limit)
        return jobs
    except Exception as e:
        print(f"Error getting restore jobs: {e}")
        return []

def analyze_restore_job(job_id: str, user_id: str):
    """Analyze a specific restore job."""
    try:
        # First, check if the job exists and find its actual owner
        actual_user_id = find_job_owner(job_id)
        if not actual_user_id:
            return
            
        if actual_user_id != user_id:
            print(f"\nNote: Job is owned by '{actual_user_id}', but you provided '{user_id}'")
            print(f"Using the actual owner '{actual_user_id}' for analysis...")
            user_id = actual_user_id
        
        print(f"Attempting to fetch job using proper user ID...")
        job = get_fzip_job(job_id, user_id)
        if not job:
            print(f"Unexpected: Job {job_id} found directly but get_fzip_job failed")
            return
        
        print(f"\n=== Restore Job Analysis ===")
        print(f"Job ID: {job.job_id}")
        print(f"Status: {job.status}")
        print(f"Progress: {job.progress}%")
        print(f"Current Phase: {job.current_phase}")
        print(f"S3 Key: {job.s3_key}")
        print(f"Error: {job.error}")
        
        print(f"\nValidation Results:")
        for key, value in (job.validation_results or {}).items():
            print(f"  {key}: {value}")
        
        print(f"\nRestore Results:")
        for key, value in (job.restore_results or {}).items():
            print(f"  {key}: {value}")
        
        # If we have an S3 key, analyze the package
        if job.s3_key:
            restore_bucket = os.environ.get('FZIP_RESTORE_PACKAGES_BUCKET', 
                                          os.environ.get('FZIP_PACKAGES_BUCKET', 'housef3-dev-fzip-packages'))
            print(f"\n=== Package Analysis ===")
            package_analysis = analyze_fzip_package(job.s3_key, restore_bucket)
            
            if "error" in package_analysis:
                print(f"Package analysis error: {package_analysis['error']}")
            else:
                print(f"Package contains:")
                for entity_type, data in package_analysis.get("data_analysis", {}).items():
                    if data.get("missing"):
                        print(f"  {entity_type}: MISSING FILE")
                    else:
                        count = data.get("count", 0)
                        print(f"  {entity_type}: {count} items")
                        if count > 0 and entity_type == "accounts":
                            print(f"    Sample account: {data.get('sample', [{}])[0].get('accountName', 'N/A')}")
    
    except Exception as e:
        print(f"Error analyzing job: {e}")
        print("\nTroubleshooting:")
        print("1. Check AWS credentials: aws configure list")
        print("2. Verify DynamoDB table access")
        print("3. Ensure correct AWS region is set")
        print("4. Check if running in correct environment (dev/prod)")
        
        # Try to provide more specific error info
        if "'NoneType' object has no attribute 'get_item'" in str(e):
            print("\nSpecific issue: DynamoDB client is None")
            print("This usually means AWS credentials or region are not configured properly")
            print("Try running: aws configure list")
            print("Or check environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION")

def main():
    """Main diagnostic function."""
    # Default job ID to analyze (the actual restore job that exists)
    DEFAULT_JOB_ID = "6c0c6bbf-095e-45dc-94fc-378582f55779"
    
    # Test DynamoDB connection first
    if not test_dynamodb_connection():
        print("Cannot proceed without DynamoDB access")
        return
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python debug_restore_issue.py <user_id> [job_id]")
        print("  python debug_restore_issue.py list <user_id>")
        print("  python debug_restore_issue.py analyze  # Uses default job ID")
        print("\nExamples:")
        print("  python debug_restore_issue.py your-user-id")
        print("  python debug_restore_issue.py your-user-id specific-job-id")
        print("  python debug_restore_issue.py list your-user-id")
        print(f"  python debug_restore_issue.py analyze  # Analyzes job {DEFAULT_JOB_ID}")
        sys.exit(1)
    
    if sys.argv[1] == "analyze":
        # Analyze the default job ID - we need to find which user owns it
        print(f"Analyzing default job ID: {DEFAULT_JOB_ID}")
        print("Note: You'll need to provide the user_id since we can't query by job_id alone")
        print("Usage: python debug_restore_issue.py <user_id> to analyze the default job")
        return
    
    if sys.argv[1] == "list":
        if len(sys.argv) < 3:
            print("Usage: python debug_restore_issue.py list <user_id>")
            sys.exit(1)
        
        user_id = sys.argv[2]
        print(f"Recent restore jobs for user {user_id}:")
        jobs = get_recent_restore_jobs(user_id)
        
        if not jobs:
            print("No restore jobs found")
            return
        
        for job in jobs:
            print(f"  {job.job_id}: {job.status.value} - {job.current_phase or 'No phase'}")
            if job.restore_results:
                accounts_created = job.restore_results.get('accounts', {}).get('created', 0)
                print(f"    Accounts created: {accounts_created}")
        
        return
    
    user_id = sys.argv[1]
    job_id = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_JOB_ID
    
    # Always analyze the specified or default job
    print(f"Analyzing job {job_id} for user {user_id}")
    analyze_restore_job(job_id, user_id)

if __name__ == "__main__":
    main()
